#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def validate_syntax(file_path: Path) -> bool:
    if file_path.suffix == ".py":
        import py_compile
        try:
            py_compile.compile(str(file_path), doraise=True)
            return True
        except Exception:
            return False
    return True
