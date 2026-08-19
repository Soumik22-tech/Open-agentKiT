#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from anthropic import Anthropic

SYNTHESIS_PROMPT = """Based on these sources, write a comprehensive research report on: {topic}

Sources:
{sources_text}

Structure: Executive Summary → Key Findings → Detailed Analysis → Conclusion → Bibliography

Each claim should be traceable to a source. Acknowledge uncertainty where appropriate.

Write the report in markdown."""


def synthesize_report(
    client: Anthropic,
    model: str,
    topic: str,
    sources: list[dict[str, Any]],
) -> str:
    if not sources:
        sources_text = "(No sources available — report based on model knowledge)"
    else:
        sources_text = "\n\n".join(
            f"SOURCE [{i+1}]: {s.get('title', 'Unknown')}\nURL: {s.get('url', '')}\n\n{s.get('full_content', s.get('snippet', ''))[:2000]}"
            for i, s in enumerate(sources)
        )

    prompt = SYNTHESIS_PROMPT.format(topic=topic, sources_text=sources_text)

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        temperature=0,
        system="You are a research analyst. Write a professional, well-structured research report.",
        messages=[{"role": "user", "content": prompt}],
    )

    return "".join(block.text for block in response.content if getattr(block, "text", None)).strip()
