# Frontend - Multi-Agent Orchestrator UI (Vue 3 + Vite)

## 1) Scope and purpose
This frontend is an operator console for the multi-agent orchestration backend.
It implements the Human-in-the-Loop control plane for one run:
1. Submit initial brief.
2. Monitor pipeline progress.
3. Review each agent artifact.
4. Approve or reject with feedback.
5. Download artifact-only outputs.

The frontend does not talk directly to n8n.
All communication goes through FastAPI backend.

## 2) Tech stack
- Vue 3 (Composition API)
- Vite
- Native `fetch` API (no axios)
- Single-page view in one component (`src/App.vue`)

## 3) Runtime configuration
Environment file:
- `frontend/.env`

Variable:
```env
VITE_API_BASE=http://localhost:8000
```

All API calls use this base URL in `src/api.js`.

## 4) Project structure
- `src/main.js`: app bootstrap
- `src/App.vue`: main UI/state machine and interactions
- `src/api.js`: API client functions
- `vite.config.js`: Vite + Vue plugin config

## 5) UI state model
Primary reactive state (`App.vue`):
- `run`: current run snapshot (`id`, `status`, `current_agent`, `is_waiting_for_user`)
- `agents`: ordered pipeline agent metadata
- `latestArtifact`: latest artifact for current agent
- `brief`: user-provided initial brief
- `feedback`: reject feedback text
- `error`, `info`: operation messages
- Loading flags:
- `loadingCreate`
- `loadingDecision`
- `loadingRefresh`
- Polling control:
- `pollTimer`
- `isPollingTickInFlight`

Derived/computed values:
- `isWaitingDecision`
- `isCompleted`
- `currentArtifactType` (agent slug -> artifact type mapping)
- action guards `canApprove`, `canReject`
- pipeline `stepper` state visualization

## 6) API client contract (`src/api.js`)
Functions and backend mapping:
1. `createRun(brief)` -> `POST /runs`
2. `getRun(runId)` -> `GET /runs/{runId}`
3. `getAgents()` -> `GET /agents`
4. `approveRun(runId)` -> `POST /runs/{runId}/approve`
5. `rejectRun(runId, feedback)` -> `POST /runs/{runId}/reject`
6. `getLatestArtifact(runId, artifactType)` -> `GET /runs/{runId}/artifacts/latest?artifact_type=<type>`
7. `getArtifactsExport(runId)` -> `GET /runs/{runId}/artifacts/export`

Error handling:
- `parseResponse()` throws a rich message with operation name and HTTP status.
- UI catches and renders message in error panel.

## 7) Polling strategy
Timer interval:
- `POLL_MS = 1800`

Algorithm:
1. Start polling after run creation.
2. On each tick, call `GET /runs/{id}`.
3. If `is_waiting_for_user=true`:
- stop polling
- load latest artifact for current agent
4. If `status=COMPLETED`:
- stop polling
5. Else keep polling.

Concurrency control:
- `isPollingTickInFlight` avoids overlapping polling requests.

Lifecycle:
- polling stops on component unmount (`onBeforeUnmount`).

## 8) Agent-to-artifact mapping in UI
Local mapping (`agentToArtifactType`):
- `requirements -> requirements`
- `inception -> inception`
- `agile -> agile`
- `diagramacion -> diagramacion`
- `pseudocodigo -> pseudocodigo`
- `qa -> qa`

Used to fetch correct latest artifact during wait-for-approval state.

## 9) Use cases
### 9.1 Create and run pipeline
1. User fills brief.
2. Clicks `Crear Run`.
3. UI calls `POST /runs`.
4. UI starts polling.
5. Backend orchestrates agent execution.

### 9.2 Review and approve agent output
1. UI reaches `is_waiting_for_user=true`.
2. UI fetches latest artifact for current agent.
3. User clicks `Aprobar y Continuar`.
4. UI calls `POST /runs/{id}/approve`.
5. Polling resumes.

### 9.3 Review and reject with feedback
1. User writes feedback (min length 3).
2. Clicks `Reajustar con Feedback`.
3. UI calls `POST /runs/{id}/reject` with body `{feedback}`.
4. Polling resumes while backend re-triggers same agent.

### 9.4 Download current artifact only
Button: `Descargar JSON`.
Behavior:
1. Takes `latestArtifact.content`.
2. If `content.artifact` exists, exports only that object.
3. Downloads file:
`<run_id>_<artifact_type>_v<version>_artifact.json`

### 9.5 Download all run artifacts (artifact-only)
Button: `Descargar Artefactos del Run`.
Behavior:
1. Calls `GET /runs/{id}/artifacts/export`.
2. Downloads file:
`<run_id>_artifacts_only.json`

## 10) UI sections
1. Brief input panel
2. Run metadata panel
- run id
- status
- current agent
- waiting decision flag
3. Pipeline stepper panel
4. Decision panel (visible only in waiting decision state)
- Approve action
- Reject with feedback action
5. Latest artifact viewer
6. Info/error status messages

## 11) Backend status interpretation in UI
The UI expects these backend statuses:
- `IN_PROGRESS_*`
- `WAITING_APPROVAL_*`
- `RETRYING_*`
- `COMPLETED`

Stepper color/state mapping:
- `completed`
- `running`
- `waiting`
- `retrying`
- `pending`

## 12) Development
### 12.1 Requirements
- Node `^20.19.0 || >=22.12.0`

### 12.2 Install
```powershell
cd Frontend\frontend
npm install
```

### 12.3 Run dev server
```powershell
npm run dev
```

### 12.4 Build
```powershell
npm run build
```

### 12.5 Preview production build
```powershell
npm run preview
```

## 13) End-to-end integration checklist
1. Backend running on `http://localhost:8000`
2. n8n workflows active and callbacking backend
3. `VITE_API_BASE` points to backend
4. CORS in backend includes frontend origin
5. Create run from UI and verify polling transitions
6. Validate approve/reject flow across all 6 agents
7. Validate artifact downloads

## 14) Known constraints
1. Single-component UI (`App.vue`) concentrates logic/state.
2. No router/state manager yet.
3. No authentication flow.
4. No resume-by-run-id deep link.
5. Polling is timer-based; no SSE/WebSocket.

## 15) Suggested frontend improvements
1. Split `App.vue` into feature components.
2. Add Vue Router and a run detail route (`/runs/:id`).
3. Persist active run id in localStorage.
4. Add syntax-highlighted JSON viewer.
5. Add network retry/backoff and offline indicators.
6. Replace polling with SSE for status updates.
