#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


def _version_from_specifier(specifier: str) -> str:
    """Return the best available current version from a dependency specifier."""
    for operator in ("==", "===", ">=", "~=", "^", "~"):
        if operator in specifier:
            value = specifier.split(operator, 1)[1].split(",", 1)[0].strip()
            return value.split(".*", 1)[0]
    return "0.0.0"


def _dependency(name: str, version: str, ecosystem: str, source: str, raw: str = "") -> dict[str, str]:
    return {
        "package_name": name,
        "current_version": version or "0.0.0",
        "ecosystem": ecosystem,
        "source": source,
        "raw": raw,
    }


def parse_requirements(path: Path) -> list[dict[str, str]]:
    dependencies = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(("-r ", "--")):
            continue
        try:
            requirement = Requirement(line.split("#", 1)[0].strip())
        except Exception:
            continue
        dependencies.append(_dependency(
            requirement.name,
            _version_from_specifier(str(requirement.specifier)),
            "python",
            str(path),
            line,
        ))
    return dependencies


def parse_pyproject(path: Path) -> list[dict[str, str]]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    dependencies: list[dict[str, str]] = []
    project = data.get("project", {})
    for raw in project.get("dependencies", []):
        try:
            requirement = Requirement(raw)
        except Exception:
            continue
        dependencies.append(_dependency(requirement.name, _version_from_specifier(str(requirement.specifier)), "python", str(path), raw))

    poetry = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    for name, spec in poetry.items():
        if name.lower() == "python":
            continue
        raw = str(spec) if isinstance(spec, str) else json.dumps(spec)
        version = _version_from_specifier(raw if any(op in raw for op in ("==", ">=", "~=", "^", "~")) else f"=={raw}")
        dependencies.append(_dependency(name, version, "python", str(path), raw))
    return dependencies


def parse_package_json(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    dependencies = []
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        for name, spec in data.get(section, {}).items():
            version = re.sub(r"^[~^<>= ]+", "", str(spec)).split(" ", 1)[0]
            if version.startswith("workspace:"):
                version = version.split(":", 1)[1] or "0.0.0"
            dependencies.append(_dependency(name, version, "node", str(path), f"{section}:{spec}"))
    return dependencies


def parse_go_mod(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    dependencies = []
    in_require = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_require = True
            continue
        if in_require and stripped == ")":
            in_require = False
            continue
        single_line = stripped.startswith("require ")
        if single_line:
            stripped = stripped[len("require "):].strip()
        if not in_require and not single_line:
            continue
        parts = stripped.split()
        if len(parts) >= 2 and not parts[0].startswith("//"):
            dependencies.append(_dependency(parts[0], parts[1].lstrip("v"), "go", str(path), stripped))
    return dependencies


def find_manifest(project: Path, requested: str | None = None) -> Path:
    if requested:
        candidate = Path(requested)
        if not candidate.is_absolute():
            candidate = project / candidate
        if not candidate.exists():
            raise FileNotFoundError(f"Manifest not found: {candidate}")
        return candidate
    for name in ("requirements.txt", "pyproject.toml", "package.json", "go.mod"):
        candidate = project / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No supported manifest found. Expected requirements.txt, pyproject.toml, package.json, or go.mod.")


def parse_manifest(path: Path) -> list[dict[str, str]]:
    if path.name == "requirements.txt":
        return parse_requirements(path)
    if path.name == "pyproject.toml":
        return parse_pyproject(path)
    if path.name == "package.json":
        return parse_package_json(path)
    if path.name == "go.mod":
        return parse_go_mod(path)
    raise ValueError(f"Unsupported manifest: {path.name}")
