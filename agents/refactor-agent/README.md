# Multi-File Code Refactoring Agent

Give it a refactoring goal (e.g., "convert callbacks to async/await"), it analyzes your entire codebase, creates a plan, shows diffs, and executes changes safely with full rollback capability.

## Prerequisites

- Python 3.10+
- `pip`
- `ANTHROPIC_API_KEY`
- Git repository (created automatically if missing)

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`
3. Run `python agent.py --project . --goal "your refactoring goal"`

## Usage

```bash
python agent.py --project . --goal "convert callbacks to async/await"
python agent.py --project . --goal "add type hints" --files "*.py"
python agent.py --project . --goal "rename User to Account" --dry-run
python agent.py --rollback
```

## Safety

- Creates git backup branch before any changes
- Shows diffs for your approval
- Validates syntax after each change
- Full rollback via `--rollback` flag
- If project has no git repo: warn user, create one automatically (git init + initial commit)
- Maximum safety: always backup before any write
- Show token usage + estimated cost at end

DIFF DISPLAY:
- Show colored diff for each file (red=removed, green=added)
- Summary: "+45 lines, -23 lines across 8 files"
- Side-by-side diff for small files, unified diff for large

README must include:
- Clear warning: "Always use in a git repo. This tool writes to your files."
- Example walkthrough: goal → plan → diff preview → execution → result
- Limitations: very large codebases (500+ files) need targeted --files flag
- How rollback works

## Prerequisites

- Python 3.10+
- `pip`
- `ANTHROPIC_API_KEY`
- Git repository (created automatically if missing)

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`
3. Run `python agent.py --project . --goal "your refactoring goal"`

## Usage

```bash
python agent.py --project . --goal "convert callbacks to async/await"
python agent.py --project . --goal "add type hints" --files "*.py"
python agent.py --project . --goal "rename User to Account" --dry-run
python agent.py --rollback
```

## Safety

- Creates git backup branch before any changes
- Shows diffs for your approval
- Validates syntax after each change
- Full rollback via `--rollback` flag
