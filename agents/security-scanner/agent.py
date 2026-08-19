#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from scanner.file_scanner import collect_project_files
from scanner.regex_prescan import prescan_files
from scanner.ai_scanner import scan_flagged_files

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan a codebase for security vulnerabilities.")
    parser.add_argument("--project", default=".", help="Path to the project to scan")
    parser.add_argument("--severity", help="Filter by severity: CRITICAL,HIGH,MEDIUM,LOW")
    parser.add_argument("--output", help="Output HTML report to file")
    parser.add_argument("--fix", action="store_true", help="Generate fix suggestions file")
    parser.add_argument("--ignore", help="Path to .scanignore file with patterns to exclude")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model to use (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(1)


def render_summary(summary: dict[str, Any]) -> None:
    table = Table(show_header=False, box=None)
    table.add_row("Files scanned", str(summary["files_scanned"]))
    table.add_row("Vulnerabilities found", str(summary["total_vulns"]))
    table.add_row("Critical", str(summary["critical"]))
    table.add_row("High", str(summary["high"]))
    table.add_row("Medium", str(summary["medium"]))
    table.add_row("Low", str(summary["low"]))
    console.print(Panel(table, title="Security Scan Summary", border_style="red" if summary["total_vulns"] > 0 else "green"))


def render_vulnerabilities(vulns: list[dict[str, Any]], severity_filter: set[str] | None = None) -> None:
    if not vulns:
        console.print(Panel("No vulnerabilities found.", title="Results", border_style="green"))
        return

    filtered = [v for v in vulns if not severity_filter or v["severity"] in severity_filter]
    if not filtered:
        console.print(Panel("No vulnerabilities match the severity filter.", title="Results", border_style="green"))
        return

    severity_style = {
        "CRITICAL": "bold red",
        "HIGH": "red",
        "MEDIUM": "yellow",
        "LOW": "cyan",
    }

    table = Table(title="Vulnerabilities")
    table.add_column("File", style="bold")
    table.add_column("Line")
    table.add_column("Severity")
    table.add_column("CWE")
    table.add_column("Title")

    for vuln in sorted(filtered, key=lambda v: ("CRITICAL", "HIGH", "MEDIUM", "LOW").index(v.get("severity", "LOW"))):
        severity = vuln.get("severity", "LOW")
        table.add_row(
            vuln.get("file", "?"),
            str(vuln.get("line", "?")),
            f"[{severity_style[severity]}]{severity}[/{severity_style[severity]}]",
            vuln.get("cwe_id", "?"),
            vuln.get("title", "?"),
        )

    console.print(table)


def main() -> int:
    args = parse_args()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        die("Missing ANTHROPIC_API_KEY. Set it in your environment or .env file.")

    project_root = Path(args.project).expanduser().resolve()
    if not project_root.exists():
        die(f"Project directory not found: {project_root}")

    severity_filter = None
    if args.severity:
        severity_filter = set(s.upper().strip() for s in args.severity.split(","))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("[cyan]Collecting files...", total=None)
        files = collect_project_files(project_root, ignore_file=args.ignore)

    console.print(f"[cyan]Found {len(files)} files to analyze.[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("[cyan]Pre-scanning with regex...", total=None)
        flagged_files = prescan_files(files)

    console.print(f"[yellow]Flagged {len(flagged_files)} files for deep analysis.[/yellow]")

    client = Anthropic(api_key=api_key)
    all_vulns = []
    if flagged_files:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("[cyan]Running AI security analysis...", total=None)
            all_vulns = scan_flagged_files(client, args.model, flagged_files)

    summary = {
        "files_scanned": len(files),
        "total_vulns": len(all_vulns),
        "critical": sum(1 for v in all_vulns if v.get("severity") == "CRITICAL"),
        "high": sum(1 for v in all_vulns if v.get("severity") == "HIGH"),
        "medium": sum(1 for v in all_vulns if v.get("severity") == "MEDIUM"),
        "low": sum(1 for v in all_vulns if v.get("severity") == "LOW"),
    }

    render_summary(summary)
    render_vulnerabilities(all_vulns, severity_filter)

    if args.fix and all_vulns:
        fixes_path = project_root / "security_fixes.md"
        with open(fixes_path, "w", encoding="utf-8") as f:
            f.write("# Security Fixes\n\n")
            for vuln in all_vulns:
                f.write(f"## {vuln.get('title', 'Unknown vulnerability')}\n\n")
                f.write(f"**File:** {vuln.get('file', 'unknown')}\n")
                f.write(f"**Line:** {vuln.get('line', 'unknown')}\n")
                f.write(f"**Severity:** {vuln.get('severity', 'unknown')}\n")
                f.write(f"**CWE:** {vuln.get('cwe_id', 'unknown')}\n\n")
                f.write("### Description\n")
                f.write(f"{vuln.get('description', 'No description')}\n\n")
                f.write("### Fixed Code\n")
                f.write("```\n")
                f.write(vuln.get("fixed_code", "No fix provided"))
                f.write("\n```\n\n")
        console.print(f"[green]Security fixes saved to[/green] {fixes_path}")

    if args.output:
        report_path = Path(args.output)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("<html><head><title>Security Scan Report</title></head><body>\n")
            f.write(f"<h1>Security Scan Report</h1>\n")
            f.write(f"<p>Files scanned: {summary['files_scanned']}</p>\n")
            f.write(f"<p>Vulnerabilities found: {summary['total_vulns']}</p>\n")
            f.write("</body></html>\n")
        console.print(f"[green]HTML report saved to[/green] {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
