# Research & Report Agent

Give it a topic, it searches the web, reads multiple sources, synthesizes information with Claude, and generates a professional research report with citations.

## Prerequisites

- Python 3.10+
- `pip`
- `ANTHROPIC_API_KEY`

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`
3. Run `python agent.py --topic "your research topic"`

## Usage

```bash
python agent.py --topic "impact of remote work on productivity"
python agent.py --topic "Kubernetes security best practices" --depth deep
python agent.py --topic "..." --html
python agent.py --topic "..." --no-web  # Use Claude knowledge only
```

## Depth Levels

- **quick:** 3 searches × 2 sources (5 min, ~$0.10)
- **standard:** 5 searches × 3 sources (10 min, ~$0.25)
- **deep:** 8 searches × 5 sources (20 min, ~$0.60)

## Output

- Markdown report (auto-saved)
- HTML version (with `--html` flag)
- Proper citations for every claim
- Bibliography with URLs

SOURCE QUALITY SIGNALS (heuristics):
  - Prefer: .edu, .gov, major news outlets, official documentation
  - Acceptable: established tech blogs, Wikipedia (as starting point only)
  - Penalize: forums (Reddit, Quora), personal blogs without credentials, sites with excessive ads

REPORT QUALITY:
  - Executive summary: 2-3 sentences, complete standalone summary
  - Key findings: 5-7 bullet points with citations
  - Detailed analysis: 800-1500 words, structured sections
  - Conflicting views section: where sources disagree (honest research shows uncertainty)
  - Word count shown at end
  - Reading time estimate

README must include:
  - How to get each API key (with links)
  - Which provider to use if you have no keys (DuckDuckGo)
  - Example report output (truncated)
  - Cost estimate per research session
  - Comparison: this vs Perplexity Pro

## Prerequisites

- Python 3.10+
- `pip`
- `ANTHROPIC_API_KEY`

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`
3. Run `python agent.py --topic "your research topic"`

## Usage

```bash
python agent.py --topic "impact of remote work on productivity"
python agent.py --topic "Kubernetes security best practices" --depth deep
python agent.py --topic "..." --html
python agent.py --topic "..." --no-web  # Use Claude knowledge only
```

## Depth Levels

- **quick:** 3 searches × 2 sources (5 min, ~$0.10)
- **standard:** 5 searches × 3 sources (10 min, ~$0.25)
- **deep:** 8 searches × 5 sources (20 min, ~$0.60)

## Output

- Markdown report (auto-saved)
- HTML version (with `--html` flag)
- Proper citations for every claim
- Bibliography with URLs
