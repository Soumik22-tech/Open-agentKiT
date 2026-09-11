from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path


def _git(root: Path, args: list[str]) -> str:
    try:
        return subprocess.run(['git', *args], cwd=root, text=True, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return ''


def map_ownership(root: Path, directories: list[str], enabled: bool = True) -> dict:
    if not enabled:
        return {'available': False, 'directories': [], 'active_contributors': []}
    result = []
    for directory in directories:
        output = _git(root, ['log', '--format=%an|%ad', '--date=short', '--', directory])
        rows = [line.split('|', 1) for line in output.splitlines() if '|' in line]
        counts = Counter(row[0] for row in rows)
        contributors = [{'name': name, 'commits': count} for name, count in counts.most_common(3)]
        result.append({'directory': directory, 'contributors': contributors, 'last_active': rows[0][1] if rows else '', 'bus_factor_warning': len(counts) == 1 and bool(counts)})
    active = Counter(_git(root, ['log', '--since=6 months ago', '--format=%an']).splitlines())
    return {'available': bool(result), 'directories': result, 'active_contributors': [{'name': n, 'commits': c} for n, c in active.most_common()]}
