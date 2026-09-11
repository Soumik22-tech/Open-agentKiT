#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from core.input_parser import parse_input
from core.postmortem_builder import build_postmortem, render

console=Console(); MODEL='claude-sonnet-4-20250514'
def main():
    p=argparse.ArgumentParser(description='Generate a blameless incident postmortem from raw notes.'); p.add_argument('--notes'); p.add_argument('--stdin',action='store_true'); p.add_argument('--format',dest='input_format'); p.add_argument('--severity-style',choices=['sev','priority'],default='sev'); p.add_argument('--output',default='POSTMORTEM.md'); p.add_argument('--template',choices=['google','simple'],default='google'); p.add_argument('--model',default=MODEL); args=p.parse_args()
    if not args.notes and not args.stdin: p.error('Provide --notes or --stdin')
    text=sys.stdin.read() if args.stdin else Path(args.notes).read_text(encoding='utf-8',errors='ignore'); timeline=parse_input(text,args.notes or 'stdin')
    if not os.getenv('ANTHROPIC_API_KEY'): data={'summary':'AI generation skipped because ANTHROPIC_API_KEY is not set.','impact':'Insufficient information in source notes — please add manually','timeline':timeline['events'],'action_items':[]}
    else: data=build_postmortem(Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY')),args.model,timeline,args.severity_style,args.template)
    output=render(data,'INC-'+datetime.now().strftime('%Y%m%d-%H%M%S'),args.template); Path(args.output).write_text(output,encoding='utf-8'); console.print(Panel(output,title='Incident Postmortem')); return 0
if __name__=='__main__': raise SystemExit(main())
