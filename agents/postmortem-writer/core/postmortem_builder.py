from __future__ import annotations
import json

def build_postmortem(client, model: str, timeline: dict, severity_style: str, template: str) -> dict:
    prompt=f"""Write a blameless incident postmortem from only these notes:\n{json.dumps(timeline,indent=2)}\n
Template: {template}; severity style: {severity_style}. Never invent impact, root cause, owners, or deadlines. Use 'Insufficient information in source notes — please add manually' where unsupported. Never blame people; frame systems and processes. Return JSON with summary, impact, severity, duration, services, timeline, root_cause, contributing_factors, detection, resolution, what_went_well, action_items (task/owner/deadline/priority), and open_questions."""
    response=client.messages.create(model=model,max_tokens=3000,temperature=0,system='You write blameless Google SRE-style postmortems and preserve uncertainty.',messages=[{'role':'user','content':prompt}])
    text=''.join(block.text for block in response.content if getattr(block,'text',None)).strip(); start,end=text.find('{'),text.rfind('}')
    try: return json.loads(text)
    except json.JSONDecodeError: return json.loads(text[start:end+1]) if start>=0 and end>start else {'summary':'Insufficient information in source notes — please add manually','action_items':[]}

def render(data: dict, incident_id: str, template: str) -> str:
    missing='Insufficient information in source notes — please add manually'
    lines=['# Incident Postmortem', '', '> **Draft — review before distributing.** This document was AI-assisted and requires human verification.', '', f'- Incident ID: {incident_id}', f"- Severity: {data.get('severity', missing)}", f"- Duration: {data.get('duration', missing)}", f"- Services: {', '.join(data.get('services', [])) or missing}", '']
    sections=[('Summary','summary'),('Impact','impact'),('Timeline','timeline'),('Root Cause','root_cause'),('Contributing Factors','contributing_factors'),('Detection','detection'),('Resolution','resolution'),('What Went Well','what_went_well')]
    if template=='simple': sections=[x for x in sections if x[0] in {'Summary','Timeline','Root Cause'}]
    for title,key in sections:
        lines += [f'## {title}']
        value=data.get(key,missing)
        if isinstance(value,list): lines += [f"- {item if isinstance(item,str) else item.get('time','') + ': ' + item.get('event','')}" for item in value] or [missing]
        else: lines += [str(value or missing)]
        lines.append('')
    lines += ['## Action Items']
    for item in data.get('action_items',[]) or []:
        if isinstance(item,dict): lines.append(f"- [ ] {item.get('task',missing)} — Owner: {item.get('owner','Unassigned')} — Due: {item.get('deadline','Not specified')} — Priority: {item.get('priority','Not specified')}")
    if not data.get('action_items'): lines.append(f'- {missing}')
    lines += ['', '## Open Questions', *[f'- {item}' for item in data.get('open_questions',[]) or [missing]]]
    return '\n'.join(lines)+'\n'
