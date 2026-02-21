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
  /** Nombre para descarga: REQ-001, INC-001, US-001, TC-001, etc. */
  download_filename: string
}

export interface GetArtifactsResponseInterface {
  artifacts: ChatArtifactInterface[]
}
