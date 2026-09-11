#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.manifest_parser import find_manifest, parse_manifest
from core.registry_client import RegistryClient
from core.risk_assessor import assess_risk
from core.usage_scanner import scan_usage

console = Console()
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assess dependency upgrades against real code usage.")
    parser.add_argument("--project", required=True, help="Project directory")
    parser.add_argument("--manifest", help="Manifest path or filename")
    parser.add_argument("--package", help="Check one package only")
    parser.add_argument("--severity", choices=["LOW", "MEDIUM", "HIGH"], help="Only show this risk level")
    parser.add_argument("--output", help="Write a Markdown report")
    parser.add_argument("--verbose", action="store_true", help="Show detailed risk breakdowns")
    parser.add_argument("--auto-apply-safe", action="store_true", help="Apply only LOW-risk version updates")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL})")
    return parser.parse_args()


def die(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise SystemExit(1)


def render_table(results: list[dict]) -> None:
    table = Table(title="Dependency Upgrade Risk")
    for column in ("Package", "Current", "Latest", "Risk", "Recommendation"):
        table.add_column(column)
    for result in results:
        style = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red"}.get(result["risk"], "white")
        table.add_row(result["package"], result["current"], result["latest"] or "unknown", f"[{style}]{result['risk']}[/{style}]", result["recommendation"])
    console.print(table)


def markdown_report(results: list[dict], manifest: Path) -> str:
    lines = [f"# Dependency Upgrade Report\n\nManifest: `{manifest}`\n"]
    for result in results:
        lines += [
            f"## {result['package']} {result['current']} -> {result['latest']}",
            f"- **Risk:** {result['risk']}",
            f"- **Recommendation:** {result['recommendation']}",
            f"- **Usage:** {result['usage'].get('summary', 'Unknown')}",
            f"- **Reason:** {result['reason'] or 'No additional reason supplied.'}",
        ]
        if result["breaking_changes"]:
            lines.append("- **Relevant breaking changes:**")
            lines.extend(f"  - {item}" for item in result["breaking_changes"])
        if result["migration_steps"]:
            lines.append("- **Migration steps:**")
            lines.extend(f"  - {item}" for item in result["migration_steps"])
        lines.append("")
    return "\n".join(lines)


def apply_safe_updates(manifest: Path, results: list[dict]) -> list[str]:
    safe = {result["package"]: result for result in results if result["risk"] == "LOW" and result["outdated"] and result["latest"]}
    if not safe:
        return []
    backup = manifest.with_suffix(manifest.suffix + ".bak")
    shutil.copy2(manifest, backup)
    text = manifest.read_text(encoding="utf-8")
    changed = []
    for package, result in safe.items():
        if manifest.name == "package.json":
            import json
            data = json.loads(text)
            for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                if package in data.get(section, {}):
                    prefix = "^" if str(data[section][package]).startswith("^") else ""
                    data[section][package] = prefix + result["latest"]
                    changed.append(f"{package}: {result['current']} -> {result['latest']}")
            text = json.dumps(data, indent=2) + "\n"
        else:
            import re
            pattern = re.compile(rf"^({re.escape(package)}\s*)([^\s#]+)(.*)$", re.MULTILINE | re.IGNORECASE)
            replacement = rf"\g<1>=={result['latest']}\g<3>"
            new_text, count = pattern.subn(replacement, text)
            if count:
                text = new_text
                changed.append(f"{package}: {result['current']} -> {result['latest']}")
    if changed:
        manifest.write_text(text, encoding="utf-8")
    else:
        backup.unlink(missing_ok=True)
    return changed


def main() -> int:
    args = parse_args()
    project = Path(args.project).resolve()
    if not project.is_dir():
        die(f"Project directory not found: {project}")
    try:
        manifest = find_manifest(project, args.manifest)
        dependencies = parse_manifest(manifest)
    except (OSError, ValueError, FileNotFoundError) as exc:
        die(str(exc))
    if args.package:
        dependencies = [d for d in dependencies if d["package_name"].lower() == args.package.lower()]
        if not dependencies:
            die(f"Package not found in manifest: {args.package}")

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")) if os.getenv("ANTHROPIC_API_KEY") else None
    registry = RegistryClient()
    results = []
    for dependency in dependencies:
        info = registry.package_info(dependency)
        if not info.get("available"):
            results.append({"package": dependency["package_name"], "current": dependency["current_version"], "latest": "", "risk": "LOW", "recommendation": "skipped", "reason": info.get("error", "Unavailable"), "outdated": False, "breaking_changes": [], "migration_steps": [], "usage": {"summary": "Not assessed"}})
            continue
        usage = scan_usage(project, dependency)
        changelog = registry.github_releases(info.get("repository_url", ""), dependency["current_version"], info.get("latest_version", ""))
        if client:
            result = assess_risk(client, args.model, dependency, info, usage, changelog)
        else:
            from core.risk_assessor import version_gap
            gap = version_gap(dependency["current_version"], info.get("latest_version", ""))
            result = {"package": dependency["package_name"], "current": dependency["current_version"], "latest": info.get("latest_version", ""), "risk": "HIGH" if gap["major"] else "MEDIUM" if gap["outdated"] else "LOW", "recommendation": "upgrade with testing" if gap["outdated"] else "No upgrade needed", "reason": "AI assessment skipped because ANTHROPIC_API_KEY is not set.", "outdated": gap["outdated"], "breaking_changes": [], "migration_steps": [], "usage": usage}
        results.append(result)

    shown = [result for result in results if not args.severity or result["risk"] == args.severity]
    render_table(shown)
    if args.verbose:
        for result in shown:
            console.print(Panel(markdown_report([result], manifest), title=result["package"]))
    if args.output:
        Path(args.output).write_text(markdown_report(shown, manifest), encoding="utf-8")
        console.print(f"[green]Report saved to {args.output}[/green]")
    if args.auto_apply_safe:
        changed = apply_safe_updates(manifest, results)
        console.print(f"[green]Applied {len(changed)} LOW-risk updates; backup: {manifest.name}.bak[/green]" if changed else "[yellow]No LOW-risk updates were applied.[/yellow]")
    counts = {risk: sum(result["risk"] == risk for result in results) for risk in ("LOW", "MEDIUM", "HIGH")}
    console.print(f"[cyan]{len(results)} packages checked. {counts['LOW']} low risk, {counts['MEDIUM']} need testing, {counts['HIGH']} high risk.[/cyan]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
