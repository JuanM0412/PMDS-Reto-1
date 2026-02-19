import { BaseService } from '@/shared/services/BaseService'
import type {
  PostStepRequestInterface,
  PostStepResponseInterface,
  GetLogsResponseInterface,
  GetArtifactsResponseInterface,
} from '@/shared/interfaces/chat/ChatApiInterface'
import ApiRoutesUtil, { CHAT_ROUTES } from '@/shared/utils/ApiRoutesUtil'

const REST_ROUND_TRIP_DELAY_MS = 500

const AGENT_LABELS: Record<1 | 2 | 3 | 4 | 5 | 6, string> = {
  1: 'Agente 1',
  2: 'Agente 2',
  3: 'Agente 3',
  4: 'Agente 4',
  5: 'Agente 5',
  6: 'Agente 6',
}

class ChatService extends BaseService {
  /**
   * POST step: ejecuta el agente del paso indicado.
   * Parametros: step, uuid, context, is_feedback.
   */
  async postStep(
    step: 1 | 2 | 3 | 4 | 5 | 6,
    uuid: string,
    context: string,
    is_feedback: boolean
  ): Promise<{ message: string }> {
    await new Promise((r) => setTimeout(r, REST_ROUND_TRIP_DELAY_MS))
    const url = ApiRoutesUtil.apiUrl(CHAT_ROUTES.step)
    const body: PostStepRequestInterface = { step, uuid, context, is_feedback }

    try {
      const data = await this.makeRequest<PostStepResponseInterface>(url, true, 'POST', body)
      return { message: data.message }
    } catch {
      return {
        message: `${AGENT_LABELS[step]}: error al procesar el paso`,
      }
    }
  }

  /**
   * GET logs: obtiene los logs del agente para el step y uuid dados.
   */
  async getLogs(step: number, uuid: string): Promise<string[]> {
    const url = `${ApiRoutesUtil.apiUrl(CHAT_ROUTES.logs)}?step=${step}&uuid=${encodeURIComponent(uuid)}`
    try {
      const data = await this.makeRequest<GetLogsResponseInterface>(url, true, 'GET')
      return data.logs ?? []
    } catch {
      return []
    }
  }

  /**
   * GET artifacts: obtiene los artifacts del agente para el step y uuid dados.
   */
  async getArtifacts(step: number, uuid: string): Promise<{ id: string; name: string }[]> {
    const url = `${ApiRoutesUtil.apiUrl(CHAT_ROUTES.artifacts)}?step=${step}&uuid=${encodeURIComponent(uuid)}`
    try {
      const data = await this.makeRequest<GetArtifactsResponseInterface>(url, true, 'GET')
      return data.artifacts ?? []
    } catch {
      return []
    }
  }

  /**
   * GET artifact download: obtiene el contenido JSON del artifact por step, uuid e id.
   */
  async getArtifactDownload(
    step: number,
    uuid: string,
    artifactId: string
  ): Promise<Record<string, unknown>> {
    const url = `${ApiRoutesUtil.apiUrl(CHAT_ROUTES.artifactDownload)}?step=${step}&uuid=${encodeURIComponent(uuid)}&id=${encodeURIComponent(artifactId)}`
    const data = await this.makeRequest<Record<string, unknown>>(url, true, 'GET')
    return data ?? {}
  }
}

export default new ChatService()
