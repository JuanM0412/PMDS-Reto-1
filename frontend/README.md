# Frontend - Pipeline Multiagente (Vue 3)

## 1. Objetivo
Este frontend implementa la interfaz de operacion del flujo multiagente con Human-in-the-Loop:
- Usuario envia brief inicial.
- Se ejecutan 6 steps en secuencia.
- En cada entrega el usuario puede aprobar o rechazar.
- Si rechaza, envia feedback y se reintenta el mismo step.
- Puede consultar logs y descargar artefactos por step.

## 2. Stack
- Vue 3 + Composition API
- TypeScript
- Vue Router
- Vite

## 3. Flujo funcional
1. Usuario escribe mensaje inicial y pulsa `Enviar`.
2. Se genera `uuid` para la ejecucion.
3. Front llama `POST /api/chat/step` con `step=1`.
4. Backend responde `message` para aprobacion.
5. Si usuario aprueba, front llama automaticamente el siguiente step (2..6).
6. Si usuario rechaza, front llama el mismo step con `is_feedback=true` y `context=<feedback>`.
7. En steps completados el usuario puede:
- Ver logs (`GET /api/chat/logs`)
- Ver artefactos (`GET /api/chat/artifacts`)
- Descargar artefacto (`GET /api/chat/artifacts/download`)

## 4. Contrato esperado del backend
Todos los llamados usan prefijo `/api/chat`.

### 4.1 POST `/api/chat/step`
Request:
```json
{
  "step": 1,
  "uuid": "run-uuid",
  "context": "brief inicial o feedback",
  "is_feedback": false
}
```
Response:
```json
{
  "message": "texto para UI"
}
```

### 4.2 GET `/api/chat/logs?step=<n>&uuid=<uuid>`
Response:
```json
{
  "logs": ["..."]
}
```

### 4.3 GET `/api/chat/artifacts?step=<n>&uuid=<uuid>`
Response:
```json
{
  "artifacts": [
    { "id": "123", "name": "Requirements Agent v1 - 2026-02-19 19:39:43" }
  ]
}
```

### 4.4 GET `/api/chat/artifacts/download?step=<n>&uuid=<uuid>&id=<artifact_id>`
Response:
- JSON del artefacto (el frontend lo descarga como archivo `.json`).

## 5. Configuracion de API
Archivo recomendado: `.env` en la raiz de `frontend/`.

```env
VITE_API_BASE_URL=http://localhost:8000
```

Notas:
- Si no defines variable, el front usa fallback `http://localhost:8000`.
- No existe modo simulacion en el servicio actual: siempre intenta consumir backend real.

## 6. Estructura relevante
- `src/features/chat/views/ChatView.vue`: UI principal de pipeline.
- `src/features/chat/composables/useChat.ts`: estado y logica del flujo.
- `src/features/chat/services/ChatService.ts`: llamadas HTTP al backend.
- `src/shared/utils/ApiRoutesUtil.ts`: rutas y base URL.
- `src/shared/services/BaseService.ts`: wrapper basico de `fetch`.

## 7. Ejecucion local
```bash
cd frontend
npm install
npm run dev
```

Abrir URL de Vite (normalmente `http://localhost:5173`).

## 8. Build
```bash
npm run build-only
```
Salida en `dist/`.

## 9. Integracion end-to-end
Para funcionamiento completo necesitas:
1. Backend FastAPI corriendo en `http://localhost:8000`.
2. Postgres levantado para backend.
3. n8n corriendo con los 6 webhooks de agentes y callbacks al backend.

## 10. Problemas comunes
- Mensaje "error al procesar el paso": backend caido, CORS o timeout.
- No aparecen logs/artifacts: callback n8n no esta llegando al backend.
- Descarga vacia: revisar `id` de artefacto y respuesta de `/artifacts/download`.
