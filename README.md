# PMDS Reto 1 - Sistema Multiagente (Frontend + Backend + n8n)

## 1. Que es este proyecto
Este proyecto implementa un sistema multiagente para apoyar un proceso de arquitectura y diseno de software con minima intervencion humana.

Objetivo funcional:
- Recibir un brief inicial de negocio/producto.
- Ejecutar 6 agentes especializados en secuencia.
- En cada entrega, aplicar Human-in-the-Loop (aprobar o rechazar).
- Si se rechaza, reintentar el mismo agente con feedback.
- Persistir y versionar artefactos por agente.
- Permitir consulta de logs y descarga de artefactos.

## 2. Arquitectura general
Componentes:
1. Frontend Vue (`frontend/`)
- UI de pipeline por steps.
- Control de aprobacion/rechazo.
- Consulta de logs y artefactos.

2. Backend FastAPI (`Backend/`)
- Orquesta el flujo de steps.
- Arma contexto para cada agente.
- Dispara webhooks de n8n.
- Recibe callbacks de agentes.
- Guarda artefactos y logs.

3. n8n (Docker)
- Ejecuta cada flujo agente (LLM + parseo + callback).

4. PostgreSQL (Docker)
- Persistencia de runs, artefactos, ejecuciones y logs.

## 3. Como funciona el flujo end-to-end
Secuencia simplificada:
1. Front hace `POST /api/chat/step` con `step=1`, `uuid`, `context=brief`, `is_feedback=false`.
2. Backend crea/usa run con `uuid`, dispara webhook n8n del step 1.
3. Flujo n8n genera artefacto y hace callback a backend.
4. Backend guarda artefacto/version y responde `message` al front.
5. Usuario aprueba o rechaza:
- Aprobar: front llama step siguiente (`step+1`).
- Rechazar: front llama mismo step con `is_feedback=true` y `context=<feedback>`.
6. Backend registra cada intento en `step_executions` y `step_logs`.

## 4. Pipeline de agentes
Definido en `Backend/app/orchestration.py`:

1. Requirements -> `brief-to-requirements`
2. Inception -> `inception`
3. Agile/HU -> `HU`
4. Diagramacion -> `Diagramacion`
5. Pseudocodigo -> `Pseudocodigo`
6. QA -> `QA`

Archivos de flujos n8n (para importar):
- `Backend/agentes/brief-to-requirements.json`
- `Backend/agentes/inception.json`
- `Backend/agentes/Agile.json`
- `Backend/agentes/Diagramacion.json`
- `Backend/agentes/Pseudocodigo.json`
- `Backend/agentes/QA.json`

## 5. Decisiones de diseno (como lo hicimos)
1. Contrato frontend-first por steps
- Se implemento `/api/chat/*` para que el front controle el pipeline por `step` + `uuid`.
- Se evita que el front maneje estados complejos de run en backend.

2. Human-in-the-loop simple
- Solo 2 acciones del usuario: aprobar o rechazar.
- En rechazo, el backend reusa ultimo artefacto del step y aplica feedback.

3. Trazabilidad completa
- Se agregaron `step_executions` y `step_logs` para historial por intento.
- Logs sintetizados desde backend para diagnostico rapido.

4. Persistencia desacoplada de n8n
- Artefactos quedan versionados en backend aunque n8n sea stateless.

5. Timeboxing por request
- `POST /api/chat/step` espera hasta ~90 segundos.
- Si no llega callback a tiempo, devuelve mensaje de "sigue en procesamiento".

## 6. Prerrequisitos
- Git
- Docker Desktop
- Python 3.11+ (probado con 3.13)
- Node.js 20+
- npm

## 7. Replicacion completa desde cero

### 7.1 Clonar repositorio
```powershell
git clone https://github.com/Sebastian-jimenez30/PMDS-Reto-1.git
cd PMDS-Reto-1
```

### 7.2 Levantar PostgreSQL (backend)
El proyecto ya trae compose para DB en `Backend/docker-compose.yml`.

```powershell
cd Backend
docker compose up -d
```

Verificar estado:
```powershell
docker compose ps
```
Debe aparecer `reto1_multiagentes_db` en `healthy`.

### 7.3 Configurar y ejecutar backend
1. Crear `.env` desde ejemplo:
```powershell
copy .env.example .env
```

2. Instalar dependencias:
```powershell
python -m pip install -r app\requirements.txt
```

3. Ejecutar API:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Verificar:
- `http://localhost:8000/health`
- `http://localhost:8000/docs`

### 7.4 Levantar n8n en Docker
Desde otra terminal:

```powershell
docker run -d --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n n8nio/n8n:latest
```

Abrir n8n:
- `http://localhost:5678`

> Nota: en Docker Desktop (Windows/Mac), `host.docker.internal` permite que n8n en contenedor llame al backend en host.

### 7.5 Importar flujos de agentes en n8n
En n8n:
1. Crear cuenta/ingresar a la instancia.
2. Ir a Workflows -> Import from file.
3. Importar uno a uno los 6 JSON de `Backend/agentes/`.
4. Guardar cada workflow.
5. Activar cada workflow (`Active = ON`).

### 7.6 Configurar credenciales LLM en n8n
Los flujos usan nodos `Groq Chat Model`.

En cada workflow:
1. Abrir nodo `Groq Chat Model`.
2. Crear/seleccionar credencial `groqApi` valida.
3. Guardar workflow.

Sin esta credencial, los agentes no generan salida.

### 7.7 Verificar callbacks n8n -> backend
Cada flujo debe tener un nodo HTTP Request que apunte a backend:
- `/callbacks/agent/requirements`
- `/callbacks/agent/inception`
- `/callbacks/agent/agile`
- `/callbacks/agent/diagramacion`
- `/callbacks/agent/pseudocodigo`
- `/callbacks/agent/qa`

URL recomendada si n8n esta en Docker y backend en host:
- `http://host.docker.internal:8000/callbacks/agent/<slug>`

Si ambos estan fuera de Docker:
- `http://localhost:8000/callbacks/agent/<slug>`

### 7.8 Ejecutar frontend
Desde otra terminal:

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Abrir:
- `http://localhost:5173`

## 8. Contrato de integracion frontend <-> backend
Base backend: `http://localhost:8000`

Endpoints usados por frontend:
1. `POST /api/chat/step`
Request:
```json
{
  "step": 1,
  "uuid": "<uuid>",
  "context": "<brief o feedback>",
  "is_feedback": false
}
```
Response:
```json
{ "message": "..." }
```

2. `GET /api/chat/logs?step=<n>&uuid=<uuid>`
Response:
```json
{ "logs": ["..."] }
```

3. `GET /api/chat/artifacts?step=<n>&uuid=<uuid>`
Response:
```json
{ "artifacts": [{ "id": "...", "name": "..." }] }
```

4. `GET /api/chat/artifacts/download?step=<n>&uuid=<uuid>&id=<artifact_id>`
Response:
- JSON del artefacto para descarga.

## 9. Prueba rapida de humo
1. En frontend, enviar brief inicial.
2. Confirmar que step 1 responde con mensaje.
3. Abrir logs del step 1.
4. Ver artifacts del step 1 y descargar uno.
5. Aprobar para avanzar a step 2.
6. Rechazar en algun step y reenviar feedback.
7. Verificar nueva version de artefacto en ese step.

## 10. Estructura del repo
```text
PMDS-Reto-1/
  Backend/
    agentes/                 # Flujos n8n (json)
    app/                     # FastAPI + SQLAlchemy
    docker-compose.yml       # PostgreSQL
    README.md                # Documentacion tecnica backend
  frontend/
    src/                     # Vue app
    README.md                # Documentacion tecnica frontend
```

## 11. Troubleshooting
1. `POST /api/chat/step` tarda ~90s y responde "sigue en procesamiento"
- El callback desde n8n no llego.
- Revisar URL del nodo HTTP Request de cada flujo.
- Revisar que backend este en `:8000`.

2. No aparecen artifacts/logs en frontend
- Revisar que workflow este `Active` en n8n.
- Verificar errores de ejecucion en historial de n8n.
- Revisar credenciales Groq.

3. Error de conexion a DB en backend
- Revisar `docker compose ps` en `Backend/`.
- Confirmar `DATABASE_URL` en `Backend/.env`.

4. Error CORS en navegador
- Ajustar `CORS_ALLOW_ORIGINS` en `Backend/.env`.

## 12. Comandos utiles
Backend:
```powershell
cd Backend
docker compose up -d
uvicorn app.main:app --reload --port 8000
```

Frontend:
```powershell
cd frontend
npm run dev
```

n8n:
```powershell
docker start n8n
```

## 13. Documentacion por componente
- Backend detallado: `Backend/README.md`
- Frontend detallado: `frontend/README.md`
