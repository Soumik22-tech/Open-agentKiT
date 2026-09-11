#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

CACHE_TTL = 24 * 60 * 60
DEFAULT_CACHE = Path.home() / ".cache" / "dependency-upgrader"


class RegistryClient:
    """Rate-limited registry client with a 24-hour JSON response cache."""

    def __init__(self, cache_dir: Path | None = None, session: requests.Session | None = None):
        self.cache_dir = cache_dir or DEFAULT_CACHE
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "dependency-upgrader/1.0"})
        self.last_request = 0.0

    def _get(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any] | None:
        cache_file = self.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        if cache_file.exists() and time.time() - cache_file.stat().st_mtime < CACHE_TTL:
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                cache_file.unlink(missing_ok=True)
        delay = 0.25 - (time.time() - self.last_request)
        if delay > 0:
            time.sleep(delay)
        try:
            response = self.session.get(url, headers=headers or {}, timeout=15)
            self.last_request = time.time()
            if response.status_code == 429:
                return None
            response.raise_for_status()
            data = response.json()
            cache_file.write_text(json.dumps(data), encoding="utf-8")
            return data
        except (requests.RequestException, ValueError, OSError):
            return None

    def _get_text(self, url: str, headers: dict[str, str] | None = None) -> str:
        cache_file = self.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".txt")
        if cache_file.exists() and time.time() - cache_file.stat().st_mtime < CACHE_TTL:
            return cache_file.read_text(encoding="utf-8", errors="ignore")
        delay = 0.25 - (time.time() - self.last_request)
        if delay > 0:
            time.sleep(delay)
        try:
            response = self.session.get(url, headers=headers or {}, timeout=15)
            self.last_request = time.time()
            if response.status_code == 429:
                return ""
            response.raise_for_status()
            cache_file.write_text(response.text, encoding="utf-8")
            return response.text
        except (requests.RequestException, OSError):
            return ""

    def package_info(self, dependency: dict[str, str]) -> dict[str, Any]:
        ecosystem = dependency["ecosystem"]
        name = dependency["package_name"]
        if ecosystem == "python":
            data = self._get(f"https://pypi.org/pypi/{quote(name)}/json")
            if not data:
                return {"available": False, "error": "Package not found or PyPI unavailable"}
            info = data.get("info", {})
            return {
                "available": True, "latest_version": info.get("version", ""),
                "summary": info.get("summary", ""), "repository_url": _repository_url(info.get("project_urls", {})),
                "changelog": _pypi_changelog(info), "source": "PyPI",
            }
        if ecosystem == "node":
            package_url = quote(name, safe="@/")
            data = self._get(f"https://registry.npmjs.org/{package_url}")
            if not data:
                return {"available": False, "error": "Package not found or npm unavailable"}
            return {
                "available": True, "latest_version": data.get("dist-tags", {}).get("latest", ""),
                "summary": data.get("description", ""), "repository_url": _repository_url(data.get("repository", {})),
                "changelog": "", "source": "npm",
            }
        if ecosystem == "go":
            module_url = quote(name, safe="/@")
            data = self._get(f"https://proxy.golang.org/{module_url}/@latest")
            if not data:
                return {"available": False, "error": "Module not found or Go proxy unavailable"}
            return {
                "available": True, "latest_version": str(data.get("Version", "")).lstrip("v"),
                "summary": "", "repository_url": f"https://{name}", "changelog": "", "source": "Go proxy",
            }
        return {"available": False, "error": f"Unsupported ecosystem: {ecosystem}"}

    def github_releases(self, repository_url: str, current: str, latest: str) -> str:
        owner_repo = _github_owner_repo(repository_url)
        if not owner_repo:
            return "No changelog available — relying on version diff only"
        token = os.getenv("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = self._get(f"https://api.github.com/repos/{owner_repo}/releases?per_page=30", headers)
        if not data:
            return "No changelog available — GitHub API unavailable or rate limit reached"
        notes = []
        for release in data:
            tag = str(release.get("tag_name", ""))
            body = release.get("body") or ""
            if body:
                notes.append(f"{tag}:\n{body}")
        release_notes = "\n\n".join(notes)[:12000]
        if release_notes:
            return release_notes
        for filename in ("CHANGELOG.md", "changelog.md", "HISTORY.md"):
            url = f"https://raw.githubusercontent.com/{owner_repo}/HEAD/{filename}"
            text = self._get_text(url)
            if text:
                return text[:12000]
        return "No changelog available — relying on version diff only"


def _repository_url(value: Any) -> str:
    """Extract a repository URL from npm or PyPI project URL formats."""
    if isinstance(value, dict):
        if "url" in value:
            value = value.get("url", "")
        else:
            preferred_labels = ("source code", "source", "repository", "github", "homepage")
            found = ""
            lower_map = {str(k).lower(): v for k, v in value.items()}
            for label in preferred_labels:
                if label in lower_map:
                    found = lower_map[label]
                    break
            if not found:
                for candidate in value.values():
                    if isinstance(candidate, str) and "github.com" in candidate:
                        found = candidate
                        break
            value = found
    return str(value or "").replace("git+", "").removesuffix(".git")


def _github_owner_repo(url: str) -> str | None:
    match = re.search(r"github\.com[/:]([^/]+/[^/#]+)", url)
    return match.group(1).removesuffix(".git") if match else None


def _pypi_changelog(info: dict) -> str:
    urls = info.get("project_urls") or {}
    candidates = [url for label, url in urls.items() if any(word in label.lower() for word in ("change", "release", "history"))]
    return f"Changelog: {candidates[0]}" if candidates else ""
