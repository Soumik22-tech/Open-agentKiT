# Infra/Config Auditor

Audits Dockerfiles, Kubernetes manifests, GitHub Actions, and GitLab CI with deterministic checks plus optional Claude contextual review.

```bash
pip install -r requirements.txt
python agent.py --project . --rules-only
python agent.py --project . --output audit-report.md
python agent.py --project . --ci-mode
```

`--rules-only` requires no API key and exits 1 when a CRITICAL issue is found in `--ci-mode`. Typical findings include mutable image tags, root containers, missing probes/resources/timeouts, plain secrets, and unpinned CI actions. The optional AI pass reviews cross-file inconsistencies and workload context; deterministic findings remain visible.

Add `python agent.py --project . --rules-only --ci-mode` as a required GitHub Actions check. Rule-based results are a pre-deployment safety net, not a replacement for policy engines or runtime monitoring.
