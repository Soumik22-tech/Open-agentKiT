# Dependency Upgrade Agent

Checks outdated Python, Node.js, and Go dependencies, reads available release notes, scans your codebase for actual usage, and explains upgrade risk before changing anything.

## Setup

```bash
pip install -r requirements.txt
$env:ANTHROPIC_API_KEY = "your-key"  # PowerShell
export ANTHROPIC_API_KEY="your-key" # macOS/Linux
```

## Usage

```bash
python agent.py --project .
python agent.py --project . --manifest requirements.txt --verbose
python agent.py --project . --package requests --severity HIGH
python agent.py --project . --output upgrade-report.md
python agent.py --project . --auto-apply-safe
```

Supported manifests: `requirements.txt`, `pyproject.toml`, `package.json`, and `go.mod`.

## Why This Beats Dependabot

Dependabot and Renovate identify version changes and open pull requests. This agent also scans the project to find the exact imports and usage sites affected, reads available release notes, and asks Claude to connect breaking changes to those real call sites. A major upgrade can therefore say which imported API is at risk and what migration step is needed instead of only saying “review this PR.”

For example, if a project imports `requests.Session` in 18 files and the target release changes timeout or adapter behavior, the report lists those usages and recommends a migration/testing level. Unused APIs mentioned in a changelog do not inflate the project’s risk.

## Rate Limits and Caching

Registry responses are cached for 24 hours under `~/.cache/dependency-upgrader`, and requests are rate-limited. GitHub’s unauthenticated API is limited to roughly 60 requests per hour. Set `GITHUB_TOKEN` in the environment for a higher limit. If GitHub is unavailable or rate-limited, the report explicitly falls back to version-diff-only analysis.

Private or internal packages that cannot be resolved are skipped with a note rather than crashing the scan.

## Automatic Updates

`--auto-apply-safe` only updates packages assessed as LOW risk and creates `manifest.ext.bak` before writing. MEDIUM and HIGH risk packages are never modified automatically. Review the generated report and run your project’s tests after any update.
