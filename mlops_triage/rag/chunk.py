from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_SECTION_RE = re.compile(r"(?=^##\s)", re.MULTILINE)


@dataclass(frozen=True)
class RunbookChunk:
    chunk_id: str
    source_file: str
    title: str
    text: str


def _split_long_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text.strip()]
    parts: list[str] = []
    start = 0
    while start < len(text):
        parts.append(text[start : start + max_chars].strip())
        start += max_chars
    return [p for p in parts if p]


def chunk_markdown_file(path: Path, *, max_chars: int = 900) -> list[RunbookChunk]:
    raw = path.read_text(encoding="utf-8")
    title_match = re.match(r"^#\s+(.+)", raw)
    doc_title = title_match.group(1).strip() if title_match else path.stem

    sections = _SECTION_RE.split(raw)

    chunks: list[RunbookChunk] = []
    for idx, section in enumerate(sections if sections else [raw]):
        section = section.strip()
        if not section:
            continue
        for part_idx, part in enumerate(_split_long_text(section, max_chars)):
            chunk_id = f"{path.name}#{idx}:{part_idx}"
            chunks.append(
                RunbookChunk(
                    chunk_id=chunk_id,
                    source_file=path.name,
                    title=doc_title,
                    text=part,
                )
            )
    return chunks


def load_runbook_chunks(runbooks_dir: Path, *, max_chars: int = 900) -> list[RunbookChunk]:
    if not runbooks_dir.is_dir():
        raise FileNotFoundError(f"Runbooks directory not found: {runbooks_dir}")

    chunks: list[RunbookChunk] = []
    for path in sorted(runbooks_dir.glob("*.md")):
        chunks.extend(chunk_markdown_file(path, max_chars=max_chars))
    return chunks
