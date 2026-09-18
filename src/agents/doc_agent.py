"""
Document Extraction Sub-Agent — Parse, extract, and index documents.

Handles PDF, DOCX, and text document processing. Extracts key information,
tables, and key-value pairs using LLM. Triggers the ingestion pipeline to
add extracted content to the Qdrant vector store.
"""

from __future__ import annotations

import time
import logging
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import tool

from src.agents.state import AgentMetadata, AgentState
from src.config import get_settings
from src.utils.prompts import DOC_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Document Parsing Utilities
# ──────────────────────────────────────────────────────────────
def parse_pdf(file_path: str) -> dict[str, Any]:
    """Parse a PDF file and extract text content."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append({
                "page_number": i + 1,
                "content": text.strip(),
                "char_count": len(text),
            })

        return {
            "success": True,
            "file_name": Path(file_path).name,
            "total_pages": len(pages),
            "pages": pages,
            "total_chars": sum(p["char_count"] for p in pages),
        }
    except ImportError:
        return {"success": False, "error": "pypdf not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_docx(file_path: str) -> dict[str, Any]:
    """Parse a DOCX file and extract text content."""
    try:
        from docx import Document

        doc = Document(file_path)
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append({
                    "content": para.text.strip(),
                    "style": para.style.name if para.style else "Normal",
                })

        # Extract tables
        tables = []
        for i, table in enumerate(doc.tables):
            rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                rows.append(cells)
            tables.append({"table_index": i, "rows": rows})

        return {
            "success": True,
            "file_name": Path(file_path).name,
            "paragraphs": paragraphs,
            "tables": tables,
            "total_paragraphs": len(paragraphs),
            "total_tables": len(tables),
        }
    except ImportError:
        return {"success": False, "error": "python-docx not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_text(file_path: str) -> dict[str, Any]:
    """Parse a plain text or markdown file."""
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        return {
            "success": True,
            "file_name": Path(file_path).name,
            "content": content,
            "char_count": len(content),
            "line_count": content.count("\n") + 1,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Document Tools
# ──────────────────────────────────────────────────────────────
def create_doc_tools(vector_store: Any | None = None) -> list:
    """Create document extraction tools."""

    @tool
    def extract_document_content(file_path: str) -> str:
        """Extract text content from a document (PDF, DOCX, TXT, or MD).

        Args:
            file_path: Path to the document file.

        Returns:
            Extracted text content from the document.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            result = parse_pdf(file_path)
        elif suffix in (".docx", ".doc"):
            result = parse_docx(file_path)
        elif suffix in (".txt", ".md", ".csv"):
            result = parse_text(file_path)
        else:
            return f"Unsupported file type: {suffix}. Supported: .pdf, .docx, .txt, .md"

        if not result.get("success"):
            return f"Failed to parse document: {result.get('error', 'Unknown error')}"

        # Format extracted content
        if "pages" in result:
            # PDF
            content_parts = []
            for page in result["pages"][:10]:  # Limit to first 10 pages
                content_parts.append(
                    f"--- Page {page['page_number']} ---\n{page['content'][:1000]}"
                )
            summary = (
                f"📄 Document: {result['file_name']}\n"
                f"   Pages: {result['total_pages']}\n"
                f"   Total Characters: {result['total_chars']}\n\n"
                + "\n\n".join(content_parts)
            )
        elif "paragraphs" in result:
            # DOCX
            content_parts = [p["content"] for p in result["paragraphs"][:20]]
            summary = (
                f"📄 Document: {result['file_name']}\n"
                f"   Paragraphs: {result['total_paragraphs']}\n"
                f"   Tables: {result['total_tables']}\n\n"
                + "\n\n".join(content_parts)
            )
        else:
            # Text
            summary = (
                f"📄 Document: {result['file_name']}\n"
                f"   Characters: {result['char_count']}\n"
                f"   Lines: {result['line_count']}\n\n"
                + result.get("content", "")[:3000]
            )

        return summary

    @tool
    def extract_tables_from_document(file_path: str) -> str:
        """Extract tables from a DOCX document.

        Args:
            file_path: Path to the DOCX file.

        Returns:
            Extracted tables in markdown format.
        """
        result = parse_docx(file_path)
        if not result.get("success"):
            return f"Failed to extract tables: {result.get('error', 'Unknown error')}"

        tables = result.get("tables", [])
        if not tables:
            return "No tables found in the document."

        formatted = []
        for table in tables:
            rows = table["rows"]
            if not rows:
                continue

            # Create markdown table
            headers = rows[0]
            header_row = "| " + " | ".join(headers) + " |"
            separator = "| " + " | ".join(["---"] * len(headers)) + " |"
            data_rows = [
                "| " + " | ".join(cells) + " |"
                for cells in rows[1:]
            ]

            formatted.append(
                f"Table {table['table_index'] + 1}:\n"
                + header_row + "\n" + separator + "\n" + "\n".join(data_rows)
            )

        return "\n\n".join(formatted)

    @tool
    def extract_key_value_pairs(text: str) -> str:
        """Extract key-value pairs from document text using pattern matching.

        Args:
            text: The text to extract key-value pairs from.

        Returns:
            Extracted key-value pairs in structured format.
        """
        import re

        patterns = [
            r"^(.+?):\s*(.+)$",           # Key: Value
            r"^(.+?)\s*=\s*(.+)$",         # Key = Value
            r"^(.+?)\s*-\s*(.+)$",         # Key - Value
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
            return "No key-value pairs found in the text."

        return "Extracted Key-Value Pairs:\n" + "\n".join(pairs[:30])

    @tool
    def ingest_document_to_knowledge_base(file_path: str) -> str:
        """Ingest a document into the vector knowledge base for future retrieval.

        This processes the document (chunk, embed, store) and makes it searchable.

        Args:
            file_path: Path to the document to ingest.

        Returns:
            Status of the ingestion process.
        """
        if vector_store is None:
            return (
                "⚠️ Vector store not available. Document parsed but not ingested.\n"
                "Start the Qdrant service and re-try."
            )

        try:
            from src.pipelines.ingestion import ingest_document

            result = ingest_document(file_path, vector_store)
            return (
                f"✅ Document ingested successfully!\n"
                f"   File: {result.get('file_name', Path(file_path).name)}\n"
                f"   Chunks created: {result.get('chunk_count', 0)}\n"
                f"   Collection: {get_settings().qdrant_collection_name}"
            )
        except Exception as e:
            logger.error(f"Document ingestion failed: {e}")
            return f"❌ Ingestion failed: {str(e)}"

    return [
        extract_document_content,
        extract_tables_from_document,
        extract_key_value_pairs,
        ingest_document_to_knowledge_base,
    ]


# ──────────────────────────────────────────────────────────────
# Document Agent Node
# ──────────────────────────────────────────────────────────────
def create_doc_agent_node(llm: Any, vector_store: Any | None = None):
    """Create the Document Extraction agent node for the LangGraph.

    The Doc agent:
    1. Receives document-related tasks from the supervisor
    2. Parses documents (PDF, DOCX, TXT)
    3. Extracts structured data (tables, key-value pairs)
    4. Optionally ingests content into the vector store
    5. Summarizes findings for the user
    """
    tools = create_doc_tools(vector_store)
    llm_with_tools = llm.bind_tools(tools)

    def doc_agent_node(state: AgentState) -> dict[str, Any]:
        """Process document extraction and analysis tasks."""
        start_time = time.time()
        settings = get_settings()

        messages = [
            SystemMessage(content=DOC_AGENT_SYSTEM_PROMPT),
            *state["messages"],
        ]

        tools_called = []
        try:
            response = llm_with_tools.invoke(messages)

            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_map = {t.name: t for t in tools}
                tool_results = []

                for tc in response.tool_calls:
                    if tc["name"] in tool_map:
                        tools_called.append(tc["name"])
                        result = tool_map[tc["name"]].invoke(tc["args"])
                        tool_results.append(f"Result from {tc['name']}:\n{result}")

                follow_up = [
                    *messages,
                    response,
                    SystemMessage(
                        content="Document processing results:\n\n"
                        + "\n\n".join(tool_results)
                        + "\n\nPlease provide a clear summary of the extracted information."
                    ),
                ]
                final_response = llm.invoke(follow_up)
                response_content = final_response.content
            else:
                response_content = response.content

        except Exception as e:
            logger.error(f"Document agent failed: {e}")
            response_content = (
                f"I encountered an error processing the document: {str(e)}"
            )

        # Track metadata
        latency_ms = (time.time() - start_time) * 1000
        agent_meta = AgentMetadata(
            agent_name="doc_agent",
            model_used=settings.llm_model,
            latency_ms=latency_ms,
            tools_called=tools_called,
            success=True,
        )

        metadata = state.get("metadata", {})
        routing_history = metadata.get("routing_history", [])
        routing_history.append(agent_meta.model_dump())
        metadata["routing_history"] = routing_history

        return {
            "messages": [AIMessage(content=response_content, name="doc_agent")],
            "metadata": metadata,
        }

    return doc_agent_node
