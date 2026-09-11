from __future__ import annotations
from pathlib import Path
import re


def audit_ci(path: Path, text: str) -> list[dict]:
    findings=[]
    def add(rule,severity,message,fix,line=1): findings.append({'file':str(path),'rule':rule,'severity':severity,'message':message,'fix':fix,'line':line})
    upper=text.upper()
    _secret_key_pattern = re.compile(r'^\s*(?:-\s*name:\s*)?(?:[A-Za-z_]+_)?(TOKEN|PASSWORD|API_KEY|SECRET)\s*:\s*(.+)$', re.I)
    for line in text.splitlines():
        match = _secret_key_pattern.match(line)
        if not match:
            continue
        value = match.group(2).strip().strip('"').strip("'")
        if not value:
            continue
        is_safe_reference = bool(re.match(r'^\$\{\{.*\}\}$', value)) or bool(re.match(r'^\$\{?[A-Z_][A-Z0-9_]*\}?$', value))
        if not is_safe_reference:
            add('ci-hardcoded-secret', 'CRITICAL', 'Workflow appears to contain a hardcoded secret value.', 'Use the platform secret store, such as ${{ secrets.NAME }}.')
            break
    if 'CACHE' not in upper and ('INSTALL' in upper or 'PIP ' in upper or 'NPM ' in upper): add('ci-no-cache','IMPORTANT','Dependency installation has no apparent cache configuration.','Cache package-manager data to reduce build time and CI cost.')
    if 'TIMEOUT-MINUTES' not in upper: add('ci-timeout','IMPORTANT','No timeout-minutes setting was found.','Set a finite timeout for every job.')
    for i,line in enumerate(text.splitlines(),1):
        if re.search(r'uses:\s*[^@\s]+@(main|master|latest)\s*$', line, re.I): add('ci-unpinned-action','IMPORTANT','Third-party action uses a mutable branch/tag.','Pin to a reviewed version or commit SHA.',i)
    if 'CONCURRENCY:' not in upper and any(word in upper for word in ('DEPLOY','PRODUCTION','RELEASE')): add('ci-no-concurrency','NICE-TO-HAVE','Deploy workflow has no concurrency group.','Prevent overlapping deploys with a concurrency group.')
    return findings
