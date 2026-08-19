#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from core.planner import plan_refactoring
from core.executor import execute_refactoring
from core.rollback import find_rollback_sessions, restore_session
from core.validator import validate_syntax

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-file code refactoring agent.")
    parser.add_argument("--project", default=".", help="Path to the project")
    parser.add_argument("--goal", help="The refactoring goal (e.g., 'convert callbacks to async')")
    parser.add_argument("--files", help="Target specific files (glob pattern)")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, don't modify files")
    parser.add_argument("--rollback", action="store_true", help="Undo the last refactoring")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(1)


def ensure_git_repo(project_root: Path) -> None:
    git_dir = project_root / ".git"
    if not git_dir.exists():
        console.print("[yellow]No git repo found. Initializing...[/yellow]")
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_root, check=True, capture_output=True)


def create_backup_branch(project_root: Path) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    branch_name = f"refactor-agent-{timestamp}"
    subprocess.run(["git", "checkout", "-b", branch_name], cwd=project_root, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-"], cwd=project_root, check=True, capture_output=True)
    return branch_name


def main() -> int:
    args = parse_args()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        die("Missing ANTHROPIC_API_KEY.")

    project_root = Path(args.project).expanduser().resolve()
    if not project_root.exists():
        die(f"Project not found: {project_root}")

    if args.rollback:
        sessions = find_rollback_sessions(project_root)
        if not sessions:
            die("No rollback sessions found.")
        console.print("[cyan]Available sessions:[/cyan]")
        for i, session in enumerate(sessions, start=1):
            console.print(f"{i}. {session}")
        choice = Prompt.ask("Select session to restore", choices=[str(i) for i in range(1, len(sessions) + 1)])
        restore_session(project_root, sessions[int(choice) - 1])
        console.print("[green]Restored.[/green]")
        return 0

    if not args.goal:
        die("Provide a --goal for the refactoring.")

    ensure_git_repo(project_root)
    backup_branch = create_backup_branch(project_root)
    console.print(f"[cyan]Backup created on branch: {backup_branch}[/cyan]")

    client = Anthropic(api_key=api_key)

    try:
        plan = plan_refactoring(client, args.model, project_root, args.goal, args.files)
    except Exception as exc:
        die(f"Planning failed: {exc}")

    if not plan or not plan.get("files_to_change"):
        console.print("[yellow]No files identified for refactoring.[/yellow]")
        return 0

    console.print(Panel(
        "\n".join(f"- {f['path']} ({f['reason']})" for f in plan["files_to_change"][:10]),
        title="Files to change",
        border_style="blue"
    ))

    if args.dry_run:
        console.print("[cyan]Dry run mode: no changes written.[/cyan]")
        return 0

    answer = console.input("Proceed with refactoring? [Y/n]: ").strip().lower()
    if answer in {"n", "no"}:
        return 0

    try:
        changes = execute_refactoring(client, args.model, project_root, plan, args.goal)
    except Exception as exc:
        die(f"Execution failed: {exc}")

    if not changes:
        console.print("[yellow]No changes were made.[/yellow]")
        return 0

    for file_path, change_summary in changes.items():
        console.print(f"[green]Modified:[/green] {file_path}")
        if change_summary:
            console.print(f"  {change_summary}")

    console.print(f"[green]Refactoring complete. {len(changes)} files modified.[/green]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
