import json
from datetime import UTC, datetime

import pytest

from mlops_triage.sync.adapters import StubAdapter, get_adapter
from mlops_triage.sync.refresh import refresh_snapshots
from mlops_triage.tools.deployments_store import load_deployments_catalog
from mlops_triage.tools.slo_store import load_slo_snapshot


def test_stub_adapter_incident_shapes():
    adapter = StubAdapter(scenario="incident", at=datetime(2026, 3, 9, 12, 0, tzinfo=UTC))
    deployments = adapter.pull_deployments()
    slo = adapter.pull_slo_snapshot()

    assert "rec-engine" in deployments
    assert deployments["rec-engine"][0]["channel"] == "canary"
    assert slo["serving-prod-eu"]["latency_p99"]["slo_breached"] is True


def test_stub_adapter_healthy_shapes():
    adapter = StubAdapter(scenario="healthy", at=datetime(2026, 3, 9, 12, 0, tzinfo=UTC))
    slo = adapter.pull_slo_snapshot()
    assert slo["rec-engine"]["error_rate_503"]["slo_breached"] is False


def test_get_adapter_unknown_raises():
    with pytest.raises(ValueError, match="Unknown sync adapter"):
        get_adapter("nope")


def test_refresh_snapshots_writes_files(tmp_path, monkeypatch):
    deployments = tmp_path / "deployments.json"
    slo = tmp_path / "slo_snapshot.json"

    from mlops_triage.config import Settings

    settings = Settings(
        deployments_file=deployments,
        slo_snapshot_file=slo,
    )
    fixed = datetime(2026, 3, 9, 15, 30, tzinfo=UTC)
    adapter = StubAdapter(scenario="incident", at=fixed)

    result = refresh_snapshots(settings=settings, adapter="stub", adapter_instance=adapter)

    assert result.deployments_written is True
    assert deployments.is_file() and slo.is_file()

    catalog = load_deployments_catalog(deployments)
    snapshot = load_slo_snapshot(slo)
    assert catalog["serving-prod-eu"][0]["deployed_at_utc"] == "2026-03-09T15:30:00Z"
    assert snapshot["serving-prod-eu"]["latency_p99"]["slo_breached"] is True


def test_refresh_snapshots_dry_run_does_not_write(tmp_path):
    deployments = tmp_path / "deployments.json"
    slo = tmp_path / "slo_snapshot.json"

    from mlops_triage.config import Settings

    settings = Settings(
        deployments_file=deployments,
        slo_snapshot_file=slo,
    )
    result = refresh_snapshots(settings=settings, dry_run=True)
    assert result.dry_run is True
    assert not deployments.exists() and not slo.exists()


def test_refresh_atomic_replace(tmp_path):
    deployments = tmp_path / "deployments.json"
    slo = tmp_path / "slo_snapshot.json"
    deployments.write_text('{"legacy": []}\n', encoding="utf-8")

    from mlops_triage.config import Settings

    settings = Settings(deployments_file=deployments, slo_snapshot_file=slo)
    refresh_snapshots(settings=settings, adapter_instance=StubAdapter(scenario="healthy"))

    data = json.loads(deployments.read_text(encoding="utf-8"))
    assert "legacy" not in data
    assert "rec-engine" in data
    assert not deployments.with_suffix(".json.tmp").exists()
