"""
Document Routes — Upload, manage, and query documents.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────
class DocumentInfo(BaseModel):
    """Document metadata."""

    doc_id: str
    file_name: str
    file_type: str
    file_size: int
    chunk_count: int = 0
    status: str = "uploaded"


class IngestionResult(BaseModel):
    """Result of document ingestion."""

    doc_id: str
    file_name: str
    chunk_count: int
    total_chars: int
    elapsed_seconds: float
    status: str


# ──────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────
@router.post("/documents/upload", response_model=IngestionResult)
async def upload_document(file: UploadFile = File(...)) -> IngestionResult:
    """Upload and ingest a document into the knowledge base.

    Supported formats: PDF, DOCX, TXT, MD, CSV
    """
    settings = get_settings()

    # Validate file type
    if file.filename is None:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = Path(file.filename).suffix.lower()
    allowed = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv"}
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed: {', '.join(allowed)}",
        )

    # Save uploaded file
    doc_id = str(uuid.uuid4())[:8]
    upload_dir = settings.upload_dir
    file_path = upload_dir / f"{doc_id}_{file.filename}"

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"File saved: {file_path} ({len(content)} bytes)")

        # Ingest into vector store
        try:
            from src.pipelines.ingestion import ingest_document
            from src.services.vector_store import get_vector_store

            vector_store = get_vector_store()
            result = ingest_document(str(file_path), vector_store)

            return IngestionResult(
                doc_id=doc_id,
                file_name=file.filename,
                chunk_count=result.get("chunk_count", 0),
                total_chars=result.get("total_chars", 0),
                elapsed_seconds=result.get("elapsed_seconds", 0),
                status="ingested",
            )
        except Exception as e:
            logger.warning(f"Ingestion failed (file saved): {e}")
            return IngestionResult(
                doc_id=doc_id,
                file_name=file.filename,
                chunk_count=0,
                total_chars=len(content),
                elapsed_seconds=0,
                status=f"uploaded_but_not_ingested: {str(e)}",
            )

    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents() -> list[DocumentInfo]:
    """List all uploaded documents."""
    settings = get_settings()
    upload_dir = settings.upload_dir

    documents = []
    if upload_dir.exists():
        for file_path in upload_dir.iterdir():
            if file_path.is_file():
                doc_id = file_path.stem.split("_")[0] if "_" in file_path.stem else file_path.stem
                documents.append(
                    DocumentInfo(
                        doc_id=doc_id,
                        file_name=file_path.name,
                        file_type=file_path.suffix,
                        file_size=file_path.stat().st_size,
                        status="uploaded",
                    )
                )

    return documents


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str) -> dict[str, str]:
    """Delete a document and its vector embeddings."""
    settings = get_settings()
    upload_dir = settings.upload_dir

    # Find and delete the file
    deleted = False
    for file_path in upload_dir.iterdir():
        if file_path.name.startswith(doc_id):
            # Delete from vector store
            try:
                from src.services.vector_store import get_vector_store

                vector_store = get_vector_store()
                vector_store.delete_by_source(file_path.name)
            except Exception as e:
                logger.warning(f"Vector deletion failed: {e}")

            file_path.unlink()
            deleted = True
            break

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    return {"status": "deleted", "doc_id": doc_id}
