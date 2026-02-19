<script setup lang="ts">
import { ref } from 'vue'
import { useChat } from '@/features/chat/composables/useChat'

const props = defineProps<{
  messageId: string
  agentIndex: number
  logs: string[]
}>()

const { approveAgent, rejectAgent } = useChat()
const showFeedback = ref(false)
const showLogs = ref(false)
const feedbackText = ref('')

function handleApprove() {
  approveAgent(props.messageId)
}

function handleReject() {
  showFeedback.value = true
}

function toggleLogs() {
  showLogs.value = !showLogs.value
}

function handleSubmitFeedback() {
  if (feedbackText.value.trim()) {
    rejectAgent(props.messageId, feedbackText.value.trim())
    showFeedback.value = false
    feedbackText.value = ''
  }
}

function handleCancelFeedback() {
  showFeedback.value = false
  feedbackText.value = ''
}
</script>

<template>
  <div class="approval">
    <div v-if="!showFeedback" class="approval-buttons">
      <button class="btn btn-approve" @click="handleApprove">✓ Aprobar</button>
      <button class="btn btn-reject" @click="handleReject">✗ Rechazar</button>
      <button
        v-if="logs.length"
        type="button"
        class="btn btn-logs"
        @click="toggleLogs"
      >
        {{ showLogs ? 'Ocultar logs' : 'Ver logs' }}
      </button>
    </div>
    <div v-if="showLogs && logs.length" class="logs-block">
      <pre class="logs-content">{{ logs.join('\n') }}</pre>
    </div>
    <div v-if="showFeedback" class="feedback-form">
      <textarea
        v-model="feedbackText"
        class="feedback-input"
        placeholder="Escribe tu feedback o corrección..."
        rows="3"
      />
      <div class="feedback-buttons">
        <button class="btn btn-submit" @click="handleSubmitFeedback">
          Enviar feedback
        </button>
        <button class="btn btn-cancel" @click="handleCancelFeedback">
          Cancelar
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.approval {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border);
}

.approval-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.logs-block {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: var(--input-bg);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  max-height: 200px;
  overflow: auto;
}

.logs-content {
  margin: 0;
  font-size: 0.75rem;
  font-family: ui-monospace, monospace;
  line-height: 1.4;
  color: var(--text-muted);
  white-space: pre-wrap;
  word-break: break-all;
}

.feedback-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.feedback-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-family: inherit;
  background: var(--input-bg);
  color: var(--text-primary);
  resize: vertical;
}

.feedback-input:focus {
  outline: none;
  border-color: var(--primary);
}

.feedback-buttons {
  display: flex;
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

.btn:hover {
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

.btn-submit {
  background: var(--primary);
  color: var(--primary-text);
}

.btn-cancel {
  background: var(--input-bg);
  color: var(--text-primary);
  border: 1px solid var(--border);
}

.btn-logs {
  background: var(--input-bg);
  color: var(--text-muted);
  border: 1px solid var(--border);
}

.btn-logs:hover {
  color: var(--text-primary);
}
</style>
