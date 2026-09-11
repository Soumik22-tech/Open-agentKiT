from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

SKIP_DIRS = {'.git', 'node_modules', 'dist', 'build', '.venv', 'venv', '__pycache__', '.next'}
LANGUAGES = {'.py':'Python', '.js':'JavaScript', '.ts':'TypeScript', '.tsx':'TypeScript/React', '.jsx':'JavaScript/React', '.go':'Go', '.rs':'Rust', '.java':'Java', '.rb':'Ruby', '.php':'PHP'}


def analyze_repository(root: Path) -> dict:
    files = []
    extensions = Counter()
    top_dirs = Counter()
    for path in root.rglob('*'):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        files.append(path)
        extensions[path.suffix.lower()] += 1
        relative = path.relative_to(root)
        if len(relative.parts) > 1:
            top_dirs[relative.parts[0]] += 1

    languages = Counter(LANGUAGES[ext] for ext in extensions if ext in LANGUAGES)
    entry_names = {'main.py','app.py','manage.py','index.js','index.ts','Dockerfile','docker-compose.yml','Makefile'}
    entry_points = [p.relative_to(root).as_posix() for p in files if p.name in entry_names]
    frameworks = detect_frameworks(root, files)
    return {'file_count': len(files), 'top_dirs': dict(top_dirs.most_common()), 'extensions': dict(extensions), 'languages': dict(languages), 'frameworks': frameworks, 'entry_points': entry_points, 'files': [p.relative_to(root).as_posix() for p in files]}


def detect_frameworks(root: Path, files: list[Path]) -> list[str]:
    text = '\n'.join(p.read_text(encoding='utf-8', errors='ignore')[:10000] for p in files if p.name in {'package.json','requirements.txt','pyproject.toml','go.mod'} or p.suffix in {'.py','.js','.ts'})
    names = {'fastapi':'FastAPI','flask':'Flask','django':'Django','react':'React','next':'Next.js','vue':'Vue','express':'Express','pytest':'pytest','pandas':'pandas'}
    return sorted({label for token, label in names.items() if re.search(rf'\b{re.escape(token)}\b', text, re.I)})
