# Commit Writer

`commit-writer` reads the staged git diff, asks Claude for three Conventional Commit candidates, and helps you pick a commit message that is specific, readable, and merge-ready.

## Prerequisites

- Python 3.10+
- `pip`
- `ANTHROPIC_API_KEY`
- Git installed and available on your `PATH`

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and set your API key.
3. Run `bash install.sh` to add the `git ai-commit` alias.

## Usage

```bash
python agent.py
python agent.py --just-one
python agent.py --emoji
git ai-commit
```

## Before / After

```text
Bad:  fix bug
Good: feat(auth): validate password reset tokens
      - Reject expired tokens before lookup
      - Preserve the existing redirect flow
      Refs: #123
```

## Selection Flow

1. The tool shows three candidate commit messages.
2. Pick `1`, `2`, or `3`, or type `e` to edit.
3. The selected message is copied to your clipboard, and the tool offers to run `git commit` directly.

## Output Example

```text
┌────────────────────── Commit Candidates ──────────────────────┐
│ 1  feat(auth): validate password reset tokens                 │
│ 2  fix(auth): guard token lookup against expired sessions     │
│ 3  chore(auth): tighten password reset handling               │
└───────────────────────────────────────────────────────────────┘
```

## Notes

- The scope is inferred from staged file paths when possible.
- If an issue number is present in the branch name, it is surfaced in the final message.
- `--emoji` adds gitmoji prefixes such as `✨` and `🐛`.