# Open-agentKiT — 20 Free AI Agents That Replace $1,300+/Month in SaaS Tools

Production-ready Python CLI agents powered by the Claude API. Each one replicates the core value of an expensive SaaS product — code review, security scanning, dependency risk assessment, meeting notes, incident postmortems, and more — as a script you own and run yourself.

No subscriptions. No vendor lock-in. You bring your own `ANTHROPIC_API_KEY` and pay only for what you use — typically **$0.01–$0.60 per run**, instead of a monthly SaaS bill.

---

## Why this exists

Most "AI agent" repos are demos. These are not. Every agent here was built to be actually run against real projects, real git history, real databases, and real config files — and every one has been tested against real inputs (not just reviewed as code) before being pushed here.

---

## The 20 Agents

### Code Intelligence

| Agent | Replaces | Typical Price | What It Does |
|---|---|---|---|
| **PR Reviewer** | GitHub Copilot code review | $10/mo | Analyzes a GitHub PR diff, returns structured review with bugs, security issues, and a verdict |
| **Codebase Explainer** | Copilot Chat / onboarding time | $10/mo | Clones any repo, explains architecture, tech stack, and key files |
| **Bug Hunter** | SonarQube / static analysis suites | $50+/mo | Finds real logic bugs (not style issues) with confidence scores and fixes |
| **Commit Writer** | Conventional Commit IDE plugins | $0–5/mo | Generates 3 Conventional Commit message options from your staged diff |
| **README Generator** | ReadMe.io (basic tier) | $100/mo | Reads your actual code and generates a real, non-generic README |

### Business & Infra Automation

| Agent | Replaces | Typical Price | What It Does |
|---|---|---|---|
| **Security Scanner** | Snyk | $98/mo | Two-phase scan (instant regex + Claude deep analysis) for real exploitable vulnerabilities |
| **Query Builder** | Outerbase / Retool | $50/mo | Natural language → SQL for PostgreSQL, MySQL, and SQLite, read-only by default |
| **Refactor Agent** | Devin-style autonomous coding | $500/mo | Plans and executes multi-file refactors with git backup and rollback |
| **Research Agent** | Perplexity Pro | $20/mo | Searches the web, reads full pages, writes a cited research report |
| **API Doc Generator** | ReadMe.io / Swagger hosting | $100/mo | FastAPI/Flask routes → OpenAPI spec, HTML docs, and a Postman collection |

### Developer Workflow & Data

| Agent | Replaces | Typical Price | What It Does |
|---|---|---|---|
| **Changelog Generator** | Manual release notes | Time cost | Git log between two refs → categorized, human-readable changelog |
| **Test Suite Generator** | Manual test writing | Time cost | Generates pytest tests, then runs them and reports validation results |
| **Log Analyzer** | Splunk / Datadog error intelligence | $200+/mo | Stack trace → root cause, severity, and fix, with local code context |
| **Meeting Agent** | Otter.ai / Fireflies | $20–30/mo | Transcript → summary, decisions, and action items with owners and deadlines |
| **Data Analyst** | Tableau / ChatGPT Code Interpreter | $20–300+/mo | Ask questions about a CSV/Excel file in plain English, get tables and analysis |

### Engineering Operations

| Agent | Replaces | Typical Price | What It Does |
|---|---|---|---|
| **Dependency Upgrader** | Dependabot / Renovate | $0–50/mo | Reads real changelogs and your actual code's usage before rating upgrade risk |
| **Onboarding Generator** | New-hire ramp-up time | Time cost | Repo structure, setup steps, git-history ownership map, and bus-factor warnings |
| **Config Auditor** | A dedicated DevOps reviewer | High staff cost | Audits Dockerfiles, Kubernetes manifests, and CI configs; CI-gateable |
| **Postmortem Writer** | Incident management platforms | $20+/mo | Raw incident notes → a blameless, SRE-style postmortem document |
| **Accessibility Auditor** | axe DevTools Pro | Per-seat cost | Scans HTML/JSX/TSX/Vue source for WCAG violations with plain-English impact |

---

## Quick Start

**Prerequisites:** Python 3.10+, `pip`, and an `ANTHROPIC_API_KEY`.

```bash
cd agents/{agent-name}
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
python agent.py [options]
```

Every agent is fully independent — clone the repo, `cd` into the one you need, and run it. You don't need to set up all 20.

---

## Usage Examples

```bash
# Review a pull request
cd agents/pr-reviewer
python agent.py --pr https://github.com/owner/repo/pull/123

# Understand a new codebase in seconds
cd agents/codebase-explainer
python agent.py --repo https://github.com/owner/repo --depth standard

# Find real logic bugs
cd agents/bug-hunter
python agent.py --file src/utils.py

# Write your commit message for you
cd agents/commit-writer
git add .
python agent.py

# Full security audit
cd agents/security-scanner
python agent.py --project /path/to/codebase --severity HIGH,CRITICAL

# Query a database in plain English
cd agents/query-builder
python agent.py --db postgresql://user:pass@localhost/mydb

# Refactor across many files with rollback safety
cd agents/refactor-agent
python agent.py --project . --goal "convert all callbacks to async/await"

# Research a topic with citations
cd agents/research-agent
python agent.py --topic "impact of AI on software engineering" --depth deep --html

# Generate release notes between two tags
cd agents/changelog-generator
python agent.py --from v1.2.0 --to v1.3.0 --output CHANGELOG.md --append

# Generate and run a real test suite
cd agents/test-generator
python agent.py --file src/utils.py --run

# Turn a meeting transcript into action items
cd agents/meeting-agent
python agent.py --transcript zoom_transcript.vtt --output notes.md

# Talk to your spreadsheet
cd agents/data-analyst
python agent.py --file data.csv

# Check if a dependency upgrade is actually safe
cd agents/dependency-upgrader
python agent.py --project . --output upgrade-report.md

# Generate a real onboarding doc from git history
cd agents/onboarding-generator
python agent.py --project . --output ONBOARDING.md

# Audit your Dockerfiles, K8s manifests, and CI configs
cd agents/config-auditor
python agent.py --project . --rules-only --ci-mode

# Turn incident notes into a blameless postmortem
cd agents/postmortem-writer
python agent.py --notes incident-notes.txt --output postmortem.md

# Catch accessibility issues before you deploy
cd agents/a11y-auditor
python agent.py --project . --rules-only --output a11y-report.html
```

Full option lists are documented in each agent's own `README.md`.

---

## What Makes These Different From a Demo Repo

- **Two-tier checks where it matters.** Security Scanner and Config Auditor run instant, free, rule-based checks first, and only call Claude for the deeper contextual pass — so `--rules-only` mode needs no API key at all.
- **Real safety rails.** Refactor Agent creates a git backup branch and a restorable manifest before touching a single file. Query Builder is read-only by default. Data Analyst runs generated code in a sandboxed namespace with no access to `os`, `eval`, `exec`, or `open`.
- **Validation, not blind trust.** Test Suite Generator runs generated tests and reports the result instead of handing you unvalidated code.
- **Honest about limits.** Where a feature isn't implemented yet, such as JS/TS support in Test Suite Generator or Node/Go parsers in API Doc Generator, the agent says so clearly instead of pretending or failing silently.

Each agent folder contains its own `agent.py`, `requirements.txt`, `.env.example`, and `README.md` with detailed usage docs specific to that tool.

---

## Project Structure

The repository is intentionally organized as 20 independent Python CLI projects. Each agent can
be installed and run without importing the other agents. This keeps dependencies, safety behavior,
API prompts, and output formats isolated: you can use one tool in a CI job without installing the
rest of the suite.

```text
.
├── README.md                         # This overview and the complete usage guide
├── agents/
│   ├── pr-reviewer/
│   │   ├── agent.py                   # GitHub PR URL parsing, diff retrieval, review orchestration
│   │   ├── requirements.txt           # Anthropic, Rich, and HTTP dependencies
│   │   ├── .env.example               # Required environment variables
│   │   └── README.md                  # Agent-specific setup and examples
│   │
│   ├── codebase-explainer/
│   │   ├── agent.py                   # Repository cloning, file selection, stack detection, explanation
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── bug-hunter/
│   │   ├── agent.py                   # Multi-language bug analysis and fixed-code output
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── commit-writer/
│   │   ├── agent.py                   # Staged diff analysis and Conventional Commit selection
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── readme-generator/
│   │   ├── agent.py                   # Project scanning, command detection, README generation
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── security-scanner/
│   │   ├── agent.py                   # CLI orchestration, reporting, filtering, and fix output
│   │   ├── scanner/
│   │   │   ├── file_scanner.py        # Project file discovery and .gitignore handling
│   │   │   ├── regex_prescan.py       # Fast secret and dangerous-pattern checks
│   │   │   └── ai_scanner.py          # Claude deep analysis for flagged files
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── query-builder/
│   │   ├── agent.py                   # Natural-language query REPL and approval flow
│   │   ├── db/
│   │   │   ├── connector.py           # SQLite, PostgreSQL, and MySQL connections
│   │   │   └── schema_extractor.py    # Tables, columns, types, and relationships
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── refactor-agent/
│   │   ├── agent.py                   # Planning, approval, execution, and rollback orchestration
│   │   ├── core/
│   │   │   ├── planner.py             # File discovery and refactoring plan generation
│   │   │   ├── executor.py            # Controlled edits and session manifest creation
│   │   │   ├── validator.py            # Syntax and post-edit validation
│   │   │   └── rollback.py             # Restore files from a recorded refactor session
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── research-agent/
│   │   ├── agent.py                   # Topic CLI, depth selection, and report output
│   │   ├── research/
│   │   │   ├── searcher.py             # Web search, page fetching, and content cleanup
│   │   │   └── synthesizer.py          # Claude synthesis with source citations
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── api-doc-generator/
│   │   ├── agent.py                   # Framework detection and documentation orchestration
│   │   ├── parsers/
│   │   │   ├── python_parser.py       # FastAPI and Flask AST route extraction
│   │   │   ├── node_parser.py         # Explicitly reports Node.js as unsupported
│   │   │   └── go_parser.py           # Explicitly reports Go as unsupported
│   │   ├── generators/
│   │   │   ├── openapi.py              # OpenAPI 3.0 document generation
│   │   │   ├── html_docs.py             # Self-contained searchable HTML docs
│   │   │   └── postman.py               # Postman collection export
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── changelog-generator/
│   │   ├── agent.py                   # Git range parsing, grouping prompt, and release-note rendering
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── test-generator/
│   │   ├── agent.py                   # Source selection, test generation, and test execution CLI
│   │   ├── generators/
│   │   │   ├── python_analyzer.py     # Python AST function and method extraction
│   │   │   ├── js_analyzer.py         # Reserved module for planned JS/TS support
│   │   │   └── test_writer.py          # Claude pytest generation and result parsing
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── log-analyzer/
│   │   ├── agent.py                   # Log input, Claude analysis, and terminal reporting
│   │   ├── analyzer/
│   │   │   ├── log_parser.py           # Python, JavaScript, Java, and generic log parsing
│   │   │   ├── code_context.py         # Stack-trace file lookup and source snippets
│   │   │   └── pattern_db.py           # Deterministic known-error pattern matching
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── meeting-agent/
│   │   ├── agent.py                   # Transcript analysis and export-format orchestration
│   │   ├── parsers/
│   │   │   ├── format_detector.py      # VTT, SRT, labeled, and plain transcript detection
│   │   │   └── speaker_extractor.py    # Speaker parsing extension point
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── data-analyst/
│   │   ├── agent.py                   # Profile display and interactive analysis REPL
│   │   ├── core/
│   │   │   ├── data_loader.py         # CSV/Excel loading and aggregate profiling
│   │   │   ├── code_generator.py       # Natural-language question to pandas code
│   │   │   └── safe_executor.py        # Restricted execution namespace for generated code
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── dependency-upgrader/
│   │   ├── agent.py                   # End-to-end upgrade scan and report CLI
│   │   ├── core/
│   │   │   ├── manifest_parser.py      # requirements, pyproject, package.json, and go.mod parsing
│   │   │   ├── registry_client.py      # PyPI, npm, Go proxy, GitHub releases, and caching
│   │   │   ├── usage_scanner.py        # Local import and usage-site discovery
│   │   │   └── risk_assessor.py        # Version-gap logic and Claude risk assessment
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── onboarding-generator/
│   │   ├── agent.py                   # Onboarding document CLI and output formatting
│   │   ├── core/
│   │   │   ├── repo_analyzer.py        # Structure, language, framework, and entry-point detection
│   │   │   ├── ownership_mapper.py     # Git contributor and bus-factor analysis
│   │   │   ├── setup_detector.py        # Setup files, commands, and environment evidence
│   │   │   └── doc_builder.py            # Claude guide synthesis and Markdown rendering
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── config-auditor/
│   │   ├── agent.py                   # Config discovery, reporting, and CI exit codes
│   │   ├── auditors/
│   │   │   ├── docker_rules.py         # Dockerfile image, user, layer, secret, and health checks
│   │   │   ├── k8s_rules.py            # Kubernetes probes, resources, secrets, and security checks
│   │   │   ├── ci_rules.py             # GitHub Actions and GitLab CI safety checks
│   │   │   └── ai_reviewer.py           # Optional cross-file Claude review
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   ├── postmortem-writer/
│   │   ├── agent.py                   # Notes input, severity style, template, and output CLI
│   │   ├── core/
│   │   │   ├── input_parser.py         # Plain text/Slack normalization and timeline extraction
│   │   │   └── postmortem_builder.py   # Blameless Claude schema and Markdown assembly
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   └── a11y-auditor/
│       ├── agent.py                   # Source discovery, reporting, HTML output, and CI gating
│       ├── auditors/
│       │   ├── static_rules.py         # HTML/JSX/TSX/Vue WCAG source checks
│       │   ├── framework_detector.py   # React, Vue, and plain HTML detection
│       │   └── ai_reviewer.py           # Optional contextual WCAG review
│       ├── requirements.txt
│       ├── .env.example
│       └── README.md
```

### Shared File Conventions

Every agent follows the same local contract:

- `agent.py` is the executable entry point and owns the public CLI flags.
- `requirements.txt` lists only dependencies needed by that agent.
- `.env.example` documents API keys or optional service credentials without storing secrets.
- `README.md` explains setup, examples, outputs, limitations, and safety behavior.
- `core/`, `auditors/`, `scanner/`, `parsers/`, `generators/`, `db/`, and `research/` contain
  focused modules when the agent has more than one responsibility.

### How Data Flows Through an Agent

Most agents follow a predictable pipeline:

1. **Input discovery** reads a file, project directory, git range, transcript, log, or database.
2. **Deterministic analysis** parses structure, applies rules, extracts metadata, or finds local
	usage before any model call. This makes the free modes reproducible and reduces API cost.
3. **Contextual analysis** sends only the relevant material to Claude when AI review is enabled.
4. **Structured output** converts the result into JSON-like data before rendering tables, Markdown,
	HTML, SQL results, release notes, or postmortems.
5. **Safety handling** validates, backs up, limits, or clearly labels the result before writing files
	or applying changes.

The project is not one large Python package. Run commands from the individual agent directory so
its local imports and dependencies resolve exactly as documented.

---

## Total Value Replaced

| Category | Agents | Typical Monthly SaaS Cost |
|---|---|---|
| Code review & intelligence | PR Reviewer, Codebase Explainer, Bug Hunter, Commit Writer, README Generator | ~$175 |
| Security & infra | Security Scanner, Config Auditor, Dependency Upgrader | ~$150+ |
| Database & data | Query Builder, Data Analyst | ~$350 |
| Autonomous coding | Refactor Agent | ~$500 |
| Research & docs | Research Agent, API Doc Generator, Changelog Generator | ~$120 |
| Testing & ops | Test Suite Generator, Log Analyzer, Postmortem Writer | ~$220+ |
| Meetings & onboarding | Meeting Agent, Onboarding Generator | ~$30+ |
| Accessibility | Accessibility Auditor | Varies |
| **Total** | **20 agents** | **~$1,300+/month in equivalent tools** |

Your actual cost: Claude API usage, typically **$0.01–$0.60 per run** depending on the agent and input size.

*(These are rough, good-faith estimates of comparable product pricing for context — not a formal cost audit.)*

---

## FAQ

**Do I need to set up all 20 agents?**
No. Each one is fully independent. Pick the one you need and ignore the rest.

**What's the actual cost to run one?**
Just Claude API usage — most agents cost $0.01–$0.30 per run. Heavier agents like deep Research Agent runs or large Refactor Agent sessions can run up to ~$0.60.

**Can I self-host, with no API calls to Anthropic?**
No — these agents call the Claude API for the reasoning steps. You need an `ANTHROPIC_API_KEY`. The code itself is fully open source and yours to modify.

**Are these actually production-ready, or demos?**
They're built to be run for real. That said, this is a young project — if you hit a bug, please open an issue. See each agent's own README for anything not yet implemented.

**Why Claude instead of GPT-4/GPT-5?**
Strong structured JSON output, good long-context handling for reading full codebases/transcripts, and solid code reasoning at reasonable cost. Nothing stops you from porting the API calls to another provider.

**Is my code/data sent anywhere besides Anthropic?**
Only to the Claude API for the specific content each agent needs. Data Analyst specifically sends column names, types, and aggregate stats rather than raw rows. See each agent's README for its specific data-handling notes.

---

## Contributing

Found a bug? Have an idea for agent #21? Open an issue or a PR. Areas that could especially use help:

- JavaScript/TypeScript support for Test Suite Generator
- Node.js and Go route parsers for API Doc Generator
- More database drivers for Query Builder

---

## License

MIT License — use freely, modify, redistribute.
