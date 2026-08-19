#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def generate_html_docs(spec: dict[str, Any]) -> str:
    """Generate HTML documentation from OpenAPI spec."""
    html = """<html>
<head>
<title>API Documentation</title>
<style>
body { font-family: sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }
h1 { color: #333; }
.endpoint { border: 1px solid #ddd; border-radius: 4px; margin: 10px 0; padding: 15px; }
.method { display: inline-block; padding: 4px 8px; border-radius: 3px; font-weight: bold; color: white; }
.get { background: #61affe; }
.post { background: #49cc90; }
.put { background: #fca130; }
.delete { background: #f93e3e; }
</style>
</head>
<body>
<h1>API Documentation</h1>
"""

    info = spec.get("info", {})
    html += f"<p><strong>{info.get('title', 'API')}</strong> v{info.get('version', '1.0')}</p>\n"

    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            html += f"""<div class="endpoint">
<div class="method {method}">{method.upper()}</div>
<code>{path}</code>
<p>{details.get('description', details.get('summary', ''))}</p>
</div>
"""

    html += "</body></html>"
    return html
