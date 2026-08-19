#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


class SchemaExtractor:
    def __init__(self, connector):
        self.connector = connector
        self.db_type = connector.db_type

    def extract_schema(self) -> dict[str, Any]:
        if self.db_type == "sqlite":
            return self._extract_sqlite()
        elif self.db_type == "postgresql":
            return self._extract_postgresql()
        elif self.db_type == "mysql":
            return self._extract_mysql()
        return {"table_count": 0, "total_rows": 0}

    def _extract_sqlite(self) -> dict[str, Any]:
        cursor = self.connector.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        total_rows = 0
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            total_rows += cursor.fetchone()[0]
        return {"table_count": len(tables), "total_rows": total_rows, "tables": tables}

    def _extract_postgresql(self) -> dict[str, Any]:
        cursor = self.connector.conn.cursor()
        cursor.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        total_rows = 0
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                total_rows += cursor.fetchone()[0]
            except Exception:
                pass
        return {"table_count": len(tables), "total_rows": total_rows, "tables": tables}

    def _extract_mysql(self) -> dict[str, Any]:
        cursor = self.connector.conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        total_rows = 0
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                total_rows += cursor.fetchone()[0]
            except Exception:
                pass
        return {"table_count": len(tables), "total_rows": total_rows, "tables": tables}

    def format_schema(self) -> str:
        schema_info = self.extract_schema()
        tables = schema_info.get("tables", [])
        lines = ["# Database Schema\n"]

        for table in tables:
            lines.append(f"\n## Table: {table}")
            cursor = self.connector.conn.cursor()
            if self.db_type == "sqlite":
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                for col in columns:
                    lines.append(f"  - {col[1]} ({col[2]})")
            elif self.db_type == "postgresql":
                cursor.execute(
                    f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table}'"
                )
                columns = cursor.fetchall()
                for col in columns:
                    lines.append(f"  - {col[0]} ({col[1]})")
            elif self.db_type == "mysql":
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                for col in columns:
                    lines.append(f"  - {col[0]} ({col[1]})")

        return "\n".join(lines)
