#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic


def generate_analysis_code(
    client: Anthropic,
    model: str,
    df: Any,
    profile: dict,
    query: str,
) -> str:
    """Generate pandas code for the given query."""
    profile_json = json.dumps(profile, indent=2, default=str)

    prompt = f"""Given this data profile, write Python pandas code to answer: "{query}"

Data Profile:
{profile_json}

Generate ONLY valid Python code that:
- Uses 'df' as the dataframe
- Returns a result via print() or assigns to 'result'
- Works with the given columns and types
- Takes <2 seconds to run

No explanations, only code:"""

    response = client.messages.create(
        model=model,
        max_tokens=1000,
        temperature=0,
        system="You are a pandas expert. Generate concise, correct code.",
        messages=[{"role": "user", "content": prompt}],
    )

    code = "".join(block.text for block in response.content if getattr(block, "text", None)).strip()
    
    # Extract code block if wrapped in ```
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()

    return code
