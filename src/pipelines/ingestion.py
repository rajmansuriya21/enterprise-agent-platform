"""
Document Ingestion Pipeline — End-to-end document processing.

Handles the full ingestion flow: parse → chunk → embed → store
Supports PDF, DOCX, TXT, MD, and CSV formats.
Uses idempotent upserts with deterministic chunk IDs.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.pipelines.chunking import ChunkingConfig, chunk_document_pages, chunk_text

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Document Parsers
# ──────────────────────────────────────────────────────────────
def _parse_file(file_path: str) -> dict[str, Any]:
    """Parse a file based on its extension."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf(file_path)
    elif suffix in (".docx", ".doc"):
        return _parse_docx(file_path)
    elif suffix in (".txt", ".md", ".csv"):
        return _parse_text(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def _parse_pdf(file_path: str) -> dict[str, Any]:
    """Parse PDF into pages."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({"page_number": i + 1, "content": text.strip()})

        return {
            "file_name": Path(file_path).name,
            "file_type": "pdf",
            "pages": pages,
            "total_pages": len(reader.pages),
        }
    except ImportError:
        raise ImportError("pypdf is required for PDF parsing: pip install pypdf")


def _parse_docx(file_path: str) -> dict[str, Any]:
    """Parse DOCX into text."""
    try:
        from docx import Document

        doc = Document(file_path)
        content = "\n\n".join(
            para.text for para in doc.paragraphs if para.text.strip()
        )

        return {
            "file_name": Path(file_path).name,
            "file_type": "docx",
            "content": content,
        }
    except ImportError:
        raise ImportError("python-docx is required for DOCX parsing: pip install python-docx")


def _parse_text(file_path: str) -> dict[str, Any]:
    """Parse plain text files."""
    content = Path(file_path).read_text(encoding="utf-8")
    return {
        "file_name": Path(file_path).name,
        "file_type": Path(file_path).suffix.lstrip("."),
        "content": content,
    }


# ──────────────────────────────────────────────────────────────
# Ingestion Pipeline
# ──────────────────────────────────────────────────────────────
def ingest_document(
    file_path: str,
    vector_store: Any,
    chunking_config: ChunkingConfig | None = None,
) -> dict[str, Any]:
    """Ingest a document into the vector store.

    Full pipeline: parse → chunk → embed → store

    Args:
        file_path: Path to the document file.
        vector_store: VectorStoreService instance.
        chunking_config: Optional chunking configuration.

    Returns:
        Dictionary with ingestion results.
    """
    logger.info(f"Starting ingestion for: {file_path}")
    start_time = datetime.now()

    # Step 1: Parse
    parsed = _parse_file(file_path)
    file_name = parsed["file_name"]
    file_type = parsed["file_type"]

    # Step 2: Chunk
    if "pages" in parsed:
        # PDF with pages
        chunks = chunk_document_pages(
            pages=parsed["pages"],
            source=file_name,
            config=chunking_config,
        )
    else:
        # Single content block
        metadata = {
            "source": file_name,
            "file_type": file_type,
            "ingested_at": start_time.isoformat(),
        }
        chunks = chunk_text(
            text=parsed["content"],
            metadata=metadata,
            config=chunking_config,
        )

    if not chunks:
        logger.warning(f"No chunks generated from {file_path}")
        return {"file_name": file_name, "chunk_count": 0, "status": "empty"}

    # Add ingestion timestamp to all chunks
    for chunk in chunks:
        chunk["ingested_at"] = start_time.isoformat()

    # Step 3: Embed + Store
    texts = [c["content"] for c in chunks]
    metadatas = [{k: v for k, v in c.items() if k != "content"} for c in chunks]

    # Ensure collection exists
    vector_store.ensure_collection()

    # Upsert (embeddings generated internally by vector store)
    count = vector_store.upsert_documents(texts=texts, metadatas=metadatas)

    elapsed = (datetime.now() - start_time).total_seconds()
    result = {
        "file_name": file_name,
        "file_type": file_type,
        "chunk_count": count,
        "total_chars": sum(len(t) for t in texts),
        "elapsed_seconds": round(elapsed, 2),
        "status": "success",
    }

    logger.info(
        f"Ingestion complete: {file_name} → {count} chunks in {elapsed:.1f}s"
    )
    return result


def ingest_directory(
    directory_path: str,
    vector_store: Any,
    extensions: list[str] | None = None,
    chunking_config: ChunkingConfig | None = None,
) -> list[dict[str, Any]]:
    """Ingest all supported documents from a directory.

    Args:
        directory_path: Path to the directory.
        vector_store: VectorStoreService instance.
        extensions: File extensions to process. Defaults to common doc types.
        chunking_config: Optional chunking configuration.

    Returns:
        List of ingestion results for each file.
    """
    if extensions is None:
        extensions = [".pdf", ".docx", ".txt", ".md", ".csv"]

    directory = Path(directory_path)
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory_path}")

    results = []
    for ext in extensions:
        for file_path in directory.glob(f"*{ext}"):
            try:
                result = ingest_document(
                    str(file_path), vector_store, chunking_config
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to ingest {file_path}: {e}")
                results.append({
                    "file_name": file_path.name,
                    "status": "error",
                    "error": str(e),
                })

    logger.info(
        f"Directory ingestion complete: {len(results)} files processed"
    )
    return results
