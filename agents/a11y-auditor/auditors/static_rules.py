from __future__ import annotations
import re
from pathlib import Path
from bs4 import BeautifulSoup

def issue(path, rule, priority, wcag, message, fix, line=1, snippet=''):
    return {'file':str(path),'rule':rule,'priority':priority,'wcag':wcag,'message':message,'fix':fix,'line':line,'snippet':snippet}

def audit_source(path: Path, text: str, level='AA') -> list[dict]:
    findings=[]
    try: soup=BeautifulSoup(text,'html.parser')
    except Exception: soup=None
    def line_for(needle): return text[:text.find(needle)].count('\n')+1 if needle in text else 1
    if soup:
        for tag in soup.find_all('img'):
            if not tag.has_attr('alt'): findings.append(issue(path,'image-alt','CRITICAL','1.1.1 Non-text Content','Screen reader users receive no text alternative for this image.','Add a descriptive alt attribute, or alt="" when the image is decorative.',line_for(str(tag)),str(tag)))
            elif re.search(r'\.(png|jpe?g|gif|svg|webp)$',tag.get('alt',''),re.I): findings.append(issue(path,'filename-alt','SERIOUS','1.1.1 Non-text Content','A filename is not a meaningful image description.','Describe the image purpose instead of its filename.',line_for(str(tag)),str(tag)))
        for tag in soup.find_all(['video','audio']):
            if not tag.find('track'): findings.append(issue(path,'media-captions','SERIOUS','1.2.2 Captions','Media has no captions track for deaf or hard-of-hearing users.','Add a captions track with accurate timed text.',line_for(str(tag)),str(tag)))
        html=soup.find('html')
        if html is not None and not html.get('lang'): findings.append(issue(path,'html-lang','SERIOUS','3.1.1 Language of Page','Assistive technology cannot determine the page language.','Add lang="en" or the actual document language to html.',1,'<html>'))
        headings=[int(t.name[1]) for t in soup.find_all(re.compile('^h[1-6]$'))]
        if headings and headings.count(1)>1: findings.append(issue(path,'multiple-h1','MODERATE','1.3.1 Info and Relationships','Multiple page-level headings can make navigation ambiguous.','Use one h1 for the page and nested headings for sections.',1,''))
        for before,after in zip(headings,headings[1:]):
            if after>before+1: findings.append(issue(path,'heading-skip','MODERATE','1.3.1 Info and Relationships',f'Heading level skips from h{before} to h{after}.','Use a sequential heading level or restructure the sections.',1,'')); break
        for inp in soup.find_all(['input','select','textarea']):
            if inp.get('type')=='hidden': continue
            ident=inp.get('id'); labeled=bool(inp.get('aria-label') or inp.get('aria-labelledby') or (ident and soup.find('label',attrs={'for':ident})) or inp.find_parent('label'))
            if not labeled: findings.append(issue(path,'form-label','CRITICAL','1.3.1 Info and Relationships','A form control has no programmatic label, so its purpose is unclear to screen reader users.','Add a label associated with the control or an appropriate aria-label.',line_for(str(inp)),str(inp)))
            if inp.get('placeholder') and not labeled: findings.append(issue(path,'placeholder-label','SERIOUS','3.3.2 Labels or Instructions','Placeholder text disappears and is not a reliable label.','Keep a persistent label and use placeholder only as an example.',line_for(str(inp)),str(inp)))
        for tag in soup.find_all(['a','button']):
            label=tag.get_text(' ',strip=True).lower()
            if label in {'click here','read more','more'}: findings.append(issue(path,'ambiguous-link','MODERATE','2.4.4 Link Purpose','Generic link text is ambiguous in a screen-reader link list.','Describe the destination or include visually hidden context.',line_for(str(tag)),str(tag)))
    for match in re.finditer(r'<(div|span)\b[^>]*(?:onClick|@click)\s*=|<div\b[^>]*role=["\']?button',text,re.I):
        snippet=text[match.start():text.find('>',match.start())+1]; findings.append(issue(path,'nonsemantic-click','SERIOUS','2.1.1 Keyboard','A clickable non-control may not be keyboard operable.','Use a native button/link or add complete keyboard and focus behavior.',text[:match.start()].count('\n')+1,snippet))
    if re.search(r'<(a|router-link)\b(?![^>]*\bhref=)[^>]*(?:onClick|@click)',text,re.I): findings.append(issue(path,'click-only-link','SERIOUS','2.1.1 Keyboard','Navigation depends on a click handler without a real link destination.','Use a real href or framework router link.',1,''))
    return findings
