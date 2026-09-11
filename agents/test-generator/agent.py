#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from generators.python_analyzer import analyze_python_file
from generators.test_writer import generate_tests, run_tests

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate comprehensive test suites from source code.")
    parser.add_argument("--file", help="Source file to test")
    parser.add_argument("--dir", help="Directory to test (batch mode)")
    parser.add_argument("--output", help="Write tests to specified file")
    parser.add_argument("--run", action="store_true", help="Run tests after generating")
    parser.add_argument("--framework", default="pytest", help="Test framework (pytest/jest)")
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

    if not args.file and not args.dir:
        die("Provide --file or --dir")

    client = Anthropic(api_key=api_key)

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            die(f"File not found: {file_path}")

        console.print(f"[cyan]Analyzing {file_path}...[/cyan]")
        
        if file_path.suffix == ".py":
            functions = analyze_python_file(file_path)
        elif file_path.suffix in (".js", ".ts", ".jsx", ".tsx"):
            die(
                "JavaScript/TypeScript support is not implemented yet — only Python (.py) files "
                "are currently supported. See CONTRIBUTING.md to help add JS/TS support."
            )
        else:
            die(
                f"Unsupported file type: {file_path.suffix}. "
                "Currently only Python (.py) is supported."
            )

        if not functions:
            console.print("[yellow]No functions found to test.[/yellow]")
            return 0

        console.print(f"[cyan]Found {len(functions)} functions. Generating tests...[/cyan]")
        test_code = generate_tests(client, args.model, file_path, functions)

        output_file = args.output or f"test_{file_path.stem}.py"
        Path(output_file).write_text(test_code)
        console.print(f"[green]Tests written to {output_file}[/green]")

        if args.run:
            console.print("[cyan]Running tests...[/cyan]")
            passed, failed = run_tests(output_file)
            table = Table(title="Test Results")
            table.add_column("Status", style="bold")
            table.add_column("Count")
            table.add_row("[green]Passed[/green]", str(passed))
            if failed > 0:
                table.add_row("[red]Failed[/red]", str(failed))
            console.print(table)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
