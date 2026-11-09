from __future__ import annotations

import argparse
import json
import sys

from mlops_triage.sync.refresh import refresh_snapshots


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mlops-triage-sync",
        description="Refresh deployments.json and slo_snapshot.json from a sync adapter.",
    )
    parser.add_argument(
        "--adapter",
        default="stub",
        help="Data source adapter (default: stub).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch payload but do not write files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print SyncResult as JSON on stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = refresh_snapshots(adapter=args.adapter, dry_run=args.dry_run)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    if args.json:
        payload = {
            "adapter": result.adapter,
            "synced_at_utc": result.synced_at_utc,
            "deployments_path": str(result.deployments_path),
            "slo_snapshot_path": str(result.slo_snapshot_path),
            "deployments_written": result.deployments_written,
            "slo_written": result.slo_written,
            "dry_run": result.dry_run,
        }
        print(json.dumps(payload, indent=2))
    else:
        mode = "dry-run" if result.dry_run else "wrote"
        print(f"[{result.synced_at_utc}] adapter={result.adapter} ({mode})")
        print(f"  deployments: {result.deployments_path}")
        print(f"  slo:         {result.slo_snapshot_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
