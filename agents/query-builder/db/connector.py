#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
import time
from typing import Any

try:
    import psycopg2
except ImportError:
    psycopg2 = None

try:
    import mysql.connector
except ImportError:
    mysql = None


class DatabaseConnector:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.conn = None
        self._connect()

    def _connect(self) -> None:
        if self.connection_string.startswith("sqlite://"):
            db_path = self.connection_string.replace("sqlite:///", "")
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            self.db_type = "sqlite"
        elif self.connection_string.startswith("postgresql://"):
            if not psycopg2:
                raise ImportError("psycopg2 required for PostgreSQL. Install with: pip install psycopg2-binary")
            parts = self._parse_postgres_url()
            self.conn = psycopg2.connect(**parts)
            self.db_type = "postgresql"
        elif self.connection_string.startswith("mysql://"):
            if not mysql:
                raise ImportError("mysql-connector-python required. Install with: pip install mysql-connector-python")
            parts = self._parse_mysql_url()
            self.conn = mysql.connector.connect(**parts)
            self.db_type = "mysql"
        else:
            raise ValueError(f"Unsupported connection string format: {self.connection_string}")

    def _parse_postgres_url(self) -> dict[str, str]:
        from urllib.parse import urlparse
        parsed = urlparse(self.connection_string)
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "user": parsed.username or "postgres",
            "password": parsed.password or "",
            "database": parsed.path.lstrip("/"),
        }

    def _parse_mysql_url(self) -> dict[str, str]:
        from urllib.parse import urlparse
        parsed = urlparse(self.connection_string)
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 3306,
            "user": parsed.username or "root",
            "password": parsed.password or "",
            "database": parsed.path.lstrip("/"),
        }

    def execute_query(self, sql: str, timeout: int = 30) -> tuple[list[dict[str, Any]], list[str]]:
        if self.db_type == "sqlite":
            cursor = self.conn.cursor()
            cursor.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]
            columns = [desc[0] for desc in cursor.description or []]
        else:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return rows, columns

    def close(self) -> None:
        if self.conn:
            self.conn.close()
