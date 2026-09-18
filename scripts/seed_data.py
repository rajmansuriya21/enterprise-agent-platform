"""
Seed Data Script — Populate SQLite and Qdrant with sample data.

Usage:
    python -m scripts.seed_data
    # or
    make seed
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def seed_database() -> None:
    """Seed the SQLite database with sample business data."""
    from src.services.database import get_database_service

    db = get_database_service()
    sql_path = Path(__file__).resolve().parent.parent / "data" / "sample_db.sql"

    if not sql_path.exists():
        logger.error(f"SQL file not found: {sql_path}")
        return

    logger.info("📊 Seeding SQLite database...")
    sql_script = sql_path.read_text()
    db.execute_script(sql_script)

    # Verify
    tables = db.list_tables()
    logger.info(f"   Tables created: {', '.join(tables)}")
    for table in tables:
        count = db.row_count(table)
        logger.info(f"   {table}: {count} rows")

    logger.info("✅ Database seeded successfully!")


def seed_vector_store() -> None:
    """Seed the Qdrant vector store with sample documents."""
    from src.services.vector_store import get_vector_store
    from src.pipelines.ingestion import ingest_directory

    docs_dir = Path(__file__).resolve().parent.parent / "data" / "sample_docs"

    if not docs_dir.exists():
        logger.error(f"Sample docs directory not found: {docs_dir}")
        return

    logger.info("📚 Ingesting sample documents into Qdrant...")

    try:
        vector_store = get_vector_store()
        results = ingest_directory(str(docs_dir), vector_store)

        for result in results:
            status = result.get("status", "unknown")
            file_name = result.get("file_name", "unknown")
            chunks = result.get("chunk_count", 0)
            logger.info(f"   {file_name}: {chunks} chunks ({status})")

        logger.info("✅ Vector store seeded successfully!")
    except Exception as e:
        logger.warning(f"⚠️ Vector store seeding skipped: {e}")
        logger.info("   (Start Qdrant with: docker compose up qdrant)")


def main() -> None:
    """Run the full seeding process."""
    logger.info("🌱 Starting data seeding...")
    logger.info("=" * 50)

    seed_database()
    logger.info("")
    seed_vector_store()

    logger.info("")
    logger.info("=" * 50)
    logger.info("🎉 Seeding complete! The platform is ready for demo.")
    logger.info("")
    logger.info("Try these commands:")
    logger.info("  make api        → Start the FastAPI server")
    logger.info("  make streamlit  → Start the Streamlit dashboard")
    logger.info("  make dev        → Start both")


if __name__ == "__main__":
    main()
