#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate release notes from git history.")
    parser.add_argument("--from", dest="from_ref", required=True, help="Starting ref (tag/commit/branch)")
    parser.add_argument("--to", dest="to_ref", default="HEAD", help="Ending ref (default: HEAD)")
    parser.add_argument("--output", help="Write to file instead of stdout")
    parser.add_argument("--append", action="store_true", help="Append to existing CHANGELOG.md")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    parser.add_argument("--audience", choices=["users", "developers"], default="users", help="Tone/audience")
    parser.add_argument("--include-internal", action="store_true", help="Include chore/internal commits")
    parser.add_argument("--credit-contributors", action="store_true", help="Add contributor credits section")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(1)


def get_commit_log(from_ref: str, to_ref: str) -> list[dict]:
    """Fetch commit log between two refs. Handles multi-line commit bodies correctly."""
    record_sep = "\x1e"  # ASCII record separator - won't appear in normal commit text
    field_sep = "\x1f"   # ASCII unit separator
    try:
        cmd = [
            "git", "log", f"{from_ref}..{to_ref}",
            f"--pretty=format:%H{field_sep}%s{field_sep}%b{field_sep}%an{field_sep}%ad{record_sep}",
            "--date=short",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        die(f"Git log failed: {exc.stderr}")

    commits = []
    raw_records = result.stdout.strip().split(record_sep)
    for record in raw_records:
        record = record.strip()
        if not record:
            continue
        parts = record.split(field_sep)
        if len(parts) >= 5:
            commits.append({
                "hash": parts[0][:7],
                "subject": parts[1],
                "body": parts[2].strip(),
                "author": parts[3],
                "date": parts[4],
            })

    return commits


def group_commits(client: Anthropic, model: str, commits: list[dict], audience: str, include_internal: bool) -> dict:
    """Send commits to Claude for intelligent grouping and rewriting."""
    commits_text = "\n".join(
        f"- [{c['hash']}] {c['subject']} ({c['author']})" for c in commits
    )

    prompt = f"""Given these git commits, group them into categories and rewrite each into a clear, user-facing description.

Commits:
{commits_text}

Instructions:
- Group by: New Features, Improvements, Bug Fixes, Breaking Changes, Documentation{', Internal/Chore' if include_internal else ''}
- Rewrite each commit into a single clear sentence (not developer jargon)
- Merge related/duplicate commits into single bullets
- Skip noise unless --include-internal: 'wip', 'fix typo', 'merge branch'
- Detect BREAKING CHANGE from commit body
- Audience: {"users (no technical jargon, focus on value)" if audience == "users" else "developers (technical detail, file/module context)"}

Return valid JSON only: {{
  "version_summary": "2-sentence overview",
  "breaking_changes": [...],
  "features": [...],
  "improvements": [...],
  "bug_fixes": [...]}}{f", \"internal\": [...]" if include_internal else ""}
}}"""

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        system="You are a technical writer creating release notes. Rewrite commits into clear, user-facing language.",
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
        return {"version_summary": "Parse failed", "features": []}


def format_markdown(grouped: dict, version: str, date: str) -> str:
    """Format grouped commits as Keep a Changelog markdown."""
    lines = [
        f"## [{version}] - {date}",
        "",
        f"### Summary\n{grouped.get('version_summary', 'N/A')}",
        "",
    ]

    for section, title in [
        ("breaking_changes", "⚠️ Breaking Changes"),
        ("features", "✨ New Features"),
        ("improvements", "🚀 Improvements"),
        ("bug_fixes", "🐛 Bug Fixes"),
        ("internal", "🔧 Internal"),
    ]:
        items = grouped.get(section, [])
        if items:
            lines.append(f"### {title}")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        die("Missing ANTHROPIC_API_KEY.")

    commits = get_commit_log(args.from_ref, args.to_ref)
    if not commits:
        console.print(f"[yellow]No commits found between {args.from_ref}..{args.to_ref}[/yellow]")
        return 0

    console.print(f"[cyan]Found {len(commits)} commits.[/cyan]")

    client = Anthropic(api_key=api_key)
    grouped = group_commits(client, args.model, commits, args.audience, args.include_internal)

    version = args.to_ref if args.to_ref not in ["HEAD", "main", "master"] else "Unreleased"
    date_str = datetime.now().strftime("%Y-%m-%d")

    if args.format == "json":
        output = json.dumps({**grouped, "version": version, "date": date_str}, indent=2)
    else:
        output = format_markdown(grouped, version, date_str)

    console.print(Panel(output, title="Release Notes", border_style="green"))

    if args.output:
        path = Path(args.output)
        if args.append and path.exists():
            existing = path.read_text()
            output = output + "\n\n" + existing
        path.write_text(output)
        console.print(f"[green]Saved to {args.output}[/green]")

    return 0


if __name__ == "__main__":
    import os
    raise SystemExit(main())
