import json
from pathlib import Path

from mlops_triage.config import Settings
from mlops_triage.rag.chunk import chunk_markdown_file, load_runbook_chunks
from mlops_triage.rag.search import index_is_stale


def test_chunk_markdown_splits_sections(tmp_path: Path):
    md = tmp_path / "demo.md"
    md.write_text(
        "# Title\n\nIntro\n\n## Section A\n\nAlpha text.\n\n## Section B\n\nBeta text.\n",
        encoding="utf-8",
    )
    chunks = chunk_markdown_file(md)
    assert len(chunks) >= 2
    assert chunks[0].title == "Title"
    assert "Alpha" in chunks[0].text or any("Alpha" in c.text for c in chunks)


def test_load_runbook_chunks_from_repo():
    from mlops_triage.config import get_settings

    chunks = load_runbook_chunks(get_settings().runbooks_dir)
    assert len(chunks) >= 3
    sources = {c.source_file for c in chunks}
    assert "serving_latency_p99.md" in sources


def test_index_is_stale_when_runbooks_dir_mismatch(tmp_path: Path):
    runbooks = tmp_path / "runbooks"
    runbooks.mkdir()
    index_path = tmp_path / "rag_index.json"
    index_path.write_text(
        json.dumps(
            {
                "embedding_model": "nomic-embed-text",
                "runbooks_dir": "/old/project/data/runbooks",
                "records": [],
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(
        runbooks_dir=runbooks,
        rag_index_file=index_path,
        embedding_model="nomic-embed-text",
    )
    assert index_is_stale(settings) is True
