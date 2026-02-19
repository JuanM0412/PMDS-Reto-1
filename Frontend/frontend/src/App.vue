<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import {
  approveRun,
  createRun,
  getAgents,
  getArtifactsExport,
  getLatestArtifact,
  getRun,
  rejectRun,
} from "./api";

const brief = ref(
  "Queremos una super app para Medellín con onboarding, pagos, pedidos, notificaciones, soporte y panel admin para comercios, con foco en seguridad y escalabilidad."
);

const loadingCreate = ref(false);
const loadingDecision = ref(false);
const loadingRefresh = ref(false);
const isPollingTickInFlight = ref(false);
const error = ref("");
const info = ref("");

const run = ref(null);
const agents = ref([]);
const latestArtifact = ref(null);
const feedback = ref("");

const pollTimer = ref(null);
const POLL_MS = 1800;

const agentToArtifactType = {
  requirements: "requirements",
  inception: "inception",
  agile: "agile",
  diagramacion: "diagramacion",
  pseudocodigo: "pseudocodigo",
  qa: "qa",
};

const runId = computed(() => run.value?.id ?? "—");
const status = computed(() => run.value?.status ?? "—");
const currentAgent = computed(() => run.value?.current_agent ?? null);
const currentAgentSlug = computed(() => currentAgent.value?.slug ?? null);
const currentArtifactType = computed(() => {
  const slug = currentAgentSlug.value;
  return slug ? agentToArtifactType[slug] ?? null : null;
});
const isWaitingDecision = computed(() => Boolean(run.value?.is_waiting_for_user));
const isCompleted = computed(() => run.value?.status === "COMPLETED");
const canApprove = computed(() => Boolean(run.value?.id && isWaitingDecision.value && !loadingDecision.value));
const canReject = computed(() => {
  const text = feedback.value.trim();
  return Boolean(run.value?.id && isWaitingDecision.value && text.length >= 3 && !loadingDecision.value);
});

const stepper = computed(() => {
  const list = agents.value.map((a) => ({ ...a, state: "pending" }));
  if (!run.value) return list;

  if (isCompleted.value) {
    return list.map((a) => ({ ...a, state: "completed" }));
  }

  const currentOrder = currentAgent.value?.order ?? null;
  const st = run.value.status ?? "";

  return list.map((a) => {
    if (currentOrder == null) return { ...a, state: "pending" };
    if (a.order < currentOrder) return { ...a, state: "completed" };
    if (a.order > currentOrder) return { ...a, state: "pending" };

    if (st.startsWith("WAITING_APPROVAL_")) return { ...a, state: "waiting" };
    if (st.startsWith("RETRYING_")) return { ...a, state: "retrying" };
    if (st.startsWith("IN_PROGRESS_")) return { ...a, state: "running" };
    return { ...a, state: "current" };
  });
});

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value);
    pollTimer.value = null;
  }
}

function startPolling() {
  if (pollTimer.value || !run.value?.id) return;
  pollTimer.value = setInterval(async () => {
    if (isPollingTickInFlight.value) return;
    await refreshRun(false);
  }, POLL_MS);
}

async function loadAgents() {
  try {
    agents.value = await getAgents();
  } catch (e) {
    error.value = String(e?.message ?? e);
  }
}

async function loadLatestForCurrentAgent() {
  if (!run.value?.id || !currentArtifactType.value) return;
  latestArtifact.value = await getLatestArtifact(run.value.id, currentArtifactType.value);
}

async function refreshRun(showSpinner = true) {
  if (!run.value?.id) return;
  if (showSpinner) loadingRefresh.value = true;
  isPollingTickInFlight.value = true;

  try {
    const updated = await getRun(run.value.id);
    run.value = updated;

    if (updated.is_waiting_for_user) {
      await loadLatestForCurrentAgent();
      stopPolling();
      info.value = "Entrega lista para revisión. Aprueba o envía ajustes.";
      return;
    }

    if (updated.status === "COMPLETED") {
      stopPolling();
      info.value = "Pipeline completado.";
      return;
    }

    info.value = "Pipeline en ejecución...";
    startPolling();
  } catch (e) {
    stopPolling();
    error.value = String(e?.message ?? e);
  } finally {
    isPollingTickInFlight.value = false;
    if (showSpinner) loadingRefresh.value = false;
  }
}

async function startRun() {
  error.value = "";
  info.value = "";
  latestArtifact.value = null;
  feedback.value = "";
  stopPolling();

  const text = brief.value.trim();
  if (text.length < 30) {
    error.value = "El brief debe tener al menos ~30 caracteres.";
    return;
  }

  loadingCreate.value = true;
  try {
    run.value = await createRun(text);
    info.value = "Run creado. Iniciando pipeline...";
    startPolling();
    await refreshRun(false);
  } catch (e) {
    error.value = String(e?.message ?? e);
  } finally {
    loadingCreate.value = false;
  }
}

async function approveCurrent() {
  if (!run.value?.id) return;
  error.value = "";
  info.value = "";
  loadingDecision.value = true;

  try {
    run.value = await approveRun(run.value.id);
    latestArtifact.value = null;
    feedback.value = "";
    info.value = "Aprobado. Continuando al siguiente agente...";

    if (!isCompleted.value) {
      startPolling();
      await refreshRun(false);
    }
  } catch (e) {
    error.value = String(e?.message ?? e);
  } finally {
    loadingDecision.value = false;
  }
}

async function rejectCurrent() {
  if (!run.value?.id) return;
  const text = feedback.value.trim();
  if (text.length < 3) {
    error.value = "Debes escribir feedback para reajustar.";
    return;
  }

  error.value = "";
  info.value = "";
  loadingDecision.value = true;

  try {
    run.value = await rejectRun(run.value.id, text);
    latestArtifact.value = null;
    feedback.value = "";
    info.value = "Feedback enviado. Reintentando agente actual...";
    startPolling();
    await refreshRun(false);
  } catch (e) {
    error.value = String(e?.message ?? e);
  } finally {
    loadingDecision.value = false;
  }
}

function downloadArtifactJson() {
  if (!latestArtifact.value) return;
  const content = latestArtifact.value.content ?? latestArtifact.value;
  const artifactOnly =
    content && typeof content === "object" && "artifact" in content
      ? content.artifact
      : content;
  const type = latestArtifact.value.artifact_type ?? currentArtifactType.value ?? "artifact";
  const version = latestArtifact.value.version ?? "v";
  const name = `${run.value?.id ?? "run"}_${type}_v${version}_artifact.json`;

  const blob = new Blob([JSON.stringify(artifactOnly, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function downloadRunArtifactsJson() {
  if (!run.value?.id) return;
  error.value = "";
  info.value = "";
  loadingRefresh.value = true;

  try {
    const exported = await getArtifactsExport(run.value.id);
    const fileName = `${run.value.id}_artifacts_only.json`;
    const blob = new Blob([JSON.stringify(exported, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    info.value = "Se descargaron los artefactos del run (solo artifact).";
  } catch (e) {
    error.value = String(e?.message ?? e);
  } finally {
    loadingRefresh.value = false;
  }
}

function badgeClass(state) {
  return {
    completed: "badge-completed",
    running: "badge-running",
    waiting: "badge-waiting",
    retrying: "badge-retrying",
    current: "badge-current",
    pending: "badge-pending",
  }[state] ?? "badge-pending";
}

onMounted(async () => {
  await loadAgents();
});

onBeforeUnmount(() => {
  stopPolling();
});
</script>

<template>
  <div class="page">
    <header class="header">
      <h1>Orquestador Multiagente</h1>
      <p class="subtitle">Brief inicial + Human-in-the-Loop por entrega.</p>
    </header>

    <section class="panel">
      <label class="label">Brief</label>
      <textarea
        v-model="brief"
        class="textarea"
        rows="8"
        placeholder="Describe el dominio, problema, alcance y objetivos."
      />
      <div class="row">
        <button class="btn-primary" :disabled="loadingCreate || loadingDecision" @click="startRun">
          {{ loadingCreate ? "Creando..." : "Crear Run" }}
        </button>
        <button class="btn" :disabled="!run?.id || loadingRefresh" @click="refreshRun(true)">
          {{ loadingRefresh ? "Actualizando..." : "Refrescar Estado" }}
        </button>
        <button class="btn" :disabled="!run?.id || loadingRefresh" @click="downloadRunArtifactsJson">
          Descargar Artefactos del Run
        </button>
      </div>
    </section>

    <section class="panel meta-grid">
      <div><strong>Run:</strong> {{ runId }}</div>
      <div><strong>Status:</strong> {{ status }}</div>
      <div><strong>Agente actual:</strong> {{ currentAgent?.name ?? "—" }}</div>
      <div><strong>Espera decisión:</strong> {{ isWaitingDecision ? "Sí" : "No" }}</div>
    </section>

    <section v-if="agents.length" class="panel">
      <h2>Pipeline</h2>
      <div class="steps">
        <div v-for="step in stepper" :key="step.slug" class="step">
          <div class="step-title">{{ step.order }}. {{ step.name }}</div>
          <span class="badge" :class="badgeClass(step.state)">{{ step.state }}</span>
        </div>
      </div>
    </section>

    <section v-if="isWaitingDecision" class="panel">
      <h2>Revisión de Entrega</h2>
      <p class="muted">
        Revisa el artefacto de <strong>{{ currentAgent?.name }}</strong> y decide si continúa o se reajusta.
      </p>

      <div class="row">
        <button class="btn-success" :disabled="!canApprove" @click="approveCurrent">
          {{ loadingDecision ? "Enviando..." : "Aprobar y Continuar" }}
        </button>
        <button class="btn" :disabled="!latestArtifact" @click="downloadArtifactJson">
          Descargar JSON
        </button>
      </div>

      <label class="label">Feedback para reajuste</label>
      <textarea
        v-model="feedback"
        class="textarea"
        rows="4"
        placeholder="Describe claramente qué debe corregir el agente actual."
      />
      <div class="row">
        <button class="btn-danger" :disabled="!canReject" @click="rejectCurrent">
          {{ loadingDecision ? "Enviando..." : "Reajustar con Feedback" }}
        </button>
      </div>
    </section>

    <section v-if="latestArtifact" class="panel">
      <h2>Último Artefacto</h2>
      <div class="meta-inline">
        <span><strong>Tipo:</strong> {{ latestArtifact.artifact_type }}</span>
        <span><strong>Versión:</strong> {{ latestArtifact.version }}</span>
        <span><strong>Creado:</strong> {{ latestArtifact.created_at }}</span>
      </div>
      <pre class="pre">{{ JSON.stringify(latestArtifact.content, null, 2) }}</pre>
    </section>

    <p v-if="info" class="info">{{ info }}</p>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<style scoped>
.page {
  max-width: 1040px;
  margin: 24px auto;
  padding: 0 16px 32px;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}

.header h1 {
  margin: 0;
  font-size: 1.6rem;
}

.subtitle {
  margin-top: 6px;
  color: #666;
}

.panel {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid #d8dde6;
  border-radius: 12px;
  background: #f8fbff;
}

.label {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
}

.textarea {
  width: 100%;
  border: 1px solid #c8d0dc;
  border-radius: 10px;
  padding: 10px;
  font-size: 14px;
  box-sizing: border-box;
  background: #fff;
}

.row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
  font-size: 14px;
}

.steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
}

.step {
  border: 1px solid #d0d7e2;
  border-radius: 10px;
  padding: 8px 10px;
  background: #fff;
}

.step-title {
  font-size: 13px;
  margin-bottom: 6px;
}

.badge {
  display: inline-block;
  font-size: 12px;
  border-radius: 999px;
  padding: 2px 8px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.badge-completed {
  background: #dcfce7;
  color: #166534;
}

.badge-running {
  background: #dbeafe;
  color: #1e40af;
}

.badge-waiting {
  background: #fef3c7;
  color: #92400e;
}

.badge-retrying {
  background: #fee2e2;
  color: #991b1b;
}

.badge-current {
  background: #ede9fe;
  color: #5b21b6;
}

.badge-pending {
  background: #eef2f7;
  color: #4b5563;
}

button {
  border: 1px solid #c5cedc;
  border-radius: 10px;
  padding: 8px 12px;
  font-weight: 600;
  cursor: pointer;
  background: #fff;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-primary {
  background: #1d4ed8;
  color: #fff;
  border-color: #1d4ed8;
}

.btn-success {
  background: #0f766e;
  color: #fff;
  border-color: #0f766e;
}

.btn-danger {
  background: #b91c1c;
  color: #fff;
  border-color: #b91c1c;
}

.meta-inline {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  font-size: 13px;
  margin-bottom: 8px;
}

.muted {
  color: #4b5563;
  font-size: 14px;
  margin: 6px 0;
}

.pre {
  margin-top: 8px;
  max-height: 500px;
  overflow: auto;
  border: 1px solid #d3dbe6;
  border-radius: 10px;
  padding: 10px;
  background: #0f172a;
  color: #dbeafe;
  font-size: 12px;
}

.info {
  margin-top: 10px;
  color: #155e75;
}

.error {
  margin-top: 10px;
  color: #b91c1c;
  white-space: pre-wrap;
}

@media (max-width: 640px) {
  .page {
    padding: 0 10px 24px;
  }

  .header h1 {
    font-size: 1.3rem;
  }
}
</style>
