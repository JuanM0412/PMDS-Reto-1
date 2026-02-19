<script setup lang="ts">
import { ref } from 'vue'
import { useChat } from '@/features/chat/composables/useChat'

const { addMessage } = useChat()
const text = ref('')

function send() {
  const trimmed = text.value.trim()
  if (!trimmed) return
  addMessage(trimmed)
  text.value = ''
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}
</script>

<template>
  <div class="message-input">
    <div class="input-row">
      <textarea
        v-model="text"
        class="textarea"
        placeholder="Escribe un mensaje…"
        rows="1"
        @keydown="onKeydown"
      />
      <button
        type="button"
        class="btn btn-send"
        aria-label="Enviar"
        @click="send"
      >
        Enviar
      </button>
    </div>
  </div>
</template>

<style scoped>
.message-input {
  flex-shrink: 0;
  padding: 0.75rem 1.25rem 1.25rem;
  background: var(--header-bg);
  border-top: 1px solid var(--border);
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
}

.btn {
  flex-shrink: 0;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  font-size: 0.9375rem;
  cursor: pointer;
  background: var(--input-bg);
  color: var(--text-primary);
}

.btn:hover {
  background: var(--hover-bg);
}

.btn-send {
  background: var(--primary);
  color: var(--primary-text);
  border-color: var(--primary);
}

.btn-send:hover {
  filter: brightness(1.05);
}

.textarea {
  flex: 1;
  min-width: 0;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  font-size: 0.9375rem;
  font-family: inherit;
  resize: none;
  min-height: 40px;
  max-height: 120px;
  background: var(--input-bg);
  color: var(--text-primary);
}

.textarea::placeholder {
  color: var(--text-muted);
}

.textarea:focus {
  outline: none;
  border-color: var(--primary);
}
</style>
