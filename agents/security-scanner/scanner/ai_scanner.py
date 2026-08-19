#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from scanner.regex_prescan import PrescanFinding

SYSTEM_PROMPT = """You are a senior application security engineer (OWASP Top 10 expert, 15+ years experience).
Analyze the provided code for REAL exploitable vulnerabilities only.
DO NOT report: missing docstrings, logging suggestions, code style issues, theoretical issues that can't be exploited.
For each vulnerability: give exact line number, severity (CRITICAL/HIGH/MEDIUM/LOW), CWE ID, explanation of how it can be exploited, and exact fixed code.
Return ONLY valid JSON. Do not include markdown markers or explanations outside the JSON."""


def scan_flagged_files(client: Anthropic, model: str, findings: list[PrescanFinding]) -> list[dict[str, Any]]:
    all_vulns: list[dict[str, Any]] = []
    files_by_path: dict[Path, list[PrescanFinding]] = {}

    for finding in findings:
        if finding.path not in files_by_path:
            files_by_path[finding.path] = []
        files_by_path[finding.path].append(finding)

    for file_path, file_findings in files_by_path.items():
        try:
            file_content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        prompt = f"""Analyze this file for security vulnerabilities. We've flagged these areas of concern:
{chr(10).join(f"- Line {f.line_number}: {f.pattern_type} ({f.severity_hint})" for f in file_findings)}

FILE: {file_path.name}
CONTENT:
```
{file_content[:10000]}
```

Return JSON with this schema (and only this):
{{
  "vulnerabilities": [
    {{
      "line": int,
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "cwe_id": "CWE-XXX",
      "title": "string",
      "description": "string",
      "exploit_scenario": "string",
      "fixed_code": "string",
      "confidence": "HIGH|MEDIUM|LOW"
    }}
  ],
  "file_risk_score": 0-100
}}
"""

        try:
            response = client.messages.create(
                model=model,
                max_tokens=3000,
                temperature=0,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(block.text for block in response.content if getattr(block, "text", None)).strip()
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end > start:
                    data = json.loads(text[start : end + 1])
                else:
                    continue

            for vuln in data.get("vulnerabilities", []):
                vuln["file"] = str(file_path.relative_to(file_path.parent.parent.parent))
                all_vulns.append(vuln)
        except Exception:
            continue

    return all_vulns
