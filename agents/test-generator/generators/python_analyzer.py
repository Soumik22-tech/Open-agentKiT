#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


def analyze_python_file(file_path: Path) -> list[dict[str, Any]]:
    """Extract all functions and methods from a Python file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    try:
        tree = ast.parse(content)
    except Exception:
        return []

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            docstring = ast.get_docstring(node) or ""
            args = [arg.arg for arg in node.args.args]
            has_return = any(isinstance(n, ast.Return) for n in ast.walk(node))

            functions.append({
                "name": node.name,
                "args": args,
                "docstring": docstring,
                "has_return": has_return,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            })

    return functions
