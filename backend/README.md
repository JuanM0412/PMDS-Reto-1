# Agents Backend

FastAPI backend for the multi-agent pipeline. Bridges the Vue.js frontend with six n8n-powered AI agents running locally.

---

## Architecture

```
backend/
├── app/
│   ├── main.py                  # FastAPI app init, middleware, router registration
│   ├── config.py                # Settings via pydantic-settings (.env)
│   ├── database.py              # SQLAlchemy engine, session factory, Base
│   ├── constants/
│   │   └── agents.py            # Immutable pipeline agent configs (step, webhook path, artifact types)
│   ├── models/
│   │   └── agent_log.py         # ORM model → agent_logs table
│   ├── schemas/
│   │   ├── n8n.py               # Pydantic schemas for n8n callback payload
│   │   └── chat.py              # Pydantic schemas for frontend API
│   ├── repositories/
│   │   └── agent_log_repository.py  # All database access for agent_logs
│   ├── services/
│   │   ├── n8n_service.py       # HTTP client for n8n webhooks
│   │   └── agent_log_service.py # Business logic (record results, build logs/artifacts)
│   ├── routers/
│   │   ├── n8n_router.py        # Endpoint 1 — POST /api/n8n/callback
│   │   └── chat_router.py       # Endpoints 2–5 — /api/chat/*
│   └── utils/
│       └── logging.py           # Structured logging setup
├── scripts/
│   └── agents.sql               # PostgreSQL schema creation script
├── requirements.txt
├── .env.example
├── Dockerfile
└── docker-compose.yml
```

### SOLID principles applied

| Principle | Where |
|---|---|
| **S** — Single Responsibility | Repository → DB only. Service → business logic only. Router → HTTP only. |
| **O** — Open/Closed | Add a new agent by appending to `AGENTS` in `constants/agents.py`; no existing code changes needed. |
| **L** — Liskov | `AgentLogService` can be subclassed/swapped without breaking routers (they depend on the same public interface). |
| **I** — Interface Segregation | Separate schema files for n8n vs frontend contracts. |
| **D** — Dependency Inversion | Routers depend on services via FastAPI `Depends`; services depend on `AgentLogRepository`. |

---

## Database

Single table: **`agent_logs`**

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL PK | Auto-increment primary key |
| `uuid` | VARCHAR(128) | User session identifier (from frontend) |
| `agente` | INTEGER (1–6) | Pipeline step number |
| `artefacto` | JSONB | Artifact JSON returned by n8n |
| `justificacion` | TEXT | Justification text provided by n8n |
| `added` | TEXT | JSON-encoded list of added items |
| `modified` | TEXT | JSON-encoded list of modified items |
| `deleted` | TEXT | JSON-encoded list of deleted items |
| `timestamp` | TIMESTAMP | UTC timestamp of record creation |

---

## Endpoints

### Endpoint 1 — N8N Callback
```
POST /api/n8n/callback
```
Called by n8n when it finishes a pipeline step. Persists the result.

**Request body:**
```json
{
  "uuid": "session-uuid",
  "step": 1,
  "artifact": { "artifact_type_key": [] },
  "changes_made": {
    "added": [],
    "removed": [],
    "modified": []
  },
  "justification": "explanation of what was done"
}
```

---

### Endpoint 2 — Get Logs
```
GET /api/chat/logs?uuid=<uuid>&step=<1-6>
```
Returns human-readable log lines for the given session + step.

**Response:**
```json
{ "logs": ["[Run 1 — 2026-02-19 10:00:00 UTC]", "  Justification: ..."] }
```

---

### Endpoint 3 — Trigger Agent (frontend)
```
POST /api/chat/step
```
Received from the frontend. Triggers the n8n agent for the requested step and returns immediately (async). n8n will deliver the result via Endpoint 1.

**Request body:**
```json
{
  "step": 1,
  "uuid": "session-uuid",
  "context": "user input or artifact to review",
  "is_feedback": false
}
```

**Response:**
```json
{ "message": "Agent 1 (Requirements Agent) triggered successfully. Waiting for result." }
```

---

### Endpoint 4 — List Artifacts
```
GET /api/chat/artifacts?uuid=<uuid>&step=<1-6>
```
Returns a list of artifact type keys available in the latest result for a step.

**Response:**
```json
{
  "artifacts": [
    { "id": "functional_requirements", "name": "Functional Requirements" },
    { "id": "non_functional_requirements", "name": "Non Functional Requirements" }
  ]
}
```

---

### Endpoint 5 — Download Artifact
```
GET /api/chat/artifacts/download?uuid=<uuid>&step=<1-6>&id=<artifact_type>
```
Returns the full JSON content of a specific artifact.

---

## Quick Start

### 1. Set up environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 2. Start PostgreSQL (Docker)
```bash
docker compose up db -d
```

### 3. Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the backend
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API docs are available at http://localhost:8000/docs.

---

## N8N Integration

When the backend triggers n8n it sends:
```json
{
  "context": "...",
  "is_feedback": false,
  "feedback": null,
  "uuid": "session-uuid",
  "step": 1,
  "callback_url": "http://localhost:8000/api/n8n/callback"
}
```

Configure each n8n workflow to POST its result (including `uuid` and `step`) to the `callback_url` field when it finishes.
