from __future__ import annotations

from typing import Any

from mlops_triage.schemas.ml_incident import MLIncident
from mlops_triage.schemas.triage_report import TriageReport


def assert_incident_expectations(
    incident: MLIncident,
    expected: dict[str, Any],
) -> None:
    """Assert partial expectations for eval fixtures (raises AssertionError)."""
    if "severity" in expected:
        assert incident.severity == expected["severity"]

    if "component" in expected:
        assert incident.component == expected["component"]

    if "component_contains" in expected:
        assert expected["component_contains"].lower() in incident.component.lower()

    if "min_confidence" in expected:
        assert incident.confidence >= expected["min_confidence"]

    if "min_actions" in expected:
        assert len(incident.suggested_actions) >= expected["min_actions"]


def assert_triage_expectations(
    triage: TriageReport,
    expected: dict[str, Any],
) -> None:
    if "priority" in expected:
        assert triage.priority == expected["priority"]

    if "rollback_recommended" in expected:
        assert triage.rollback_recommended is expected["rollback_recommended"]

    if "min_actions" in expected:
        assert len(triage.recommended_actions) >= expected["min_actions"]

    if "summary_contains" in expected:
        assert expected["summary_contains"].lower() in triage.incident_summary.lower()
