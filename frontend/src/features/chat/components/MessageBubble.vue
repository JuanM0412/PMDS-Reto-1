<script setup lang="ts">
import type { ChatMessageInterface } from '@/shared/interfaces/chat/ChatMessageInterface'
import AgentApproval from './AgentApproval.vue'

defineProps<{
  message: ChatMessageInterface
}>()

function formatTime(date: Date): string {
  return new Date(date).toLocaleTimeString('es', {
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div class="bubble" :class="{ own: message.senderId === 'me' }">
    <p v-if="message.text" class="text">{{ message.text }}</p>
    <time class="time">{{ formatTime(message.createdAt) }}</time>
    <AgentApproval
      v-if="message.requiresApproval && !message.feedbackPending"
      :message-id="message.id"
      :agent-index="message.requiresApproval.agentIndex"
      :logs="message.agentLogs ?? []"
    />
  </div>
</template>

<style scoped>
.bubble {
  align-self: flex-start;
  max-width: 85%;
  padding: 0.625rem 0.875rem;
  border-radius: 1rem 1rem 1rem 0;
  background: var(--bubble-other);
  color: var(--text-primary);
}

.bubble.own {
  align-self: flex-end;
  border-radius: 1rem 1rem 0 1rem;
  background: var(--bubble-own);
}

.text {
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
}

.time {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.6875rem;
  opacity: 0.75;
}
</style>
