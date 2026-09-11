#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from typing import Any

from packaging.version import InvalidVersion, Version


def version_gap(current: str, latest: str) -> dict[str, Any]:
    try:
        old, new = Version(current), Version(latest)
    except InvalidVersion:
        return {"outdated": current != latest, "bump": "unknown", "major": False}
    if new <= old:
        return {"outdated": False, "bump": "current", "major": False}
    if old.major != new.major:
        bump = "major"
    elif old.minor != new.minor:
        bump = "minor"
    else:
        bump = "patch"
    return {"outdated": True, "bump": bump, "major": bump == "major"}


def assess_risk(
    client: Anthropic,
    model: str,
    dependency: dict[str, str],
    registry: dict[str, Any],
    usage: dict[str, Any],
    changelog: str,
) -> dict[str, Any]:
    gap = version_gap(dependency["current_version"], registry.get("latest_version", ""))
    if not gap["outdated"]:
        return _result(dependency, registry, usage, gap, "LOW", "Already current", "No upgrade needed.")

    prompt = f"""Assess this dependency upgrade using actual local usage.

Package: {dependency['package_name']}
Ecosystem: {dependency['ecosystem']}
Current: {dependency['current_version']}
Target: {registry.get('latest_version', 'unknown')}
Version gap: {gap['bump']}
Changelog/release notes:
{changelog or 'No changelog available — rely on the version diff only.'}

Local usage:
{json.dumps(usage, indent=2)}

Return JSON only with exactly these fields:
{{"risk": "LOW|MEDIUM|HIGH", "recommendation": "safe to auto-upgrade|upgrade with testing|manual migration needed|do not upgrade yet", "breaking_changes": ["specific relevant changes"], "migration_steps": ["specific code changes based on usage"], "reason": "specific explanation"}}
Be specific about imported functions/classes. Ignore breaking changes for APIs this project does not use."""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1800,
            temperature=0,
            system="You are a senior engineer assessing dependency upgrade risk. Do not invent package changes not present in the supplied notes.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if getattr(block, "text", None)).strip()
        parsed = _parse_json(text)
        return _result(dependency, registry, usage, gap, parsed.get("risk", "HIGH"), parsed.get("recommendation", "upgrade with testing"), parsed.get("reason", ""), parsed.get("breaking_changes", []), parsed.get("migration_steps", []))
    except Exception as exc:
        fallback_risk = "HIGH" if gap["major"] else "MEDIUM"
        return _result(dependency, registry, usage, gap, fallback_risk, "manual migration needed" if gap["major"] else "upgrade with testing", f"AI assessment unavailable: {exc}")


def _parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        return json.loads(text[start:end + 1]) if start >= 0 and end > start else {}


def _result(dependency, registry, usage, gap, risk, recommendation, reason, breaking_changes=None, migration_steps=None) -> dict[str, Any]:
    return {
        "package": dependency["package_name"], "ecosystem": dependency["ecosystem"],
        "current": dependency["current_version"], "latest": registry.get("latest_version", ""),
        "outdated": gap["outdated"], "bump": gap["bump"], "risk": risk.upper(),
        "recommendation": recommendation, "reason": reason,
        "breaking_changes": breaking_changes or [], "migration_steps": migration_steps or [],
        "usage": usage, "registry": registry,
    }
