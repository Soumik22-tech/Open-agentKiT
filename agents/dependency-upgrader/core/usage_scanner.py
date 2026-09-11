#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__", ".tox"}
CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java"}


def _package_tokens(package_name: str) -> set[str]:
    return {package_name, package_name.replace("-", "_"), package_name.replace("-", "/")}


def scan_usage(project: Path, dependency: dict[str, str]) -> dict:
    """Find imports and nearby symbols for one dependency without scanning vendored code."""
    package = dependency["package_name"]
    ecosystem = dependency["ecosystem"]
    tokens = _package_tokens(package)
    matches = []

    for path in project.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in CODE_SUFFIXES:
            continue
        relative = path.relative_to(project)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for number, line in enumerate(lines, 1):
            imported = False
            symbols: list[str] = []
            if ecosystem == "python":
                imported = bool(re.search(r"^\s*(?:from|import)\s+", line)) and any(
                    re.search(rf"\b{re.escape(token)}\b", line) for token in tokens
                )
                if imported:
                    match = re.search(r"(?:from|import)\s+([^\s]+)", line)
                    symbols = [match.group(1)] if match else []
            elif ecosystem == "node":
                imported = any(re.search(rf"(?:from|require\(['\"]){re.escape(token)}(?:['\"]|/)", line) for token in tokens)
                symbols = re.findall(r"\b(?:import|require)\b[^;]*", line) if imported else []
            elif ecosystem == "go":
                imported = any(token in line for token in tokens) and '"' in line
                symbols = [line.strip()] if imported else []

            if imported:
                matches.append({"file": relative.as_posix(), "line": number, "code": line.strip(), "symbols": symbols})

    files = sorted({item["file"] for item in matches})
    return {
        "package": package,
        "usage_count": len(matches),
        "file_count": len(files),
        "files": files,
        "matches": matches[:100],
        "summary": "No local imports found" if not matches else f"Used in {len(files)} files across {len(matches)} import sites",
    }
