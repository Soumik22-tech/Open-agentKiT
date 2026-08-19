# README Generator

`readme-generator` scans a local project, reads the most important files, and generates a complete professional `README.md` based on the actual code.

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
python agent.py
python agent.py --project /path/to/project
python agent.py --project /path/to/project --dry-run
python agent.py --project /path/to/project --style minimal
python agent.py --project /path/to/project --style full
```

## Output Example

```text
┌────────────────────── README Generator ──────────────────────┐
│ Project         mini-api                                      │
│ Language        Python                                        │
│ Package manager  pip                                           │
│ Files read      7                                              │
│ License         MIT License                                    │
└────────────────────────────────────────────────────────────────┘

## What it does
mini-api is a small FastAPI service for managing tasks.

## Installation
pip install -r requirements.txt
```

## Behavior

- Existing `README.md` files are diffed before overwrite.
- `.gitignore` rules are respected when choosing files to read.
- If a section cannot be inferred confidently, the generated README omits it instead of inventing text.