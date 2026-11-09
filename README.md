# mlops_triage

Local ML incident triage with LLMs (Ollama hoy, API compatible OpenAI; migrable a vLLM) con extracción estructurada, y espacio para agentes y RAG.

## Requisitos

- Python 3.11+
- [Ollama](https://ollama.com/) en ejecución con el modelo configurado (por defecto `qwen2.5:7b`)

```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text   # RAG / search_runbook
ollama serve   # si no corre como servicio
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev,api]"
```

Variables de entorno (opcional; los defaults apuntan a Ollama local):

| Variable        | Default                        |
|-----------------|--------------------------------|
| `LLM_BASE_URL`  | `http://localhost:11434/v1`    |
| `LLM_API_KEY`   | `ollama`                       |
| `LLM_MODEL`     | `qwen2.5:7b`                   |
| `DEPLOYMENTS_FILE` | `data/deployments.json` |
| `SLO_SNAPSHOT_FILE` | `data/slo_snapshot.json` |
| `RUNBOOKS_DIR` | `data/runbooks` |
| `RAG_INDEX_FILE` | `data/rag_index.json` (generado, en `.gitignore`) |
| `EMBEDDING_MODEL` | `nomic-embed-text` |

Podés copiarlas a un archivo `.env` en la raíz del repo.

### Datos de tools (archivos versionados)

| Archivo | Tool |
|---------|------|
| [`data/deployments.json`](data/deployments.json) | `get_recent_deployments` |
| [`data/slo_snapshot.json`](data/slo_snapshot.json) | `check_slo_status` |

Editá esos JSON para simular exports de CD/Prometheus sin tocar código. En producción podés apuntar las variables de entorno a dumps periódicos de tus sistemas reales.

### Sync de snapshots (stub + cron)

Para refrescar los JSON como si vinieran de CD/métricas (adapter **stub** local):

```bash
pip install -e ".[dev]"   # registra la CLI mlops-triage-sync
mlops-triage-sync --adapter stub
# o: python -m mlops_triage.sync
mlops-triage-sync --dry-run --json
```

Variables opcionales:

| Variable | Efecto |
|----------|--------|
| `SYNC_SCENARIO=incident` | SLO en breach + canary 12% (default, alineado al demo) |
| `SYNC_SCENARIO=healthy` | SLOs verdes, canary 5% |

Cron / launchd: ver [`scripts/cron.example`](scripts/cron.example) y el wrapper [`scripts/sync_snapshots.sh`](scripts/sync_snapshots.sh).

**Adapter Prometheus** (métricas → mismos JSON):

```bash
export PROMETHEUS_BASE_URL=http://localhost:9090
export PROMETHEUS_SERVICES=rec-engine,serving-prod-eu
# default: PROMETHEUS_SLO_QUERY_MODE=histogram
mlops-triage-sync --adapter prometheus
```

**SLO — modo `histogram` (default):** PromQL sobre series típicas de serving:

- Latencia p99: `histogram_quantile` + `rate(http_request_duration_seconds_bucket{service=…}[window])`
- Errores 503: ratio de `http_requests_total` con `status="503"`

Ventana: `PROMETHEUS_SLO_WINDOW_MINUTES` (default 15). Nombres de métrica/labels configurables en `.env.example`. Ejemplos en [`data/prometheus_histogram_queries.example.promql`](data/prometheus_histogram_queries.example.promql).

**SLO — modo `gauges`:** métricas demo `mlops_slo_latency_p99_ms` / `mlops_slo_error_rate_503_pct` (ver [`data/prometheus_metrics.example.txt`](data/prometheus_metrics.example.txt)).

| Modo | Env |
|------|-----|
| histogram | `PROMETHEUS_SLO_QUERY_MODE=histogram` (default) |
| gauges | `PROMETHEUS_SLO_QUERY_MODE=gauges` |

Deploys: sigue usando `mlops_deployment_traffic_pct` (o `PROMETHEUS_DEPLOYMENT_PROMQL`).

Breach: `PROMETHEUS_LATENCY_BASELINE_MS` / `PROMETHEUS_ERROR_BASELINE_PCT`.

### RAG runbooks (integrado)

Markdown en [`data/runbooks/`](data/runbooks/). Índice en `data/rag_index.json` (auto-regenerado si cambiás `.md`).

| Flujo | Cómo usa RAG |
|-------|----------------|
| `structured_extraction.py` | Contexto en el prompt (default on; `USE_RUNBOOKS=0` para desactivar) |
| `agent_incident_triage.py` | Excerpts precargados + tool `search_runbook` |
| `full_incident_pipeline.py` | Retrieval antes de extracción y agente; imprime `runbook_hits` |
| Tool `search_runbook` | Más búsquedas durante el agente |

```bash
python examples/rag_runbook.py "p99 latency after canary"
python examples/rag_runbook.py --rebuild
```

## Uso

**Extracción estructurada (demo MLOps):**

```bash
python examples/structured_extraction.py
```

**Smoke test de chat plano** (manual, no pytest):

```bash
python examples/smoke_chat.py
```

**Agente con tools (triage MLOps):**

```bash
python examples/agent_incident_triage.py
```

**Pipeline completo (extracción + agente):**

```bash
python examples/full_incident_pipeline.py
```

**Búsqueda en runbooks (RAG):**

```bash
python examples/rag_runbook.py
```

### API HTTP (FastAPI)

```bash
pip install -e ".[api]"
uvicorn mlops_triage.api.app:app --reload --host 127.0.0.1 --port 8000
```

```bash
curl -s http://127.0.0.1:8000/health | jq

curl -s http://127.0.0.1:8000/triage \
  -H 'Content-Type: application/json' \
  -d '{"alert": "[PagerDuty] CRITICAL serving-prod-eu\nLatency p99 spike.", "use_runbooks": true}' | jq
```

`POST /triage` ejecuta `run_incident_pipeline` (extracción + RAG + agente). Respuestas `502` si falla el LLM o el agente. Con `use_runbooks: false` no usa embeddings (útil si solo tenés el modelo de chat).

Docs interactivas: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Tests

Solo unitarios (sin Ollama):

```bash
pytest -m "not integration"
```

Incluye integración contra Ollama:

```bash
pytest -m integration
```

## Layout

```
mlops_triage/     # paquete Python
  config.py           # Settings (env)
  llm/client.py       # factory OpenAI
  llm/structured.py   # complete_structured() + Pydantic
  llm/tools.py        # Tool + OpenAI function schemas
  agent/runner.py     # run_agent() tool loop
  tools/mlops.py      # herramientas agente
  tools/deployments_store.py
  tools/slo_store.py
  rag/                # chunk, embeddings, search
  api/app.py          # FastAPI /health, /triage
  sync/               # mlops-triage-sync (stub → JSON snapshots)
  pipelines/          # run_incident_pipeline()
  eval/               # aserciones para fixtures de eval
  fixtures/           # alertas de demo compartidas
  schemas/            # modelos de salida
data/                 # json snapshots, runbooks/, rag_index.json
tests/
examples/
```

## Siguientes fases (previstas)

- CI (unit en PR, integration opcional)
- Deployments desde métricas CD/Kubernetes (además de `mlops_deployment_traffic_pct`)
