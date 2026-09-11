#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel

from analyzer.code_context import extract_code_context
from analyzer.log_parser import parse_log
from analyzer.pattern_db import check_patterns

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze error logs and stack traces.")
    parser.add_argument("--log", help="Log file path")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--clipboard", action="store_true", help="Read from clipboard")
    parser.add_argument("--repo", help="Local repo path for code context")
    parser.add_argument("--watch", action="store_true", help="Watch log file for new errors (not yet implemented)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(1)


def analyze_error(client: Anthropic, model: str, log_content: str, repo_path: str | None) -> None:
    """Analyze a single error log."""
    parsed = parse_log(log_content)
    
    if not parsed:
        console.print("[yellow]Could not parse log content.[/yellow]")
        return

    # Check pattern database
    patterns = check_patterns(parsed.get("error_type", ""))
    pattern_info = f"\n**Pattern Match:** {patterns['name']} — {patterns['description']}" if patterns else ""

    code_context = ""
    if repo_path:
        code_context = extract_code_context(
            repo_path,
            parsed.get("stack_trace", ""),
        )

    # Build prompt for Claude
    prompt = f"""Analyze this error and provide:
1. Root cause (plain English)
2. Exact file:line if traceable
3. Suggested fix (code diff if available)
4. Severity (CRITICAL/HIGH/MEDIUM/LOW)
5. Is this a known pattern?

Error Type: {parsed.get('error_type', 'Unknown')}
Message: {parsed.get('message', 'No message')}
Stack Trace:
{parsed.get('stack_trace', 'No trace')}

{pattern_info if pattern_info else '(No known pattern match)'}

{f"Relevant Code Context:\n{code_context}" if code_context else "(No repo provided — no code context available)"}

Return structured JSON."""

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        system="You are a senior debugging expert. Analyze this error and provide actionable insights.",
        messages=[{"role": "user", "content": prompt}],
    )

    analysis = "".join(block.text for block in response.content if getattr(block, "text", None)).strip()
    console.print(Panel(analysis, title="Error Analysis", border_style="red"))


def main() -> int:
    args = parse_args()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        die("Missing ANTHROPIC_API_KEY.")

    client = Anthropic(api_key=api_key)

    # Read log content
    if args.log:
        try:
            log_content = Path(args.log).read_text()
        except Exception as exc:
            die(f"Failed to read log file: {exc}")
    elif args.stdin:
        log_content = sys.stdin.read()
    elif args.clipboard:
        try:
            import pyperclip
            log_content = pyperclip.paste()
        except ImportError:
            die("pyperclip not installed. Use --log or --stdin instead.")
    else:
        die("Provide --log, --stdin, or --clipboard")

    if args.watch:
        die(
            "Watch mode is not implemented yet. "
            "Use --log or --stdin for one-off analysis instead."
        )
    else:
        analyze_error(client, args.model, log_content, args.repo)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
