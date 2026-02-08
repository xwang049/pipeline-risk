"""
RAG Knowledge Base with Vector Database

Implements semantic search using embeddings for company financial data.
Supports hybrid search (semantic + keyword) and time-travel queries.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from loguru import logger
import json

from ..base import DataSource, DataInstance


class RAGKnowledgeBase(DataSource):
    """
    RAG Knowledge Base using Chroma + SQLite

    Architecture:
    1. Vector DB (Chroma): Stores embeddings for semantic search
    2. Metadata DB (SQLite): Stores structured metadata
    3. Embedding Model: Converts text to vectors

    Data Types Stored:
    - Historical financial reports (10-K, 10-Q)
    - Past earnings call transcripts
    - Historical news articles (already processed)
    - Previous risk analysis results
    - Industry research reports
    - Company events timeline
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        self.db_path = Path(config.get('db_path', 'data/knowledge_base'))
        self.db_path.mkdir(parents=True, exist_ok=True)

        self.embedding_model = config.get('embedding_model', 'all-MiniLM-L6-v2')
        self.collection_name = config.get('collection_name', 'company_knowledge')
        self.top_k = config.get('top_k', 5)  # Top K results to return

        # Initialize databases
        self.vector_db = None
        self.metadata_db = None
        self._init_databases()

    def _init_databases(self):
        """Initialize vector database (Chroma) and metadata database (SQLite)"""
        try:
            # Initialize Chroma vector database
            import chromadb
            from chromadb.config import Settings

            self.vector_db = chromadb.PersistentClient(
                path=str(self.db_path / 'chroma'),
                settings=Settings(anonymized_telemetry=False)
            )

            # Get or create collection
            self.collection = self.vector_db.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Company financial knowledge base"}
            )

            logger.info(f"Initialized Chroma vector DB: {self.collection.count()} documents")

        except ImportError:
            logger.warning(
                "chromadb not installed. Install with: pip install chromadb\n"
                "RAG features will be limited."
            )
            self.vector_db = None

        # Initialize SQLite for metadata
        try:
            import sqlite3

            db_file = self.db_path / 'metadata.db'
            self.metadata_db = sqlite3.connect(str(db_file))

            # Create tables
            self._create_tables()

            logger.info(f"Initialized SQLite metadata DB: {db_file}")

        except Exception as e:
            logger.error(f"Failed to initialize SQLite: {e}")
            self.metadata_db = None

    def _create_tables(self):
        """Create database tables for metadata"""
        cursor = self.metadata_db.cursor()

        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                title TEXT,
                content TEXT,
                published_date DATE,
                ingestion_date DATE NOT NULL,
                source TEXT,
                metadata TEXT
            )
        """)

        # Company events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_date DATE NOT NULL,
                description TEXT,
                impact TEXT,
                metadata TEXT
            )
        """)

        # Analysis results table (store past predictions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                analysis_date DATE NOT NULL,
                risk_score REAL,
                risk_level TEXT,
                key_factors TEXT,
                full_analysis TEXT,
                model_version TEXT
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON documents(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON documents(published_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_ticker ON company_events(ticker)")

        self.metadata_db.commit()

    def fetch(
        self,
        query: Dict[str, Any],
        as_of_date: Optional[datetime] = None
    ) -> List[DataInstance]:
        """
        Fetch relevant information using RAG

        Query Types:
        1. Semantic search: query_text (finds similar content)
        2. Keyword search: ticker + doc_type
        3. Hybrid: combines both

        Args:
            query: Query parameters
                - ticker: Company ticker (required)
                - query_text: Text query for semantic search (optional)
                - doc_types: List of document types to filter (optional)
                - top_k: Number of results (optional)
            as_of_date: Only return documents before this date

        Returns:
            List of DataInstance with relevant documents
        """
        ticker = query.get('ticker')
        if not ticker:
            raise ValueError("Query must contain 'ticker' key")

        query_text = query.get('query_text')
        doc_types = query.get('doc_types', ['all'])
        top_k = query.get('top_k', self.top_k)

        # Check cache
        cache_key = self._build_cache_key(ticker, query_text, as_of_date)
        if cached := self._get_from_cache(cache_key):
            logger.debug(f"Cache hit for {ticker} (rag_kb)")
            return cached

        logger.info(f"Querying RAG knowledge base for {ticker}")

        try:
            results = {}

            # 1. Semantic search (if query_text provided)
            if query_text and self.vector_db:
                semantic_results = self._semantic_search(
                    ticker, query_text, top_k, as_of_date
                )
                results['semantic_search'] = semantic_results
                logger.debug(f"Semantic search found {len(semantic_results)} results")

            # 2. Keyword search in metadata DB
            if self.metadata_db:
                keyword_results = self._keyword_search(
                    ticker, doc_types, top_k, as_of_date
                )
                results['keyword_search'] = keyword_results
                logger.debug(f"Keyword search found {len(keyword_results)} results")

                # 3. Get historical events
                events = self._get_company_events(ticker, as_of_date)
                results['events'] = events

                # 4. Get past analysis results
                past_analyses = self._get_past_analyses(ticker, as_of_date)
                results['past_analyses'] = past_analyses

            # Create data instance
            instance = DataInstance(
                id=f"{ticker}_rag_{datetime.now().strftime('%Y%m%d')}",
                data={
                    'ticker': ticker,
                    'query': query_text,
                    'results': results,
                    'result_count': sum(
                        len(v) if isinstance(v, list) else 0
                        for v in results.values()
                    ),
                },
                metadata={
                    'ticker': ticker,
                    'as_of_date': as_of_date.isoformat() if as_of_date else None,
                    'data_type': 'rag_knowledge',
                    'query_type': 'semantic+keyword' if query_text else 'keyword',
                },
                timestamp=datetime.now(),
                source=self.source_type
            )

            result = [instance]

            # Cache the result
            self._set_to_cache(cache_key, result)

            logger.info(
                f"RAG query completed for {ticker}: "
                f"{instance.data['result_count']} total results"
            )
            return result

        except Exception as e:
            logger.error(f"Error querying RAG knowledge base for {ticker}: {e}")
            return []

    def _semantic_search(
        self,
        ticker: str,
        query_text: str,
        top_k: int,
        as_of_date: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """
        Semantic search using vector embeddings

        Uses cosine similarity to find most relevant documents.
        """
        try:
            # Build filter
            where = {"ticker": ticker}

            # Time filter if as_of_date specified
            if as_of_date:
                where["published_date"] = {"$lte": as_of_date.isoformat()}

            # Query vector database
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=where,
                include=['documents', 'metadatas', 'distances']
            )

            # Format results
            formatted = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    formatted.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i],
                        'similarity': 1 - results['distances'][0][i],  # Convert distance to similarity
                    })

            return formatted

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []

    def _keyword_search(
        self,
        ticker: str,
        doc_types: List[str],
        top_k: int,
        as_of_date: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """
        Keyword-based search in metadata database
        """
        if not self.metadata_db:
            return []

        try:
            cursor = self.metadata_db.cursor()

            # Build query
            sql = """
                SELECT id, ticker, doc_type, title, content,
                       published_date, source, metadata
                FROM documents
                WHERE ticker = ?
            """
            params = [ticker]

            # Filter by doc types
            if doc_types and 'all' not in doc_types:
                placeholders = ','.join('?' * len(doc_types))
                sql += f" AND doc_type IN ({placeholders})"
                params.extend(doc_types)

            # Filter by date
            if as_of_date:
                sql += " AND published_date <= ?"
                params.append(as_of_date.isoformat())

            sql += " ORDER BY published_date DESC LIMIT ?"
            params.append(top_k)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # Format results
            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'ticker': row[1],
                    'doc_type': row[2],
                    'title': row[3],
                    'content': row[4],
                    'published_date': row[5],
                    'source': row[6],
                    'metadata': json.loads(row[7]) if row[7] else {},
                })

            return results

        except Exception as e:
            logger.error(f"Keyword search error: {e}")
            return []

    def _get_company_events(
        self,
        ticker: str,
        as_of_date: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Get historical company events"""
        if not self.metadata_db:
            return []

        try:
            cursor = self.metadata_db.cursor()

            sql = """
                SELECT event_type, event_date, description, impact, metadata
                FROM company_events
                WHERE ticker = ?
            """
            params = [ticker]

            if as_of_date:
                sql += " AND event_date <= ?"
                params.append(as_of_date.isoformat())

            sql += " ORDER BY event_date DESC LIMIT 20"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            events = []
            for row in rows:
                events.append({
                    'event_type': row[0],
                    'event_date': row[1],
                    'description': row[2],
                    'impact': row[3],
                    'metadata': json.loads(row[4]) if row[4] else {},
                })

            return events

        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return []

    def _get_past_analyses(
        self,
        ticker: str,
        as_of_date: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Get past risk analysis results"""
        if not self.metadata_db:
            return []

        try:
            cursor = self.metadata_db.cursor()

            sql = """
                SELECT analysis_date, risk_score, risk_level,
                       key_factors, model_version
                FROM analysis_results
                WHERE ticker = ?
            """
            params = [ticker]

            if as_of_date:
                sql += " AND analysis_date <= ?"
                params.append(as_of_date.isoformat())

            sql += " ORDER BY analysis_date DESC LIMIT 10"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            analyses = []
            for row in rows:
                analyses.append({
                    'analysis_date': row[0],
                    'risk_score': row[1],
                    'risk_level': row[2],
                    'key_factors': json.loads(row[3]) if row[3] else [],
                    'model_version': row[4],
                })

            return analyses

        except Exception as e:
            logger.error(f"Error fetching past analyses: {e}")
            return []

    def ingest_document(
        self,
        ticker: str,
        doc_type: str,
        content: str,
        title: str = None,
        published_date: datetime = None,
        metadata: Dict[str, Any] = None
    ):
        """
        Ingest a new document into the knowledge base

        This method adds documents to both vector DB (for semantic search)
        and metadata DB (for structured queries).

        Args:
            ticker: Company ticker
            doc_type: Document type (earnings, 10-K, 10-Q, news, analysis, etc.)
            content: Document text content
            title: Document title
            published_date: When document was published
            metadata: Additional metadata
        """
        try:
            # Generate document ID
            doc_id = f"{ticker}_{doc_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Add to vector database
            if self.vector_db:
                self.collection.add(
                    documents=[content],
                    ids=[doc_id],
                    metadatas=[{
                        'ticker': ticker,
                        'doc_type': doc_type,
                        'title': title or '',
                        'published_date': published_date.isoformat() if published_date else '',
                        **(metadata or {})
                    }]
                )

            # Add to metadata database
            if self.metadata_db:
                cursor = self.metadata_db.cursor()
                cursor.execute("""
                    INSERT INTO documents
                    (id, ticker, doc_type, title, content, published_date,
                     ingestion_date, source, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    ticker,
                    doc_type,
                    title,
                    content[:1000],  # Store truncated content
                    published_date.isoformat() if published_date else None,
                    datetime.now().isoformat(),
                    metadata.get('source', 'manual') if metadata else 'manual',
                    json.dumps(metadata) if metadata else None
                ))
                self.metadata_db.commit()

            logger.info(f"Ingested document: {doc_id}")

        except Exception as e:
            logger.error(f"Error ingesting document: {e}")

    def validate(self) -> bool:
        """Validate RAG knowledge base"""
        # Check if Chroma is available
        chroma_ok = self.vector_db is not None

        # Check if SQLite is available
        sqlite_ok = self.metadata_db is not None

        if not chroma_ok:
            logger.warning("Chroma vector DB not available")

        if not sqlite_ok:
            logger.warning("SQLite metadata DB not available")

        # At least one should be available
        return chroma_ok or sqlite_ok

    @property
    def source_type(self) -> str:
        return "knowledge_base:rag"

    def _build_cache_key(
        self,
        ticker: str,
        query_text: Optional[str],
        as_of_date: Optional[datetime]
    ) -> str:
        """Build cache key"""
        date_str = as_of_date.strftime('%Y%m%d') if as_of_date else 'current'
        query_hash = hash(query_text) if query_text else 'none'
        return f"{ticker}_{query_hash}_{date_str}"

    def __del__(self):
        """Cleanup"""
        if self.metadata_db:
            self.metadata_db.close()
