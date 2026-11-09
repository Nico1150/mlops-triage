from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mlops_triage.eval.golden import GoldenCase, default_golden_path, load_golden_cases, run_golden_eval
from mlops_triage.pipelines import run_incident_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mlops-triage-eval",
        description="Run golden incident/triage eval cases (requires Ollama).",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=None,
        help=f"JSONL golden file (default: {default_golden_path()})",
    )
    parser.add_argument("--json", action="store_true", help="Print report as JSON")
    parser.add_argument("--id", action="append", help="Run only these case ids (repeatable)")
    return parser


def _filter_cases(cases: list[GoldenCase], ids: list[str] | None) -> list[GoldenCase]:
    if not ids:
        return cases
    wanted = set(ids)
    filtered = [c for c in cases if c.id in wanted]
    missing = wanted - {c.id for c in filtered}
    if missing:
        print(f"Unknown case ids: {sorted(missing)}", file=sys.stderr)
        sys.exit(2)
    return filtered


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cases = load_golden_cases(args.cases)
    cases = _filter_cases(cases, args.id)

    def runner(case: GoldenCase):
        return run_incident_pipeline(
            case.alert,
            use_runbooks=case.use_runbooks,
            max_agent_steps=case.max_agent_steps,
        )

    report = run_golden_eval(cases, runner)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        for result in report.results:
            mark = "PASS" if result.passed else "FAIL"
            print(f"[{mark}] {result.case_id}")
            for failure in result.failures:
                print(f"  - {failure}")
        print(f"\n{report.passed}/{len(report.results)} passed")

    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
