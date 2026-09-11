from __future__ import annotations
import json

def review(client, model, source, findings):
    prompt=f"""Review this {source['framework']} source for contextual WCAG 2.1 issues missed by static rules. Explain real user impact, criterion, exact fix, and priority CRITICAL/SERIOUS/MODERATE. Do not repeat findings or invent behavior. Code:\n{source['text'][:18000]}\nExisting findings:\n{json.dumps(findings)} Return JSON {{\"issues\":[...]}}."""
    response=client.messages.create(model=model,max_tokens=2200,temperature=0,system='You are a WCAG 2.1 accessibility expert.',messages=[{'role':'user','content':prompt}]); text=''.join(x.text for x in response.content if getattr(x,'text',None)).strip(); start,end=text.find('{'),text.rfind('}')
    try:return json.loads(text).get('issues',[])
    except json.JSONDecodeError:return json.loads(text[start:end+1]).get('issues',[]) if start>=0 and end>start else []
