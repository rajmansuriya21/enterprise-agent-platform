"""Tests for the SQL agent and tools."""

from src.agents.sql_agent import validate_sql, _format_results, _get_sample_schema


class TestSQLValidation:
    """Tests for SQL query validation."""

    def test_valid_select(self):
        is_safe, reason = validate_sql("SELECT * FROM employees")
        assert is_safe is True

    def test_valid_with_cte(self):
        is_safe, reason = validate_sql(
            "WITH dept_stats AS (SELECT dept, COUNT(*) FROM emp GROUP BY dept) SELECT * FROM dept_stats"
        )
        assert is_safe is True

    def test_reject_drop(self):
        is_safe, reason = validate_sql("DROP TABLE employees")
        assert is_safe is False

    def test_reject_delete(self):
        is_safe, reason = validate_sql("DELETE FROM employees")
        assert is_safe is False

    def test_reject_insert(self):
        is_safe, reason = validate_sql("INSERT INTO employees VALUES (1, 'test')")
        assert is_safe is False

    def test_reject_truncate(self):
        is_safe, reason = validate_sql("TRUNCATE TABLE employees")
        assert is_safe is False


class TestResultFormatting:
    """Tests for SQL result formatting."""

    def test_format_results(self):
        results = [
            {"id": 1, "name": "Alice", "salary": 100000},
            {"id": 2, "name": "Bob", "salary": 120000},
        ]
        formatted = _format_results(results)
        assert "Alice" in formatted
        assert "Bob" in formatted
        assert "|" in formatted  # Markdown table

    def test_format_empty_results(self):
        assert _format_results([]) == "No results."

    def test_format_caps_at_50(self):
        results = [{"id": i, "name": f"User_{i}"} for i in range(100)]
        formatted = _format_results(results)
        assert "50 more rows" in formatted


class TestSampleSchema:
    """Tests for sample schema."""

    def test_schema_contains_tables(self):
        schema = _get_sample_schema()
        assert "employees" in schema
        assert "departments" in schema
        assert "sales" in schema
        assert "products" in schema
