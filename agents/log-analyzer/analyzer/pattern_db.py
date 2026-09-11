#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def check_patterns(error_type: str) -> dict[str, Any] | None:
    """Check against known error patterns."""
    patterns = {
        "NoneType.*has no attribute": {
            "name": "Null Reference",
            "description": "Variable is None when attribute access attempted. Add null check.",
        },
        "Connection refused": {
            "name": "Service Down",
            "description": "Cannot connect to service. Check if service is running and port is correct.",
        },
        "Maximum call stack exceeded": {
            "name": "Infinite Recursion",
            "description": "Function calling itself infinitely. Check recursion base case.",
        },
        "CORS policy": {
            "name": "CORS Error",
            "description": "Cross-origin request blocked. Add CORS headers to server.",
        },
        "ReferenceError.*is not defined": {
            "name": "Undefined Variable",
            "description": "Variable not declared or out of scope. Check variable name and scope.",
        },
    }

    for pattern, info in patterns.items():
        if pattern.replace(".*", "").lower() in error_type.lower():
            return info

    return None
