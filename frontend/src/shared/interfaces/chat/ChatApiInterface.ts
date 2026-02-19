/**
 * Tipos de la API del chat (POST step, GET logs).
 */

export interface PostStepRequestInterface {
  step: number
  uuid: string
  context: string
  is_feedback: boolean
}

/* Modificar segun la respuesta del back */

export interface PostStepResponseInterface {
  message: string
} 

export interface GetLogsResponseInterface {
  logs: string[]
}

export interface ChatArtifactInterface {
  id: string
  name: string
}

export interface GetArtifactsResponseInterface {
  artifacts: ChatArtifactInterface[]
}
