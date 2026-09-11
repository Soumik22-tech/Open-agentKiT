# Data Analyst Agent

Interactive data analysis agent. Load CSV/Excel, ask natural language questions, Claude generates and executes pandas code, see results instantly.

## Setup

```bash
pip install -r requirements.txt
python agent.py --file data.csv
```

## Usage

```bash
python agent.py --file data.csv
python agent.py --file data.xlsx --query "average salary by department"
```

## Interactive Session Example

```
Query: what's the average value in column X?
[Claude generates: df['X'].mean()]
Result: 42.5

Query: show top 5 rows sorted by date
[Claude generates: df.nlargest(5, 'date')]
Result: [table output]

Query: exit
```

## Features

- Loads CSV and Excel files
- Profiles data without sending raw data to Claude
- Interactive REPL for exploratory analysis
- Claude generates pandas code from natural language
- Sandboxed code execution (no os/sys/open/__import__)
- Automatic output formatting
