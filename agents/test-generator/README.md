# Test Suite Generator

Analyzes source code, generates comprehensive test suites covering edge cases and error paths, runs tests and reports coverage.

## Setup

```bash
pip install -r requirements.txt
python agent.py --file src/utils.py
```

## Usage

```bash
python agent.py --file src/utils.py
python agent.py --file src/utils.py --output tests/test_utils.py
python agent.py --file src/utils.py --run
```

## Supported Languages

Currently supports Python only. JavaScript/TypeScript support is planned — contributions welcome.

## Features

- Extracts all functions and methods
- Generates tests for normal cases, edge cases, error paths
- Validates generated tests by running them
- Shows pass/fail per test
