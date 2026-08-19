# Bug Hunter

`bug-hunter` analyzes a source file with Claude, reports real logic bugs with severity and confidence, and returns a fixed version of the entire file.

## Supported Languages

- Python
- JavaScript
- TypeScript
- Go
- Rust
- Java

## Prerequisites

- Python 3.10+
- `pip`
- `ANTHROPIC_API_KEY`

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and set your API key.
3. Run `python agent.py --file path/to/code.py`

## Usage

```bash
python agent.py --file path/to/code.py
python agent.py --file path/to/code.py --fix
cat path/to/code.py | python agent.py --stdin
python agent.py --file path/to/code.py --copy-fix
python agent.py --file path/to/code.py --language python
```

## Output Example

```text
┌──────────────────────── Bug Hunter ────────────────────────┐
│ Summary: Off-by-one in pagination and unsafe null access.   │
│ Bugs found: 2                                               │
│ Overall confidence: 0.91                                    │
└─────────────────────────────────────────────────────────────┘

Line  Severity  Title                     Confidence
12    HIGH      Off-by-one in page loop   0.94
31    MEDIUM    Missing null guard        0.88

## Fixed Code
...full corrected file...
```

## Notes

- This finds logic bugs, not linting issues.
- If no bugs are found, the tool says so clearly instead of inventing findings.