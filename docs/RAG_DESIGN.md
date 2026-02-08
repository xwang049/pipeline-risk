# RAG (Retrieval-Augmented Generation) Design

## Overview

RAG enhances LLM predictions by retrieving relevant historical context from a knowledge base before generating responses.

```
User Query → RAG Knowledge Base → Retrieved Context → LLM → Enhanced Answer
```

---

## Architecture Components

### 1. Vector Database (Chroma)

**Purpose**: Semantic search using embeddings

**What it stores**:
- Document embeddings (768-dim vectors)
- Document metadata (ticker, type, date)
- Original text content

**How it works**:
```python
# Query: "What were AAPL's debt issues in 2025?"
# 1. Convert query to embedding vector
# 2. Find similar vectors (cosine similarity)
# 3. Return most relevant documents
```

**Advantages**:
- Finds semantically similar content (even if keywords don't match)
- Fast similarity search
- No need for exact keyword matching

### 2. Metadata Database (SQLite)

**Purpose**: Structured queries and metadata

**Tables**:
1. **documents**: All ingested documents
2. **company_events**: Timeline of events (earnings, M&A, etc.)
3. **analysis_results**: Past risk predictions

**How it works**:
```sql
-- Example: Get all 10-K reports for AAPL before 2026-01-01
SELECT * FROM documents
WHERE ticker = 'AAPL'
  AND doc_type = '10-K'
  AND published_date < '2026-01-01'
ORDER BY published_date DESC
```

**Advantages**:
- Precise date filtering
- Structured queries
- Fast lookups

### 3. Embedding Model

**Default**: `all-MiniLM-L6-v2` (sentence-transformers)

**Specifications**:
- Size: 80MB
- Dimensions: 384
- Speed: ~3000 sentences/sec on CPU
- Quality: Good balance of speed and accuracy

**Alternatives**:
- `all-mpnet-base-v2`: Higher quality, slower
- `paraphrase-multilingual-MiniLM-L12-v2`: Multilingual support

---

## Data Flow

### Ingestion Pipeline

```
Source Data (JSON/CSV/Text)
    ↓
Parse & Clean
    ↓
Generate Embeddings
    ↓
Store in Vector DB (Chroma)
    ↓
Store Metadata in SQLite
```

### Query Pipeline

```
User Query
    ↓
    ├─→ Semantic Search (Vector DB)
    │       → Top K similar documents
    │
    └─→ Keyword Search (SQLite)
            → Filtered by date/type
    ↓
Merge Results
    ↓
Rank by Relevance
    ↓
Inject into LLM Prompt
    ↓
LLM Generates Answer with Context
```

---

## What Data to Store

### Priority 1: Core Financial Data
- ✅ Past risk analysis results
- ✅ Company events timeline
- ✅ Earnings summaries
- ✅ Debt restructuring history

### Priority 2: Historical News
- Archived news articles
- Sentiment trends over time
- Major announcements

### Priority 3: Financial Reports
- 10-K annual reports
- 10-Q quarterly reports
- Earnings call transcripts

### Priority 4: External Research
- Industry reports
- Analyst notes
- Research papers

---

## Usage Examples

### 1. Basic Setup

```bash
# Install dependencies
pip install chromadb sentence-transformers

# Initialize knowledge base
python scripts/ingest_to_kb.py --kb-path data/knowledge_base
```

### 2. Ingest Historical Results

```bash
# Ingest past analysis results
python scripts/ingest_to_kb.py \
    --results-dir data/results \
    --kb-path data/knowledge_base
```

### 3. Enable in Config

```yaml
# config/scenarios/credit_risk.yaml
data_sources:
  - type: rag_kb
    enabled: true
    config:
      db_path: data/knowledge_base
      embedding_model: all-MiniLM-L6-v2
      top_k: 5  # Return top 5 most relevant docs
```

### 4. Query Knowledge Base

```python
from src.data.sources.rag_knowledge_base import RAGKnowledgeBase

kb = RAGKnowledgeBase({
    'db_path': 'data/knowledge_base',
    'embedding_model': 'all-MiniLM-L6-v2',
})

# Semantic search
results = kb.fetch({
    'ticker': 'AAPL',
    'query_text': 'What were the debt issues in Q4 2025?',
    'top_k': 5
})

# Keyword search
results = kb.fetch({
    'ticker': 'AAPL',
    'doc_types': ['analysis', '10-K'],
    'top_k': 10
}, as_of_date=datetime(2026, 1, 1))
```

### 5. Programmatic Ingestion

```python
from src.data.sources.rag_knowledge_base import RAGKnowledgeBase
from datetime import datetime

kb = RAGKnowledgeBase({'db_path': 'data/knowledge_base'})

# Ingest a document
kb.ingest_document(
    ticker='AAPL',
    doc_type='earnings',
    content="""
    Apple reported Q4 2025 earnings with revenue of $90B,
    missing estimates. iPhone sales declined 5% YoY.
    Services revenue grew 12%.
    """,
    title='AAPL Q4 2025 Earnings',
    published_date=datetime(2025, 11, 1),
    metadata={'source': 'SEC', 'quarter': 'Q4'}
)
```

---

## Integration with LLM

### Enhanced Prompt with RAG Context

```python
# Before (no RAG):
prompt = f"""
Analyze credit risk for {ticker}.
Financial data: {financial_data}
"""

# After (with RAG):
# 1. Retrieve relevant context
context = kb.fetch({
    'ticker': ticker,
    'query_text': f'credit risk factors for {ticker}',
    'top_k': 3
})

# 2. Format context
context_text = "\n\n".join([
    f"[Historical Context {i+1}]\n{doc['content']}"
    for i, doc in enumerate(context)
])

# 3. Enhanced prompt
prompt = f"""
Analyze credit risk for {ticker}.

Historical Context:
{context_text}

Current Financial Data:
{financial_data}

Based on both historical patterns and current data, assess credit risk.
"""
```

### Benefits of RAG

✅ **Learn from Past Predictions**
- "Last time AAPL had similar debt ratios, risk was 75"
- Helps calibrate current predictions

✅ **Detect Patterns**
- "Company always faces issues after management changes"
- Historical patterns inform current analysis

✅ **Contextualize Events**
- "Q3 earnings miss led to credit downgrade in 2024"
- Understand likely outcomes

✅ **Ground in Facts**
- Reduces hallucination
- Anchors predictions in historical data

---

## Search Strategies

### 1. Semantic Search (Default)

**When to use**: Open-ended questions

**Example**:
```python
query = "What debt problems did AAPL face?"
# Finds: refinancing issues, covenant breaches, rating downgrades
```

**Pros**: Finds conceptually similar content
**Cons**: May miss exact keyword matches

### 2. Keyword Search

**When to use**: Specific document types or dates

**Example**:
```python
query = {
    'ticker': 'AAPL',
    'doc_types': ['10-K', '10-Q'],
    'as_of_date': '2025-12-31'
}
# Finds: All 10-K and 10-Q reports before 2025-12-31
```

**Pros**: Precise filtering
**Cons**: Misses semantic matches

### 3. Hybrid Search (Recommended)

**Combines both approaches**:
1. Semantic search for relevance
2. Keyword search for precision
3. Merge and rank results

```python
query = {
    'ticker': 'AAPL',
    'query_text': 'debt covenant violations',  # Semantic
    'doc_types': ['10-K', 'news'],              # Keyword
    'as_of_date': '2026-01-01',                 # Time filter
    'top_k': 5
}
```

---

## Time-Travel Support

RAG respects `as_of_date` for backtesting:

```python
# Simulate querying knowledge base as of 2025-06-01
# Only returns documents published before that date
results = kb.fetch(
    query={'ticker': 'AAPL', 'query_text': 'risk factors'},
    as_of_date=datetime(2025, 6, 1)
)
```

**Use case**: Validate if historical predictions would have used correct context.

---

## Performance Considerations

### Embedding Generation

**Speed**: ~3000 sentences/sec (CPU)
**Memory**: ~1GB for 10K documents

**Optimization**:
- Batch embed documents (100 at a time)
- Cache embeddings
- Use GPU if available

### Query Speed

**Semantic search**: ~10-50ms for 10K documents
**Keyword search**: ~1-5ms with indexes

**Optimization**:
- Create SQLite indexes on ticker, date
- Limit top_k (5-10 is usually enough)
- Use query cache

### Storage

**Vector DB**: ~4KB per document (embedding + metadata)
**Metadata DB**: ~1-2KB per document

**Example**: 10,000 documents = ~40MB vector + 10MB metadata = 50MB total

---

## Best Practices

### 1. Document Chunking

For long documents (10-K reports):
```python
# Split into chunks
chunks = split_document(content, chunk_size=500, overlap=50)

# Ingest each chunk
for i, chunk in enumerate(chunks):
    kb.ingest_document(
        ticker=ticker,
        doc_type='10-K',
        content=chunk,
        title=f'{ticker} 10-K 2025 (Part {i+1})',
        published_date=report_date,
        metadata={'chunk': i, 'total_chunks': len(chunks)}
    )
```

### 2. Regular Updates

```bash
# Daily ingestion of new results
0 9 * * * python scripts/ingest_to_kb.py --results-dir data/results
```

### 3. Metadata Enrichment

```python
metadata = {
    'source': 'SEC',
    'fiscal_year': 2025,
    'fiscal_quarter': 'Q4',
    'report_type': '10-K',
    'section': 'Risk Factors',
    'page_numbers': '45-67',
}
```

### 4. Query Relevance Threshold

```python
# Filter low-similarity results
results = [r for r in results if r['similarity'] > 0.7]
```

---

## Comparison: Local KB vs Web APIs

| Aspect | Local Knowledge Base | Web APIs |
|--------|---------------------|----------|
| **Speed** | Fast (local) | Slower (network) |
| **Cost** | Free | API costs |
| **Data** | Historical, curated | Real-time, comprehensive |
| **Control** | Full control | Limited |
| **Offline** | Works offline | Requires internet |
| **Update** | Manual ingestion | Always fresh |

**Recommendation**: Use both!
- RAG KB: Historical context, past predictions
- Web APIs: Latest news, current financials

---

## Future Enhancements

### Phase 1 (Current)
- [x] Chroma vector database
- [x] SQLite metadata database
- [x] Semantic + keyword search
- [x] Ingestion pipeline

### Phase 2 (Next)
- [ ] Automatic ingestion from results
- [ ] Query optimization
- [ ] Relevance ranking improvements
- [ ] Multi-language support

### Phase 3 (Advanced)
- [ ] Graph database for company relationships
- [ ] Temporal embeddings (time-aware)
- [ ] Federated search (KB + Web)
- [ ] Active learning (improve embeddings)

---

## Dependencies

```bash
# Core
pip install chromadb>=0.4.0
pip install sentence-transformers>=2.2.0

# Optional (for better performance)
pip install faiss-cpu  # Faster similarity search
pip install torch      # GPU acceleration
```

---

## Troubleshooting

### Issue: Chroma not found
```bash
pip install chromadb
```

### Issue: Slow embedding generation
```python
# Use GPU if available
model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
```

### Issue: Large memory usage
```python
# Process in batches
for batch in chunk_list(documents, batch_size=100):
    kb.ingest_documents(batch)
```

---

## Summary

**RAG = Better Credit Risk Predictions**

Traditional:
```
Current Data → LLM → Prediction
```

With RAG:
```
Current Data + Historical Context → LLM → Better Prediction
```

**Key Benefits**:
1. Learn from past predictions
2. Detect historical patterns
3. Ground predictions in facts
4. Reduce hallucination
5. Provide explainable context

**When to Use**:
- ✅ Historical analysis important
- ✅ Have past prediction data
- ✅ Need explainability
- ✅ Want to learn from mistakes
- ✅ Offline access needed

**When to Skip**:
- Real-time only (no historical data)
- Extremely simple predictions
- Just starting (no data yet)
