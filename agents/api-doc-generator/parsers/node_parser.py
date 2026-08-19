"""
Node.js route parser — Coming Soon

Express, Fastify, NestJS, and Hono support is planned for a future release.
Currently, only Python frameworks (FastAPI, Flask) are supported.

To contribute: implement extract_node_routes(project_root: Path) -> list[dict]
following the same interface as python_parser.py
"""

def extract_node_routes(project_root):
	raise NotImplementedError(
		"Node.js parser is not yet implemented. "
		"Only Python (FastAPI/Flask) is currently supported. "
		"See CONTRIBUTING.md to help add this."
	)
