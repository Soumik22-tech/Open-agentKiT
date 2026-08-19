#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel

from parsers.python_parser import extract_python_routes
from generators.openapi import generate_openapi_spec
from generators.html_docs import generate_html_docs
from generators.postman import generate_postman_collection

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate API documentation from source code.")
    parser.add_argument("--project", default=".", help="Path to the API project")
    parser.add_argument("--framework", help="Force framework (fastapi, flask)")
    parser.add_argument("--output", default="./docs", help="Output directory")
    parser.add_argument("--serve", action="store_true", help="Start a local server")
    parser.add_argument("--no-html", action="store_true", help="Skip HTML generation")
    parser.add_argument("--title", default="API", help="API title")
    parser.add_argument("--version", default="1.0.0", help="API version")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(1)


def detect_framework(project_root: Path) -> str:
    reqs_file = project_root / "requirements.txt"
    if reqs_file.exists():
        text = reqs_file.read_text().lower()
        if "fastapi" in text:
            return "fastapi"
        if "flask" in text:
            return "flask"
    return "fastapi"


def main() -> int:
    args = parse_args()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        die("Missing ANTHROPIC_API_KEY.")

    project_root = Path(args.project).expanduser().resolve()
    if not project_root.exists():
        die(f"Project not found: {project_root}")

    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    framework = args.framework or detect_framework(project_root)
    console.print(f"[cyan]Detected framework: {framework}[/cyan]")

    try:
        routes = extract_python_routes(project_root)
    except Exception as exc:
        die(f"Failed to extract routes: {exc}")

    if not routes:
        die("No routes found.")

    console.print(f"[cyan]Found {len(routes)} routes.[/cyan]")

    client = Anthropic(api_key=api_key)

    try:
        spec = generate_openapi_spec(routes, args.title, args.version)
    except Exception as exc:
        die(f"Failed to generate OpenAPI spec: {exc}")

    spec_file = output_dir / "openapi.json"
    spec_file.write_text(json.dumps(spec, indent=2))
    console.print(f"[green]OpenAPI spec: {spec_file}[/green]")

    if not args.no_html:
        try:
            html = generate_html_docs(spec)
            html_file = output_dir / "index.html"
            html_file.write_text(html)
            console.print(f"[green]HTML docs: {html_file}[/green]")
        except Exception as exc:
            console.print(f"[yellow]HTML generation failed: {exc}[/yellow]")

    try:
        postman_collection = generate_postman_collection(routes, args.title)
        postman_file = output_dir / "postman_collection.json"
        postman_file.write_text(json.dumps(postman_collection, indent=2))
        console.print(f"[green]Postman collection: {postman_file}[/green]")
    except Exception as exc:
        console.print(f"[yellow]Postman generation failed: {exc}[/yellow]")

    if args.serve:
        import http.server
        import socketserver
        os.chdir(output_dir)
        Handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", 8000), Handler) as httpd:
            console.print("[green]Serving on http://localhost:8000[/green]")
            httpd.serve_forever()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
