#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable, Sequence

import requests
from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()
GITHUB_API = "https://api.github.com"
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_DIFF_CHARS = 100_000
CHUNK_TARGET_CHARS = 45_000
PR_URL_RE = re.compile(r"^https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/pull/(?P<number>\d+)(?:/.*)?$")


@dataclass(frozen=True)
class PullRequest:
    owner: str
    repo: str
    number: int
    title: str
    body: str
    state: str
    html_url: str
    base_branch: str
    head_branch: str
    additions: int
    deletions: int
    changed_files: int


@dataclass(frozen=True)
class PRFile:
    filename: str
    status: str
    additions: int
    deletions: int
    patch: str | None
    raw_url: str | None
    blob_url: str | None


class ReviewError(RuntimeError):
    pass


SYSTEM_PROMPT = """You are a senior staff engineer with 10+ years of experience reviewing production code.
You review pull requests carefully and only call out concrete issues that are grounded in the diff.

Requirements for your review:
- Focus on bugs, security, correctness, performance, and maintainability risks.
- Do not invent issues that are not supported by the diff.
- When possible, reference filenames and specific hunks or lines from the patch.
- Give actionable suggestions with precise fixes.
- If a section has no findings, say so explicitly.
- Write in clear GitHub-flavored markdown that can be pasted into a PR comment.
- Use the following sections in order:
  1. Summary of Changes
  2. Bugs Found
  3. Security Issues
  4. Performance Concerns
  5. Line-by-Line Suggestions
  6. Verdict
- Verdict must be one of APPROVE, REQUEST_CHANGES, or NEEDS_DISCUSSION.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review a GitHub pull request with Claude.")
    parser.add_argument("--pr", required=True, help="GitHub pull request URL")
    parser.add_argument("--output", help="Write the review markdown to a file")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model to use (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str, exit_code: int = 1) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(exit_code)


def parse_pr_url(url: str) -> tuple[str, str, int]:
    match = PR_URL_RE.match(url.strip())
    if not match:
        raise ReviewError("Invalid PR URL. Expected a GitHub pull request URL like https://github.com/owner/repo/pull/123")
    return match.group("owner"), match.group("repo"), int(match.group("number"))


def build_github_session(token: str | None) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pr-reviewer/1.0",
        }
    )
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    return session


def rate_limit_message(response: requests.Response) -> str | None:
    reset_header = response.headers.get("X-RateLimit-Reset")
    retry_after = response.headers.get("Retry-After")

    if retry_after:
        try:
            seconds = int(retry_after)
            return f"GitHub rate limit hit. Try again in about {seconds} seconds."
        except ValueError:
            pass

    if reset_header:
        try:
            reset_epoch = int(reset_header)
            wait_seconds = max(0, reset_epoch - int(datetime.now(timezone.utc).timestamp()))
            minutes = math.ceil(wait_seconds / 60)
            return f"GitHub rate limit hit. Try again in about {minutes} minute(s)."
        except ValueError:
            pass

    return None


def github_request(session: requests.Session, url: str, *, params: dict[str, object] | None = None) -> requests.Response:
    response = session.get(url, params=params, timeout=30)
    if response.status_code in {429, 403}:
        message = rate_limit_message(response)
        if message and response.headers.get("X-RateLimit-Remaining") == "0":
            raise ReviewError(message)
    if response.status_code in {401, 403, 404}:
        if response.status_code in {401, 403} and "Authorization" not in session.headers:
            raise ReviewError(
                "GitHub requires authentication for this PR. Set GITHUB_TOKEN with repo read access. "
                "If the repository is public, double-check the PR URL and retry."
            )
        raise ReviewError(response.text.strip() or f"GitHub API request failed with status {response.status_code}.")
    response.raise_for_status()
    return response


def fetch_pull_request(session: requests.Session, owner: str, repo: str, number: int) -> PullRequest:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{number}"
    response = github_request(session, url)
    payload = response.json()
    return PullRequest(
        owner=owner,
        repo=repo,
        number=number,
        title=payload.get("title", "Untitled PR"),
        body=payload.get("body", "") or "",
        state=payload.get("state", "unknown"),
        html_url=payload.get("html_url", f"https://github.com/{owner}/{repo}/pull/{number}"),
        base_branch=(payload.get("base") or {}).get("ref", "unknown"),
        head_branch=(payload.get("head") or {}).get("ref", "unknown"),
        additions=int(payload.get("additions", 0)),
        deletions=int(payload.get("deletions", 0)),
        changed_files=int(payload.get("changed_files", 0)),
    )


def fetch_pr_files(session: requests.Session, owner: str, repo: str, number: int) -> list[PRFile]:
    files: list[PRFile] = []
    page = 1
    while True:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{number}/files"
        response = github_request(session, url, params={"per_page": 100, "page": page})
        batch = response.json()
        if not batch:
            break
        for item in batch:
            files.append(
                PRFile(
                    filename=item.get("filename", "unknown"),
                    status=item.get("status", "unknown"),
                    additions=int(item.get("additions", 0)),
                    deletions=int(item.get("deletions", 0)),
                    patch=item.get("patch"),
                    raw_url=item.get("raw_url"),
                    blob_url=item.get("blob_url"),
                )
            )
        if len(batch) < 100:
            break
        page += 1
    return files


def file_section(pr_file: PRFile) -> str:
    lines = [
        f"File: {pr_file.filename}",
        f"Status: {pr_file.status}",
        f"Additions: {pr_file.additions}",
        f"Deletions: {pr_file.deletions}",
    ]
    if pr_file.patch:
        lines.append("Patch:")
        lines.append(pr_file.patch)
    else:
        lines.append("Patch: <no patch available, likely binary or large file>")
    return "\n".join(lines)


def build_diff_text(files: Sequence[PRFile]) -> str:
    sections = [file_section(item) for item in files]
    return "\n\n".join(f"---\n{section}" for section in sections)


def chunk_sections(sections: Sequence[str], max_chars: int = CHUNK_TARGET_CHARS) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0

    for section in sections:
        size = len(section)
        if current and current_size + size + 2 > max_chars:
            chunks.append("\n\n".join(current))
            current = []
            current_size = 0
        current.append(section)
        current_size += size + 2

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def collect_text(response: object) -> str:
    content = getattr(response, "content", None)
    if not content:
        return ""
    texts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            texts.append(text)
    return "".join(texts).strip()


def call_claude(client: Anthropic, model: str, system_prompt: str, user_prompt: str, max_tokens: int = 3000) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return collect_text(response)


def review_chunk(
    client: Anthropic,
    model: str,
    pr: PullRequest,
    chunk_text: str,
    chunk_index: int,
    chunk_total: int,
) -> str:
    prompt = f"""Review chunk {chunk_index} of {chunk_total} for PR {pr.owner}/{pr.repo}#{pr.number}.

Return concise markdown with only concrete findings from this chunk.
Keep the same section structure as the final review, but you may leave sections empty if there are no findings.

PR title: {pr.title}
PR description: {pr.body or 'N/A'}

DIFF CHUNK:
{chunk_text}
"""
    return call_claude(client, model, SYSTEM_PROMPT, prompt, max_tokens=3500)


def synthesize_reviews(client: Anthropic, model: str, pr: PullRequest, chunk_reviews: Sequence[str]) -> str:
    joined_reviews = "\n\n".join(
        f"Chunk {index + 1}:\n{review}" for index, review in enumerate(chunk_reviews)
    )
    prompt = f"""Combine the partial reviews below into a single final GitHub-ready review for PR {pr.owner}/{pr.repo}#{pr.number}.

Rules:
- Merge duplicate findings.
- Prefer the most specific and actionable wording.
- Keep only concrete issues supported by the partial reviews.
- If there are no issues, say that clearly.
- End with a single verdict line using APPROVE, REQUEST_CHANGES, or NEEDS_DISCUSSION.

PR title: {pr.title}
PR description: {pr.body or 'N/A'}

PARTIAL REVIEWS:
{joined_reviews}
"""
    return call_claude(client, model, SYSTEM_PROMPT, prompt, max_tokens=3500)


def review_pr(client: Anthropic, model: str, pr: PullRequest, files: Sequence[PRFile]) -> str:
    file_sections = [file_section(item) for item in files]
    diff_text = build_diff_text(files)
    if len(diff_text) <= MAX_DIFF_CHARS:
        prompt = f"""Review this pull request.

PR title: {pr.title}
PR description: {pr.body or 'N/A'}
Base branch: {pr.base_branch}
Head branch: {pr.head_branch}
Changed files: {pr.changed_files}
Additions: {pr.additions}
Deletions: {pr.deletions}

DIFF:
{diff_text}
"""
        return call_claude(client, model, SYSTEM_PROMPT, prompt, max_tokens=4500)

    chunks = chunk_sections(file_sections, max_chars=CHUNK_TARGET_CHARS)
    chunk_reviews = [
        review_chunk(client, model, pr, chunk, index + 1, len(chunks))
        for index, chunk in enumerate(chunks)
    ]
    return synthesize_reviews(client, model, pr, chunk_reviews)


def render_pr_summary(pr: PullRequest, file_count: int) -> None:
    table = Table(title="PR Summary", show_header=False, box=None)
    table.add_row("Repository", f"{pr.owner}/{pr.repo}")
    table.add_row("PR", f"#{pr.number} {pr.title}")
    table.add_row("State", pr.state)
    table.add_row("Branches", f"{pr.head_branch} -> {pr.base_branch}")
    table.add_row("Changes", f"{file_count} files, +{pr.additions}/-{pr.deletions}")
    table.add_row("URL", pr.html_url)
    console.print(Panel(table, title="PR Review", border_style="blue"))


def save_output(path: str, review_markdown: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(review_markdown.rstrip() + "\n")
    console.print(f"[green]Saved review to[/green] {path}")


def maybe_rate_limit_message(error: ReviewError) -> str:
    return str(error).strip() or "GitHub API request failed."


def main() -> int:
    args = parse_args()
    github_token = os.getenv("GITHUB_TOKEN")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        die("Missing ANTHROPIC_API_KEY. Set it in your environment or .env file.")

    try:
        owner, repo, number = parse_pr_url(args.pr)
    except ReviewError as exc:
        die(str(exc))

    session = build_github_session(github_token)
    client = Anthropic(api_key=anthropic_key)

    try:
        pr = fetch_pull_request(session, owner, repo, number)
        files = fetch_pr_files(session, owner, repo, number)
    except ReviewError as exc:
        message = maybe_rate_limit_message(exc)
        if "rate limit" in message.lower():
            die(message)
        if not github_token and any(code in message.lower() for code in ("404", "not found", "forbidden", "private")):
            die(
                "GitHub could not access this PR. If this is a private repository, set GITHUB_TOKEN with repo read access. "
                "If the repository is public, double-check the PR URL."
            )
        die(message)

    render_pr_summary(pr, len(files))
    review_markdown = review_pr(client, args.model, pr, files)

    console.print(Panel(review_markdown, title="Claude Review", border_style="green"))
    console.print("\n[bold]Markdown output:[/bold]\n")
    console.print(review_markdown)

    if args.output:
        save_output(args.output, review_markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
