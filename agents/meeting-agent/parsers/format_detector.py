#!/usr/bin/env python3
from __future__ import annotations


def detect_format(content: str) -> str:
    """Auto-detect transcript format."""
    if "WEBVTT" in content:
        return "WebVTT"
    if "-->" in content and "\n\n" in content:
        return "SRT"
    if "Speaker:" in content or "[" in content and "]:" in content:
        return "Labeled"
    return "Generic"


def parse_transcript(content: str) -> list[dict]:
    """Parse transcript into speaker/text pairs."""
    lines = content.split("\n")
    turns = []
    current_speaker = "Unknown"
    current_text = []

    for line in lines:
        if "Speaker:" in line:
            current_speaker = line.split("Speaker:")[-1].strip()
        elif line.strip() and not line.startswith("["):
            current_text.append(line.strip())

    return turns
