# Incident Postmortem Writer

Turns rough incident notes, Slack exports, and mixed logs into a blameless Google SRE-style postmortem.

```bash
pip install -r requirements.txt
python agent.py --notes incident-notes.txt --output postmortem.md
python agent.py --notes slack-export.json --format slack-export --severity-style sev
cat notes.txt | python agent.py --stdin --template simple
```

The parser normalizes timestamped events and sorts them. Claude is instructed to preserve uncertainty, never invent a root cause or owner, and frame actions as system/process improvements rather than personal blame. Every document prominently includes a mandatory human-review disclaimer because AI output must be verified before distribution.

Example action output: `- [ ] Add an alert for connection-pool utilization above 80% — Owner: Unassigned — Due: Not specified`.
