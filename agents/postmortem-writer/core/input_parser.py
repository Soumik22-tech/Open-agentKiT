from __future__ import annotations
import json, re
from datetime import datetime
from pathlib import Path

TIME_PATTERNS=[r'\b(\d{1,2}:\d{2}(?::\d{2})?)\b',r'\b(20\d{2}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?)\b']

def _time_sort_key(time_str: str) -> tuple:
    """Convert a time string into a sortable tuple, placing invalid values last."""
    time_str = time_str.strip()

    full_match = re.match(r'^(\d{4})-(\d{2})-(\d{2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?$', time_str)
    if full_match:
        y, mo, d, h, mi, s = full_match.groups()
        return (0, int(y), int(mo), int(d), int(h), int(mi), int(s or 0))

    time_match = re.match(r'^(\d{1,2}):(\d{2})(?::(\d{2}))?$', time_str)
    if time_match:
        h, mi, s = time_match.groups()
        return (1, 0, 0, 0, int(h), int(mi), int(s or 0))

    return (2, 0, 0, 0, 0, 0, 0)

def parse_input(text: str, source_name: str = '') -> dict:
    events=[]
    try:
        data=json.loads(text)
        if isinstance(data,dict): data=data.get('messages', data.get('conversation', []))
        if isinstance(data,list):
            for item in data:
                if not isinstance(item,dict): continue
                stamp=item.get('ts') or item.get('timestamp') or item.get('time') or ''
                content=item.get('text') or item.get('content') or ''
                user=item.get('user_name') or item.get('user') or item.get('author') or 'unknown'
                events.append({'time':str(stamp),'source':str(user),'content':str(content)})
    except json.JSONDecodeError: pass
    if not events:
        for line in text.splitlines():
            match=next((re.search(pattern,line) for pattern in TIME_PATTERNS if re.search(pattern,line)),None)
            if match:
                stamp=match.group(1); content=line[match.end():].lstrip(' :-|'); events.append({'time':stamp,'source':'notes','content':content or line})
            elif line.strip() and events: events[-1]['content'] += ' ' + line.strip()
    events.sort(key=lambda item: _time_sort_key(item['time']))
    joined=' '.join(e['content'].lower() for e in events)
    start=events[0]['time'] if events else ''
    resolution=next((e['time'] for e in events if re.search(r'\b(resolved|fixed|recovered|back to normal)\b',e['content'],re.I)), '')
    return {'source':source_name,'events':events,'likely_start':start,'likely_resolution':resolution,'raw_length':len(text)}
