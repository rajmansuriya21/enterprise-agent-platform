"""
Document Tools — PDF/DOCX/image parsing and extraction tools.

Provides tools for parsing various document formats, extracting
tables and key-value pairs, and ingesting content into the vector store.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def create_doc_tools(vector_store: Any | None = None) -> list:
    """Create document extraction tools.

    Args:
        vector_store: VectorStoreService instance for ingestion.

    Returns:
        List of LangChain tool objects.
    """

    @tool
    def parse_pdf(file_path: str) -> str:
        """Parse a PDF file and extract its text content.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Extracted text content with page numbers.
        """
        try:
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            parts = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    parts.append(f"--- Page {i+1} ---\n{text.strip()[:1000]}")

            if not parts:
                return "PDF parsed but no text content found (may be a scanned document)."

            return (
                f"📄 PDF: {Path(file_path).name} ({len(reader.pages)} pages)\n\n"
                + "\n\n".join(parts[:10])
            )
        except ImportError:
            return "pypdf not installed. Run: pip install pypdf"
        except Exception as e:
            return f"PDF parsing error: {str(e)}"

    @tool
    def parse_docx(file_path: str) -> str:
        """Parse a DOCX file and extract its text content.

        Args:
            file_path: Path to the DOCX file.

        Returns:
            Extracted text content.
        """
        try:
            from docx import Document

            doc = Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

            return (
                f"📄 DOCX: {Path(file_path).name} ({len(paragraphs)} paragraphs, {len(doc.tables)} tables)\n\n"
                + "\n\n".join(paragraphs[:20])
            )
        except ImportError:
            return "python-docx not installed. Run: pip install python-docx"
        except Exception as e:
            return f"DOCX parsing error: {str(e)}"

    @tool
    def extract_tables(file_path: str) -> str:
        """Extract tables from a DOCX document as markdown tables.

        Args:
            file_path: Path to the DOCX file.

        Returns:
            Extracted tables in markdown format.
        """
        try:
            from docx import Document

            doc = Document(file_path)
            if not doc.tables:
                return "No tables found in the document."

            formatted = []
            for i, table in enumerate(doc.tables):
                rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
                if not rows:
                    continue

                headers = rows[0]
                header_row = "| " + " | ".join(headers) + " |"
                separator = "| " + " | ".join(["---"] * len(headers)) + " |"
                data_rows = ["| " + " | ".join(cells) + " |" for cells in rows[1:]]

                formatted.append(
                    f"Table {i+1}:\n" + header_row + "\n" + separator + "\n" + "\n".join(data_rows)
                )

            return "\n\n".join(formatted) or "Tables found but could not be formatted."
        except ImportError:
            return "python-docx not installed."
        except Exception as e:
            return f"Table extraction error: {str(e)}"

    @tool
    def extract_key_values(text: str) -> str:
        """Extract key-value pairs from document text using pattern matching.

        Args:
            text: The text to extract key-value pairs from.

        Returns:
            Extracted key-value pairs.
        """
        patterns = [
            r"^(.+?):\s*(.+)$",
            r"^(.+?)\s*=\s*(.+)$",
            r"^(.+?)\s*-\s*(.+)$",
        ]

        pairs = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    key, value = match.groups()
                    if len(key) < 50 and len(value) < 200:
                        pairs.append(f"  {key.strip()}: {value.strip()}")
                    break

        if not pairs:
            return "No key-value pairs found."

        return "Extracted Key-Value Pairs:\n" + "\n".join(pairs[:30])

    return [parse_pdf, parse_docx, extract_tables, extract_key_values]
