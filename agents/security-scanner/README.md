# Security Vulnerability Scanner

Scans your codebase for real security vulnerabilities using two-phase analysis: fast regex pre-scan + Claude AI deep analysis. Outputs severity-ranked reports with exact fixes.

## Prerequisites

- Python 3.10+
- `pip`
- `ANTHROPIC_API_KEY`

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and set your API key.
3. Run `python agent.py --project /path/to/project`

## Usage

```bash
python agent.py --project /path/to/project
python agent.py --project . --severity HIGH,CRITICAL
python agent.py --project . --output report.html
python agent.py --project . --fix
```

## Output Example

Shows vulnerabilities sorted by severity with CWE IDs, line numbers, and fixed code snippets.

## How It Works

**Phase 1:** Regex patterns scan all files instantly for obvious issues (hardcoded secrets, shell=True, eval, etc.)

**Phase 2:** Files flagged in Phase 1 are sent to Claude for deep analysis with full context.

Result: Real vulnerabilities reported with high confidence, no false positives.
```
