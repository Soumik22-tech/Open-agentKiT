# Meeting Transcript → Action Items Agent

Analyzes meeting transcripts to extract summaries, decisions, and structured action items with owners and deadlines.

## Setup

```bash
pip install -r requirements.txt
python agent.py --transcript meeting.txt
```

## Usage

```bash
python agent.py --transcript meeting.txt
python agent.py --transcript zoom_export.vtt
python agent.py --transcript meeting.txt --output notes.md
python agent.py --transcript meeting.txt --format slack
python agent.py --transcript meeting.txt --format jira
```

## Output Formats

- **markdown**: Clean .md file with sections
- **slack**: Formatted message ready to paste into Slack
- **jira**: CSV importable into Jira
- **plain**: Simple text for email

## Features

- Auto-detects transcript format (Zoom, Otter.ai, plain text)
- Extracts executive summary
- Lists key decisions
- Generates action items with owners and deadlines
- Multiple export formats
