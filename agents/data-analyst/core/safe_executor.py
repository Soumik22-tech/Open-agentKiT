#!/usr/bin/env python3
from __future__ import annotations

import io
import sys
from typing import Any


def execute_code(code: str, df: Any, timeout: int = 5) -> str | None:
    """Safely execute generated pandas code with sandboxing."""
    # Sandbox: restrict dangerous imports/builtins
    restricted_builtins = {
        "__import__": None,
        "open": None,
        "exec": None,
        "eval": None,
        "compile": None,
        "globals": None,
        "locals": None,
    }

    safe_globals = {
        "__builtins__": {k: v for k, v in __builtins__.items() if k not in restricted_builtins},
        "df": df,
        "pd": __import__("pandas"),
        "print": print,
    }

    # Capture output
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        exec(code, safe_globals)
        output = sys.stdout.getvalue()
        return output.strip() if output.strip() else "[No output]"
    except Exception as exc:
        return f"[Error: {type(exc).__name__}: {str(exc)[:200]}]"
    finally:
        sys.stdout = old_stdout
