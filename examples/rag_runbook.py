"""Search local runbooks with embeddings (builds index on first run)."""

import argparse
import json

from mlops_triage.config import get_settings
from mlops_triage.llm import create_openai_client
from mlops_triage.rag import build_runbook_index, search_runbooks


def main() -> None:
    parser = argparse.ArgumentParser(description="Query runbook RAG index")
    parser.add_argument(
        "query",
        nargs="?",
        default="p99 latency spike after canary deploy",
        help="Search query",
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild embeddings index before search",
    )
    args = parser.parse_args()

    settings = get_settings()
    client = create_openai_client(settings)

    if args.rebuild:
        path = build_runbook_index(client=client, settings=settings)
        print(f"Rebuilt index: {path}\n")

    result = search_runbooks(
        args.query,
        top_k=args.top_k,
        client=client,
        settings=settings,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
