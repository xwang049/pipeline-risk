#!/usr/bin/env python3
"""
Knowledge Base Ingestion Tool

Ingests various data sources into the RAG knowledge base:
1. Historical analysis results
2. Saved news articles
3. Financial reports
4. Company events
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import argparse
from datetime import datetime
from loguru import logger

from src.data.sources.rag_knowledge_base import RAGKnowledgeBase


def ingest_analysis_results(kb: RAGKnowledgeBase, results_dir: Path):
    """
    Ingest historical analysis results from experiments/runs/

    This creates a historical record of predictions for comparison.
    """
    logger.info(f"Ingesting analysis results from {results_dir}")

    result_files = list(results_dir.glob("risk_prediction_*.json"))
    logger.info(f"Found {len(result_files)} result files")

    for filepath in result_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract date from filename or data
            generation_timestamp = data.get('generation_timestamp')
            if generation_timestamp:
                analysis_date = datetime.fromisoformat(generation_timestamp)
            else:
                # Parse from filename: risk_prediction_20260208_123456.json
                date_str = filepath.stem.split('_')[-2]
                analysis_date = datetime.strptime(date_str, '%Y%m%d')

            # Ingest each company's analysis
            for company in data.get('all_results', []):
                ticker = company.get('ticker')
                if not ticker:
                    continue

                # Create document content
                content = f"""
Company: {ticker}
Analysis Date: {analysis_date.date()}
Risk Score: {company.get('risk_score', 'N/A')}/100
Risk Level: {company.get('risk_level', 'Unknown')}

Key Risk Factors:
{chr(10).join(f"- {f}" for f in company.get('key_risk_factors', []))}

Reasoning:
{company.get('reasoning', 'N/A')}

Traditional Signals:
{json.dumps(company.get('traditional_signals', {}), indent=2)}
"""

                # Ingest to KB
                kb.ingest_document(
                    ticker=ticker,
                    doc_type='analysis',
                    content=content.strip(),
                    title=f"Risk Analysis - {ticker} - {analysis_date.date()}",
                    published_date=analysis_date,
                    metadata={
                        'source': 'pipeline_result',
                        'risk_score': company.get('risk_score'),
                        'risk_level': company.get('risk_level'),
                        'confidence': company.get('confidence_level'),
                    }
                )

                logger.debug(f"Ingested analysis for {ticker} from {analysis_date.date()}")

            logger.info(f"Processed {filepath.name}")

        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")

    logger.info("Analysis results ingestion complete")


def ingest_news_archive(kb: RAGKnowledgeBase, news_archive_dir: Path):
    """
    Ingest archived news articles

    Useful for building historical news corpus for semantic search.
    """
    logger.info(f"Ingesting news archive from {news_archive_dir}")

    # Assuming news archive is in JSON format
    news_files = list(news_archive_dir.glob("news_*.json"))
    logger.info(f"Found {len(news_files)} news archive files")

    for filepath in news_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                articles = json.load(f)

            for article in articles:
                ticker = article.get('ticker')
                if not ticker:
                    continue

                # Parse date
                pub_date_str = article.get('published_date')
                if pub_date_str:
                    try:
                        pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                        pub_date = pub_date.replace(tzinfo=None)
                    except:
                        pub_date = None
                else:
                    pub_date = None

                # Create content
                content = f"""
Title: {article.get('title', 'Untitled')}
Source: {article.get('source', 'Unknown')}
Date: {pub_date.date() if pub_date else 'Unknown'}

{article.get('description', '')}

Sentiment: {article.get('sentiment', 'Neutral')}
"""

                # Ingest
                kb.ingest_document(
                    ticker=ticker,
                    doc_type='news',
                    content=content.strip(),
                    title=article.get('title'),
                    published_date=pub_date,
                    metadata={
                        'source': article.get('source'),
                        'url': article.get('url'),
                        'sentiment': article.get('sentiment'),
                    }
                )

            logger.info(f"Processed {filepath.name}")

        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")

    logger.info("News archive ingestion complete")


def ingest_company_events(kb: RAGKnowledgeBase, events_file: Path):
    """
    Ingest company events from CSV/JSON

    Events: earnings announcements, management changes, M&A, etc.
    """
    logger.info(f"Ingesting company events from {events_file}")

    # This is a placeholder - implement based on your events file format
    logger.warning("Company events ingestion not yet implemented")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest data into RAG knowledge base"
    )
    parser.add_argument(
        '--results-dir',
        type=Path,
        default=Path('data/results'),
        help='Directory with analysis results'
    )
    parser.add_argument(
        '--news-archive',
        type=Path,
        help='Directory with archived news articles'
    )
    parser.add_argument(
        '--events-file',
        type=Path,
        help='File with company events'
    )
    parser.add_argument(
        '--kb-path',
        type=Path,
        default=Path('data/knowledge_base'),
        help='Knowledge base path'
    )

    args = parser.parse_args()

    # Initialize knowledge base
    logger.info("Initializing RAG knowledge base...")
    kb = RAGKnowledgeBase({
        'db_path': str(args.kb_path),
        'embedding_model': 'all-MiniLM-L6-v2',
        'collection_name': 'company_knowledge',
    })

    if not kb.validate():
        logger.error("Knowledge base validation failed. Check dependencies.")
        return 1

    # Ingest data sources
    if args.results_dir and args.results_dir.exists():
        ingest_analysis_results(kb, args.results_dir)

    if args.news_archive and args.news_archive.exists():
        ingest_news_archive(kb, args.news_archive)

    if args.events_file and args.events_file.exists():
        ingest_company_events(kb, args.events_file)

    logger.info("✓ Data ingestion complete!")

    # Print stats
    if kb.metadata_db:
        cursor = kb.metadata_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]
        logger.info(f"Total documents in knowledge base: {doc_count}")

    if kb.vector_db:
        logger.info(f"Total embeddings in vector DB: {kb.collection.count()}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
