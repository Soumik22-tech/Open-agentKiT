#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


def extract_python_routes(project_root: Path) -> list[dict[str, Any]]:
    """Extract routes from FastAPI/Flask Python files."""
    routes: list[dict[str, Any]] = []

    for py_file in project_root.rglob("*.py"):
        if "venv" in py_file.parts or "__pycache__" in py_file.parts:
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        try:
            tree = ast.parse(content)
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            method = decorator.func.attr
                            if method in {"get", "post", "put", "delete", "patch"}:
                                path = "/"
                                if decorator.args:
                                    if isinstance(decorator.args[0], ast.Constant):
                                        path = decorator.args[0].value
                                docstring = ast.get_docstring(node) or "No description"
                                routes.append({
                                    "path": path,
                                    "method": method.upper(),
                                    "name": node.name,
                                    "description": docstring[:100],
                                })

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if hasattr(decorator.func, "attr") and decorator.func.attr == "route":
                            path = "/"
                            methods = ["GET"]
                            if decorator.args:
                                if isinstance(decorator.args[0], ast.Constant):
                                    path = decorator.args[0].value
                            for keyword in decorator.keywords:
                                if keyword.arg == "methods" and isinstance(keyword.value, ast.List):
                                    methods = [
                                        e.value for e in keyword.value.elts if isinstance(e, ast.Constant)
                                    ]
                            for method in methods:
                                routes.append({
                                    "path": path,
                                    "method": method,
                                    "name": node.name,
                                    "description": ast.get_docstring(node) or "No description",
                                })

    return routes
