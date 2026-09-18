"""Tests for the database service."""

import pytest


class TestDatabaseService:
    """Tests for the SQLite database service."""

    def test_health_check(self, temp_db):
        assert temp_db.health_check() is True

    def test_list_tables(self, temp_db):
        tables = temp_db.list_tables()
        assert "test_table" in tables

    def test_get_schema(self, temp_db):
        schema = temp_db.get_schema()
        assert "test_table" in schema
        assert "name" in schema
        assert "value" in schema

    def test_execute_query(self, temp_db):
        results = temp_db.execute_query("SELECT * FROM test_table")
        assert len(results) == 3
        assert results[0]["name"] == "Alice"

    def test_execute_query_with_filter(self, temp_db):
        results = temp_db.execute_query(
            "SELECT * FROM test_table WHERE value > ?", (100.0,)
        )
        assert len(results) == 2

    def test_row_count(self, temp_db):
        count = temp_db.row_count("test_table")
        assert count == 3

    def test_execute_write(self, temp_db):
        affected = temp_db.execute_write(
            "INSERT INTO test_table VALUES (4, 'Dave', 250.0)"
        )
        assert affected == 1
        assert temp_db.row_count("test_table") == 4


class TestDatabaseServiceErrors:
    """Tests for error handling."""

    def test_invalid_query(self, temp_db):
        with pytest.raises(Exception):
            temp_db.execute_query("SELECT * FROM nonexistent_table")
