#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pathspec
from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

try:
    from git import Repo
except Exception:  # pragma: no cover - fallback if GitPython is unavailable at runtime
    Repo = None

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEPTH_LIMITS = {"quick": 5, "standard": 20, "deep": 50}
SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "out",
    "coverage",
    "target",
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
}
IMPORTANT_FILENAMES = {
    "readme": 120,
    "package.json": 115,
    "pyproject.toml": 115,
    "cargo.toml": 115,
    "go.mod": 115,
    "main.py": 110,
    "app.py": 108,
    "index.js": 108,
    "index.ts": 108,
    "main.ts": 108,
    "server.py": 106,
    "cli.py": 106,
    "app.ts": 106,
    "app.jsx": 104,
    "app.tsx": 104,
    "index.jsx": 102,
    "index.tsx": 102,
    "dockerfile": 100,
    "makefile": 98,
    "justfile": 98,
    "requirements.txt": 96,
    "poetry.lock": 10,
    "package-lock.json": 10,
    "pnpm-lock.yaml": 10,
    "yarn.lock": 10,
}
FRAMEWORK_HINTS = {
    "react": {"react", "react-dom"},
    "next.js": {"next"},
    "express": {"express"},
    "fastapi": {"fastapi"},
    "django": {"django"},
    "flask": {"flask"},
    "vue": {"vue"},
    "svelte": {"svelte"},
    "nest.js": {"@nestjs/core"},
}


@dataclass(frozen=True)
class SelectedFile:
    path: Path
    score: int
    reason: str
    content: str


class ExplainerError(RuntimeError):
    pass


SYSTEM_PROMPT = "You are a senior engineer explaining this codebase to a new team member. Be specific, practical, and honest about what you can infer from the files you were given."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Explain a codebase by reading its key files and asking Claude.")
    parser.add_argument("--repo", required=True, help="GitHub repository URL")
    parser.add_argument("--depth", choices=sorted(DEPTH_LIMITS), default="standard", help="How many files to inspect")
    parser.add_argument("--format", choices=["terminal", "markdown", "json"], default="terminal", help="Output format")
    parser.add_argument("--save", action="store_true", help="Write the explanation to CODEBASE.md in the cloned repo")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model to use (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(1)


def clone_repo(repo_url: str) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="codebase-explainer-"))
    try:
        if Repo is not None:
            Repo.clone_from(repo_url, temp_dir, depth=1)
            return temp_dir
        subprocess.run(["git", "clone", "--depth", "1", repo_url, str(temp_dir)], check=True, capture_output=True, text=True)
        return temp_dir
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise ExplainerError(f"Failed to clone repository: {exc}") from exc


def load_gitignore_spec(root: Path) -> pathspec.PathSpec | None:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return None
    patterns = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
    patterns = [line for line in patterns if line and not line.lstrip().startswith("#")]
    if not patterns:
        return None
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def is_ignored(relative_path: str, spec: pathspec.PathSpec | None) -> bool:
    if spec and spec.match_file(relative_path):
        return True
    parts = Path(relative_path).parts
    return any(part in SKIP_DIRS for part in parts)


def normalize_name(path: Path) -> str:
    return path.name.lower()


def score_file(path: Path, root: Path, text: str | None = None) -> tuple[int, str]:
    name = normalize_name(path)
    relative = path.relative_to(root).as_posix().lower()
    score = 10
    reason = "source file"

    for key, value in IMPORTANT_FILENAMES.items():
        if name == key or relative.endswith(f"/{key}"):
            score = max(score, value)
            reason = f"important file: {key}"
            break

    if any(segment in relative for segment in ("/src/", "/app/", "/cmd/", "/lib/", "/core/", "/server/")):
        score += 18
        reason = "core implementation file"

    if any(name.endswith(ext) for ext in (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".md", ".json", ".yaml", ".yml", ".toml")):
        score += 8

    if name.startswith(("main.", "app.", "index.", "cli.", "server.")):
        score += 22
        reason = "entry point"

    if text:
        lowered = text.lower()
        if "if __name__ == '__main__'" in lowered or 'if __name__ == "__main__"' in lowered:
            score += 20
            reason = "python entry point"
        if re.search(r"\bmain\s*\(", text):
            score += 10
        if "fastapi(" in lowered or "express()" in lowered or "django" in lowered:
            score += 5

    return score, reason


def parse_python_dependencies(pyproject_text: str) -> list[str]:
    deps: list[str] = []
    for match in re.finditer(r"^[A-Za-z0-9_.-]+(?=\s*[<>=~!])", pyproject_text, re.MULTILINE):
        deps.append(match.group(0))
    return deps


def detect_stack(root: Path) -> dict[str, Any]:
    stack = {
        "languages": [],
        "frameworks": [],
        "package_manager": None,
        "monorepo": False,
        "run_command": None,
        "test_command": None,
    }
    files = {path.name.lower(): path for path in root.rglob("*") if path.is_file()}
    lower_names = set(files)

    if "package.json" in lower_names:
        stack["languages"].append("JavaScript/TypeScript")
        package_json = json.loads(files["package.json"].read_text(encoding="utf-8", errors="ignore"))
        if "pnpm-lock.yaml" in lower_names or package_json.get("packageManager", "").startswith("pnpm"):
            stack["package_manager"] = "pnpm"
        elif "yarn.lock" in lower_names:
            stack["package_manager"] = "yarn"
        else:
            stack["package_manager"] = "npm"
        dependencies = {}
        for group in ("dependencies", "devDependencies", "peerDependencies"):
            dependencies.update(package_json.get(group, {}))
        for framework, hints in FRAMEWORK_HINTS.items():
            if any(dep in dependencies for dep in hints):
                stack["frameworks"].append(framework)
        scripts = package_json.get("scripts", {}) if isinstance(package_json.get("scripts", {}), dict) else {}
        if "dev" in scripts:
            stack["run_command"] = f"{stack['package_manager']} run dev" if stack["package_manager"] else "npm run dev"
        elif "start" in scripts:
            stack["run_command"] = f"{stack['package_manager']} start" if stack["package_manager"] else "npm start"
        if "test" in scripts:
            stack["test_command"] = f"{stack['package_manager']} test" if stack["package_manager"] else "npm test"
        if any(key in package_json for key in ("workspaces", "packageManager")) or (root / "pnpm-workspace.yaml").exists():
            stack["monorepo"] = True

    if "pyproject.toml" in lower_names:
        stack["languages"].append("Python")
        text = files["pyproject.toml"].read_text(encoding="utf-8", errors="ignore")
        deps = parse_python_dependencies(text)
        lower_deps = {dep.lower() for dep in deps}
        for framework in ("fastapi", "django", "flask"):
            if framework in lower_deps:
                stack["frameworks"].append(framework)
        if "poetry" in text.lower():
            stack["package_manager"] = stack["package_manager"] or "poetry"
            stack["run_command"] = "poetry run python main.py"
            stack["test_command"] = "poetry run pytest"

    if "requirements.txt" in lower_names:
        stack["languages"].append("Python")
        req_text = files["requirements.txt"].read_text(encoding="utf-8", errors="ignore").lower()
        for framework in ("fastapi", "django", "flask"):
            if framework in req_text:
                stack["frameworks"].append(framework)
        if stack["package_manager"] is None:
            stack["package_manager"] = "pip"
            stack["run_command"] = stack["run_command"] or "python main.py"
            stack["test_command"] = stack["test_command"] or "pytest"

    if "go.mod" in lower_names:
        stack["languages"].append("Go")
        stack["package_manager"] = stack["package_manager"] or "go"
        stack["run_command"] = stack["run_command"] or "go run ./..."
        stack["test_command"] = stack["test_command"] or "go test ./..."

    if "cargo.toml" in lower_names:
        stack["languages"].append("Rust")
        stack["package_manager"] = stack["package_manager"] or "cargo"
        stack["run_command"] = stack["run_command"] or "cargo run"
        stack["test_command"] = stack["test_command"] or "cargo test"

    if "makefile" in lower_names or "justfile" in lower_names:
        stack["run_command"] = stack["run_command"] or "make run"
        stack["test_command"] = stack["test_command"] or "make test"

    if any(name in lower_names for name in ("turbo.json", "nx.json", "go.work", "pnpm-workspace.yaml", "workspace.json")):
        stack["monorepo"] = True

    stack["languages"] = sorted(set(stack["languages"])) or ["Unknown"]
    stack["frameworks"] = sorted(set(stack["frameworks"])) or ["Unknown"]
    return stack


def file_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def collect_selected_files(root: Path, depth: str) -> list[SelectedFile]:
    spec = load_gitignore_spec(root)
    limit = DEPTH_LIMITS[depth]
    candidates: list[SelectedFile] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if is_ignored(relative, spec):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".tar", ".gz", ".exe", ".dll", ".so", ".bin"}:
            continue
        try:
            text = file_text(path)
        except Exception:
            continue
        score, reason = score_file(path, root, text)
        candidates.append(SelectedFile(path=path, score=score, reason=reason, content=text[:20_000]))

    candidates.sort(key=lambda item: (-item.score, len(item.content), item.path.as_posix()))
    return candidates[:limit]


def summarize_monorepo(root: Path) -> str:
    markers = ["pnpm-workspace.yaml", "turbo.json", "nx.json", "go.work", "workspace.json"]
    if any((root / marker).exists() for marker in markers):
        return "Workspace/monorepo markers were found at the root."
    package_json = root / "package.json"
    if package_json.exists():
        try:
            payload = json.loads(package_json.read_text(encoding="utf-8", errors="ignore"))
            if any(key in payload for key in ("workspaces", "packageManager")):
                return "The root package.json suggests a workspace or monorepo layout."
        except Exception:
            pass
    return "No obvious monorepo markers were found."


def build_prompt(root: Path, repo_url: str, selected_files: list[SelectedFile], stack: dict[str, Any]) -> str:
    file_blocks = []
    for selected in selected_files:
        relative = selected.path.relative_to(root).as_posix()
        block = f"FILE: {relative}\nREASON: {selected.reason}\nCONTENT:\n{selected.content}"
        file_blocks.append(block)
    return f"""Analyze this repository and return valid JSON only.

Repository URL: {repo_url}
Detected languages: {', '.join(stack['languages'])}
Detected frameworks: {', '.join(stack['frameworks'])}
Package manager: {stack['package_manager'] or 'unknown'}
Run command guess: {stack['run_command'] or 'unknown'}
Test command guess: {stack['test_command'] or 'unknown'}
Monorepo guess: {stack['monorepo']}

Required JSON schema:
{{
  "what_it_does_eli5": "string",
  "what_it_does_technical": "string",
  "tech_stack": ["string"],
  "architecture_overview": ["string"],
  "key_files": [{{"path": "string", "what_it_does": "string"}}],
  "how_to_run": ["string"],
  "how_to_contribute": ["string"],
  "gotchas": ["string"],
  "monorepo_notes": "string",
  "confidence": 0.0
}}

Rules:
- Be honest when something is inferred rather than explicitly documented.
- If there is no README, say so in the explanation.
- Explain the codebase for a new teammate.
- Keep the output concise but complete.

FILES:
{chr(10).join(file_blocks)}
"""


def extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ExplainerError("Claude did not return valid JSON.")
        return json.loads(match.group(0))


def call_claude(client: Anthropic, model: str, prompt: str) -> dict[str, Any]:
    response = client.messages.create(
        model=model,
        max_tokens=5000,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return extract_json("".join(block.text for block in response.content if getattr(block, "text", None)).strip())


def render_markdown(data: dict[str, Any], metadata: dict[str, Any]) -> str:
    lines = [
        f"# Codebase Explanation",
        "",
        f"**Repository:** {metadata['repo_url']}",
        f"**Languages:** {', '.join(metadata['languages'])}",
        f"**Frameworks:** {', '.join(metadata['frameworks'])}",
        f"**Package manager:** {metadata['package_manager'] or 'unknown'}",
        "",
        "## What it does",
        data.get("what_it_does_eli5", ""),
        "",
        "## Technical summary",
        data.get("what_it_does_technical", ""),
        "",
        "## Tech stack",
    ]
    for item in data.get("tech_stack", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Architecture overview"])
    for item in data.get("architecture_overview", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Key files"])
    for item in data.get("key_files", []):
        lines.append(f"- `{item.get('path', '')}` — {item.get('what_it_does', '')}")
    lines.extend(["", "## How to run it locally"])
    for item in data.get("how_to_run", []):
        lines.append(f"- {item}")
    lines.extend(["", "## How to contribute"])
    for item in data.get("how_to_contribute", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Gotchas / non-obvious things"])
    for item in data.get("gotchas", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Monorepo notes", data.get("monorepo_notes", ""), "", f"**Confidence:** {data.get('confidence', 0.0)}"])
    return "\n".join(lines).strip() + "\n"


def render_terminal(data: dict[str, Any], metadata: dict[str, Any]) -> None:
    summary = Table(show_header=False, box=None)
    summary.add_row("Repository", metadata["repo_url"])
    summary.add_row("Languages", ", ".join(metadata["languages"]))
    summary.add_row("Frameworks", ", ".join(metadata["frameworks"]))
    summary.add_row("Files read", str(len(metadata["selected_files"])))
    summary.add_row("Monorepo", "yes" if metadata["monorepo"] else "no")
    console.print(Panel(summary, title="Codebase Explainer", border_style="blue"))

    for title, value in [
        ("What it does", data.get("what_it_does_eli5", "")),
        ("Technical summary", data.get("what_it_does_technical", "")),
        ("Monorepo notes", data.get("monorepo_notes", "")),
    ]:
        console.print(Panel(value or "(not provided)", title=title, border_style="green"))

    tech_table = Table(title="Tech Stack")
    tech_table.add_column("Item")
    for item in data.get("tech_stack", []):
        tech_table.add_row(item)
    console.print(tech_table)

    files_table = Table(title="Key Files")
    files_table.add_column("Path")
    files_table.add_column("What it does")
    for item in data.get("key_files", []):
        files_table.add_row(item.get("path", ""), item.get("what_it_does", ""))
    console.print(files_table)

    console.print(Panel(Markdown(render_markdown(data, metadata)), title="Markdown Output", border_style="magenta"))


def write_save_file(root: Path, markdown: str) -> Path:
    output_path = root / "CODEBASE.md"
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def main() -> int:
    args = parse_args()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        die("Missing ANTHROPIC_API_KEY. Set it in your environment or .env file.")

    try:
        temp_root = clone_repo(args.repo)
    except ExplainerError as exc:
        die(str(exc))

    try:
        selected_files = collect_selected_files(temp_root, args.depth)
        stack = detect_stack(temp_root)
        monorepo_note = summarize_monorepo(temp_root)
        prompt = build_prompt(temp_root, args.repo, selected_files, stack)
        client = Anthropic(api_key=api_key)
        data = call_claude(client, args.model, prompt)
        data.setdefault("monorepo_notes", monorepo_note)
        metadata = {
            "repo_url": args.repo,
            "languages": stack["languages"],
            "frameworks": stack["frameworks"],
            "package_manager": stack["package_manager"],
            "monorepo": stack["monorepo"],
            "selected_files": [item.path.relative_to(temp_root).as_posix() for item in selected_files],
        }
        markdown = render_markdown(data, metadata)

        if args.format == "terminal":
            render_terminal(data, metadata)
        elif args.format == "markdown":
            console.print(markdown)
        else:
            console.print_json(json.dumps({"metadata": metadata, "explanation": data}, indent=2))

        if args.save:
            output_path = write_save_file(temp_root, markdown)
            console.print(f"[green]Saved explanation to[/green] {output_path}")
    finally:
        if not args.save:
            shutil.rmtree(temp_root, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
