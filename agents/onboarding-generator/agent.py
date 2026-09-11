#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from core.doc_builder import build_guide, render_markdown
from core.ownership_mapper import map_ownership
from core.repo_analyzer import analyze_repository
from core.setup_detector import detect_setup

console = Console(); DEFAULT_MODEL = 'claude-sonnet-4-20250514'

def main() -> int:
    parser = argparse.ArgumentParser(description='Generate an evidence-based engineering onboarding guide.')
    parser.add_argument('--project', required=True); parser.add_argument('--output', default='ONBOARDING.md'); parser.add_argument('--team-size', choices=['small','medium','large'], default='medium'); parser.add_argument('--no-git-history', action='store_true'); parser.add_argument('--format', choices=['markdown','html'], default='markdown'); parser.add_argument('--model', default=DEFAULT_MODEL)
    args = parser.parse_args(); root = Path(args.project).resolve()
    if not root.is_dir(): parser.error(f'Project not found: {root}')
    analysis = analyze_repository(root); setup = detect_setup(root); dirs = [name for name in analysis['top_dirs'] if name not in {'.github'}]
    ownership = map_ownership(root, dirs, not args.no_git_history)
    key_files = '\n'.join(analysis['files'][:80]); api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        generated = build_guide(Anthropic(api_key=api_key), args.model, {**analysis, 'sample_files': key_files}, setup, ownership)
    else:
        generated = {'overview': 'AI synthesis skipped because ANTHROPIC_API_KEY is not set. Review the verified repository inventory below.', 'reading_order': [{'path': p, 'reason': 'Detected repository entry point or representative source file.'} for p in analysis['entry_points'][:10]], 'key_concepts': [], 'gotchas': [], 'first_tasks': []}
    output = render_markdown(analysis, setup, ownership, generated)
    if args.format == 'html': output = '<html><body><pre>' + output.replace('&','&amp;').replace('<','&lt;') + '</pre></body></html>'
    Path(args.output).write_text(output, encoding='utf-8'); console.print(Panel(output[:3000], title='Onboarding Guide')); return 0

if __name__ == '__main__': raise SystemExit(main())
