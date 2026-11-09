from __future__ import annotations

from typing import Any


def format_runbook_context(search_result: dict[str, Any]) -> str:
    hits = search_result.get("hits") or []
    if not hits:
        return "(No runbook excerpts retrieved.)"

    blocks: list[str] = []
    for hit in hits:
        blocks.append(
            f"[{hit['source_file']}] (score={hit['score']})\n{hit['text'].strip()}"
        )
    return "\n\n---\n\n".join(blocks)


def runbook_source_names(search_result: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for hit in search_result.get("hits") or []:
        name = hit.get("source_file")
        if name and name not in names:
            names.append(name)
    return names
