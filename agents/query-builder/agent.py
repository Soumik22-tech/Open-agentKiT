#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from db.connector import DatabaseConnector
from db.schema_extractor import SchemaExtractor

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"
SYSTEM_PROMPT = """You are an expert SQL engineer. You will be given a database schema and a natural language question.
Generate the most efficient, correct SQL query to answer the question.
Rules:
- NEVER generate DELETE, DROP, UPDATE, INSERT queries — SELECT only (read-only safety)
- Use JOINs correctly based on foreign key relationships
- Add LIMIT 1000 if no limit specified (prevent runaway queries)
- If the question is ambiguous, make a reasonable assumption and state it
- Prefer CTEs over nested subqueries for readability
- Return ONLY valid JSON: { 'sql': '...', 'explanation': '...', 'assumptions': [...] }"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Natural language SQL query builder.")
    parser.add_argument("--db", required=True, help="Database connection string")
    parser.add_argument("--no-confirm", action="store_true", help="Skip SQL confirmation")
    parser.add_argument("--query", help="Run a single query (non-interactive)")
    parser.add_argument("--export", help="Export results to CSV")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model to use (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(1)


def render_schema_info(schema_summary: dict[str, Any]) -> None:
    table = Table(show_header=False, box=None)
    table.add_row("Tables", str(schema_summary["table_count"]))
    table.add_row("Total rows", str(schema_summary["total_rows"]))
    console.print(Panel(table, title="Database Connected", border_style="blue"))


def generate_sql(client: Anthropic, model: str, schema: str, query: str) -> dict[str, Any]:
    prompt = f"""Database schema:
{schema}

Natural language question: {query}

Generate an efficient SELECT query. Return JSON only."""
    
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    
    text = "".join(block.text for block in response.content if getattr(block, "text", None)).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        return {"sql": "", "explanation": "Failed to parse response", "assumptions": []}


def render_results(rows: list[dict[str, Any]], columns: list[str]) -> None:
    if not rows:
        console.print("[yellow]No results.[/yellow]")
        return

    table = Table(title=f"Results ({len(rows)} rows)")
    for col in columns:
        table.add_column(col)

    for row in rows[:50]:
        table.add_row(*[str(row.get(col, "")) for col in columns])

    console.print(table)
    if len(rows) > 50:
        console.print(f"[yellow]Showing 50 of {len(rows)} rows. Use --export to save all results.[/yellow]")


def main() -> int:
    args = parse_args()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        die("Missing ANTHROPIC_API_KEY. Set it in your environment or .env file.")

    try:
        connector = DatabaseConnector(args.db)
    except Exception as exc:
        die(f"Failed to connect to database: {exc}")

    try:
        extractor = SchemaExtractor(connector)
        schema_summary = extractor.extract_schema()
        schema_str = extractor.format_schema()
    except Exception as exc:
        die(f"Failed to extract schema: {exc}")

    render_schema_info(schema_summary)

    client = Anthropic(api_key=api_key)

    if args.query:
        try:
            result = generate_sql(client, args.model, schema_str, args.query)
            sql = result.get("sql", "")
            if not sql:
                die("Failed to generate SQL.")
            console.print(Panel(sql, title="Generated SQL"))
            if not args.no_confirm:
                answer = console.input("Execute? [Y/n]: ").strip().lower()
                if answer in {"n", "no"}:
                    return 0
            rows, columns = connector.execute_query(sql, timeout=30)
            render_results(rows, columns)
            if args.export:
                import csv
                with open(args.export, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=columns)
                    writer.writeheader()
                    writer.writerows(rows)
                console.print(f"[green]Exported to {args.export}[/green]")
        except Exception as exc:
            die(f"Query execution failed: {exc}")
    else:
        console.print("[cyan]Interactive mode. Type 'exit' to quit.[/cyan]")
        while True:
            query = console.input("\n[bold]You:[/bold] ").strip()
            if query.lower() in {"exit", "quit"}:
                break
            if not query:
                continue
            try:
                result = generate_sql(client, args.model, schema_str, query)
                sql = result.get("sql", "")
                explanation = result.get("explanation", "")
                if not sql:
                    console.print("[yellow]Failed to generate SQL.[/yellow]")
                    continue
                console.print(Panel(f"{explanation}\n\n```sql\n{sql}\n```", title="Generated SQL"))
                if not args.no_confirm:
                    answer = console.input("Execute? [Y/n]: ").strip().lower()
                    if answer in {"n", "no"}:
                        continue
                rows, columns = connector.execute_query(sql, timeout=30)
                render_results(rows, columns)
            except Exception as exc:
                console.print(f"[red]Error:[/red] {exc}")

    connector.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
