"""
Semantic Chunking — Intelligent document splitting strategies.

Implements configurable chunking with metadata preservation,
supporting recursive character splitting and section-aware chunking.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ChunkingConfig:
    """Configuration for chunking strategy."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] | None = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]


def chunk_text(
    text: str,
    metadata: dict[str, Any] | None = None,
    config: ChunkingConfig | None = None,
) -> list[dict[str, Any]]:
    """Split text into semantically meaningful chunks.

    Uses recursive character splitting with configurable parameters.
    Preserves metadata from the source document.

    Args:
        text: The text to chunk.
        metadata: Source metadata to attach to each chunk.
        config: Chunking configuration.

    Returns:
        List of chunk dictionaries with text and metadata.
    """
    if config is None:
        config = ChunkingConfig()

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=config.separators,
            length_function=len,
        )
        texts = splitter.split_text(text)
    except ImportError:
        # Fallback: simple chunking
        texts = _simple_chunk(text, config.chunk_size, config.chunk_overlap)

    chunks = []
    base_metadata = metadata or {}

    for i, chunk_text_content in enumerate(texts):
        chunk = {
            "content": chunk_text_content.strip(),
            "chunk_index": i,
            "chunk_total": len(texts),
            "char_count": len(chunk_text_content),
            **base_metadata,
        }
        chunks.append(chunk)

    logger.info(
        f"Split text into {len(chunks)} chunks "
        f"(size={config.chunk_size}, overlap={config.chunk_overlap})"
    )
    return chunks


def chunk_document_pages(
    pages: list[dict[str, Any]],
    source: str,
    config: ChunkingConfig | None = None,
) -> list[dict[str, Any]]:
    """Chunk a multi-page document (e.g., PDF pages).

    Preserves page number metadata for each chunk.

    Args:
        pages: List of page dicts with 'content' and 'page_number'.
        source: Source file name.
        config: Chunking configuration.

    Returns:
        List of chunk dictionaries.
    """
    all_chunks = []

    for page in pages:
        page_metadata = {
            "source": source,
            "page": page.get("page_number", 0),
            "file_type": "pdf",
        }
        page_chunks = chunk_text(
            text=page.get("content", ""),
            metadata=page_metadata,
            config=config,
        )
        all_chunks.extend(page_chunks)

    logger.info(f"Chunked {len(pages)} pages into {len(all_chunks)} chunks")
    return all_chunks


def _simple_chunk(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Simple fallback chunking when langchain-text-splitters is unavailable."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
        if start >= len(text):
            break
    return chunks
