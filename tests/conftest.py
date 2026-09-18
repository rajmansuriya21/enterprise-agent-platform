"""
Test Fixtures — Shared fixtures for the test suite.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    mock = MagicMock()
    mock.invoke.return_value = MagicMock(content="Mock LLM response")
    mock.with_structured_output.return_value = mock
    mock.bind_tools.return_value = mock
    return mock


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store for testing."""
    mock = MagicMock()
    mock.search.return_value = [
        {
            "content": "Sample document content for testing",
            "source": "test_doc.pdf",
            "chunk_id": "test-chunk-1",
            "score": 0.95,
        }
    ]
    mock.hybrid_search.return_value = mock.search.return_value
    mock.health_check.return_value = True
    return mock


@pytest.fixture
def mock_db_service():
    """Create a mock database service for testing."""
    mock = MagicMock()
    mock.get_schema.return_value = "TABLE: test (id INTEGER, name TEXT)"
    mock.list_tables.return_value = ["test"]
    mock.execute_query.return_value = [{"id": 1, "name": "test"}]
    mock.health_check.return_value = True
    return mock


@pytest.fixture
def mock_cache():
    """Create a mock cache service for testing."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.health_check.return_value = True
    return mock


@pytest.fixture
def sample_state():
    """Create a sample agent state for testing."""
    from langchain_core.messages import HumanMessage

    return {
        "messages": [HumanMessage(content="What is the leave policy?")],
        "next_agent": "",
        "context": [],
        "tool_results": [],
        "citations": [],
        "metadata": {},
    }


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary SQLite database for testing."""
    db_path = str(tmp_path / "test.db")
    from src.services.database import DatabaseService

    db = DatabaseService(db_path=db_path)

    # Create test table
    db.execute_script("""
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            value REAL
        );
        INSERT INTO test_table VALUES (1, 'Alice', 100.0);
        INSERT INTO test_table VALUES (2, 'Bob', 200.0);
        INSERT INTO test_table VALUES (3, 'Carol', 150.0);
    """)

    return db
