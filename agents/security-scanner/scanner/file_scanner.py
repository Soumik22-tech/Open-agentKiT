#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

import pathspec
from anthropic import Anthropic

SKIP_DIRS = {".git", "node_modules", "__pycache__", "dist", "build", ".venv", "venv"}
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz",
    ".exe", ".dll", ".so", ".bin", ".lock", ".min.js"
}


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


def collect_project_files(root: Path, ignore_file: str | None = None) -> list[Path]:
    spec = load_gitignore_spec(root)
    if ignore_file and (root / ignore_file).exists():
        patterns = [(root / ignore_file).read_text(encoding="utf-8", errors="ignore").splitlines()]
        spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if is_ignored(relative, spec):
            continue
        if path.suffix.lower() in SKIP_EXTENSIONS:
            continue
        files.append(path)

    return files
