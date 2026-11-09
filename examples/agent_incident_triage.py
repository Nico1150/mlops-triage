"""Triage a serving incident with a local tool-calling agent."""

from mlops_triage.agent import AgentError, run_agent
from mlops_triage.config import get_settings
from mlops_triage.fixtures import SAMPLE_ALERT
from mlops_triage.llm import create_openai_client
from mlops_triage.schemas.triage_report import TriageReport
from mlops_triage.tools import default_mlops_tools

SYSTEM_PROMPT = """\
You are an on-call MLOps engineer triaging production ML serving incidents.

Workflow:
1. search_runbook for procedures related to the alert (latency, canary, rollback).
2. Use tools to gather deployment and SLO context (do not guess numbers).
3. Call submit_triage_report once; set runbook_sources to filenames you relied on.

Be concise; prefer rec-engine and serving-prod-eu as service names when relevant.
"""

if __name__ == "__main__":
    settings = get_settings()
    client = create_openai_client(settings)
    tools = default_mlops_tools()

    from mlops_triage.rag import (
        ensure_runbook_index,
        format_runbook_context,
        search_runbooks,
    )

    ensure_runbook_index(client=client, settings=settings)
    runbook_ctx = search_runbooks(
        SAMPLE_ALERT.strip(),
        top_k=2,
        client=client,
        settings=settings,
    )
    runbook_block = format_runbook_context(runbook_ctx)

    try:
        result = run_agent(
            client=client,
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Triage this alert and submit a triage report:\n\n"
                        f"{SAMPLE_ALERT.strip()}\n\n"
                        f"Pre-retrieved runbook excerpts:\n{runbook_block}"
                    ),
                },
            ],
            tools=tools,
            temperature=0.2,
            max_steps=12,
            terminal_tool="submit_triage_report",
        )
    except AgentError as exc:
        raise SystemExit(f"Agent failed: {exc}") from exc

    if isinstance(result, TriageReport):
        print(result.model_dump_json(indent=2))
    else:
        print(result)
