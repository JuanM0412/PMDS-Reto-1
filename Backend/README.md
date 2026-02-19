# Backend - Multi-Agent Orchestrator (FastAPI)

## 1) Scope and purpose
This backend orchestrates an end-to-end software architecture and design flow executed by 6 external n8n agents.
The user interaction model is Human-in-the-Loop (HITL):
1. User submits one initial brief.
2. System runs one agent at a time.
3. For each agent output, user decides:
- Approve: move to next agent.
- Reject with feedback: rerun same agent using last output as context.

The backend is the source of truth for:
- Run lifecycle and state transitions.
- Agent ordering and routing.
- Context composition between agents.
- Artifact persistence and versioning.
- Artifact export (artifact-only payloads).

## 2) High-level architecture
Components:
1. FastAPI app (`app/main.py`)
2. SQLAlchemy models + SQLite database (`app/models.py`, `app/db.py`, `app.db`)
3. Orchestration module (`app/orchestration.py`)
4. API routers:
- `app/routers/runs.py`
- `app/routers/orchestrator.py`
- `app/routers/artifacts.py`
5. External n8n flows (called by webhook)

Primary interaction directions:
1. Backend -> n8n: triggers next agent with `{run_id, context, is_feedback, feedback}`
2. n8n -> Backend: callback with agent output
3. Frontend -> Backend: run creation, polling, approve/reject, artifact download/export

## 3) Agent pipeline definition
Pipeline is statically defined in `app/orchestration.py` (`PIPELINE_STEPS`):

| order | slug         | artifact_type | webhook_url |
|------:|--------------|---------------|-------------|
| 1     | requirements | requirements  | `http://localhost:5678/webhook/brief-to-requirements` |
| 2     | inception    | inception     | `http://localhost:5678/webhook/inception` |
| 3     | agile        | agile         | `http://localhost:5678/webhook/HU` |
| 4     | diagramacion | diagramacion  | `http://localhost:5678/webhook/Diagramacion` |
| 5     | pseudocodigo | pseudocodigo  | `http://localhost:5678/webhook/Pseudocodigo` |
| 6     | qa           | qa            | `http://localhost:5678/webhook/QA` |

On startup, backend syncs DB agents against this pipeline (`seed_agents()`).

## 4) Data model
### 4.1 `agents`
Columns:
- `id` (PK)
- `name`
- `slug` (unique)
- `n8n_webhook_url`
- `order`

### 4.2 `runs`
Columns:
- `id` (PK, generated `RUN_<timestamp+random>`)
- `domain`
- `brief`
- `status`
- `current_agent_id` (FK -> agents.id, nullable)
- `is_waiting_for_user` (bool)
- `created_at`
- `updated_at`

### 4.3 `artifacts`
Columns:
- `id` (PK)
- `run_id` (FK -> runs.id)
- `artifact_type`
- `version` (incremental per `run_id + artifact_type`)
- `content_json` (JSON serialized as text)
- `created_at`

Index:
- `ix_artifacts_run_type_created` on `(run_id, artifact_type, created_at)`

## 5) State machine
Canonical statuses produced by routers:
- `IN_PROGRESS_<AGENT_SLUG_UPPER>`
- `WAITING_APPROVAL_<AGENT_SLUG_UPPER>`
- `RETRYING_<AGENT_SLUG_UPPER>`
- `COMPLETED`

Transitions:
1. `POST /runs` -> first agent triggered -> `IN_PROGRESS_REQUIREMENTS`
2. Agent callback/artifact receive -> `WAITING_APPROVAL_<CURRENT>`
3. Approve -> next agent:
- if exists: `IN_PROGRESS_<NEXT>`
- else: `COMPLETED`
4. Reject with feedback -> same agent rerun -> `RETRYING_<CURRENT>` then callback returns to `WAITING_APPROVAL_<CURRENT>`

## 6) Context composition rules
`build_context_for_agent(...)` composes next payload context from run brief + latest artifacts.

Rules by target agent:
1. `requirements`: `{domain, brief}`
2. `inception`: `{domain, brief, requirements}`
3. `agile`: `{requirements, inception}`
4. `diagramacion`: `{requirements, inception, agile}`
5. `pseudocodigo`: `{requirements, agile, diagramacion}`
6. `qa`: `{requirements, inception, agile, diagramacion, pseudocodigo}`

Reject/retry behavior:
- Context is not rebuilt from all artifacts.
- Context is set to the last artifact of the current agent.
- `is_feedback=true`, `feedback=<user_text>`

## 7) API reference
Base URL: `http://localhost:8000`

### 7.1 Health
`GET /health`
Response:
```json
{ "status": "ok" }
```

### 7.2 Create run
`POST /runs`
Body:
```json
{
  "domain": "super-app",
  "brief": "... min 30 chars ..."
}
```
Behavior:
1. Create run.
2. Select first pipeline agent.
3. Trigger first n8n webhook in background.
4. Return run snapshot.

### 7.3 Get run
`GET /runs/{run_id}`
Response includes:
- `status`
- `current_agent` metadata
- `is_waiting_for_user`

### 7.4 List pipeline agents
`GET /agents`
Returns ordered agent list from pipeline.

### 7.5 Agent callback
`POST /callbacks/agent/{agent_slug}`
Accepted payloads:
1. Preferred:
```json
{
  "run_id": "RUN_...",
  "content": { "artifact": { }, "changes_made": { }, "justification": "..." }
}
```
2. Tolerated wrapper from some n8n configurations:
```json
{
  "body": {
    "run_id": "RUN_...",
    "content": { }
  }
}
```
Notes:
- `artifact_type` is inferred from `agent_slug` via pipeline mapping.
- If `content` is missing, backend uses remaining payload fields as content fallback.
- Saves artifact and sets run to `WAITING_APPROVAL_<AGENT>`.

### 7.6 Approve current artifact
`POST /runs/{run_id}/approve`
Behavior:
1. Requires `is_waiting_for_user=true`.
2. Finds next pipeline agent.
3. Builds context for next agent.
4. Triggers next webhook.
5. If no next agent, marks run `COMPLETED`.

### 7.7 Reject current artifact with feedback
`POST /runs/{run_id}/reject`
Body:
```json
{
  "feedback": "Please adjust ..."
}
```
Behavior:
1. Requires `is_waiting_for_user=true`.
2. Loads latest artifact for current agent.
3. Sends retry payload:
```json
{
  "run_id": "RUN_...",
  "context": { "...last_current_agent_output..." },
  "is_feedback": true,
  "feedback": "..."
}
```
4. Sets status `RETRYING_<AGENT>`.

### 7.8 Store artifact (manual/system fallback)
`POST /runs/{run_id}/artifacts`
Body (minimal):
```json
{
  "artifact_type": "requirements",
  "content": { "artifact": { } }
}
```
Notes:
- If `run.current_agent` is present, backend enforces `artifact_type` from current agent mapping.
- After save, run is set to waiting approval.

### 7.9 Get latest artifact by type
`GET /runs/{run_id}/artifacts/latest?artifact_type=<type>`
Legacy alias supported:
- `type=<type>`

### 7.10 Export artifact-only payloads
`GET /runs/{run_id}/artifacts/export`
Returns latest artifact per type, transformed to keep only `content.artifact` when present.
Example response:
```json
{
  "run_id": "RUN_...",
  "exported_at": "2026-02-17T23:00:00Z",
  "artifacts": [
    {
      "artifact_type": "requirements",
      "version": 2,
      "created_at": "2026-02-17T22:10:00Z",
      "artifact": { "...": "..." }
    }
  ]
}
```

## 8) n8n integration contract
### 8.1 Outgoing payload from backend to n8n
```json
{
  "run_id": "RUN_...",
  "context": { "...depends on agent..." },
  "is_feedback": false,
  "feedback": ""
}
```
Retry call uses `is_feedback=true` and non-empty `feedback`.

### 8.2 Incoming payload from n8n to backend
Use callback endpoint per agent slug:
- `/callbacks/agent/requirements`
- `/callbacks/agent/inception`
- `/callbacks/agent/agile`
- `/callbacks/agent/diagramacion`
- `/callbacks/agent/pseudocodigo`
- `/callbacks/agent/qa`

Body should include:
```json
{
  "run_id": "RUN_...",
  "content": {
    "artifact": { "..." },
    "changes_made": { "added": [], "removed": [], "modified": [] },
    "justification": "..."
  }
}
```

## 9) Configuration
Environment variables (`.env`):
```env
DATABASE_URL=sqlite:///./app.db
N8N_WEBHOOK_URL=http://localhost:5678/webhook-test/brief-to-requirements
REQUEST_TIMEOUT_SECONDS=30
CORS_ALLOW_ORIGINS=["http://localhost:5173"]
```

Important note:
- Pipeline webhooks come from `PIPELINE_STEPS` and are stored in DB by `seed_agents()`.
- `N8N_WEBHOOK_URL` is only used by legacy helper `trigger_n8n_requirements()`.

## 10) Run and development
### 10.1 Install
```powershell
cd Backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r app\requirements.txt
```

### 10.2 Start API
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 10.3 OpenAPI docs
- `http://localhost:8000/docs`

## 11) Sequence (happy path)
1. Frontend -> `POST /runs`
2. Backend -> n8n requirements webhook
3. n8n -> `POST /callbacks/agent/requirements`
4. Frontend polls `GET /runs/{id}` until `WAITING_APPROVAL_REQUIREMENTS`
5. Frontend loads artifact via `/artifacts/latest`
6. Frontend -> `POST /runs/{id}/approve`
7. Backend -> next n8n webhook
8. Repeat until `COMPLETED`

## 12) Sequence (reject path)
1. Run is in `WAITING_APPROVAL_<AGENT>`
2. Frontend -> `POST /runs/{id}/reject` with feedback
3. Backend loads last artifact for current agent
4. Backend -> same n8n webhook with `is_feedback=true`
5. n8n sends corrected output to callback
6. Backend returns to `WAITING_APPROVAL_<AGENT>`

## 13) Known constraints and technical debt
1. SQLite schema migration is manual/minimal. Startup only patches missing `runs` columns. No Alembic yet.
2. `artifacts.content_json` is TEXT. For production, use JSONB (Postgres) + migrations.
3. No authN/authZ on endpoints.
4. No idempotency keys for callback dedup.
5. No retry queue/circuit breaker for failed webhook calls.
6. No formal per-agent JSON schema validation in backend for all artifact types.

## 14) Suggested next hardening steps
1. Add Alembic migrations.
2. Add authentication and role model (reviewer/operator).
3. Add callback signature verification.
4. Add structured run/audit log table.
5. Add dead-letter/retry strategy for n8n failures.
6. Add per-agent schema registry and strict validation.
