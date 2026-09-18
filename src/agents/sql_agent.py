"""
SQL Sub-Agent — Natural Language to SQL with validation and safe execution.

Converts natural language queries to SQL, introspects the database schema,
validates queries for safety (prevents injection), executes them, and
formats the results for human-readable output.
"""

from __future__ import annotations

import time
import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import tool

from src.agents.state import AgentMetadata, AgentState
from src.config import get_settings
from src.utils.prompts import SQL_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# SQL Safety Utilities
# ──────────────────────────────────────────────────────────────
DANGEROUS_PATTERNS = [
    r"\bDROP\s+TABLE\b",
    r"\bDROP\s+DATABASE\b",
    r"\bTRUNCATE\b",
    r"\bDELETE\s+FROM\b(?!\s+WHERE)",
    r"\bALTER\s+TABLE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r";\s*--",  # SQL comment injection
    r";\s*DROP\b",
    r"UNION\s+SELECT.*FROM\s+sqlite_master",
]


def validate_sql(sql: str) -> tuple[bool, str]:
    """Validate a SQL query for safety.

    Returns:
        Tuple of (is_safe, reason). If unsafe, reason explains why.
    """
    sql_upper = sql.upper().strip()

    # Only allow SELECT and WITH (CTEs)
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, "Only SELECT queries are allowed for safety."

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, f"Query contains potentially dangerous pattern: {pattern}"

    return True, "Query is safe to execute."


# ──────────────────────────────────────────────────────────────
# SQL Tools
# ──────────────────────────────────────────────────────────────
def create_sql_tools(db_service: Any | None = None) -> list:
    """Create SQL-specific tools bound to a database service."""

    @tool
    def get_database_schema() -> str:
        """Get the complete database schema including all tables, columns, and types.

        Use this tool FIRST before writing any SQL query to understand the data structure.

        Returns:
            Formatted string of all tables with their column definitions.
        """
        if db_service is None:
            return _get_sample_schema()

        try:
            schema = db_service.get_schema()
            return schema
        except Exception as e:
            logger.error(f"Schema introspection failed: {e}")
            return f"Schema retrieval error: {str(e)}"

    @tool
    def execute_sql_query(sql: str) -> str:
        """Execute a SQL SELECT query against the business database.

        IMPORTANT: Always call get_database_schema() first to understand available tables.
        Only SELECT queries are allowed. The query is validated for safety before execution.

        Args:
            sql: A valid SQL SELECT query.

        Returns:
            Query results formatted as a readable table, or an error message.
        """
        # Validate the query
        is_safe, reason = validate_sql(sql)
        if not is_safe:
            return f"⚠️ Query rejected: {reason}"

        if db_service is None:
            return _execute_sample_query(sql)

        try:
            results = db_service.execute_query(sql)
            if not results:
                return "Query executed successfully but returned no results."
            return _format_results(results)
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            return f"SQL execution error: {str(e)}. Please check your query syntax."

    @tool
    def list_tables() -> str:
        """List all available tables in the database.

        Returns:
            List of table names.
        """
        if db_service is None:
            return "Available tables: employees, departments, sales, products, customers, orders"

        try:
            tables = db_service.list_tables()
            return f"Available tables: {', '.join(tables)}"
        except Exception as e:
            return f"Error listing tables: {str(e)}"

    return [get_database_schema, execute_sql_query, list_tables]


# ──────────────────────────────────────────────────────────────
# Sample data for demo mode (when no DB is connected)
# ──────────────────────────────────────────────────────────────
def _get_sample_schema() -> str:
    return """
DATABASE SCHEMA:
================

TABLE: employees
  - id (INTEGER, PRIMARY KEY)
  - name (TEXT, NOT NULL)
  - email (TEXT, UNIQUE)
  - department_id (INTEGER, FOREIGN KEY -> departments.id)
  - salary (REAL)
  - hire_date (TEXT)
  - position (TEXT)

TABLE: departments
  - id (INTEGER, PRIMARY KEY)
  - name (TEXT, NOT NULL)
  - budget (REAL)
  - manager_id (INTEGER, FOREIGN KEY -> employees.id)

TABLE: sales
  - id (INTEGER, PRIMARY KEY)
  - product_id (INTEGER, FOREIGN KEY -> products.id)
  - customer_id (INTEGER, FOREIGN KEY -> customers.id)
  - amount (REAL)
  - quantity (INTEGER)
  - sale_date (TEXT)
  - region (TEXT)

TABLE: products
  - id (INTEGER, PRIMARY KEY)
  - name (TEXT, NOT NULL)
  - category (TEXT)
  - price (REAL)
  - stock_quantity (INTEGER)

TABLE: customers
  - id (INTEGER, PRIMARY KEY)
  - name (TEXT, NOT NULL)
  - email (TEXT)
  - company (TEXT)
  - region (TEXT)

TABLE: orders
  - id (INTEGER, PRIMARY KEY)
  - customer_id (INTEGER, FOREIGN KEY -> customers.id)
  - order_date (TEXT)
  - total_amount (REAL)
  - status (TEXT)
"""


def _execute_sample_query(sql: str) -> str:
    """Execute a query against sample in-memory data for demo purposes."""
    sql_lower = sql.lower()

    if "employees" in sql_lower and "count" in sql_lower:
        return "| count |\n|-------|\n| 150   |"
    elif "sales" in sql_lower and "region" in sql_lower:
        return (
            "| region      | total_sales  | order_count |\n"
            "|-------------|-------------|-------------|\n"
            "| North       | $1,245,890  | 342         |\n"
            "| South       | $987,650    | 278         |\n"
            "| East        | $1,567,230  | 423         |\n"
            "| West        | $876,440    | 231         |"
        )
    elif "departments" in sql_lower:
        return (
            "| department  | employee_count | avg_salary |\n"
            "|-------------|---------------|------------|\n"
            "| Engineering | 45            | $125,000   |\n"
            "| Sales       | 30            | $95,000    |\n"
            "| Marketing   | 20            | $88,000    |\n"
            "| HR          | 15            | $78,000    |\n"
            "| Finance     | 12            | $105,000   |"
        )
    elif "products" in sql_lower:
        return (
            "| product           | category    | price   | stock |\n"
            "|-------------------|-------------|---------|-------|\n"
            "| Enterprise Suite  | Software    | $999    | 500   |\n"
            "| Analytics Pro     | Software    | $599    | 750   |\n"
            "| Cloud Storage     | Service     | $49/mo  | ∞     |\n"
            "| Support Premium   | Service     | $199/mo | ∞     |"
        )
    else:
        return (
            "| id | name           | value      |\n"
            "|----|----------------|------------|\n"
            "| 1  | Sample Row 1   | $10,000    |\n"
            "| 2  | Sample Row 2   | $25,000    |\n"
            "| 3  | Sample Row 3   | $15,000    |"
        )


def _format_results(results: list[dict]) -> str:
    """Format query results as a markdown table."""
    if not results:
        return "No results."

    headers = list(results[0].keys())
    header_row = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"

    rows = []
    for row in results[:50]:  # Cap at 50 rows
        row_str = "| " + " | ".join(str(row.get(h, "")) for h in headers) + " |"
        rows.append(row_str)

    table = "\n".join([header_row, separator, *rows])

    if len(results) > 50:
        table += f"\n\n... and {len(results) - 50} more rows (showing first 50)"

    return table


# ──────────────────────────────────────────────────────────────
# SQL Agent Node
# ──────────────────────────────────────────────────────────────
def create_sql_agent_node(llm: Any, db_service: Any | None = None):
    """Create the SQL agent node for the LangGraph.

    The SQL agent:
    1. Introspects the database schema
    2. Translates natural language to SQL
    3. Validates the query for safety
    4. Executes the query
    5. Formats and explains the results
    """
    tools = create_sql_tools(db_service)
    llm_with_tools = llm.bind_tools(tools)

    def sql_agent_node(state: AgentState) -> dict[str, Any]:
        """Execute the SQL pipeline: schema → generate SQL → validate → execute → explain."""
        start_time = time.time()
        settings = get_settings()

        # Get the query from conversation
        user_query = ""
        task_desc = state.get("metadata", {}).get("last_task", "")
        for msg in reversed(state["messages"]):
            if hasattr(msg, "content") and getattr(msg, "name", "") != "supervisor":
                if not msg.content.startswith("[Supervisor"):
                    user_query = msg.content
                    break

        effective_query = task_desc if task_desc else user_query

        # Step 1: Get schema
        schema = _get_sample_schema()
        if db_service is not None:
            try:
                schema = db_service.get_schema()
            except Exception:
                pass

        # Step 2: Generate SQL and response using LLM
        messages = [
            SystemMessage(
                content=SQL_AGENT_SYSTEM_PROMPT.format(
                    schema=schema,
                    query=effective_query,
                )
            ),
            *state["messages"],
        ]

        try:
            response = llm_with_tools.invoke(messages)

            # Check if the LLM wants to call tools
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_results = []
                tool_map = {t.name: t for t in tools}
                for tc in response.tool_calls:
                    if tc["name"] in tool_map:
                        result = tool_map[tc["name"]].invoke(tc["args"])
                        tool_results.append(result)

                # Generate final response with tool results
                follow_up = [
                    *messages,
                    response,
                    SystemMessage(
                        content=f"Tool results:\n" + "\n".join(str(r) for r in tool_results)
                    ),
                ]
                final_response = llm.invoke(follow_up)
                response_content = final_response.content
            else:
                response_content = response.content

        except Exception as e:
            logger.error(f"SQL agent failed: {e}")
            response_content = f"I encountered an error processing your data query: {str(e)}"

        # Track metadata
        latency_ms = (time.time() - start_time) * 1000
        agent_meta = AgentMetadata(
            agent_name="sql_agent",
            model_used=settings.llm_model,
            latency_ms=latency_ms,
            tools_called=["get_database_schema", "execute_sql_query"],
            success=True,
        )

        metadata = state.get("metadata", {})
        routing_history = metadata.get("routing_history", [])
        routing_history.append(agent_meta.model_dump())
        metadata["routing_history"] = routing_history

        return {
            "messages": [AIMessage(content=response_content, name="sql_agent")],
            "metadata": metadata,
        }

    return sql_agent_node
