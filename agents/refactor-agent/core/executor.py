#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any
import json
from datetime import datetime

from anthropic import Anthropic


def execute_refactoring(
    client: Anthropic,
    model: str,
    project_root: Path,
    plan: dict[str, Any],
    goal: str,
) -> dict[Path, str]:
    changes: dict[Path, str] = {}

    # Create a session directory to save original file contents for rollback
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    sessions_dir = project_root / ".refactor-agent" / "sessions" / session_id
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Build manifest mapping relative file path -> original content
    manifest: dict[str, str] = {}
    for file_spec in plan.get("files_to_change", []):
        file_path = project_root / file_spec["path"]
        if file_path.exists():
            try:
                original = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                original = ""
        else:
            original = ""
        manifest[str(file_path.relative_to(project_root))] = original

    for file_spec in plan.get("files_to_change", []):
        file_path = project_root / file_spec["path"]
        if not file_path.exists() and file_spec["change_type"] != "CREATE":
            continue

        if file_spec["change_type"] == "DELETE":
            if file_path.exists():
                file_path.unlink()
                changes[file_path] = "Deleted"
            continue

        if file_path.exists():
            original_content = file_path.read_text(encoding="utf-8", errors="ignore")
        else:
            original_content = ""

        prompt = f"""Refactor this file to achieve: {goal}

Original file:
```
{original_content[:5000]}
```

Return ONLY the complete new file content, no markdown or explanation. Write it directly."""

        response = client.messages.create(
            model=model,
            max_tokens=3000,
            temperature=0,
            system="You are a senior software engineer. Refactor the code.",
            messages=[{"role": "user", "content": prompt}],
        )

        new_content = "".join(block.text for block in response.content if getattr(block, "text", None)).strip()
        if new_content:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(new_content, encoding="utf-8")
            changes[file_path] = f"+{len(new_content)} bytes"

    # Save manifest for this session so rollback can restore originals
    try:
        manifest_file = sessions_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    except Exception:
        pass

    return changes
