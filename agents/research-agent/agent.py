#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel

from research.searcher import search_web
from research.synthesizer import synthesize_report

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEPTH_LIMITS = {"quick": 3, "standard": 5, "deep": 8}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Research a topic and generate a report.")
    parser.add_argument("--topic", required=True, help="Research topic")
    parser.add_argument("--depth", choices=sorted(DEPTH_LIMITS), default="standard", help="How deep to research")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--no-web", action="store_true", help="Use Claude knowledge only")
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

    client = Anthropic(api_key=api_key)

    sources = []
    if not args.no_web:
        console.print(f"[cyan]Researching: {args.topic}[/cyan]")
        try:
            sources = search_web(args.topic, depth=args.depth)
        except Exception as exc:
            console.print(f"[yellow]Warning: Web search failed: {exc}[/yellow]")

    if sources:
        console.print(f"[cyan]Found {len(sources)} sources.[/cyan]")

    try:
        report = synthesize_report(client, args.model, args.topic, sources)
    except Exception as exc:
        die(f"Synthesis failed: {exc}")

    console.print(Panel(report, title="Research Report", border_style="green"))

    output_file = Path(f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    output_file.write_text(report, encoding="utf-8")
    console.print(f"[green]Report saved to {output_file}[/green]")

    if args.html:
        html_file = output_file.with_suffix(".html")
        html_content = f"""<html>
<head><title>Research Report</title>
<style>body {{ font-family: sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}</style>
</head>
<body>
<h1>Research Report</h1>
<p>Topic: {args.topic}</p>
<pre>{report}</pre>
</body></html>"""
        html_file.write_text(html_content)
        console.print(f"[green]HTML report saved to {html_file}[/green]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
