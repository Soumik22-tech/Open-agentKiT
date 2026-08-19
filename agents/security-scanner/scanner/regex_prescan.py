#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", "dist", "build", ".venv", "venv"
}
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz",
    ".exe", ".dll", ".so", ".bin", ".lock", ".min.js"
}


class PrescanFinding(NamedTuple):
    path: Path
    line_number: int
    pattern_type: str
    match_text: str
    severity_hint: str


REGEX_PATTERNS = {
    "hardcoded_secret": {
        "patterns": [
            (r'(?:password|passwd|pwd|api[_-]?key|token|secret)\s*[=:]\s*["\']([^"\']+)["\']', "HIGH"),
            (r'(?:AWS|AZURE|GITHUB|DATABASE)\s*(?:KEY|SECRET|PASSWORD)\s*[=:]\s*["\']([^"\']+)["\']', "CRITICAL"),
        ],
        "description": "Hardcoded secret (password, API key, token)",
    },
    "sql_injection": {
        "patterns": [
            (r'(?:sql|query|execute)\s*\(\s*["\']?\s*f["\']?["\'](.{1,100})["\']|SELECT.*["\'].*\+|SELECT.*\.format\(', "HIGH"),
        ],
        "description": "Potential SQL injection (string formatting in query)",
    },
    "command_injection": {
        "patterns": [
            (r'shell\s*=\s*True', "HIGH"),
            (r'os\.system\s*\(|subprocess\.call.*shell', "HIGH"),
        ],
        "description": "Command injection risk (shell=True or os.system)",
    },
    "eval_unsafe": {
        "patterns": [
            (r'eval\s*\(|exec\s*\(|pickle\.loads\s*\(|yaml\.load\s*\(', "CRITICAL"),
        ],
        "description": "Unsafe deserialization or code execution",
    },
    "weak_crypto": {
        "patterns": [
            (r'md5|sha1|DES|RC4|ECB', "MEDIUM"),
        ],
        "description": "Weak cryptographic algorithm",
    },
}


def prescan_files(files: list[Path]) -> list[PrescanFinding]:
    findings: list[PrescanFinding] = []

    for file_path in files:
        if file_path.suffix.lower() in SKIP_EXTENSIONS:
            continue

        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line_num, line in enumerate(text.splitlines(), start=1):
            for pattern_type, pattern_data in REGEX_PATTERNS.items():
                for pattern, severity in pattern_data["patterns"]:
                    if re.search(pattern, line, re.IGNORECASE):
                        match = re.search(pattern, line, re.IGNORECASE)
                        match_text = match.group(0)[:50] if match else ""
                        findings.append(
                            PrescanFinding(
                                path=file_path,
                                line_number=line_num,
                                pattern_type=pattern_type,
                                match_text=match_text,
                                severity_hint=severity,
                            )
                        )
                        break

    return findings
