#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from anthropic import Anthropic

PLANNING_PROMPT = """Analyze this codebase and identify every file that must change to achieve: {goal}

Be conservative — only include files that MUST change.

Codebase files:
{files_summary}

Return JSON only:
{{
  "files_to_change": [
    {{"path": "...", "reason": "...", "change_type": "MODIFY|CREATE|DELETE"}}
  ]
}}"""


def plan_refactoring(
    client: Anthropic,
    model: str,
    project_root: Path,
    goal: str,
    target_files: str | None,
) -> dict[str, Any]:
    exts = ["*.py", "*.js", "*.ts", "*.tsx", "*.jsx", "*.go", "*.java", "*.rs"]
    files = [p for ext in exts for p in project_root.rglob(ext)]
    if target_files:
        import fnmatch
        files = [f for f in files if fnmatch.fnmatch(str(f), target_files)]

    files_summary = "\n".join(f.relative_to(project_root).as_posix() for f in files[:20])

    prompt = PLANNING_PROMPT.format(goal=goal, files_summary=files_summary)

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        system="You are a senior software architect.",
        messages=[{"role": "user", "content": prompt}],
    )

    text = "".join(block.text for block in response.content if getattr(block, "text", None)).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        return {"files_to_change": []}
