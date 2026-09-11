#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


def extract_code_context(
	repo_path: str,
	stack_trace: str,
	context_lines: int = 15,
) -> str:
	"""Find files referenced in the stack trace and extract surrounding code context."""
	repo = Path(repo_path)

	if not repo.exists():
		return "(repo path not found)"

	patterns = [
		r'File "([^"]+)", line (\d+)',
		r'at .*?\(?([^\s():]+\.[a-zA-Z]+):(\d+)(?::\d+)?\)?',
		r'([^\s:]+\.[a-zA-Z]+):(\d+)',
	]

	found_refs = []
	for pattern in patterns:
		for match in re.finditer(pattern, stack_trace):
			file_ref, line_ref = match.group(1), match.group(2)
			found_refs.append((file_ref, int(line_ref)))

	if not found_refs:
		return "(no file:line references found in stack trace)"

	context_blocks = []
	seen = set()

	for file_ref, line_num in found_refs:
		if (file_ref, line_num) in seen:
			continue
		seen.add((file_ref, line_num))

		candidate = repo / file_ref
		if not candidate.exists():
			matches = list(repo.rglob(Path(file_ref).name))
			if matches:
				candidate = matches[0]
			else:
				continue

		try:
			lines = candidate.read_text(encoding="utf-8", errors="ignore").split("\n")
		except Exception:
			continue

		start = max(0, line_num - 1 - context_lines)
		end = min(len(lines), line_num + context_lines)
		snippet_lines = []
		for i in range(start, end):
			marker = ">>> " if (i + 1) == line_num else "    "
			snippet_lines.append(f"{marker}{i+1}: {lines[i]}")

		relative_path = candidate.relative_to(repo) if candidate.is_relative_to(repo) else candidate
		context_blocks.append(
			f"--- {relative_path} (around line {line_num}) ---\n" + "\n".join(snippet_lines)
		)

		if len(context_blocks) >= 5:
			break

	if not context_blocks:
		return "(referenced files not found in repo)"

	return "\n\n".join(context_blocks)
