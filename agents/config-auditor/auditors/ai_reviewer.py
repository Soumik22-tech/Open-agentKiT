from __future__ import annotations
import json

def review_configs(client, model: str, configs: list[dict], findings: list[dict]) -> list[dict]:
    prompt = f"""Review these infrastructure configs as a senior DevOps engineer. Add only contextual issues that deterministic rules could not establish. Rank all supplied issues as CRITICAL, IMPORTANT, or NICE-TO-HAVE and provide exact fixes. Do not invent config behavior. Configs: {json.dumps(configs)[:30000]} Findings: {json.dumps(findings)} Return JSON: {{\"issues\":[{{\"file\":\"\",\"severity\":\"\",\"message\":\"\",\"fix\":\"\"}}]}}"""
    response=client.messages.create(model=model,max_tokens=2400,temperature=0,system='You are a senior DevOps and SRE reviewer.',messages=[{'role':'user','content':prompt}])
    text=''.join(block.text for block in response.content if getattr(block,'text',None)).strip(); start,end=text.find('{'),text.rfind('}')
    try: return json.loads(text)['issues']
    except (json.JSONDecodeError,KeyError): return json.loads(text[start:end+1]).get('issues',[]) if start>=0 and end>start else []
