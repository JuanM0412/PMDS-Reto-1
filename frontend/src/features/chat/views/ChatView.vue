<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useChat } from '@/features/chat/composables/useChat'
import type { AgentStatus } from '@/features/chat/composables/useChat'
import MermaidDiagramPreview from '@/features/chat/components/MermaidDiagramPreview.vue'
import PseudocodePreview from '@/features/chat/components/PseudocodePreview.vue'
import {
  extractMermaidBlocks,
  extractPseudocodeBlocks,
  toArtifactPreviewText,
  type MermaidBlockInterface,
  type PseudocodeBlockInterface,
} from '@/shared/utils/MermaidArtifactUtil'

const {
  addMessage,
  approveAgent,
  rejectAgent,
  fetchLogs,
  fetchArtifacts,
  fetchArtifactDownload,
  currentMessageUuid,
  agentStatuses,
  pendingApprovalMessage,
  isFlowActive,
} = useChat()

const initialText = ref('')
const showRejectBox = ref(false)
const feedbackText = ref('')
const showLogs = ref(false)
const displayedLogs = ref<string[]>([])
const logsLoading = ref(false)
/** Índices de cuadros (0-5) con panel de logs abierto; pueden ser varios a la vez */
const openLogsBoxIndices = ref<number[]>([])
const boxLogsByIndex = ref<Record<number, string[]>>({})
const boxLogsLoadingByIndex = ref<Record<number, boolean>>({})
/** Índices de cuadros con tabla de artifacts abierta */
const openArtifactsBoxIndices = ref<number[]>([])
const boxArtifactsByIndex = ref<Record<number, { id: string; name: string }[]>>({})
const boxArtifactsLoadingByIndex = ref<Record<number, boolean>>({})
const artifactPreviewByIndex = ref<
  Record<
    number,
    | {
        artifactId: string
        artifactName: string
        blocks: MermaidBlockInterface[]
        pseudocodeBlocks: PseudocodeBlockInterface[]
        payloadPreviewText: string
      }
    | undefined
  >
>({})
const artifactPreviewLoadingByIndex = ref<Record<number, boolean>>({})
const artifactPreviewErrorByIndex = ref<Record<number, string>>({})

/** Modal de vista previa de artefacto */
const artifactModalOpen = ref(false)
const artifactModalLoading = ref(false)
const artifactModalBoxIndex = ref<number | null>(null)
const artifactModalArtifactId = ref<string | null>(null)
const artifactModalContent = ref<{
  artifactName: string
  blocks: MermaidBlockInterface[]
  pseudocodeBlocks: PseudocodeBlockInterface[]
  payloadPreviewText: string
} | null>(null)

const AGENT_NAMES = [
  'Requirements Agent',
  'Inception Agent',
  'Agile Agent',
  'Diagramacion Agent',
  'Pseudocodigo Agent',
  'QA Agent',
]

function getStatusLabel(s: AgentStatus): string {
  return s === 'pending' ? 'PENDING' : s === 'running' ? 'RUNNING' : 'COMPLETED'
}

function getStatusClass(s: AgentStatus): string {
  return `status-${s}`
}

function handleSend() {
  const text = initialText.value.trim()
  if (!text || isFlowActive.value) return
  addMessage(text)
  initialText.value = ''
}

function handleApprove() {
  if (!pendingApprovalMessage.value) return
  approveAgent(pendingApprovalMessage.value.id)
}

function handleReject() {
  showRejectBox.value = true
}

function handleSubmitFeedback() {
  if (!pendingApprovalMessage.value || !feedbackText.value.trim()) return
  rejectAgent(pendingApprovalMessage.value.id, feedbackText.value.trim())
  feedbackText.value = ''
  showRejectBox.value = false
}

function handleCancelFeedback() {
  showRejectBox.value = false
  feedbackText.value = ''
}

async function toggleLogs() {
  if (showLogs.value) {
    showLogs.value = false
    return
  }
  const msg = pendingApprovalMessage.value
  const uuid = currentMessageUuid.value
  if (!msg?.requiresApproval || uuid == null) return
  showLogs.value = true
  displayedLogs.value = []
  logsLoading.value = true
  try {
    displayedLogs.value = await fetchLogs(msg.requiresApproval.agentIndex, uuid)
  } finally {
    logsLoading.value = false
  }
}

function isLogsOpen(boxIndex: number): boolean {
  return openLogsBoxIndices.value.includes(boxIndex)
}

function isArtifactsOpen(boxIndex: number): boolean {
  return openArtifactsBoxIndices.value.includes(boxIndex)
}

async function toggleBoxLogs(boxIndex: number) {
  const uuid = currentMessageUuid.value
  if (uuid == null) return
  if (openLogsBoxIndices.value.includes(boxIndex)) {
    openLogsBoxIndices.value = openLogsBoxIndices.value.filter((j) => j !== boxIndex)
    return
  }
  openLogsBoxIndices.value = [...openLogsBoxIndices.value, boxIndex]
  const step = boxIndex + 1
  boxLogsLoadingByIndex.value = { ...boxLogsLoadingByIndex.value, [boxIndex]: true }
  try {
    const logs = await fetchLogs(step, uuid)
    boxLogsByIndex.value = { ...boxLogsByIndex.value, [boxIndex]: logs }
  } finally {
    boxLogsLoadingByIndex.value = { ...boxLogsLoadingByIndex.value, [boxIndex]: false }
  }
}

async function toggleBoxArtifacts(boxIndex: number) {
  const uuid = currentMessageUuid.value
  if (uuid == null) return
  if (openArtifactsBoxIndices.value.includes(boxIndex)) {
    openArtifactsBoxIndices.value = openArtifactsBoxIndices.value.filter((j) => j !== boxIndex)
    artifactPreviewByIndex.value = { ...artifactPreviewByIndex.value, [boxIndex]: undefined }
    artifactPreviewErrorByIndex.value = { ...artifactPreviewErrorByIndex.value, [boxIndex]: '' }
    return
  }
  openArtifactsBoxIndices.value = [...openArtifactsBoxIndices.value, boxIndex]
  const step = boxIndex + 1
  boxArtifactsLoadingByIndex.value = { ...boxArtifactsLoadingByIndex.value, [boxIndex]: true }
  try {
    const artifacts = await fetchArtifacts(step, uuid)
    boxArtifactsByIndex.value = { ...boxArtifactsByIndex.value, [boxIndex]: artifacts }
  } finally {
    boxArtifactsLoadingByIndex.value = { ...boxArtifactsLoadingByIndex.value, [boxIndex]: false }
  }
}

function isPreviewOpen(boxIndex: number, artifactId: string): boolean {
  return (
    artifactModalOpen.value &&
    artifactModalBoxIndex.value === boxIndex &&
    artifactModalArtifactId.value === artifactId
  )
}

function closeArtifactModal() {
  artifactModalOpen.value = false
  artifactModalContent.value = null
  artifactModalBoxIndex.value = null
  artifactModalArtifactId.value = null
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && artifactModalOpen.value) closeArtifactModal()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

async function handlePreviewArtifact(boxIndex: number, art: { id: string; name: string }) {
  const uuid = currentMessageUuid.value
  if (uuid == null) return

  if (
    artifactModalOpen.value &&
    artifactModalBoxIndex.value === boxIndex &&
    artifactModalArtifactId.value === art.id
  ) {
    closeArtifactModal()
    artifactPreviewByIndex.value = { ...artifactPreviewByIndex.value, [boxIndex]: undefined }
    return
  }

  const step = boxIndex + 1
  artifactPreviewLoadingByIndex.value = { ...artifactPreviewLoadingByIndex.value, [boxIndex]: true }
  artifactPreviewErrorByIndex.value = { ...artifactPreviewErrorByIndex.value, [boxIndex]: '' }
  artifactModalLoading.value = true
  artifactModalContent.value = null
  try {
    const payload = await fetchArtifactDownload(step, uuid, art.id)
    const blocks = extractMermaidBlocks(payload)
    const pseudocodeBlocks = extractPseudocodeBlocks(payload)
    const payloadPreviewText = toArtifactPreviewText(payload)

    const preview = {
      artifactId: art.id,
      artifactName: art.name,
      blocks,
      pseudocodeBlocks,
      payloadPreviewText,
    }
    artifactPreviewByIndex.value = { ...artifactPreviewByIndex.value, [boxIndex]: preview }
    artifactModalContent.value = {
      artifactName: art.name,
      blocks,
      pseudocodeBlocks,
      payloadPreviewText,
    }
    artifactModalBoxIndex.value = boxIndex
    artifactModalArtifactId.value = art.id
    artifactModalOpen.value = true
  } catch {
    artifactPreviewByIndex.value = { ...artifactPreviewByIndex.value, [boxIndex]: undefined }
    artifactPreviewErrorByIndex.value = {
      ...artifactPreviewErrorByIndex.value,
      [boxIndex]: 'No fue posible cargar la vista previa de este artefacto.',
    }
  } finally {
    artifactPreviewLoadingByIndex.value = { ...artifactPreviewLoadingByIndex.value, [boxIndex]: false }
    artifactModalLoading.value = false
  }
}

function sanitizeFileName(name: string): string {
  return name.replace(/[^\w\s.-]/gi, '_').replace(/\s+/g, '_') || 'artifact'
}

async function handleDownloadArtifact(
  boxIndex: number,
  art: { id: string; name: string }
) {
  const uuid = currentMessageUuid.value
  if (uuid == null) return
  const step = boxIndex + 1
  try {
    const json = await fetchArtifactDownload(step, uuid, art.id)
    const blob = new Blob([JSON.stringify(json, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${sanitizeFileName(art.name)}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    // Error ya manejado por el servicio o se puede mostrar un toast
  }
}
</script>

<template>
  <div class="pipeline-view">
    <header class="pipeline-header">
      <h1 class="pipeline-title">Pipeline</h1>
      <p class="pipeline-subtitle">Escribe el mensaje inicial para desencadenar el flujo de agentes.</p>
    </header>

    <section class="initial-message">
      <textarea
        v-model="initialText"
        class="initial-textarea"
        placeholder="Escribe aquí tu mensaje inicial..."
        rows="6"
        :disabled="isFlowActive"
      />
      <button
        type="button"
        class="btn btn-send"
        :disabled="!initialText.trim() || isFlowActive"
        @click="handleSend"
      >
        Enviar
      </button>
    </section>

    <section class="agents-grid">
      <div
        v-for="(name, i) in AGENT_NAMES"
        :key="i"
        class="agent-box"
        :class="getStatusClass(agentStatuses[i] ?? 'pending')"
      >
        <span class="agent-number">{{ i + 1 }}.</span>
        <span class="agent-name">{{ name }}</span>
        <span class="agent-badge" :class="getStatusClass(agentStatuses[i] ?? 'pending')">
          {{ getStatusLabel(agentStatuses[i] ?? 'pending') }}
        </span>
        <template v-if="(agentStatuses[i] ?? 'pending') === 'completed' && currentMessageUuid">
          <div class="box-actions">
            <button
              type="button"
              class="btn btn-logs-inline"
              @click="toggleBoxLogs(i)"
            >
              {{ isLogsOpen(i) ? 'Ocultar logs' : 'Ver logs' }}
            </button>
            <button
              type="button"
              class="btn btn-logs-inline"
              @click="toggleBoxArtifacts(i)"
            >
              {{ isArtifactsOpen(i) ? 'Ocultar artifacts' : 'Ver artifacts' }}
            </button>
          </div>
          <div v-if="isLogsOpen(i)" class="box-logs-block">
            <p v-if="boxLogsLoadingByIndex[i]" class="logs-loading">Cargando logs...</p>
            <pre v-else class="logs-content">{{ (boxLogsByIndex[i] ?? []).join('\n') }}</pre>
          </div>
          <div v-if="isArtifactsOpen(i)" class="box-artifacts-block">
            <p v-if="boxArtifactsLoadingByIndex[i]" class="logs-loading">Cargando artifacts...</p>
            <table v-else class="artifacts-table">
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Vista</th>
                  <th>Descarga</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="art in (boxArtifactsByIndex[i] ?? [])" :key="art.id">
                  <td>{{ art.name }}</td>
                  <td>
                    <button
                      type="button"
                      class="btn btn-preview-inline"
                      @click="handlePreviewArtifact(i, art)"
                    >
                      {{ isPreviewOpen(i, art.id) ? 'Ocultar' : 'Ver' }}
                    </button>
                  </td>
                  <td>
                    <button
                      type="button"
                      class="btn btn-download-inline"
                      @click="handleDownloadArtifact(i, art)"
                    >
                      Descargar
                    </button>
                  </td>
                </tr>
                <tr v-if="!(boxArtifactsByIndex[i] ?? []).length && !boxArtifactsLoadingByIndex[i]">
                  <td colspan="3" class="artifacts-empty">Sin artifacts</td>
                </tr>
              </tbody>
            </table>
            <p v-if="artifactPreviewLoadingByIndex[i]" class="logs-loading">Cargando vista previa...</p>
            <p v-else-if="artifactPreviewErrorByIndex[i]" class="artifacts-empty">
              {{ artifactPreviewErrorByIndex[i] }}
            </p>
          </div>
        </template>
      </div>
    </section>

    <!-- Modal de vista previa de artefacto (un solo modal para todos los agentes) -->
    <Teleport to="body">
      <Transition name="artifact-modal">
        <div
          v-if="artifactModalOpen"
          class="artifact-modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="artifact-modal-title"
          @click.self="closeArtifactModal"
        >
          <div class="artifact-modal-panel">
            <div class="artifact-modal-header">
              <h2 id="artifact-modal-title" class="artifact-modal-title">
                {{ artifactModalContent?.artifactName ?? 'Vista previa' }}
              </h2>
              <button
                type="button"
                class="artifact-modal-close"
                aria-label="Cerrar"
                @click="closeArtifactModal"
              >
                ×
              </button>
            </div>
            <div class="artifact-modal-body">
              <p v-if="artifactModalLoading" class="logs-loading">Cargando vista previa...</p>
              <template v-else-if="artifactModalContent">
                <div
                  v-if="(artifactModalContent.blocks?.length ?? 0) > 0"
                  class="artifact-modal-section"
                >
                  <p class="section-title">Diagramas Mermaid</p>
                  <MermaidDiagramPreview
                    v-for="block in artifactModalContent.blocks"
                    :key="block.key"
                    :title="block.title"
                    :code="block.code"
                  />
                </div>
                <div
                  v-if="(artifactModalContent.pseudocodeBlocks?.length ?? 0) > 0"
                  class="artifact-modal-section"
                >
                  <p class="section-title">Pseudocódigo</p>
                  <PseudocodePreview
                    v-for="block in artifactModalContent.pseudocodeBlocks"
                    :key="`pseudo-${block.key}`"
                    :title="block.title"
                    :code="block.code"
                  />
                </div>
                <div class="artifact-modal-section">
                  <p class="section-title">Contenido del artefacto</p>
                  <pre class="artifact-modal-json">{{ artifactModalContent.payloadPreviewText || 'Sin contenido para mostrar.' }}</pre>
                </div>
              </template>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <template v-if="pendingApprovalMessage">
      <section class="approval-section">
        <div v-if="pendingApprovalMessage.text" class="response-preview">
          {{ pendingApprovalMessage.text }}
        </div>
        <div class="approval-buttons">
          <button type="button" class="btn btn-approve" @click="handleApprove">
            Aprobar
          </button>
          <button type="button" class="btn btn-reject" @click="handleReject">
            Rechazar
          </button>
          <button
            type="button"
            class="btn btn-logs"
            @click="toggleLogs"
          >
            {{ showLogs ? 'Ocultar logs' : 'Ver logs' }}
          </button>
        </div>

        <div v-if="showLogs" class="logs-block">
          <p v-if="logsLoading" class="logs-loading">Cargando logs...</p>
          <pre v-else class="logs-content">{{ displayedLogs.join('\n') }}</pre>
        </div>

        <div v-if="showRejectBox" class="feedback-box">
          <textarea
            v-model="feedbackText"
            class="feedback-textarea"
            placeholder="Escribe tu feedback o corrección..."
            rows="3"
          />
          <div class="feedback-actions">
            <button
              type="button"
              class="btn btn-submit-feedback"
              :disabled="!feedbackText.trim()"
              @click="handleSubmitFeedback"
            >
              Enviar feedback
            </button>
            <button type="button" class="btn btn-cancel" @click="handleCancelFeedback">
              Cancelar
            </button>
          </div>
        </div>
      </section>
    </template>

  </div>
</template>

<style scoped>
.pipeline-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 100vh;
  background: var(--chat-bg);
  padding: 1.5rem 2rem 2rem;
}

.pipeline-header {
  margin-bottom: 1.5rem;
}

.pipeline-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
}

.pipeline-subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.initial-message {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 2rem;
}

.initial-textarea {
  width: 100%;
  padding: 1rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  font-size: 1rem;
  font-family: inherit;
  background: var(--input-bg);
  color: var(--text-primary);
  resize: vertical;
  min-height: 140px;
}

.initial-textarea:focus {
  outline: none;
  border-color: var(--primary);
}

.initial-textarea:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.agents-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.agent-box {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 1rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  background: var(--header-bg);
}

.agent-number {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.agent-name {
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--text-primary);
}

.agent-badge {
  display: inline-block;
  align-self: flex-start;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-pending {
  background: #374151;
  color: #9ca3af;
}

.status-running {
  background: #1e3a8a;
  color: #bfdbfe;
}

.agent-box.status-running .agent-name,
.agent-box.status-running .agent-number {
  color: #bfdbfe;
}

.agent-badge.status-running {
  background: #1d4ed8;
  color: #bfdbfe;
}

.status-completed {
  background: #065f46;
  color: #d1fae5;
}

.agent-box.status-completed .agent-name,
.agent-box.status-completed .agent-number {
  color: #d1fae5;
}

.agent-badge.status-completed {
  background: #047857;
  color: #d1fae5;
}

.box-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.btn-logs-inline {
  padding: 0.35rem 0.6rem;
  font-size: 0.75rem;
  background: rgba(255, 255, 255, 0.15);
  color: inherit;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 0.25rem;
  cursor: pointer;
}

.btn-logs-inline:hover {
  background: rgba(255, 255, 255, 0.25);
}

.box-logs-block {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 0.25rem;
  max-height: 120px;
  overflow: auto;
}

.box-logs-block .logs-loading,
.box-logs-block .logs-content {
  font-size: 0.6875rem;
  margin: 0;
}

.box-logs-block .logs-content {
  font-family: ui-monospace, monospace;
  white-space: pre-wrap;
  word-break: break-word;
}

.box-artifacts-block {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 0.25rem;
  overflow: auto;
}

.box-artifacts-block .logs-loading {
  font-size: 0.6875rem;
  margin: 0;
}

.artifacts-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}

.artifacts-table th,
.artifacts-table td {
  padding: 0.35rem 0.5rem;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.15);
}

.artifacts-table th {
  font-weight: 600;
}

.artifacts-empty {
  color: var(--text-muted);
  font-style: italic;
}

.btn-download-inline {
  padding: 0.25rem 0.5rem;
  font-size: 0.6875rem;
  background: rgba(255, 255, 255, 0.2);
  color: inherit;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 0.25rem;
  cursor: pointer;
}

.btn-download-inline:hover {
  background: rgba(255, 255, 255, 0.3);
}

.btn-preview-inline {
  padding: 0.25rem 0.5rem;
  font-size: 0.6875rem;
  background: rgba(16, 185, 129, 0.25);
  color: #d1fae5;
  border: 1px solid rgba(16, 185, 129, 0.45);
  border-radius: 0.25rem;
  cursor: pointer;
}

.btn-preview-inline:hover {
  background: rgba(16, 185, 129, 0.35);
}

.mermaid-preview-block {
  margin-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.preview-caption {
  margin: 0;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.artifact-section {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.section-title {
  margin: 0;
  font-size: 0.75rem;
  color: #d1d5db;
  font-weight: 600;
}

.artifact-json-preview {
  margin: 0;
  padding: 0.6rem;
  border-radius: 0.375rem;
  background: rgba(255, 255, 255, 0.06);
  color: #d1d5db;
  font-size: 0.6875rem;
  line-height: 1.35;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 280px;
  overflow: auto;
}

.approval-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
  background: var(--header-bg);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
}

.response-preview {
  font-size: 0.9375rem;
  color: var(--text-primary);
  line-height: 1.4;
  max-height: 4em;
  overflow: hidden;
  text-overflow: ellipsis;
}

.approval-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: filter 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-send {
  align-self: flex-start;
  background: var(--primary);
  color: var(--primary-text);
}

.btn-send:hover:not(:disabled) {
  filter: brightness(1.1);
}

.btn-approve {
  background: #10b981;
  color: white;
}

.btn-reject {
  background: #ef4444;
  color: white;
}

.btn-logs {
  background: var(--input-bg);
  color: var(--text-primary);
  border: 1px solid var(--border);
}

.btn-approve:hover,
.btn-reject:hover,
.btn-logs:hover {
  filter: brightness(1.1);
}

.feedback-box {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border);
}

.feedback-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-family: inherit;
  background: var(--input-bg);
  color: var(--text-primary);
  resize: vertical;
}

.feedback-textarea:focus {
  outline: none;
  border-color: var(--primary);
}

.feedback-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-submit-feedback {
  background: var(--primary);
  color: var(--primary-text);
}

.btn-cancel {
  background: var(--input-bg);
  color: var(--text-primary);
  border: 1px solid var(--border);
}

.logs-block {
  padding: 0.75rem 1rem;
  background: var(--input-bg);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  max-height: 200px;
  overflow: auto;
}

.logs-loading {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.logs-content {
  margin: 0;
  font-size: 0.8125rem;
  font-family: ui-monospace, monospace;
  color: var(--text-muted);
  white-space: pre-wrap;
  word-break: break-word;
}

/* Modal de vista previa de artefacto */
.artifact-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
}

.artifact-modal-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 56rem;
  max-height: 90vh;
  border-radius: 0.75rem;
  background: var(--header-bg);
  border: 1px solid var(--border);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.artifact-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.artifact-modal-title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

.artifact-modal-close {
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  font-size: 1.5rem;
  line-height: 1;
  color: var(--text-muted);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 0.375rem;
  cursor: pointer;
}

.artifact-modal-close:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.08);
}

.artifact-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.artifact-modal-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.artifact-modal-section .section-title {
  margin: 0;
  font-size: 0.875rem;
  color: #d1d5db;
  font-weight: 600;
}

.artifact-modal-json {
  margin: 0;
  padding: 1rem;
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.06);
  color: #d1d5db;
  font-size: 0.8125rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow: auto;
}

.artifact-modal-enter-active,
.artifact-modal-leave-active {
  transition: opacity 0.2s ease;
}

.artifact-modal-enter-from,
.artifact-modal-leave-to {
  opacity: 0;
}

.artifact-modal-enter-active .artifact-modal-panel,
.artifact-modal-leave-active .artifact-modal-panel {
  transition: transform 0.2s ease;
}

.artifact-modal-enter-from .artifact-modal-panel,
.artifact-modal-leave-to .artifact-modal-panel {
  transform: scale(0.96);
}
</style>
