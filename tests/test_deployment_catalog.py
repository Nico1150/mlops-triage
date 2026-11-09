from mlops_triage.sync.deployment_catalog import (
    catalog_from_kube_replica_rows,
    catalog_from_request_traffic_rows,
    version_from_kube_deployment,
)


def test_version_from_kube_deployment_strips_prefix():
    assert version_from_kube_deployment("rec-engine-3.8.1", "rec-engine") == "3.8.1"


def test_request_traffic_share_to_catalog():
    rows = [
        {"labels": {"version": "3.8.1", "channel": "canary"}, "value": 12.0},
        {"labels": {"version": "3.8.0"}, "value": 88.0},
    ]
    catalog = catalog_from_request_traffic_rows(
        rows,
        service="rec-engine",
        version_label="version",
        channel_label="channel",
    )
    assert len(catalog) == 2
    assert sum(d["traffic_pct"] for d in catalog) == 100
    assert catalog[0]["version"] == "3.8.0"
    assert catalog[0]["channel"] == "stable"


def test_kube_replicas_share_to_catalog():
    rows = [
        {"labels": {"deployment": "serving-prod-eu-3.8.1"}, "value": 1.0},
        {"labels": {"deployment": "serving-prod-eu-3.8.0"}, "value": 9.0},
    ]
    catalog = catalog_from_kube_replica_rows(
        rows,
        service="serving-prod-eu",
        deployment_label="deployment",
        channel_label=None,
    )
    assert catalog[1]["version"] == "3.8.1"
    assert catalog[1]["channel"] == "canary"
