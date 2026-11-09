from typing import Literal

from pydantic import BaseModel, Field

from mlops_triage.llm.tools import Tool
from mlops_triage.schemas.triage_report import TriageReport
from mlops_triage.rag.search import search_runbooks
from mlops_triage.tools.deployments_store import fetch_recent_deployments
from mlops_triage.tools.slo_store import fetch_slo_status


class GetRecentDeploymentsArgs(BaseModel):
    service: str = Field(description="Service name, e.g. rec-engine or serving-prod-eu")
    limit: int = Field(default=3, ge=1, le=10)


class CheckSloStatusArgs(BaseModel):
    service: str
    metric: Literal["latency_p99", "error_rate_503"]


class SearchRunbookArgs(BaseModel):
    query: str = Field(description="Natural language query about on-call procedures")
    top_k: int = Field(default=3, ge=1, le=8)


def _get_recent_deployments(args: GetRecentDeploymentsArgs) -> dict[str, object]:
    return fetch_recent_deployments(args.service, args.limit)


def _check_slo_status(args: CheckSloStatusArgs) -> dict[str, object]:
    return fetch_slo_status(args.service, args.metric)


def _search_runbook(args: SearchRunbookArgs) -> dict[str, object]:
    return search_runbooks(args.query, top_k=args.top_k)


def _submit_triage_report(args: TriageReport) -> TriageReport:
    return args


def default_mlops_tools() -> list[Tool]:
    return [
        Tool(
            name="get_recent_deployments",
            description=(
                "List recent deployments for an ML service from the deployments catalog "
                "(version, channel, traffic %)."
            ),
            parameters_model=GetRecentDeploymentsArgs,
            handler=_get_recent_deployments,
        ),
        Tool(
            name="check_slo_status",
            description=(
                "Check SLO breach status from the metrics snapshot file for "
                "latency_p99 or error_rate_503."
            ),
            parameters_model=CheckSloStatusArgs,
            handler=_check_slo_status,
        ),
        Tool(
            name="search_runbook",
            description=(
                "Search internal runbooks (markdown) for on-call procedures "
                "relevant to the incident."
            ),
            parameters_model=SearchRunbookArgs,
            handler=_search_runbook,
        ),
        Tool(
            name="submit_triage_report",
            description=(
                "Submit the final structured triage report once you have enough "
                "context from tools. Call this exactly once to finish."
            ),
            parameters_model=TriageReport,
            handler=_submit_triage_report,
        ),
    ]
