#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "${ROOT}/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT}/venv/bin/activate"
fi

if command -v mlops-triage-sync >/dev/null 2>&1; then
  exec mlops-triage-sync --adapter stub "$@"
fi

exec python -m mlops_triage.sync --adapter stub "$@"
