#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from pathlib import Path
import yaml
from rich.console import Console
from rich.table import Table
from auditors.docker_rules import audit_docker
from auditors.k8s_rules import audit_k8s
from auditors.ci_rules import audit_ci
from auditors.ai_reviewer import review_configs

console=Console(); MODEL='claude-sonnet-4-20250514'; SKIP={'.git','node_modules','dist','build','.next'}

def discover(root):
    found=[]
    for p in root.rglob('*'):
        if not p.is_file() or any(x in SKIP for x in p.relative_to(root).parts): continue
        if p.name.startswith('Dockerfile') or p.name in {'docker-compose.yml','docker-compose.yaml','.gitlab-ci.yml'} or '.github/workflows' in p.as_posix(): found.append(p)
        elif p.suffix in {'.yml','.yaml'}:
            try:
                if any(isinstance(doc,dict) and doc.get('kind') for doc in yaml.safe_load_all(p.read_text(encoding='utf-8',errors='ignore'))): found.append(p)
            except yaml.YAMLError: pass
    return found

def markdown(findings):
    lines=['# Infrastructure Configuration Audit','']
    for f in findings: lines += [f"## {f.get('severity','IMPORTANT')}: {f.get('file')}:{f.get('line',1)}",f"**{f.get('message','')}**",f"Fix: {f.get('fix','')}",'']
    return '\n'.join(lines)

def main():
    p=argparse.ArgumentParser(description='Audit Docker, Kubernetes, and CI configuration.'); p.add_argument('--project',required=True); p.add_argument('--rules-only',action='store_true'); p.add_argument('--severity'); p.add_argument('--output'); p.add_argument('--fix',action='store_true'); p.add_argument('--ci-mode',action='store_true'); p.add_argument('--model',default=MODEL); args=p.parse_args(); root=Path(args.project).resolve()
    if not root.is_dir(): p.error(f'Project not found: {root}')
    configs=[]; findings=[]
    for path in discover(root):
        text=path.read_text(encoding='utf-8',errors='ignore'); configs.append({'file':str(path.relative_to(root)),'content':text[:12000]})
        if path.name.startswith('Dockerfile'): findings += audit_docker(path.relative_to(root),text)
        elif path.name in {'.gitlab-ci.yml'} or '.github/workflows' in path.as_posix(): findings += audit_ci(path.relative_to(root),text)
        else:
            try:
                for document in yaml.safe_load_all(text):
                    if isinstance(document,dict): findings += audit_k8s(path.relative_to(root),document)
            except yaml.YAMLError: findings.append({'file':str(path.relative_to(root)),'severity':'IMPORTANT','message':'YAML could not be parsed safely.','fix':'Correct the YAML syntax before deployment.'})
    if not args.rules_only and os.getenv('ANTHROPIC_API_KEY'):
        from anthropic import Anthropic
        findings += review_configs(Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY')),args.model,configs,findings)
    shown=[f for f in findings if not args.severity or f.get('severity') in args.severity.split(',')]
    table=Table(title='Infrastructure Audit'); [table.add_column(c) for c in ('File','Severity','Issue')]
    for f in shown: table.add_row(str(f.get('file','')),str(f.get('severity','')),str(f.get('message','')))
    console.print(table)
    if args.output: Path(args.output).write_text(markdown(shown),encoding='utf-8')
    if args.fix: Path('fixes.md').write_text(markdown(shown),encoding='utf-8')
    return 1 if args.ci_mode and any(f.get('severity')=='CRITICAL' for f in shown) else 0
if __name__=='__main__': raise SystemExit(main())
