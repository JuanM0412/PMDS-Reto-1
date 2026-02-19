# Backend - Orquestador Multiagente (FastAPI)

## 1. Objetivo
Este backend orquesta un flujo secuencial de 6 agentes en n8n para generar artefactos de arquitectura y diseno de software.

Modelo de operacion:
1. El usuario envia un brief inicial.
2. El sistema ejecuta el agente del step solicitado.
3. El usuario aprueba o rechaza cada entrega.
4. Si rechaza, se reintenta el mismo step con feedback.

El frontend consume un contrato por steps (`/api/chat/*`) y no necesita manejar estados complejos de run.

## 2. Arquitectura actual
Componentes principales:
- `app/main.py`: inicializacion FastAPI, CORS, seed de agentes, registro de routers.
- `app/orchestration.py`: pipeline de 6 steps, webhooks n8n y reglas de contexto entre agentes.
- `app/routers/chat.py`: contrato principal consumido por el frontend (`/api/chat/*`).
- `app/routers/orchestrator.py`: callback de n8n y endpoints auxiliares legacy.
- `app/models.py`: modelos SQLAlchemy (`runs`, `artifacts`, `step_executions`, `step_logs`, `agents`).
- `app/services.py`: cliente HTTP para disparar webhooks n8n.

Persistencia:
- Base recomendada: PostgreSQL (Docker).
- `artifacts.content_json` se guarda como texto JSON.

## 3. Pipeline de agentes
Definido en `app/orchestration.py` (`PIPELINE_STEPS`):

1. `requirements` -> `http://localhost:5678/webhook/brief-to-requirements`
2. `inception` -> `http://localhost:5678/webhook/inception`
3. `agile` -> `http://localhost:5678/webhook/HU`
4. `diagramacion` -> `http://localhost:5678/webhook/Diagramacion`
5. `pseudocodigo` -> `http://localhost:5678/webhook/Pseudocodigo`
6. `qa` -> `http://localhost:5678/webhook/QA`

Tipos de artefacto por step:
- step 1: `requirements`
- step 2: `inception`
- step 3: `agile`
- step 4: `diagramacion`
- step 5: `pseudocodigo`
- step 6: `qa`

## 4. Contrato API principal (frontend)
Base URL local: `http://localhost:8000`

### 4.1 `POST /api/chat/step`
Ejecuta un step especifico.

Request:
```json
{
  "step": 1,
  "uuid": "run-uuid-generado-en-front",
  "context": "texto o feedback",
  "is_feedback": false
}
```

Reglas:
- `step=1` y `is_feedback=false`: `context` es el brief inicial.
- `step>1` y `is_feedback=false`: backend arma el contexto automaticamente con artefactos previos.
- `is_feedback=true`: backend toma como `context` interno el ultimo artefacto de ese step y usa el `context` recibido como feedback del usuario.

Response:
```json
{
  "message": "texto para mostrar en UI"
}
```

Timeout:
- Espera maxima end-to-end por request: 90 segundos (`STEP_WAIT_TIMEOUT_SECONDS`).
- Si no llega callback a tiempo: responde mensaje de "sigue en procesamiento" y deja trazabilidad en logs.

### 4.2 `GET /api/chat/logs?step=<n>&uuid=<run_id>`
Respuesta:
```json
{
  "logs": ["..."]
}
```
Incluye logs sintetizados por backend y por intento (`attempt 1`, `attempt 2`, etc.).

### 4.3 `GET /api/chat/artifacts?step=<n>&uuid=<run_id>`
Respuesta:
```json
{
  "artifacts": [
    { "id": "12", "name": "Requirements Agent v1 - 2026-02-19 19:39:43" }
  ]
}
```

### 4.4 `GET /api/chat/artifacts/download?step=<n>&uuid=<run_id>&id=<artifact_id>`
Devuelve solo el contenido util del artefacto (si existe `artifact` dentro del JSON, retorna ese nodo).

## 5. Callback de n8n
Endpoint de entrada:
- `POST /callbacks/agent/{agent_slug}`

`agent_slug` validos:
- `requirements`, `inception`, `agile`, `diagramacion`, `pseudocodigo`, `qa`

Payload esperado:
```json
{
  "run_id": "<uuid>",
  "content": {
    "artifact": { },
    "changes_made": { "added": [], "removed": [], "modified": [] },
    "justification": "..."
  }
}
```

Tambien se tolera wrapper:
```json
{
  "body": {
    "run_id": "<uuid>",
    "content": { }
  }
}
```

## 6. Modelo de datos
Tablas principales:
- `runs`: ejecucion logica por `uuid`.
- `artifacts`: versiones por `run_id + artifact_type`.
- `step_executions`: intentos por step (status, payload, response, feedback).
- `step_logs`: logs sintetizados por intento.
- `agents`: metadata de agentes y webhook URL.

## 7. Variables de entorno
Ejemplo en `.env.example`:

```env
DATABASE_URL=postgresql+psycopg://postgres:12345678@localhost:5432/reto1_multiagentes
REQUEST_TIMEOUT_SECONDS=95
STEP_WAIT_TIMEOUT_SECONDS=90
ARTIFACT_POLL_INTERVAL_SECONDS=1
CORS_ALLOW_ORIGINS=["http://localhost:5173"]
```

## 8. Ejecucion local
### 8.1 Requisitos
- Python 3.11+
- Docker Desktop
- n8n levantado en `http://localhost:5678`

### 8.2 Levantar Postgres
```powershell
cd Backend
docker compose up -d
```

### 8.3 Configurar backend
```powershell
cd Backend
copy .env.example .env
python -m pip install -r app\requirements.txt
```

### 8.4 Ejecutar API
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 8.5 Verificar
- `GET http://localhost:8000/health`
- `GET http://localhost:8000/docs`

## 9. Endpoints auxiliares (legacy)
Siguen expuestos para soporte/manual:
- `GET /agents`
- `POST /runs/{run_id}/approve`
- `POST /runs/{run_id}/reject`

El frontend actual NO depende de estos endpoints.

## 10. Troubleshooting rapido
- Si `POST /api/chat/step` tarda 90s y responde "sigue en procesamiento": el callback de n8n no esta entrando.
- Si no aparecen artifacts: revisar URL de callback en n8n y `run_id` enviado.
- Si error de DB al iniciar: verificar contenedor postgres y `DATABASE_URL`.
- Si CORS falla: incluir origen del frontend en `CORS_ALLOW_ORIGINS`.
