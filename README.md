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
  pipelines/          # run_incident_pipeline()
  eval/               # aserciones para fixtures de eval
  fixtures/           # alertas de demo compartidas
  schemas/            # modelos de salida
data/                 # json snapshots, runbooks/, rag_index.json
tests/
examples/
```

## Siguientes fases (previstas)

- Conectar snapshots a cron/Prometheus
- CI (unit en PR, integration opcional)
