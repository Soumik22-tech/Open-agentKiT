from pathlib import Path

def detect_framework(path: Path, text: str) -> str:
    if path.suffix == '.vue' or '<template' in text: return 'Vue'
    if path.suffix in {'.jsx','.tsx'} or 'from "react"' in text or "from 'react'" in text: return 'React'
    return 'HTML'
