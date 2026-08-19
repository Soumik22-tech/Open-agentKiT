# PR Reviewer

`pr-reviewer` fetches a GitHub pull request diff, sends it to Claude, and returns a structured markdown review you can paste directly into a PR comment.

## Prerequisites

- Python 3.10+
- `pip`
- `ANTHROPIC_API_KEY`
- `GITHUB_TOKEN` for private repositories or higher GitHub API limits

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and set your keys.
3. Run `python agent.py --pr https://github.com/owner/repo/pull/123`

## Usage

```bash
python agent.py --pr https://github.com/acme/payments/pull/482
python agent.py --pr https://github.com/acme/payments/pull/482 --output review.md
python agent.py --pr https://github.com/acme/payments/pull/482 --model claude-sonnet-4-20250514
```

## Output Example

```text
┌──────────────────────── PR Review ────────────────────────┐
│ Repository  acme/payments                                 │
│ PR          #482 Add invoice reconciliation               │
│ Verdict     REQUEST_CHANGES                               │
└───────────────────────────────────────────────────────────┘

## Summary of Changes
...

## Bugs Found
- Missing null check before invoice lookup

## Verdict
REQUEST_CHANGES
```

## Behavior

- Large diffs are chunked automatically if they exceed the review window.
- Rate limits are surfaced with a human-readable wait time.
- Output is markdown, so it is ready for a GitHub comment or a saved review file.