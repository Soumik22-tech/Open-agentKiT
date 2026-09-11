from __future__ import annotations
from pathlib import Path


def audit_k8s(path: Path, document: dict) -> list[dict]:
    findings=[]; kind=document.get('kind',''); metadata=document.get('metadata') or {}; spec=document.get('spec') or {}
    def add(rule, severity, message, fix): findings.append({'file':str(path),'rule':rule,'severity':severity,'message':message,'fix':fix,'line':1})
    if not kind: return findings
    pod = spec.get('template', {}).get('spec', {}) if kind in {'Deployment','StatefulSet','DaemonSet'} else spec
    containers = pod.get('containers', []) or []
    for container in containers:
        image=str(container.get('image',''))
        if image.endswith(':latest') or ':' not in image: add('k8s-image-pin','IMPORTANT',f"Container image '{image}' is not pinned to a stable version.",'Use an immutable version tag or digest.')
        security=container.get('securityContext',{}) or {}
        if security.get('privileged') is True or security.get('allowPrivilegeEscalation') is True: add('k8s-privileged','CRITICAL','Container enables privileged execution or privilege escalation.','Disable privilege escalation unless an explicit security review approves it.')
        if not (container.get('resources') or {}).get('requests') or not (container.get('resources') or {}).get('limits'): add('k8s-resources','IMPORTANT','Container lacks complete resource requests and limits.','Set CPU and memory requests and limits.')
        for env in container.get('env',[]) or []:
            if any(word in str(env.get('name','')).upper() for word in ('PASSWORD','TOKEN','SECRET','API_KEY')) and 'valueFrom' not in env: add('k8s-plain-secret','CRITICAL','Sensitive environment variable is supplied as a plain value.','Reference a Kubernetes Secret with valueFrom.secretKeyRef.')
    if kind in {'Deployment','StatefulSet'}:
        if int(spec.get('replicas',1) or 1) == 1: add('k8s-single-replica','IMPORTANT','Workload has one replica and may be a single point of failure.','Set an appropriate replica count or document why this is a singleton.')
        first_container = (spec.get('template',{}).get('spec',{}).get('containers') or [{}])[0]
        if not first_container.get('livenessProbe'): add('k8s-liveness','IMPORTANT','No liveness probe is configured.','Add a livenessProbe for service health.')
        if not first_container.get('readinessProbe'): add('k8s-readiness','IMPORTANT','No readiness probe is configured.','Add a readinessProbe so traffic only reaches ready pods.')
    if pod.get('hostNetwork') or pod.get('hostPID'): add('k8s-host-namespace','CRITICAL','Pod uses host network or PID namespace.','Remove host namespace sharing unless explicitly required and reviewed.')
    return findings
