# Codebase Explainer

`codebase-explainer` clones a GitHub repository, reads the most important files, and produces a practical explanation of what the project does and how it is structured.

## Prerequisites

- Python 3.10+
- `pip`
- `ANTHROPIC_API_KEY`

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and set your API key.
3. Run `python agent.py --repo https://github.com/owner/repo`

## Usage

```bash
python agent.py --repo https://github.com/acme/web-app
python agent.py --repo https://github.com/acme/web-app --depth quick
python agent.py --repo https://github.com/acme/web-app --format markdown --save
python agent.py --repo https://github.com/acme/web-app --format json
```

## Output Example

```text
┌────────────────────── Codebase Explainer ──────────────────────┐
│ Repository   https://github.com/acme/web-app                   │
│ Languages    TypeScript, Python                                 │
│ Frameworks    React, FastAPI                                    │
│ Files read    20                                                │
└─────────────────────────────────────────────────────────────────┘

## What it does
This project is a customer dashboard that combines a React frontend with a FastAPI backend.

## Architecture overview
- The frontend handles authenticated user workflows.
- The backend exposes REST endpoints for billing and profile data.
- Shared config lives in the root workspace files.
```

## Behavior

- File selection is ranked so READMEs, manifests, and entry points are read first.
- `.gitignore` rules are respected when choosing files.
- If the repository looks like a monorepo, the explanation calls that out explicitly.