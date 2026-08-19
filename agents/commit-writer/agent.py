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

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"
EMOJI_MAP = {
    "feat": "✨",
    "fix": "🐛",
    "docs": "📚",
    "style": "🎨",
    "refactor": "♻️",
    "perf": "⚡",
    "test": "✅",
    "chore": "🔧",
    "ci": "👷",
    "build": "🏗️",
}


@dataclass(frozen=True)
class CommitCandidate:
    type: str
    scope: str
    subject: str
    body_lines: list[str]
    breaking: bool
    refs: str | None
    reason: str

    def headline(self, emoji: bool = False) -> str:
        if not self.type:
            return self.subject
        prefix = self.type
        if emoji and self.type in EMOJI_MAP:
            prefix = f"{EMOJI_MAP[self.type]} {prefix}"
        scope = f"({self.scope})" if self.scope else ""
        headline = f"{prefix}{scope}: {self.subject}".strip()
        if self.refs:
            headline = f"{headline}\n\nRefs: {self.refs}"
        return headline

    def full_message(self, emoji: bool = False) -> str:
        lines = [self.headline(emoji=emoji)]
        if self.body_lines:
            lines.append("")
            lines.extend(f"- {line}" for line in self.body_lines)
        if self.breaking:
            lines.extend(["", "BREAKING CHANGE: This commit includes breaking changes."])
        return "\n".join(lines).strip()


class CommitWriterError(RuntimeError):
    pass


SYSTEM_PROMPT = """You are an expert in Conventional Commits and Git history hygiene.
Given a staged git diff, generate three high-quality commit message candidates.
Be concise, accurate, and specific.
Use these commit types only: feat, fix, docs, style, refactor, perf, test, chore, ci, build.
Infer the best scope from the files changed.
If an issue number is detectable from the branch name, include it in Refs.
Return valid JSON only.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate conventional commit messages from staged changes.")
    parser.add_argument("--just-one", action="store_true", help="Use the best candidate directly")
    parser.add_argument("--emoji", action="store_true", help="Add gitmoji prefixes to the selected commit message")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model to use (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(1)


def run_git(args: list[str]) -> str:
    completed = subprocess.run(["git", *args], capture_output=True, text=True)
    if completed.returncode != 0:
        raise CommitWriterError(completed.stderr.strip() or completed.stdout.strip() or "Git command failed.")
    return completed.stdout.strip()


def ensure_git_repo() -> None:
    try:
        inside = run_git(["rev-parse", "--is-inside-work-tree"])
    except CommitWriterError as exc:
        raise CommitWriterError("Not in a git repository. Run this inside a repository.") from exc
    if inside.lower() != "true":
        raise CommitWriterError("Not in a git repository. Run this inside a repository.")


def get_staged_diff() -> tuple[list[str], str]:
    staged_files = run_git(["diff", "--staged", "--name-only"]).splitlines()
    if not any(name.strip() for name in staged_files):
        raise CommitWriterError("Run git add first. There are no staged changes.")
    diff = run_git(["diff", "--staged", "--unified=3"])
    return [name.strip() for name in staged_files if name.strip()], diff


def detect_scope(files: list[str]) -> str:
    ignore = {"src", "lib", "app", "test", "tests", "spec", "packages", "cmd", "internal", "server", "client", "docs"}
    candidates: list[str] = []
    for file_name in files:
        parts = Path(file_name).parts
        if len(parts) > 1:
            for part in parts[:-1]:
                lowered = part.lower()
                if lowered not in ignore and re.fullmatch(r"[a-zA-Z0-9_.-]+", part):
                    candidates.append(lowered)
                    break
    if not candidates:
        return ""
    return max(set(candidates), key=candidates.count)


def detect_issue_ref(branch_name: str) -> str | None:
    patterns = [
        r"#(\d+)",
        r"(?:issue|bug|task|story)[/-](\d+)",
        r"(?:[/-])(\d{2,6})(?:[/-]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, branch_name, re.IGNORECASE)
        if match:
            return f"#{match.group(1)}"
    return None


def build_prompt(files: list[str], diff: str, scope: str, issue_ref: str | None, branch_name: str) -> str:
    files_text = "\n".join(f"- {file_name}" for file_name in files)
    return f"""Create three candidate Conventional Commit messages from the staged diff.

Branch name: {branch_name}
Detected scope: {scope or 'unknown'}
Issue reference: {issue_ref or 'none'}
Changed files:
{files_text}

Return valid JSON only with this schema:
{{
  "candidates": [
    {{
      "type": "feat|fix|docs|style|refactor|perf|test|chore|ci|build",
      "scope": "string",
      "subject": "short description in imperative mood",
      "body_lines": ["bullet 1", "bullet 2"],
      "breaking": false,
      "refs": "#123 or null",
      "reason": "why this message is a strong choice"
    }}
  ]
}}

Rules:
- Return exactly 3 candidates with meaningfully different phrasings.
- Keep the subject line concise.
- Use the conventional commits spec.
- Include issue refs only if they are actually present.
- Infer the intent from the diff, not from the branch name alone.

DIFF:
{diff}
"""


def extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise CommitWriterError("Claude did not return valid JSON.")
        return json.loads(text[start : end + 1])


def call_claude(client: Anthropic, model: str, prompt: str) -> dict[str, Any]:
    response = client.messages.create(
        model=model,
        max_tokens=3000,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if getattr(block, "text", None)).strip()
    return extract_json(text)


def normalize_candidates(payload: dict[str, Any], issue_ref: str | None) -> list[CommitCandidate]:
    candidates: list[CommitCandidate] = []
    for item in payload.get("candidates", [])[:3]:
        scope = str(item.get("scope", "")).strip()
        refs = item.get("refs") or issue_ref
        if isinstance(refs, str) and not refs.startswith("#"):
            refs = f"#{refs}"
        candidates.append(
            CommitCandidate(
                type=str(item.get("type", "chore")).strip(),
                scope=scope,
                subject=str(item.get("subject", "update code")).strip(),
                body_lines=[str(line).strip() for line in item.get("body_lines", []) if str(line).strip()],
                breaking=bool(item.get("breaking", False)),
                refs=str(refs) if refs else None,
                reason=str(item.get("reason", "")),
            )
        )
    if len(candidates) != 3:
        raise CommitWriterError("Claude did not return exactly three commit candidates.")
    return candidates


def render_candidates(candidates: list[CommitCandidate], emoji: bool) -> None:
    table = Table(title="Commit Candidates")
    table.add_column("Choice")
    table.add_column("Commit message")
    table.add_column("Reason")
    for index, candidate in enumerate(candidates, start=1):
        table.add_row(str(index), candidate.full_message(emoji=emoji), candidate.reason)
    console.print(table)


def copy_to_clipboard(text: str) -> None:
    if sys.platform.startswith("win"):
        subprocess.run(["clip"], input=text, text=True, check=True)
        return
    if sys.platform == "darwin":
        subprocess.run(["pbcopy"], input=text, text=True, check=True)
        return
    subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)


def choose_candidate(candidates: list[CommitCandidate], emoji: bool, just_one: bool) -> CommitCandidate:
    if just_one or not sys.stdin.isatty():
        return candidates[0]

    while True:
        choice = console.input("Choose 1, 2, or 3, or type e to edit: ").strip().lower()
        if choice in {"1", "2", "3"}:
            return candidates[int(choice) - 1]
        if choice == "e":
            edited = console.input("Paste your edited commit message: ").strip()
            if edited:
                return CommitCandidate(type="", scope="", subject=edited, body_lines=[], breaking=False, refs=None, reason="User edited")
        console.print("[yellow]Please choose 1, 2, 3, or e.[/yellow]")


def prompt_to_commit(message: str) -> None:
    answer = console.input("Run git commit -m now? [y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        return
    subject, *rest = message.split("\n\n", 1)
    body = rest[0] if rest else ""
    cmd = ["git", "commit", "-m", subject]
    if body:
        cmd.extend(["-m", body])
    completed = subprocess.run(cmd, text=True)
    if completed.returncode != 0:
        raise CommitWriterError("git commit failed.")
    console.print("[green]git commit completed.[/green]")


def main() -> int:
    args = parse_args()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        die("Missing ANTHROPIC_API_KEY. Set it in your environment or .env file.")

    try:
        ensure_git_repo()
        files, diff = get_staged_diff()
        branch_name = run_git(["branch", "--show-current"]) or "unknown"
        scope = detect_scope(files)
        issue_ref = detect_issue_ref(branch_name)
        client = Anthropic(api_key=api_key)
        payload = call_claude(client, args.model, build_prompt(files, diff, scope, issue_ref, branch_name))
        candidates = normalize_candidates(payload, issue_ref)
    except CommitWriterError as exc:
        die(str(exc))

    render_candidates(candidates, args.emoji)
    chosen = choose_candidate(candidates, args.emoji, args.just_one)
    message = chosen.full_message(emoji=args.emoji)

    try:
        copy_to_clipboard(message)
        console.print("[green]Commit message copied to clipboard.[/green]")
    except Exception:
        console.print("[yellow]Clipboard copy failed. You can copy the displayed message manually.[/yellow]")

    console.print(Panel(message, title="Selected Commit Message", border_style="green"))

    try:
        prompt_to_commit(message)
    except CommitWriterError as exc:
        die(str(exc))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
