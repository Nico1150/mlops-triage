import json

import pytest
from pydantic import ValidationError

from mlops_triage.llm.structured import StructuredOutputError, parse_structured_response
from mlops_triage.schemas import MLIncident


def test_parse_plain_json():
    raw = json.dumps(
        {
            "severity": "high",
            "component": "serving",
            "summary": "Latency spike",
            "suggested_actions": ["Scale replicas"],
            "confidence": 0.9,
        }
    )
    incident = parse_structured_response(raw, MLIncident)
    assert incident.severity == "high"
    assert incident.component == "serving"


def test_parse_json_inside_markdown_fence():
    raw = """```json
{
  "severity": "critical",
  "component": "serving",
  "summary": "p99 latency breach",
  "suggested_actions": ["Rollback canary"],
  "confidence": 0.85
}
```"""
    incident = parse_structured_response(raw, MLIncident)
    assert incident.severity == "critical"


def test_parse_invalid_severity_raises():
    raw = json.dumps(
        {
            "severity": "urgent",
            "component": "serving",
            "summary": "x",
            "suggested_actions": ["a"],
            "confidence": 0.5,
        }
    )
    with pytest.raises((ValidationError, json.JSONDecodeError)):
        parse_structured_response(raw, MLIncident)


def test_structured_output_error_is_exception():
    assert issubclass(StructuredOutputError, Exception)
