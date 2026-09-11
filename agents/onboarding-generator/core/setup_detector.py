from __future__ import annotations

import re
from pathlib import Path


def detect_setup(root: Path) -> dict:
    evidence = []
    commands = []
    for name, command in [('Makefile','make targets'), ('package.json','npm scripts'), ('docker-compose.yml','docker compose'), ('docker-compose.yaml','docker compose'), ('pyproject.toml','Python project metadata'), ('requirements.txt','pip dependencies'), ('CONTRIBUTING.md','contributor guide'), ('README.md','existing README')]:
        path = root / name
        if path.exists():
            evidence.append(name)
            text = path.read_text(encoding='utf-8', errors='ignore')
            if name == 'Makefile':
                commands.extend(re.findall(r'^([A-Za-z0-9_-]+):', text, re.M))
            if name == 'package.json':
                commands.extend(re.findall(r'"([A-Za-z0-9:_-]+)"\s*:', text))
    env_vars = set()
    for path in root.rglob('*'):
        if path.is_file() and path.suffix in {'.py','.js','.ts','.tsx','.jsx'} and not any(part in {'.git','node_modules','dist','build'} for part in path.parts):
            text = path.read_text(encoding='utf-8', errors='ignore')
            env_vars.update(re.findall(r'(?:os\.environ(?:\.get)?\(["\']|process\.env\.)([A-Z][A-Z0-9_]+)', text))
    steps = []
    if (root/'requirements.txt').exists() or (root/'pyproject.toml').exists(): steps.append('Install Python dependencies')
    if (root/'package.json').exists(): steps.append('Install Node.js dependencies')
    if (root/'.env.example').exists(): steps.append('Copy .env.example and configure environment variables')
    if (root/'docker-compose.yml').exists() or (root/'docker-compose.yaml').exists(): steps.append('Start local services with Docker Compose')
    return {'evidence': evidence, 'commands': sorted(set(commands)), 'environment_variables': sorted(env_vars), 'suggested_steps': steps or ['Setup process unclear from repository — recommend asking a team member']}
