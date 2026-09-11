#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.data_loader import load_and_profile
from core.code_generator import generate_analysis_code
from core.safe_executor import execute_code

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive data analysis with Claude.")
    parser.add_argument("--file", required=True, help="CSV or Excel file to analyze")
    parser.add_argument("--query", help="Single query (non-interactive)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(1)


def main() -> int:
    args = parse_args()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        die("Missing ANTHROPIC_API_KEY.")

    file_path = Path(args.file)
    if not file_path.exists():
        die(f"File not found: {file_path}")

    console.print(f"[cyan]Loading {file_path}...[/cyan]")
    df, profile = load_and_profile(file_path)

    if df is None:
        die("Failed to load data file.")

    console.print(f"[cyan]Loaded {len(df)} rows, {len(df.columns)} columns[/cyan]")

    # Display profile
    table = Table(title="Data Profile")
    table.add_column("Column")
    table.add_column("Type")
    table.add_column("Null%")
    for col in df.columns:
        null_pct = (df[col].isnull().sum() / len(df)) * 100
        table.add_row(col, str(df[col].dtype), f"{null_pct:.1f}%")
    console.print(table)

    client = Anthropic(api_key=api_key)

    if args.query:
        # Single query
        code = generate_analysis_code(client, args.model, df, profile, args.query)
        result = execute_code(code, df)
        if result:
            console.print(Panel(result, title="Result", border_style="green"))
    else:
        # Interactive REPL
        console.print("[cyan]Interactive mode. Type 'exit' to quit.[/cyan]")
        while True:
            try:
                query = console.input("[blue]Query:[/blue] ")
                if query.lower() in ["exit", "quit"]:
                    break
                if not query.strip():
                    continue

                code = generate_analysis_code(client, args.model, df, profile, query)
                result = execute_code(code, df)
                if result:
                    console.print(Panel(result, title="Result", border_style="green"))
            except KeyboardInterrupt:
                break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
