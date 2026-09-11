# Log & Incident Analyzer

Analyzes error logs and stack traces, provides root cause analysis, suggested fixes, and code context.

## Setup

```bash
pip install -r requirements.txt
python agent.py --log error.txt
```

## Usage

```bash
python agent.py --log error.log
python agent.py --log error.log --repo /path/to/project
cat error.log | python agent.py --stdin
python agent.py --clipboard --repo .
```

## Features

- Auto-detects log format (Python, JavaScript, Java, generic)
- Pattern matching for common error types
- Code context extraction
- Root cause analysis via Claude
- Severity assessment
- Watch mode for tailing logs (planned)
