from __future__ import annotations
from pathlib import Path


def audit_docker(path: Path, text: str) -> list[dict]:
    lines = text.splitlines(); findings = []; upper = text.upper()
    def add(rule, severity, message, fix, line=1): findings.append({'file': str(path), 'rule': rule, 'severity': severity, 'message': message, 'fix': fix, 'line': line})
    for i, line in enumerate(lines, 1):
        if line.strip().upper().startswith('FROM ') and ':latest' in line.lower(): add('docker-pinned-base', 'IMPORTANT', 'Base image uses the mutable latest tag.', 'Pin an audited image tag or digest.', i)
        if line.strip().upper().startswith('COPY . .') and any(x.strip().upper().startswith('COPY ') and ('PACKAGE' in x.upper() or 'REQUIREMENTS' in x.upper()) for x in lines[:i-1]) is False and ('package.json' in upper or 'requirements.txt' in upper): add('docker-layer-cache', 'NICE-TO-HAVE', 'COPY . . appears before dependency metadata, reducing layer-cache reuse.', 'Copy dependency manifests and install dependencies before copying application source.', i)
        if re_secret(line): add('docker-secret', 'CRITICAL', 'Potential secret is being passed through ARG or ENV and may be baked into image history.', 'Use runtime secret injection instead of ARG/ENV for credentials.', i)
    if not any(line.strip().upper().startswith('USER ') for line in lines): add('docker-root', 'IMPORTANT', 'No USER directive was found; the container likely runs as root.', 'Create and switch to a non-root user.', 1)
    if 'HEALTHCHECK' not in upper: add('docker-healthcheck', 'NICE-TO-HAVE', 'No HEALTHCHECK directive was found.', 'Add a health check appropriate to the service.', 1)
    if 'APT-GET INSTALL' in upper and '--NO-INSTALL-RECOMMENDS' not in upper: add('docker-apt-recommends', 'NICE-TO-HAVE', 'apt-get install does not disable recommended packages.', 'Use --no-install-recommends and clean apt lists in the same layer.', 1)
    return findings


def re_secret(line: str) -> bool:
    upper = line.upper()
    return any(token in upper for token in ('API_KEY=', 'PASSWORD=', 'SECRET=', 'TOKEN=')) and any(upper.strip().startswith(x) for x in ('ARG ', 'ENV '))
