# Changelog & Release Notes Generator

Reads git history between two tags/commits, groups changes intelligently, writes professional release notes — the kind users actually want to read.

## Setup

```bash
pip install -r requirements.txt
python agent.py --from v1.2.0 --to v1.3.0
```

## Usage

```bash
python agent.py --from v1.2.0 --to v1.3.0
python agent.py --from v1.2.0 --to HEAD --output CHANGELOG.md --append
python agent.py --from v1.2.0 --to HEAD --format json
python agent.py --from v1.2.0 --to HEAD --audience users
```

## Features

- Intelligent commit grouping (Features, Fixes, Breaking Changes)
- Professional, user-facing language
- Multiple output formats (Markdown, JSON)
- Append to existing CHANGELOG.md
- Contributor credits (--credit-contributors)
