# Onboarding Doc Generator

Generates an evidence-based Day 1 onboarding guide from repository structure, setup files, and git ownership history.

```bash
pip install -r requirements.txt
python agent.py --project . --output ONBOARDING.md
python agent.py --project . --no-git-history --format html
```

The ownership section reports top contributors per directory and flags a bus-factor warning when one contributor owns all recorded history. It uses only author names already present in local git history and never fetches personal data. Setup commands are reported from repository evidence; unclear setup is stated as unclear rather than invented.
