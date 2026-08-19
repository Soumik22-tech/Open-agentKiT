#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def find_rollback_sessions(project_root: Path) -> list[str]:
    sessions_dir = project_root / ".refactor-agent" / "sessions"
    if not sessions_dir.exists():
        return []
    return sorted([d.name for d in sessions_dir.iterdir() if d.is_dir()])


def restore_session(project_root: Path, session_id: str) -> None:
    session_dir = project_root / ".refactor-agent" / "sessions" / session_id
    if not session_dir.exists():
        return
    manifest_file = session_dir / "manifest.json"
    if manifest_file.exists():
        import json
        manifest = json.loads(manifest_file.read_text())
        for file_path, original_content in manifest.items():
            (project_root / file_path).write_text(original_content, encoding="utf-8")
