#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any


def parse_log(content: str) -> dict[str, Any]:
    """Parse various log formats to extract structured error info."""
    
    # Python traceback
    if "Traceback (most recent call last)" in content:
        lines = content.split("\n")
        error_line = next((l for l in reversed(lines) if l.strip() and not l.startswith(" ")), "")
        return {
            "type": "python",
            "error_type": error_line.split(":")[0] if ":" in error_line else "Exception",
            "message": error_line,
            "stack_trace": content,
        }

    # JavaScript/Node stack
    if "at " in content and ("Error:" in content or "TypeError:" in content):
        error_type = re.search(r"(\w+Error):", content)
        return {
            "type": "javascript",
            "error_type": error_type.group(1) if error_type else "Error",
            "message": content.split("\n")[0],
            "stack_trace": content,
        }

    # Java stack
    if "Exception in thread" in content:
        error_match = re.search(r"Exception in thread.*?:\s*(\S+Error)", content)
        return {
            "type": "java",
            "error_type": error_match.group(1) if error_match else "Exception",
            "message": content.split("\n")[1] if len(content.split("\n")) > 1 else "",
            "stack_trace": content,
        }

    # Generic log with ERROR/FATAL
    if re.search(r"(ERROR|FATAL|CRITICAL)", content):
        lines = content.split("\n")
        error_lines = [l for l in lines if re.search(r"(ERROR|FATAL|CRITICAL)", l)]
        return {
            "type": "generic",
            "error_type": "ApplicationError",
            "message": error_lines[0] if error_lines else content[:200],
            "stack_trace": content,
        }

    return {
        "type": "unknown",
        "error_type": "UnknownError",
        "message": content[:200],
        "stack_trace": content,
    }
