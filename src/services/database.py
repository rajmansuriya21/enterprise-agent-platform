"""
Database Service — Async SQLite service for business data queries.

Provides schema management, parameterized query execution, and
schema introspection for the SQL agent.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from src.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """SQLite database service for business data operations."""

    def __init__(self, db_path: str | None = None) -> None:
        settings = get_settings()
        if db_path:
            self._db_path = db_path
        else:
            self._db_path = str(settings.sqlite_path)

        # Ensure the directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get a SQLite connection with row factory."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Schema Operations ────────────────────────────────────
    def get_schema(self) -> str:
        """Get the complete database schema as a formatted string."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Get all table names
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row["name"] for row in cursor.fetchall()]

            if not tables:
                return "Database is empty — no tables found."

            schema_parts = ["DATABASE SCHEMA:", "=" * 40]

            for table in tables:
                if table.startswith("sqlite_"):
                    continue

                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()

                schema_parts.append(f"\nTABLE: {table}")
                for col in columns:
                    pk = " (PRIMARY KEY)" if col["pk"] else ""
                    nullable = "" if col["notnull"] else " (NULLABLE)"
                    default = f" DEFAULT {col['dflt_value']}" if col["dflt_value"] else ""
                    schema_parts.append(
                        f"  - {col['name']} ({col['type']}{pk}{nullable}{default})"
                    )

                # Get foreign keys
                cursor.execute(f"PRAGMA foreign_key_list({table})")
                fks = cursor.fetchall()
                for fk in fks:
                    schema_parts.append(
                        f"  FK: {fk['from']} → {fk['table']}.{fk['to']}"
                    )

            return "\n".join(schema_parts)
        finally:
            conn.close()

    def list_tables(self) -> list[str]:
        """List all table names in the database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            return [row["name"] for row in cursor.fetchall()]
        finally:
            conn.close()

    # ── Query Execution ──────────────────────────────────────
    def execute_query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as a list of dicts.

        Args:
            sql: SQL query string.
            params: Query parameters for parameterized queries.

        Returns:
            List of result rows as dictionaries.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
        finally:
            conn.close()

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        """Execute a write operation (INSERT/UPDATE/DELETE).

        Args:
            sql: SQL statement.
            params: Statement parameters.

        Returns:
            Number of affected rows.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"Write operation failed: {e}")
            raise
        finally:
            conn.close()

    def execute_script(self, script: str) -> None:
        """Execute a multi-statement SQL script."""
        conn = self._get_connection()
        try:
            conn.executescript(script)
            conn.commit()
            logger.info("SQL script executed successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Script execution failed: {e}")
            raise
        finally:
            conn.close()

    # ── Health Check ─────────────────────────────────────────
    def health_check(self) -> bool:
        """Check if the database is accessible."""
        try:
            conn = self._get_connection()
            conn.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False

    def row_count(self, table: str) -> int:
        """Get the row count for a table."""
        result = self.execute_query(f"SELECT COUNT(*) as count FROM {table}")
        return result[0]["count"] if result else 0


def get_database_service() -> DatabaseService:
    """Create and return a DatabaseService instance."""
    return DatabaseService()
