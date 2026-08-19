# API Documentation Generator

Scans your FastAPI/Flask codebase, extracts all routes, generates OpenAPI 3.0 spec + beautiful self-hosted HTML docs + Postman collection. Auto-detected, no config needed.

## Prerequisites

- Python 3.10+
- `pip`
- `ANTHROPIC_API_KEY`
- FastAPI or Flask project

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`
3. Run `python agent.py --project /path/to/api`

## Usage

```bash
python agent.py --project /path/to/api
python agent.py --project . --output ./docs
python agent.py --project . --serve  # Start local server
python agent.py --project . --title "My API" --version "2.0.0"
python agent.py --project . --no-html  # OpenAPI spec only
```

## Output Files

- **openapi.json** — OpenAPI 3.0 spec (import to Swagger UI, Postman, Insomnia, etc.)
- **index.html** — Beautiful self-contained documentation
- **postman_collection.json** — Ready-to-import Postman collection

## Supported Frameworks

Currently supports: Python (FastAPI, Flask). Node.js and Go support coming soon — contributions welcome.
  python agent.py --project . --output ./docs        (output directory)
  python agent.py --project . --serve               (start local HTTP server to view docs)
  python agent.py --project . --no-html             (openapi.json only, skip HTML)
  python agent.py --project . --title "My API" --version "2.0.0"

AUTO-DETECTION:
  - Detect framework from: requirements.txt, package.json, go.mod
  - FastAPI → parse main.py/app.py first, follow router imports
  - Flask → find Flask() instantiation, follow register_blueprint calls
  - Express → find express() instantiation, follow router requires

SMART BEHAVIORS:
  - Handle nested routers (Express router files, FastAPI APIRouter includes)
  - Detect authentication: look for JWT/OAuth/API key patterns → add securitySchemes
  - Detect common patterns: pagination params, filters, sort params
  - If endpoint has no docstring: generate one from code analysis

SERVE MODE (--serve flag):
  python -m http.server in output dir
  Open browser automatically
  Watch for file changes and auto-regenerate

README must include:
  - Framework support matrix (which parsers exist)
  - Example: Flask project in → HTML docs out (screenshot-style ASCII)
  - How to customize the HTML template
  - OpenAPI spec can be imported into: Swagger UI, Postman, Insomnia, Stoplight

## Prerequisites

- Python 3.10+
- `pip`
- `ANTHROPIC_API_KEY`
- FastAPI or Flask project

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`
3. Run `python agent.py --project /path/to/api`

## Usage

```bash
python agent.py --project /path/to/api
python agent.py --project . --output ./docs
python agent.py --project . --serve  # Start local server
python agent.py --project . --title "My API" --version "2.0.0"
python agent.py --project . --no-html  # OpenAPI spec only
```

## Output Files

- **openapi.json** — OpenAPI 3.0 spec (import to Swagger UI, Postman, Insomnia, etc.)
- **index.html** — Beautiful self-contained documentation
- **postman_collection.json** — Ready-to-import Postman collection

## Supported Frameworks

Currently supports: Python (FastAPI, Flask). Node.js and Go support coming soon — contributions welcome.
