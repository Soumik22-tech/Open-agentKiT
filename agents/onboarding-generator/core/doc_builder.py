from __future__ import annotations

import json
from typing import Any


def build_guide(client: Any, model: str, analysis: dict, setup: dict, ownership: dict) -> dict:
    prompt = f"""Create an onboarding guide from verified repository evidence. Do not invent setup commands or ownership.
Repository analysis:\n{json.dumps(analysis, indent=2)}
Setup evidence:\n{json.dumps(setup, indent=2)}
Ownership:\n{json.dumps(ownership, indent=2)}
Return JSON with overview, reading_order (path/reason), key_concepts, gotchas, first_tasks."""
    response = client.messages.create(model=model, max_tokens=2400, temperature=0, system='You are a senior engineer creating a practical, evidence-based onboarding guide.', messages=[{'role':'user','content':prompt}])
    text = ''.join(block.text for block in response.content if getattr(block, 'text', None)).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find('{'), text.rfind('}')
        return json.loads(text[start:end+1]) if start >= 0 and end > start else {'overview':'Insufficient AI output.', 'reading_order':[]}


def render_markdown(analysis: dict, setup: dict, ownership: dict, generated: dict) -> str:
    lines = ['# Engineering Onboarding Guide', '', '> Draft generated from repository evidence. Verify commands and ownership with the team.', '', '## Welcome', generated.get('overview', 'Overview unavailable.'), '', '## Tech Stack']
    lines += [f'- {name}: {count} files' for name, count in analysis.get('languages', {}).items()]
    lines += [f'- Frameworks: {", ".join(analysis.get("frameworks", [])) or "Not detected"}', '', '## Setup Instructions']
    lines += [f'{i}. {step}' for i, step in enumerate(setup.get('suggested_steps', []), 1)]
    if setup.get('commands'): lines += ['', f"Available commands: `{', '.join(setup['commands'])}`"]
    if setup.get('environment_variables'): lines += ['', 'Environment variables:', *[f'- `{item}`' for item in setup['environment_variables']]]
    lines += ['', '## Repository Tour']
    for item in generated.get('reading_order', []): lines.append(f"- **{item.get('path','')}** — {item.get('reason','')}")
    lines += ['', '## Key Concepts', *[f'- {x}' for x in generated.get('key_concepts', [])], '', '## Who to Ask']
    if ownership.get('available'):
        for item in ownership.get('directories', []):
            names = ', '.join(x['name'] for x in item['contributors']) or 'No git history'
            warning = ' — limited institutional knowledge' if item['bus_factor_warning'] else ''
            lines.append(f"- **{item['directory']}**: {names}{warning}")
    else: lines.append('- Git ownership history unavailable or intentionally skipped.')
    lines += ['', '## Common Gotchas', *[f'- {x}' for x in generated.get('gotchas', [])], '', '## Suggested First Tasks', *[f'- {x}' for x in generated.get('first_tasks', [])]]
    return '\n'.join(lines) + '\n'
