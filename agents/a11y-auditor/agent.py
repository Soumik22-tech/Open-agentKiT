#!/usr/bin/env python3
from __future__ import annotations
import argparse, html, os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from auditors.framework_detector import detect_framework
from auditors.static_rules import audit_source

console=Console(); SKIP={'.git','node_modules','dist','build','.next','coverage'}; MODEL='claude-sonnet-4-20250514'
def files(root):
    if root.is_file(): return [root]
    return [p for p in root.rglob('*') if p.is_file() and p.suffix in {'.html','.jsx','.tsx','.vue'} and not any(x in SKIP for x in p.relative_to(root).parts)]
def render_html(findings):
    rows=''.join(f"<tr><td>{html.escape(str(x.get('file')))}</td><td>{x.get('priority')}</td><td>{html.escape(x.get('message',''))}</td><td><pre>{html.escape(x.get('fix',''))}</pre></td></tr>" for x in findings)
    return f'<!doctype html><meta charset="utf-8"><title>Accessibility Audit</title><style>body{{font:16px system-ui;margin:2rem}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:.6rem;text-align:left}}pre{{white-space:pre-wrap}}</style><h1>Accessibility Audit</h1><table><tr><th>File</th><th>Priority</th><th>User impact</th><th>Fix</th></tr>{rows}</table>'
def main():
    p=argparse.ArgumentParser(description='Audit HTML, JSX, TSX, and Vue source for WCAG issues.'); p.add_argument('--project'); p.add_argument('--file'); p.add_argument('--rules-only',action='store_true'); p.add_argument('--wcag-level',choices=['A','AA','AAA'],default='AA'); p.add_argument('--output'); p.add_argument('--ci-mode',action='store_true'); p.add_argument('--model',default=MODEL); args=p.parse_args()
    if not args.project and not args.file: p.error('Provide --project or --file')
    target=Path(args.file or args.project).resolve(); findings=[]; sources=[]
    for path in files(target):
        text=path.read_text(encoding='utf-8',errors='ignore'); source={'file':str(path),'framework':detect_framework(path,text),'text':text}; sources.append(source); findings += audit_source(path,text,args.wcag_level)
    if not args.rules_only and os.getenv('ANTHROPIC_API_KEY'):
        from anthropic import Anthropic
        from auditors.ai_reviewer import review
        for source in sources: findings += review(Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY')),args.model,source,[x for x in findings if x.get('file')==source['file']])
    if args.output: Path(args.output).write_text(render_html(findings) if args.output.endswith('.html') else '\n'.join(f"- {x.get('priority')}: {x.get('file')} — {x.get('message')}\n  Fix: {x.get('fix')}" for x in findings),encoding='utf-8')
    table=Table(title='Accessibility Audit'); [table.add_column(x) for x in ('File','Priority','WCAG','Issue')]
    for x in findings: table.add_row(str(x.get('file')),str(x.get('priority')),str(x.get('wcag','')),str(x.get('message')))
    console.print(table); counts={level:sum(item.get('priority')==level for item in findings) for level in ('CRITICAL','SERIOUS','MODERATE')}; console.print(f"Scanned {len(sources)} files. {counts}"); return 1 if args.ci_mode and any(x.get('priority')=='CRITICAL' for x in findings) else 0
if __name__=='__main__': raise SystemExit(main())
