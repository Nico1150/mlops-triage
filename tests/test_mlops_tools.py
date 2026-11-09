import json

from mlops_triage.llm.tools import execute_tool
from mlops_triage.schemas.triage_report import TriageReport
from mlops_triage.tools.mlops import default_mlops_tools


def _tool(name: str):
    for tool in default_mlops_tools():
        if tool.name == name:
            return tool
    raise AssertionError(f"Tool not found: {name}")


def test_get_recent_deployments_reads_catalog_file():
    tool = _tool("get_recent_deployments")
    payload = execute_tool(tool, json.dumps({"service": "rec-engine", "limit": 2}))
    data = json.loads(payload)
    assert data["service"] == "rec-engine"
    assert len(data["deployments"]) == 2
    assert data["deployments"][0]["version"] == "3.8.1"
    assert "source" in data
    assert data["source"].endswith("data/deployments.json")


def test_check_slo_status_reads_snapshot_file():
    tool = _tool("check_slo_status")
    payload = execute_tool(
        tool,
        json.dumps({"service": "serving-prod-eu", "metric": "latency_p99"}),
    )
    data = json.loads(payload)
    assert data["found"] is True
    assert data["slo_breached"] is True
    assert data["source"].endswith("data/slo_snapshot.json")


def test_submit_triage_report_validates():
    tool = _tool("submit_triage_report")
    args = {
        "incident_summary": "Test",
        "root_cause_hypothesis": "Canary deploy",
        "recommended_actions": ["Rollback"],
        "rollback_recommended": True,
        "priority": "P1",
        "runbook_sources": ["canary_rollback.md"],
    }
    payload = execute_tool(tool, json.dumps(args))
    report = TriageReport.model_validate_json(payload)
    assert report.rollback_recommended is True
