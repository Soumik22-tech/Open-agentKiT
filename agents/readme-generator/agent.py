#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pathspec
from anthropic import Anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"
STYLE_LIMITS = {"minimal": 5, "standard": 10, "full": 20}
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
IMPORTANT_FILES = {
    "readme.md": 200,
    "readme": 200,
    "package.json": 180,
    "pyproject.toml": 180,
    "requirements.txt": 180,
    "cargo.toml": 180,
    "go.mod": 180,
    "license": 170,
    "makefile": 160,
    "justfile": 160,
    ".env.example": 150,
    "main.py": 140,
    "app.py": 138,
    "index.js": 138,
    "index.ts": 138,
    "main.ts": 138,
    "cli.py": 136,
    "server.py": 136,
    "app.ts": 136,
    "app.tsx": 134,
    "index.tsx": 132,
    "index.jsx": 132,
    "dockerfile": 120,
}


@dataclass(frozen=True)
class SelectedFile:
    path: Path
    score: int
    reason: str
    content: str


class ReadmeGeneratorError(RuntimeError):
    pass


SYSTEM_PROMPT = "You are a technical writer. Generate a README that would make a developer immediately understand and want to use this project."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a professional README from a local project.")
    parser.add_argument("--project", default=".", help="Path to the local project directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview the generated README without writing it")
    parser.add_argument("--style", choices=sorted(STYLE_LIMITS), default="standard", help="How much context to gather")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model to use (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(1)


def load_gitignore_spec(root: Path) -> pathspec.PathSpec | None:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return None
    patterns = [line for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines() if line and not line.lstrip().startswith("#")]
    if not patterns:
        return None
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def is_ignored(relative_path: str, spec: pathspec.PathSpec | None) -> bool:
    if spec and spec.match_file(relative_path):
        return True
    parts = Path(relative_path).parts
    return any(part in SKIP_DIRS for part in parts)


def file_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def score_file(path: Path, root: Path) -> tuple[int, str]:
    name = path.name.lower()
    relative = path.relative_to(root).as_posix().lower()
    score = 20
    reason = "source file"

    for key, value in IMPORTANT_FILES.items():
        if name == key or relative.endswith(f"/{key}"):
            score = max(score, value)
            reason = f"important file: {key}"
            break

    if any(segment in relative for segment in ("/src/", "/app/", "/lib/", "/cmd/", "/server/", "/client/", "/core/")):
        score += 20
        reason = "core source file"

    if name.startswith(("main.", "app.", "index.", "cli.", "server.")):
        score += 25
        reason = "entry point"

    if any(name.endswith(ext) for ext in (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".php", ".cs")):
        score += 10

    if "test" in relative or relative.endswith(("_test.py", ".test.ts", ".spec.ts", ".test.js", ".spec.js")):
        score -= 40

    return score, reason


def detect_language(root: Path) -> str:
    extensions = Counter()
    for path in root.rglob("*"):
        if path.is_file() and path.suffix:
            extensions[path.suffix.lower()] += 1
    if not extensions:
        return "Unknown"
    top = extensions.most_common(1)[0][0]
    return {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript/React",
        ".jsx": "JavaScript/React",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
    }.get(top, top.lstrip(".").upper())


def detect_package_manager(root: Path) -> str | None:
    package_json = root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(file_text(package_json))
        except Exception:
            data = {}
        if data.get("packageManager", "").startswith("pnpm") or (root / "pnpm-lock.yaml").exists():
            return "pnpm"
        if (root / "yarn.lock").exists():
            return "yarn"
        return "npm"
    if (root / "pyproject.toml").exists():
        text = file_text(root / "pyproject.toml").lower()
        if "poetry" in text:
            return "poetry"
        if "uv" in text:
            return "uv"
        return "pip"
    if (root / "go.mod").exists():
        return "go"
    if (root / "Cargo.toml").exists():
        return "cargo"
    return None


def detect_commands(root: Path, package_manager: str | None) -> dict[str, str | None]:
    commands = {"install": None, "run": None, "test": None}
    if package_manager == "npm":
        commands.update({"install": "npm install", "run": "npm run dev", "test": "npm test"})
    elif package_manager == "pnpm":
        commands.update({"install": "pnpm install", "run": "pnpm run dev", "test": "pnpm test"})
    elif package_manager == "yarn":
        commands.update({"install": "yarn install", "run": "yarn dev", "test": "yarn test"})
    elif package_manager == "poetry":
        commands.update({"install": "poetry install", "run": "poetry run python main.py", "test": "poetry run pytest"})
    elif package_manager == "pip":
        commands.update({"install": "pip install -r requirements.txt", "run": "python main.py", "test": "pytest"})
    elif package_manager == "uv":
        commands.update({"install": "uv sync", "run": "uv run python main.py", "test": "uv run pytest"})
    elif package_manager == "go":
        commands.update({"install": "go mod tidy", "run": "go run .", "test": "go test ./..."})
    elif package_manager == "cargo":
        commands.update({"install": "cargo build", "run": "cargo run", "test": "cargo test"})

    if (root / "Makefile").exists() or (root / "makefile").exists():
        commands["run"] = commands["run"] or "make run"
        commands["test"] = commands["test"] or "make test"
    if (root / "justfile").exists():
        commands["run"] = commands["run"] or "just run"
        commands["test"] = commands["test"] or "just test"

    return commands


def detect_license(root: Path) -> str | None:
    for candidate in ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]:
        path = root / candidate
        if path.exists():
            first_line = file_text(path).splitlines()[:3]
            return first_line[0].strip() if first_line else candidate
    return None


def detect_env_vars(root: Path, selected_files: list[SelectedFile]) -> list[str]:
    values = set()
    env_example = root / ".env.example"
    if env_example.exists():
        for line in file_text(env_example).splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key = line.split("=", 1)[0].strip()
            if key:
                values.add(key)

    patterns = [
        r"os\.getenv\(\s*['\"]([A-Z0-9_]+)['\"]",
        r"os\.environ\.get\(\s*['\"]([A-Z0-9_]+)['\"]",
        r"process\.env\.([A-Z0-9_]+)",
        r"import\.meta\.env\.([A-Z0-9_]+)",
        r"ENV\[['\"]([A-Z0-9_]+)['\"]\]",
    ]
    for selected in selected_files:
        text = selected.content
        for pattern in patterns:
            values.update(match.group(1) for match in re.finditer(pattern, text))
    return sorted(values)


def collect_selected_files(root: Path, style: str) -> list[SelectedFile]:
    spec = load_gitignore_spec(root)
    limit = STYLE_LIMITS[style]
    mandatory_names = {
        "readme.md",
        "readme",
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "cargo.toml",
        "go.mod",
        "license",
        "license.md",
        "license.txt",
        "copying",
        ".env.example",
        "makefile",
        "justfile",
    }
    selected: list[SelectedFile] = []
    seen: set[Path] = set()

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if is_ignored(relative, spec):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".tar", ".gz", ".exe", ".dll", ".so", ".bin", ".lock"}:
            continue
        try:
            content = file_text(path)
        except Exception:
            continue
        score, reason = score_file(path, root)
        selected.append(SelectedFile(path=path, score=score, reason=reason, content=content[:20_000]))

    selected.sort(key=lambda item: (-item.score, len(item.content), item.path.as_posix()))

    curated: list[SelectedFile] = []
    for item in selected:
        if item.path.name.lower() in mandatory_names or item.path.name.lower() in mandatory_names or item.path.suffix.lower() in {".md", ".toml", ".json", ".txt", ".yaml", ".yml", ".py", ".js", ".ts", ".tsx", ".go", ".rs", ".java", ".rb", ".php", ".cs"}:
            curated.append(item)
            seen.add(item.path)

    for item in selected:
        if item.path in seen:
            continue
        curated.append(item)
        if len(curated) >= limit:
            break

    return curated[:limit]


def detect_project_name(root: Path) -> str:
    package_json = root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(file_text(package_json))
            if data.get("name"):
                return str(data["name"])
        except Exception:
            pass
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = file_text(pyproject)
        match = re.search(r"^name\s*=\s*[\"']([^\"']+)[\"']", text, re.MULTILINE)
        if match:
            return match.group(1)
    return root.name


def build_prompt(root: Path, project_name: str, selected_files: list[SelectedFile], metadata: dict[str, Any]) -> str:
    blocks = []
    for selected in selected_files:
        relative = selected.path.relative_to(root).as_posix()
        blocks.append(
            f"FILE: {relative}\nREASON: {selected.reason}\nCONTENT:\n{selected.content}"
        )

    env_vars = metadata.get("env_vars", [])
    env_text = ", ".join(env_vars) if env_vars else "none detected"
    license_text = metadata.get("license") or "unknown"

    return f"""Generate a production-ready README.md in markdown only.

Project name: {project_name}
Language: {metadata.get('language', 'Unknown')}
Package manager: {metadata.get('package_manager') or 'unknown'}
Install command: {metadata.get('commands', {}).get('install') or 'unknown'}
Run command: {metadata.get('commands', {}).get('run') or 'unknown'}
Test command: {metadata.get('commands', {}).get('test') or 'unknown'}
Detected environment variables: {env_text}
License: {license_text}

Rules:
- Use only facts supported by the provided files.
- If something cannot be determined, omit that section instead of inventing content.
- Never write placeholder text like "Your project description here".
- Make the README immediately usable for a real developer.
- Include the sections: title/tagline, badges, what it does, demo/screenshot placeholder, installation, usage, configuration, contributing, license.
- If there is an existing README in the files, preserve its intent when it is useful.
- Keep the tone professional and practical.

FILES:
{chr(10).join(blocks)}
"""


def call_claude(client: Anthropic, model: str, prompt: str) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=5000,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if getattr(block, "text", None)).strip()


def read_project(root: Path, style: str) -> tuple[list[SelectedFile], dict[str, Any]]:
    language = detect_language(root)
    package_manager = detect_package_manager(root)
    commands = detect_commands(root, package_manager)
    selected_files = collect_selected_files(root, style)
    metadata = {
        "language": language,
        "package_manager": package_manager,
        "commands": commands,
        "license": detect_license(root),
    }
    metadata["env_vars"] = detect_env_vars(root, selected_files)
    metadata["existing_readme"] = (root / "README.md").read_text(encoding="utf-8", errors="ignore") if (root / "README.md").exists() else None
    return selected_files, metadata


def markdown_to_console(markdown_text: str, title: str) -> None:
    console.print(Panel(Markdown(markdown_text), title=title, border_style="blue"))


def diff_text(old: str, new: str) -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    return "".join(difflib.unified_diff(old_lines, new_lines, fromfile="README.md", tofile="README.md.generated"))


def maybe_overwrite(existing: str | None, proposed: str, root: Path, dry_run: bool) -> bool:
    if dry_run:
        return False
    readme_path = root / "README.md"
    if not existing:
        return True
    if existing.strip() == proposed.strip():
        console.print("[green]README.md is already up to date.[/green]")
        return False
    console.print(Panel(diff_text(existing, proposed) or "No diff produced.", title="README Diff", border_style="yellow"))
    if not sys.stdin.isatty():
        console.print("[yellow]Non-interactive session detected. Skipping overwrite.[/yellow]")
        return False
    answer = console.input("Overwrite README.md with the generated version? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def main() -> int:
    args = parse_args()
    root = Path(args.project).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        die(f"Project directory not found: {root}")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        die("Missing ANTHROPIC_API_KEY. Set it in your environment or .env file.")

    selected_files, metadata = read_project(root, args.style)
    if not selected_files:
        die("No readable project files were found.")

    project_name = detect_project_name(root)
    prompt = build_prompt(root, project_name, selected_files, metadata)
    client = Anthropic(api_key=api_key)
    markdown = call_claude(client, args.model, prompt)

    header = Table(show_header=False, box=None)
    header.add_row("Project", project_name)
    header.add_row("Language", metadata["language"])
    header.add_row("Package manager", metadata["package_manager"] or "unknown")
    header.add_row("Files read", str(len(selected_files)))
    header.add_row("License", metadata["license"] or "unknown")
    console.print(Panel(header, title="README Generator", border_style="blue"))

    if args.dry_run:
        markdown_to_console(markdown, "Generated README Preview")
        return 0

    existing = metadata["existing_readme"]
    if maybe_overwrite(existing, markdown, root, args.dry_run):
        (root / "README.md").write_text(markdown.rstrip() + "\n", encoding="utf-8")
        console.print(f"[green]Wrote README.md to[/green] {root / 'README.md'}")
    else:
        console.print(Markdown(markdown))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
