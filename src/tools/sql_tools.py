"""
SQL Tools — SQL execution, schema introspection, and validation tools.

These tools provide the SQL agent with safe database interaction
capabilities including query validation, schema discovery, and
parameterized execution.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# ── SQL Safety ───────────────────────────────────────────────
DANGEROUS_PATTERNS = [
    r"\bDROP\s+TABLE\b",
    r"\bDROP\s+DATABASE\b",
    r"\bTRUNCATE\b",
    r"\bDELETE\s+FROM\b(?!\s+WHERE)",
    r"\bALTER\s+TABLE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r";\s*--",
    r";\s*DROP\b",
    r"UNION\s+SELECT.*FROM\s+sqlite_master",
]


def validate_sql_query(sql: str) -> tuple[bool, str]:
    """Validate a SQL query for safety. Only SELECT and WITH (CTE) allowed."""
    sql_upper = sql.upper().strip()
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, "Only SELECT queries are allowed for safety."
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, f"Query contains potentially dangerous pattern: {pattern}"
    return True, "Query is safe to execute."


def create_sql_tools(db_service: Any | None = None) -> list:
    """Create SQL-specific tools bound to a database service.

    Args:
        db_service: DatabaseService instance.

    Returns:
        List of LangChain tool objects.
    """

    @tool
    def get_database_schema() -> str:
        """Get the complete database schema including all tables, columns, and types.

        Use this tool FIRST before writing any SQL query to understand the data structure.

        Returns:
            Formatted string of all tables with their column definitions.
        """
        if db_service is None:
            return _get_fallback_schema()

        try:
            return db_service.get_schema()
        except Exception as e:
            logger.error(f"Schema introspection failed: {e}")
            return f"Schema retrieval error: {str(e)}"

    @tool
    def execute_sql(sql: str) -> str:
        """Execute a SQL SELECT query against the business database.

        IMPORTANT: Always call get_database_schema() first to understand available tables.
        Only SELECT queries are allowed. The query is validated for safety before execution.

        Args:
            sql: A valid SQL SELECT query.

        Returns:
            Query results formatted as a readable table, or an error message.
        """
        is_safe, reason = validate_sql_query(sql)
        if not is_safe:
            return f"⚠️ Query rejected: {reason}"

        if db_service is None:
            return "Database service not available. Please configure the database."

        try:
            results = db_service.execute_query(sql)
            if not results:
                return "Query executed successfully but returned no results."

            # Format as markdown table
            headers = list(results[0].keys())
            header_row = "| " + " | ".join(headers) + " |"
            separator = "| " + " | ".join(["---"] * len(headers)) + " |"
            rows = []
            for row in results[:50]:
                row_str = "| " + " | ".join(str(row.get(h, "")) for h in headers) + " |"
                rows.append(row_str)

            table = "\n".join([header_row, separator, *rows])
            if len(results) > 50:
                table += f"\n\n... and {len(results) - 50} more rows"
            return table
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            return f"SQL execution error: {str(e)}"

    @tool
    def list_tables() -> str:
        """List all available tables in the database.

        Returns:
            Comma-separated list of table names.
        """
        if db_service is None:
            return "Available tables: employees, departments, sales, products, customers, orders"
        try:
            tables = db_service.list_tables()
            return f"Available tables: {', '.join(tables)}"
        except Exception as e:
            return f"Error listing tables: {str(e)}"

    @tool
    def validate_sql(sql: str) -> str:
        """Validate a SQL query for safety before execution.

        Args:
            sql: SQL query to validate.

        Returns:
            Validation result indicating if the query is safe.
        """
        is_safe, reason = validate_sql_query(sql)
        return f"{'✅ SAFE' if is_safe else '❌ UNSAFE'}: {reason}"

    return [get_database_schema, execute_sql, list_tables, validate_sql]


def _get_fallback_schema() -> str:
    return (
        "TABLE: employees (id INTEGER PK, name TEXT, email TEXT, department_id INTEGER, salary REAL, hire_date TEXT, position TEXT)\n"
        "TABLE: departments (id INTEGER PK, name TEXT, budget REAL, manager_id INTEGER)\n"
        "TABLE: sales (id INTEGER PK, product_id INTEGER, customer_id INTEGER, amount REAL, quantity INTEGER, sale_date TEXT, region TEXT)\n"
        "TABLE: products (id INTEGER PK, name TEXT, category TEXT, price REAL, stock_quantity INTEGER)\n"
        "TABLE: customers (id INTEGER PK, name TEXT, email TEXT, company TEXT, region TEXT)\n"
        "TABLE: orders (id INTEGER PK, customer_id INTEGER, order_date TEXT, total_amount REAL, status TEXT)"
    )
