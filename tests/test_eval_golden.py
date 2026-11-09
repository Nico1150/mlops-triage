import pytest

from mlops_triage.eval.golden import (
    GoldenCase,
    evaluate_golden_case,
    load_golden_cases,
    run_golden_eval,
)
from mlops_triage.eval.metrics import assert_triage_expectations
from mlops_triage.pipelines.incident import IncidentPipelineResult
from mlops_triage.schemas.ml_incident import MLIncident
from mlops_triage.schemas.triage_report import TriageReport


def test_load_golden_cases_from_repo():
    cases = load_golden_cases()
    assert len(cases) >= 2
    ids = {c.id for c in cases}
    assert "serving_p99" in ids


def test_evaluate_golden_case_pass_and_fail():
    incident = MLIncident(
        severity="critical",
        component="serving-prod-eu",
        summary="Latency spike",
        suggested_actions=["Check canary"],
        confidence=0.9,
    )
    triage = TriageReport(
        incident_summary="Critical latency on serving-prod-eu",
        root_cause_hypothesis="Canary deploy",
        recommended_actions=["Rollback canary"],
        rollback_recommended=True,
        priority="P1",
        runbook_sources=["serving_latency_p99.md"],
    )
    result = IncidentPipelineResult(incident=incident, triage=triage)
    case = GoldenCase(
        id="demo",
        alert="x",
        expected_incident={"severity": "critical"},
        expected_triage={"priority": "P1", "runbook_sources_contains": "serving_latency"},
    )
    passed = evaluate_golden_case(case, result)
    assert passed.passed

    bad_case = GoldenCase(
        id="demo",
        alert="x",
        expected_incident={},
        expected_triage={"priority": "P4"},
    )
    failed = evaluate_golden_case(bad_case, result)
    assert not failed.passed
    assert failed.failures


def test_run_golden_eval_mock_runner():
    cases = [
        GoldenCase(id="a", alert="1", expected_incident={"severity": "critical"}),
    ]

    def runner(case: GoldenCase) -> IncidentPipelineResult:
        return IncidentPipelineResult(
            incident=MLIncident(
                severity="critical",
                component="s",
                summary="s",
                suggested_actions=["x"],
                confidence=1.0,
            ),
            triage=TriageReport(
                incident_summary="s",
                root_cause_hypothesis="h",
                recommended_actions=["a"],
                rollback_recommended=False,
                priority="P2",
            ),
        )

    report = run_golden_eval(cases, runner)
    assert report.all_passed


def test_assert_triage_runbook_sources_contains():
    triage = TriageReport(
        incident_summary="summary",
        root_cause_hypothesis="h",
        recommended_actions=["do"],
        rollback_recommended=False,
        priority="P2",
        runbook_sources=["canary_rollback.md"],
    )
    assert_triage_expectations(triage, {"runbook_sources_contains": "canary"})
    with pytest.raises(AssertionError):
        assert_triage_expectations(triage, {"runbook_sources_contains": "missing.md"})


@pytest.mark.integration
@pytest.mark.parametrize(
    "case",
    load_golden_cases(),
    ids=lambda c: c.id,
)
def test_golden_pipeline_case(
    case: GoldenCase,
    skip_without_ollama,
    skip_without_embedding_model,
):
    from mlops_triage.pipelines import run_incident_pipeline

    result = run_incident_pipeline(
        case.alert,
        use_runbooks=case.use_runbooks,
        max_agent_steps=case.max_agent_steps,
    )
    outcome = evaluate_golden_case(case, result)
    assert outcome.passed, "\n".join(outcome.failures)
