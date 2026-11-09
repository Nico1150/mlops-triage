import json

import pytest

from mlops_triage.tools.deployments_store import fetch_recent_deployments, load_deployments_catalog


def test_load_deployments_catalog_from_repo_file():
    catalog = load_deployments_catalog()
    assert "rec-engine" in catalog
    assert catalog["rec-engine"][0]["version"] == "3.8.1"


def test_fetch_recent_deployments_respects_limit(tmp_path):
    path = tmp_path / "deployments.json"
    path.write_text(
        json.dumps(
            {
                "svc-a": [
                    {"version": "1.0.0", "channel": "stable", "traffic_pct": 100},
                    {"version": "0.9.0", "channel": "stable", "traffic_pct": 0},
                ]
            }
        ),
        encoding="utf-8",
    )

    result = fetch_recent_deployments("svc-a", 1, catalog_path=path)
    assert len(result["deployments"]) == 1
    assert result["deployments"][0]["version"] == "1.0.0"
    assert result["source"].endswith("deployments.json")


def test_fetch_unknown_service_returns_empty_list():
    result = fetch_recent_deployments("unknown-service", 3)
    assert result["deployments"] == []


def test_missing_catalog_raises(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError):
        load_deployments_catalog(missing)
