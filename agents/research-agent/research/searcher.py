#!/usr/bin/env python3
from __future__ import annotations

import time
import re
from typing import Any


def _fetch_page_content(url: str, timeout: int = 10) -> str:
    """Fetch and clean main text content from a URL."""
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; research-agent/1.0)"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # Remove nav, footer, script, style, ads
        for tag in soup(["nav", "footer", "script", "style", "aside", "header", "form"]):
            tag.decompose()
        # Get main content — prefer article/main tags, fallback to body
        main = soup.find("article") or soup.find("main") or soup.find("body")
        if not main:
            return ""
        text = main.get_text(separator="\n", strip=True)
        # Clean up excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Truncate to 3000 words max
        words = text.split()
        if len(words) > 3000:
            text = " ".join(words[:3000]) + "... [truncated]"
        return text
    except Exception:
        return ""


def search_web(topic: str, depth: str = "standard") -> list[dict[str, Any]]:
    """Search the web and fetch full page content for each result."""
    depth_limits = {"quick": 3, "standard": 5, "deep": 8}
    max_results = depth_limits.get(depth, 5)

    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return []

    sources: list[dict[str, Any]] = []
    try:
        ddgs = DDGS()
        results = list(ddgs.text(topic, max_results=max_results * 2))
    except Exception:
        return []

    fetched = 0
    for result in results:
        if fetched >= max_results:
            break
        url = result.get("href") or result.get("link") or ""
        if not url:
            continue
        title = result.get("title", "")
        snippet = result.get("body", "")
        # Skip low-quality sources
        skip_domains = ["reddit.com", "quora.com", "pinterest.com", "facebook.com"]
        if any(d in url for d in skip_domains):
            continue
        # Fetch full page
        full_content = _fetch_page_content(url)
        sources.append({
            "title": title,
            "url": url,
            "snippet": snippet,
            "full_content": full_content if full_content else snippet,
        })
        fetched += 1
        time.sleep(1)  # Be polite — 1 second between requests

    return sources
