#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_PATH="$SCRIPT_DIR/agent.py"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required to install the alias."
  exit 1
fi

git config --global alias.ai-commit "!python \"$AGENT_PATH\""

echo "Installed git ai-commit alias."
echo "Usage: git ai-commit"
