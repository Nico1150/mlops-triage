from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mlops_triage.config import Settings, get_settings
from mlops_triage.sync.adapters import SnapshotAdapter, get_adapter


@dataclass(frozen=True)
class SyncResult:
    adapter: str
    synced_at_utc: str
    deployments_path: Path
    slo_snapshot_path: Path
    deployments_written: bool
    slo_written: bool
    dry_run: bool


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, indent=2, sort_keys=False)
    text = f"{text}\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def refresh_snapshots(
    *,
    adapter: str = "stub",
    settings: Settings | None = None,
    dry_run: bool = False,
    adapter_instance: SnapshotAdapter | None = None,
) -> SyncResult:
    """Pull deployment catalog + SLO snapshot from an adapter and write JSON files."""
    cfg = settings or get_settings()
    puller = adapter_instance or get_adapter(adapter)
    synced_at = datetime.now(UTC).isoformat()

    deployments = puller.pull_deployments()
    slo_snapshot = puller.pull_slo_snapshot()

    deployments_path = cfg.deployments_file
    slo_path = cfg.slo_snapshot_file

    if not dry_run:
        _write_json_atomic(deployments_path, deployments)
        _write_json_atomic(slo_path, slo_snapshot)

    return SyncResult(
        adapter=adapter,
        synced_at_utc=synced_at,
        deployments_path=deployments_path.resolve(),
        slo_snapshot_path=slo_path.resolve(),
        deployments_written=not dry_run,
        slo_written=not dry_run,
        dry_run=dry_run,
    )
