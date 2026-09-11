#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from anthropic import Anthropic


def generate_tests(
    client: Anthropic,
    model: str,
    source_file: Path,
    functions: list[dict[str, Any]],
) -> str:
    """Generate comprehensive tests for functions."""
    source_code = source_file.read_text()
    functions_summary = "\n".join(
        f"- {f['name']}({', '.join(f['args'])}): {f['docstring'][:100]}"
        for f in functions
    )

    prompt = f"""Given this Python source file and its functions, generate comprehensive pytest tests.

Source file: {source_file.name}
Functions:
{functions_summary}

Source code:
```python
{source_code[:2000]}
```

Generate a complete test file that:
- Tests each function with normal cases, edge cases, and error conditions
- Uses pytest fixtures for setup/teardown
- Mocks external dependencies (file I/O, network, DB)
- Has meaningful assertions
- Is ready to run with pytest

Return ONLY valid Python code, no explanation."""

    response = client.messages.create(
        model=model,
        max_tokens=3000,
        temperature=0,
        system="You are a senior test engineer. Generate comprehensive, runnable pytest tests.",
        messages=[{"role": "user", "content": prompt}],
    )

    test_code = "".join(block.text for block in response.content if getattr(block, "text", None)).strip()
    
    # Ensure imports
    if "import pytest" not in test_code:
        test_code = "import pytest\n" + test_code
    
    return test_code


def run_tests(test_file: str) -> tuple[int, int]:
    """Run generated tests and return pass/fail counts."""
    try:
        result = subprocess.run(
            ["pytest", test_file, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Parse output to count passes/fails
        passed = result.stdout.count(" PASSED")
        failed = result.stdout.count(" FAILED")
        return passed, failed
    except Exception:
        return 0, 0
