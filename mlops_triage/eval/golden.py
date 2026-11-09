from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from mlops_triage.eval.metrics import assert_incident_expectations, assert_triage_expectations
from mlops_triage.pipelines.incident import IncidentPipelineResult

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def default_golden_path() -> Path:
    override = os.environ.get("GOLDEN_CASES_FILE", "").strip()
    if override:
        return Path(override)
    return _REPO_ROOT / "tests" / "fixtures" / "incidents.jsonl"


@dataclass(frozen=True)
class GoldenCase:
    id: str
    alert: str
    expected_incident: dict[str, object]
    expected_triage: dict[str, object] = field(default_factory=dict)
    use_runbooks: bool = True
    max_agent_steps: int = 22


@dataclass(frozen=True)
class GoldenCaseResult:
    case_id: str
    passed: bool
    failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class GoldenEvalReport:
    results: tuple[GoldenCaseResult, ...]

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return len(self.results) - self.passed

    @property
    def all_passed(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "total": len(self.results),
            "passed": self.passed,
            "failed": self.failed,
            "cases": [
                {
                    "id": r.case_id,
                    "passed": r.passed,
                    "failures": list(r.failures),
                }
                for r in self.results
            ],
        }


def load_golden_cases(path: Path | None = None) -> list[GoldenCase]:
    file_path = path or default_golden_path()
    if not file_path.is_file():
        raise FileNotFoundError(f"Golden cases file not found: {file_path}")

    cases: list[GoldenCase] = []
    with file_path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            if raw.get("skip"):
                continue
            try:
                cases.append(
                    GoldenCase(
                        id=str(raw["id"]),
                        alert=str(raw["alert"]),
                        expected_incident=dict(raw.get("expected_incident") or {}),
                        expected_triage=dict(raw.get("expected_triage") or {}),
                        use_runbooks=bool(raw.get("use_runbooks", True)),
                        max_agent_steps=int(raw.get("max_agent_steps", 22)),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Invalid golden case at {file_path}:{line_no}") from exc
    return cases


def evaluate_golden_case(case: GoldenCase, result: IncidentPipelineResult) -> GoldenCaseResult:
    failures: list[str] = []

    try:
        assert_incident_expectations(result.incident, case.expected_incident)
    except AssertionError as exc:
        failures.append(f"incident: {exc}")

    if case.expected_triage:
        try:
            assert_triage_expectations(result.triage, case.expected_triage)
        except AssertionError as exc:
            failures.append(f"triage: {exc}")

    return GoldenCaseResult(
        case_id=case.id,
        passed=not failures,
        failures=tuple(failures),
    )


def run_golden_eval(
    cases: list[GoldenCase],
    runner: Callable[[GoldenCase], IncidentPipelineResult],
) -> GoldenEvalReport:
    results = tuple(evaluate_golden_case(case, runner(case)) for case in cases)
    return GoldenEvalReport(results=results)
