# AI-Powered Query Builder

Connect to any database (PostgreSQL, MySQL, SQLite), describe what you want in natural language, get the optimized SQL query + results. Read-only safe. Interactive REPL.

## Prerequisites

- Python 3.10+
- `pip`
- `ANTHROPIC_API_KEY`
- Database connection string

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`
3. Run `python agent.py --db <CONNECTION_STRING>`

## Usage

```bash
python agent.py --db sqlite:///mydb.sqlite
python agent.py --db postgresql://user:pass@host/db
python agent.py --db mysql://user:pass@host/db
python agent.py --db ... --query "top 10 customers by revenue"
python agent.py --db ... --export results.csv
```

## Safety Features

- Read-only mode: only SELECT queries allowed
- Query timeout: 30 seconds
- Row limit: 10,000 rows max
- Schema extraction: structure only, no data sent to Claude
- Schema never sent to Claude includes actual data — only structure

RESULT DISPLAY:
- Rich table with column types shown
- Row count + query execution time shown
- If result > 50 rows: show first 50, offer to export full result to CSV
- Numeric columns: auto-format with commas, 2 decimal places
- Date columns: auto-format for readability

CONVERSATION MEMORY:
- Claude remembers previous queries in the session
- User can say "same as before but for last week" → Claude refers to previous query
- Session history saved to session_YYYYMMDD.json

README must include:
- How to get DB connection string for each DB type
- Security note: why it's safe (read-only, no data sent to Claude)
- Example session showing natural language → SQL → results
- Limitations: complex queries with 10+ JOINs may need manual refinement

## Prerequisites

- Python 3.10+
- `pip`
- `ANTHROPIC_API_KEY`
- Database connection string

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`
3. Run `python agent.py --db <CONNECTION_STRING>`

## Usage

```bash
python agent.py --db sqlite:///mydb.sqlite
python agent.py --db postgresql://user:pass@host/db
python agent.py --db mysql://user:pass@host/db
python agent.py --db ... --query "top 10 customers by revenue"
python agent.py --db ... --export results.csv
```

## Safety Features

- Read-only mode: only SELECT queries allowed
- Query timeout: 30 seconds
- Row limit: 10,000 rows
- Schema extraction: structure only, no data sent to Claude
