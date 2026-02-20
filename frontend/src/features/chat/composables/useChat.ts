import { ref, type Ref, computed } from 'vue'
import type { ChatMessageInterface } from '@/shared/interfaces/chat/ChatMessageInterface'
import UuidUtil from '@/shared/utils/UuidUtil'
import ChatService from '@/features/chat/services/ChatService'

export type AgentStatus = 'pending' | 'running' | 'completed'

function createId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

const INITIAL_AGENT_STATUSES: AgentStatus[] = ['pending', 'pending', 'pending', 'pending', 'pending', 'pending']

const messages: Ref<ChatMessageInterface[]> = ref([])
const currentMessageUuid = ref<string | null>(null)
const currentAgentIndex = ref<number>(0)
const currentOriginalMessageId = ref<string | null>(null)
const agentStatuses = ref<AgentStatus[]>([...INITIAL_AGENT_STATUSES])
const isProcessingNext = ref(false)

function pushBotMessage(
  text: string,
  agentIndex: number,
  originalMessageId: string
) {
  const reply: ChatMessageInterface = {
    id: createId(),
    text,
    createdAt: new Date(),
    senderId: 'bot',
    requiresApproval: {
      agentIndex,
      originalMessageId,
    },
  }
  messages.value.push(reply)
}

export function useChat() {
  async function processNextAgent() {
    if (isProcessingNext.value) return
    if (!currentMessageUuid.value || !currentOriginalMessageId.value)
      return

    const nextIndex = (currentAgentIndex.value + 1) as 1 | 2 | 3 | 4 | 5 | 6
    if (nextIndex > 6) {
      currentAgentIndex.value = 0
      currentOriginalMessageId.value = null
      return
    }

    isProcessingNext.value = true
    currentAgentIndex.value = nextIndex
    agentStatuses.value[nextIndex - 1] = 'running'

    // Build context from the previous agent's artifacts
    let context = ''
    const prevStep = nextIndex - 1
    if (prevStep >= 1 && currentMessageUuid.value) {
      try {
        const artifacts = await ChatService.getArtifacts(prevStep, currentMessageUuid.value)
        const artifactContents: Record<string, unknown> = {}
        for (const artifact of artifacts) {
          const content = await ChatService.getArtifactDownload(
            prevStep,
            currentMessageUuid.value,
            artifact.id,
          )
          artifactContents[artifact.id] = content
        }
        if (Object.keys(artifactContents).length > 0) {
          context = JSON.stringify(artifactContents)
        }
      } catch {
        // proceed without context if artifact fetch fails
      }
    }

    try {
      const result = await ChatService.postStep(
        nextIndex,
        currentMessageUuid.value,
        context,
        false,
      )
      agentStatuses.value[nextIndex - 1] = 'completed'
      pushBotMessage(result.message, nextIndex, currentOriginalMessageId.value)
    } finally {
      isProcessingNext.value = false
    }
  }

  async function approveAgent(messageId: string) {
    const message = messages.value.find((m) => m.id === messageId)
    if (!message?.requiresApproval) return

    message.requiresApproval = undefined
    await processNextAgent()
  }

  async function rejectAgent(messageId: string, feedback: string) {
    const message = messages.value.find((m) => m.id === messageId)
    if (!message?.requiresApproval) return

    const { agentIndex, originalMessageId } = message.requiresApproval
    if (!currentMessageUuid.value) return

    message.feedbackPending = true

    agentStatuses.value[agentIndex - 1] = 'running'
    const result = await ChatService.postStep(
      agentIndex as 1 | 2 | 3 | 4 | 5 | 6,
      currentMessageUuid.value,
      feedback,
      true
    )
    agentStatuses.value[agentIndex - 1] = 'completed'

    const correctedMessage: ChatMessageInterface = {
      id: createId(),
      text: result.message,
      createdAt: new Date(),
      senderId: 'bot',
      requiresApproval: {
        agentIndex,
        originalMessageId,
      },
    }
    messages.value.push(correctedMessage)
    message.requiresApproval = undefined
  }

  async function addMessage(text: string) {
    const messageUuid = UuidUtil.generate()
    const message: ChatMessageInterface = {
      id: createId(),
      text: text.trim(),
      createdAt: new Date(),
      senderId: 'me',
    }
    messages.value.push(message)

    agentStatuses.value = [...INITIAL_AGENT_STATUSES]
    currentMessageUuid.value = messageUuid
    currentOriginalMessageId.value = message.id
    currentAgentIndex.value = 0

    agentStatuses.value[0] = 'running'
    const result = await ChatService.postStep(1, messageUuid, text.trim(), false)
    agentStatuses.value[0] = 'completed'
    pushBotMessage(result.message, 1, message.id)
    currentAgentIndex.value = 1
  }

  async function fetchLogs(step: number, uuid: string): Promise<string[]> {
    return ChatService.getLogs(step, uuid)
  }

  async function fetchArtifacts(step: number, uuid: string): Promise<{ id: string; name: string }[]> {
    return ChatService.getArtifacts(step, uuid)
  }

  async function fetchArtifactDownload(
    step: number,
    uuid: string,
    artifactId: string
  ): Promise<Record<string, unknown>> {
    return ChatService.getArtifactDownload(step, uuid, artifactId)
  }

  const pendingApprovalMessage = computed(() =>
    messages.value.find((m) => m.senderId === 'bot' && m.requiresApproval && !m.feedbackPending)
  )

  const isFlowActive = computed(() => !!currentMessageUuid.value)

  return {
    messages,
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
  }
}
