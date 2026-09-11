#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel

from parsers.format_detector import detect_format, parse_transcript

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze meeting transcripts for summaries and action items.")
    parser.add_argument("--transcript", required=True, help="Transcript file path")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--format", choices=["markdown", "slack", "jira", "plain"], default="markdown", help="Output format")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(1)


def _chunk_text(text: str, chunk_size: int = 10000) -> list[str]:
    """Split text into chunks at line boundaries, each under chunk_size chars."""
    lines = text.split("\n")
    chunks = []
    current = []
    current_len = 0
    for line in lines:
        if current_len + len(line) > chunk_size and current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def analyze_transcript(client: Anthropic, model: str, transcript_text: str) -> dict:
    """Analyze meeting transcript with Claude. Chunks long transcripts automatically."""
    if len(transcript_text) <= 12000:
        return _analyze_chunk(client, model, transcript_text, is_final=True)

    console.print(
        f"[cyan]Long transcript detected ({len(transcript_text)} chars) — "
        f"processing in chunks...[/cyan]"
    )

    chunks = _chunk_text(transcript_text)
    partial_analyses = []

    for i, chunk in enumerate(chunks):
        console.print(f"[cyan]Analyzing chunk {i+1}/{len(chunks)}...[/cyan]")
        partial = _analyze_chunk(client, model, chunk, is_final=False)
        partial_analyses.append(partial)

    merge_prompt = f"""You are merging {len(partial_analyses)} partial meeting analyses from
different segments of the same meeting into one final combined analysis.

Partial analyses:
{json.dumps(partial_analyses, indent=2)}

Combine them into one final result. Deduplicate action items and topics that appear in multiple
segments (they're likely the same item mentioned twice). Keep the executive summary concise
(3-4 sentences covering the whole meeting, not just one segment).

Return valid JSON only in this exact schema:
{{
  "summary": "...",
  "topics": [...],
  "decisions": [...],
  "action_items": [{{"task": "...", "owner": "...", "deadline": "..."}}],
  "open_questions": [...],
  "followup_needed": true/false
}}"""

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        system="You are an expert meeting analyst merging partial analyses into one final result.",
        messages=[{"role": "user", "content": merge_prompt}],
    )

    text = "".join(
        block.text for block in response.content if getattr(block, "text", None)
    ).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        return {"summary": "Merge failed", "action_items": []}


def _analyze_chunk(
    client: Anthropic,
    model: str,
    text: str,
    is_final: bool,
) -> dict:
    """Analyze a single chunk (or the full transcript if short enough)."""
    prompt = f"""Analyze this meeting transcript {"segment" if not is_final else ""} and extract:
1. Executive summary (3-4 sentences)
2. Key discussion topics (bulleted)
3. Decisions made (explicit agreements only)
4. Action items (must have: WHAT, WHO is responsible, deadline if mentioned)
5. Open questions / unresolved items
6. Follow-up meeting needed?

Transcript:
{text}

Return valid JSON only: {{
  "summary": "...",
  "topics": [...],
  "decisions": [...],
  "action_items": [
    {{
      "task": "...",
      "owner": "...",
      "deadline": "..."
    }}
  ],
  "open_questions": [...],
  "followup_needed": true/false
}}"""

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        system="You are an expert meeting analyst. Extract actionable information from transcripts.",
        messages=[{"role": "user", "content": prompt}],
    )

    text_out = "".join(
        block.text for block in response.content if getattr(block, "text", None)
    ).strip()

    try:
        return json.loads(text_out)
    except json.JSONDecodeError:
        start = text_out.find("{")
        end = text_out.rfind("}")
        if start != -1 and end > start:
            return json.loads(text_out[start:end + 1])
        return {"summary": "Parse failed", "action_items": []}


def format_output(analysis: dict, format_type: str) -> str:
    """Format analysis output."""
    if format_type == "markdown":
        lines = [
            "# Meeting Notes\n",
            f"## Summary\n{analysis.get('summary', 'N/A')}\n",
            "## Key Topics",
        ]
        for topic in analysis.get("topics", []):
            lines.append(f"- {topic}")
        
        lines.append("\n## Decisions")
        for decision in analysis.get("decisions", []):
            lines.append(f"- {decision}")
        
        lines.append("\n## Action Items")
        for item in analysis.get("action_items", []):
            owner = item.get("owner", "Unassigned")
            deadline = item.get("deadline", "No deadline")
            lines.append(f"- **{item.get('task', 'Task')}** (@{owner}, due: {deadline})")
        
        return "\n".join(lines)
    
    elif format_type == "slack":
        lines = [
            ":memo: *Meeting Summary*",
            f"_{analysis.get('summary', 'N/A')}_",
            "",
            "*Action Items:*",
        ]
        for item in analysis.get("action_items", []):
            lines.append(f"• {item.get('task', 'Task')} — @{item.get('owner', 'TBD')} (due {item.get('deadline', 'TBD')})")
        return "\n".join(lines)
    
    elif format_type == "jira":
        lines = ["Summary,Assignee,Due Date,Description"]
        for item in analysis.get("action_items", []):
            task = item.get("task", "Task").replace(",", ";")
            owner = item.get("owner", "Unassigned")
            deadline = item.get("deadline", "")
            lines.append(f'"{task}",{owner},{deadline},"Action item from meeting"')
        return "\n".join(lines)
    
    else:  # plain
        lines = [
            f"MEETING SUMMARY\n{analysis.get('summary', 'N/A')}\n",
            "ACTION ITEMS",
        ]
        for item in analysis.get("action_items", []):
            lines.append(f"- {item.get('task', 'Task')} ({item.get('owner', 'Unassigned')}, due {item.get('deadline', 'TBD')})")
        return "\n".join(lines)


def main() -> int:
    args = parse_args()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        die("Missing ANTHROPIC_API_KEY.")

    try:
        transcript_content = Path(args.transcript).read_text()
    except Exception as exc:
        die(f"Failed to read transcript: {exc}")

    console.print(f"[cyan]Detecting transcript format...[/cyan]")
    fmt = detect_format(transcript_content)
    console.print(f"[cyan]Format: {fmt}[/cyan]")

    client = Anthropic(api_key=api_key)
    analysis = analyze_transcript(client, args.model, transcript_content)

    output = format_output(analysis, args.format)
    console.print(Panel(output, title="Meeting Analysis", border_style="blue"))

    if args.output:
        Path(args.output).write_text(output)
        console.print(f"[green]Saved to {args.output}[/green]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
