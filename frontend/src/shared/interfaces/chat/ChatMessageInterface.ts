/**
 * Tipos del dominio chat (mensajes y aprobación).
 */

export interface ChatMessageInterface {
  id: string
  text: string
  createdAt: Date
  senderId: string
  requiresApproval?: {
    agentIndex: number
    originalMessageId: string
  }
  feedbackPending?: boolean
  agentLogs?: string[]
}
