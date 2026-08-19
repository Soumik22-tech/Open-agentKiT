#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyperclip
from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"
SUPPORTED_LANGUAGES = {
    "python": {".py"},
    "javascript": {".js", ".cjs", ".mjs"},
    "typescript": {".ts", ".tsx"},
    "go": {".go"},
    "rust": {".rs"},
    "java": {".java"},
}
SEVERITY_STYLES = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "cyan",
}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass(frozen=True)
class BugFinding:
    line: int
    severity: str
    title: str
    explanation: str
    trigger_example: str
    confidence: float


class BugHunterError(RuntimeError):
    pass


SYSTEM_PROMPT = """You are a senior engineer focused only on logic bugs, correctness problems, and real failure modes.
Do not suggest style changes, formatting, docstrings, or linting fixes.
Look for concrete bugs such as off-by-one errors, null/undefined access, race conditions, SQL injection, improper error handling,
type mismatches, infinite loops, resource leaks, and incorrect assumptions about input shape or state.
For each finding, provide an example input or execution scenario that reproduces it.
Return valid JSON only.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find real logic bugs in source code with Claude.")
    parser.add_argument("--file", help="Path to a source file")
    parser.add_argument("--stdin", action="store_true", help="Read code from stdin")
    parser.add_argument("--fix", action="store_true", help="Overwrite the file with Claude's fixed version")
    parser.add_argument("--copy-fix", action="store_true", help="Copy Claude's fixed version to the clipboard")
    parser.add_argument("--language", help="Force the language if auto-detection fails")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model to use (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(1)


def detect_language_from_path(path: Path | None) -> str | None:
    if not path:
        return None
    suffix = path.suffix.lower()
    for language, extensions in SUPPORTED_LANGUAGES.items():
        if suffix in extensions:
            return language
    return None


def detect_language_from_content(code: str) -> str | None:
    lower = code.lower()
    if "package main" in lower or re.search(r"\bfunc\s+main\s*\(", lower):
        return "go"
    if re.search(r"\bfn\s+main\s*\(", lower):
        return "rust"
    if re.search(r"\bpublic\s+class\b", lower):
        return "java"
    if "def " in code and ("import " in code or "from " in code):
        return "python"
    if "function " in code or "=>" in code or "const " in code or "let " in code:
        return "javascript"
    return None


def read_code(args: argparse.Namespace) -> tuple[str, Path | None]:
    if args.stdin:
        code = sys.stdin.read()
        if not code.strip():
            raise BugHunterError("No code was received on stdin.")
        return code, None
    if not args.file:
        raise BugHunterError("Provide --file or use --stdin.")
    path = Path(args.file)
    if not path.exists():
        raise BugHunterError(f"File not found: {path}")
    return path.read_text(encoding="utf-8", errors="ignore"), path


def infer_language(args: argparse.Namespace, path: Path | None, code: str) -> str:
    if args.language:
        language = args.language.lower().strip()
        if language not in SUPPORTED_LANGUAGES:
            raise BugHunterError(f"Unsupported language override: {args.language}. Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}")
        return language

    language = detect_language_from_path(path) or detect_language_from_content(code)
    if not language:
        raise BugHunterError(
            "Could not auto-detect the language. Use --language with one of: "
            + ", ".join(sorted(SUPPORTED_LANGUAGES))
        )
    return language


def build_prompt(code: str, language: str) -> str:
    return f"""Analyze the following {language} code and return valid JSON only.

Requirements:
- Focus on LOGIC bugs, not style or linting.
- Do not include cosmetic feedback.
- Report only real bugs that can cause incorrect behavior, security issues, crashes, or data loss.
- For each bug, include a concrete example input or scenario that triggers it.
- Confidence should be a number between 0 and 1 for each bug and for the overall result.

Return this JSON schema exactly:
{{
  "bugs": [
    {{
      "line": 1,
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "title": "short bug title",
      "explanation": "why this is a bug",
      "trigger_example": "example input or scenario",
      "confidence": 0.0
    }}
  ],
  "fixed_code": "entire corrected file contents",
  "summary": "1-3 sentence summary",
  "confidence": 0.0
}}

Code:
```{language}
{code}
```
"""


def extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise BugHunterError("Claude did not return valid JSON.")
        return json.loads(text[start : end + 1])


def call_claude(client: Anthropic, model: str, prompt: str) -> dict[str, Any]:
    response = client.messages.create(
        model=model,
        max_tokens=5000,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if getattr(block, "text", None)).strip()
    return extract_json(text)


def normalize_bug(item: dict[str, Any]) -> BugFinding:
    severity = str(item.get("severity", "low")).lower()
    if severity not in SEVERITY_ORDER:
        severity = "low"
    return BugFinding(
        line=int(item.get("line", 0) or 0),
        severity=severity,
        title=str(item.get("title", "Untitled bug")),
        explanation=str(item.get("explanation", "")),
        trigger_example=str(item.get("trigger_example", "")),
        confidence=float(item.get("confidence", 0.0) or 0.0),
    )


def render_summary(summary: str, confidence: float, bug_count: int) -> None:
    panel = Panel(
        f"[bold]Summary:[/bold] {summary}\n\n[bold]Bugs found:[/bold] {bug_count}\n[bold]Overall confidence:[/bold] {confidence:.2f}",
        title="Bug Hunter",
        border_style="blue",
    )
    console.print(panel)


def render_table(bugs: list[BugFinding]) -> None:
    if not bugs:
        console.print(Panel("No logic bugs were found in this file.", title="Findings", border_style="green"))
        return

    table = Table(title="Bug Findings")
    table.add_column("Line", style="bold")
    table.add_column("Severity")
    table.add_column("Title")
    table.add_column("Confidence")
    for bug in sorted(bugs, key=lambda item: (SEVERITY_ORDER[item.severity], item.line or 10**9)):
        severity_style = SEVERITY_STYLES[bug.severity]
        table.add_row(
            str(bug.line or "-"),
            f"[{severity_style}]{bug.severity.upper()}[/{severity_style}]",
            bug.title,
            f"{bug.confidence:.2f}",
        )
    console.print(table)


def render_details(bugs: list[BugFinding]) -> None:
    if not bugs:
        return
    for bug in sorted(bugs, key=lambda item: (SEVERITY_ORDER[item.severity], item.line or 10**9)):
        console.print(
            Panel(
                f"[bold]Line:[/bold] {bug.line or 'unknown'}\n"
                f"[bold]Severity:[/bold] {bug.severity.upper()}\n"
                f"[bold]Why it is a bug:[/bold] {bug.explanation}\n"
                f"[bold]Trigger example:[/bold] {bug.trigger_example}\n"
                f"[bold]Confidence:[/bold] {bug.confidence:.2f}",
                title=bug.title,
                border_style=SEVERITY_STYLES[bug.severity],
            )
        )


def copy_to_clipboard(text: str) -> None:
    try:
        pyperclip.copy(text)
        return
    except Exception:
        if sys.platform.startswith("win"):
            subprocess.run(["clip"], input=text, text=True, check=True)
            return
        raise BugHunterError("Could not copy to clipboard. Install pyperclip or use a supported clipboard command.")


def write_back(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    console.print(f"[green]Wrote fixed code to[/green] {path}")


def main() -> int:
    args = parse_args()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        die("Missing ANTHROPIC_API_KEY. Set it in your environment or .env file.")

    try:
        code, path = read_code(args)
        language = infer_language(args, path, code)
    except BugHunterError as exc:
        die(str(exc))

    client = Anthropic(api_key=api_key)
    payload = call_claude(client, args.model, build_prompt(code, language))

    bugs = [normalize_bug(item) for item in payload.get("bugs", [])]
    fixed_code = str(payload.get("fixed_code", ""))
    summary = str(payload.get("summary", ""))
    confidence = float(payload.get("confidence", 0.0) or 0.0)

    render_summary(summary, confidence, len(bugs))
    render_table(bugs)
    render_details(bugs)

    console.print(Panel(fixed_code or "(no fixed code returned)", title="Fixed Code", border_style="magenta"))

    if args.fix:
        if not path:
            die("--fix requires --file so the corrected code can be written back.")
        if not fixed_code.strip():
            die("Claude did not return fixed code.")
        write_back(path, fixed_code)

    if args.copy_fix:
        if not fixed_code.strip():
            die("Claude did not return fixed code to copy.")
        try:
            copy_to_clipboard(fixed_code)
            console.print("[green]Fixed code copied to clipboard.[/green]")
        except BugHunterError as exc:
            die(str(exc))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
