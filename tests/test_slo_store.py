import json

import pytest

from mlops_triage.tools.slo_store import fetch_slo_status, load_slo_snapshot


def test_load_slo_snapshot_from_repo_file():
    snapshot = load_slo_snapshot()
    assert snapshot["serving-prod-eu"]["latency_p99"]["slo_breached"] is True


def test_fetch_slo_status_breach_from_file():
    result = fetch_slo_status("serving-prod-eu", "latency_p99")
    assert result["found"] is True
    assert result["slo_breached"] is True
    assert str(result["source"]).endswith("data/slo_snapshot.json")


def test_fetch_unknown_metric_not_found(tmp_path):
    path = tmp_path / "slo_snapshot.json"
    path.write_text(
        json.dumps({"svc-a": {"latency_p99": {"slo_breached": False}}}),
        encoding="utf-8",
    )
    result = fetch_slo_status("svc-a", "error_rate_503", snapshot_path=path)
    assert result["found"] is False


def test_missing_snapshot_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_slo_snapshot(tmp_path / "missing.json")
