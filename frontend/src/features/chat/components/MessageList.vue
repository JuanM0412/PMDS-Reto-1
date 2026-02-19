<script setup lang="ts">
import { useChat } from '@/features/chat/composables/useChat'
import MessageBubble from './MessageBubble.vue'

const { messages } = useChat()
</script>

<template>
  <div class="message-list" ref="listRef">
    <div v-if="messages.length === 0" class="empty-state">
      <p>No hay mensajes aún.</p>
      <p class="empty-hint">Escribe algo o adjunta un archivo para empezar.</p>
    </div>
    <MessageBubble
      v-for="msg in messages"
      :key="msg.id"
      :message="msg"
    />
  </div>
</template>

<style scoped>
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  color: var(--text-muted);
  font-size: 0.9375rem;
}

.empty-hint {
  font-size: 0.8125rem;
  opacity: 0.85;
}
</style>
