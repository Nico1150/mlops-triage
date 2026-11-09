"""Full pipeline: structured extraction then agent triage."""

import json

from mlops_triage.fixtures import SAMPLE_ALERT
from mlops_triage.pipelines import run_incident_pipeline


if __name__ == "__main__":
    result = run_incident_pipeline(SAMPLE_ALERT)

    print("=== Structured incident ===")
    print(result.incident.model_dump_json(indent=2))
    if result.runbook_hits:
        print("\n=== Runbook hits (retrieval) ===")
        for hit in result.runbook_hits:
            print(f"- {hit['source_file']} (score={hit['score']})")

    print("\n=== Triage report ===")
    print(result.triage.model_dump_json(indent=2))
    print("\n=== Combined (JSON) ===")
    print(
        json.dumps(
            {
                "incident": result.incident.model_dump(),
                "triage": result.triage.model_dump(),
            },
            indent=2,
        )
    )
