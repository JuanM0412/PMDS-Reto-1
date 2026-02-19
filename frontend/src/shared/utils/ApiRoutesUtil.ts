/**
 * Utilidad para rutas base del API y construcción de URLs.
 */

const API_PREFIX = '/api'
const DEFAULT_API_BASE_URL = 'http://localhost:8000'

export const CHAT_ROUTES = {
  step: `${API_PREFIX}/chat/step`,
  logs: `${API_PREFIX}/chat/logs`,
  artifacts: `${API_PREFIX}/chat/artifacts`,
  /** GET step/uuid/id_artifact → descarga el artifact en JSON */
  artifactDownload: `${API_PREFIX}/chat/artifacts/download`,
} as const

export default class ApiRoutesUtil {
  static getBaseUrl(): string {
    return (
      ((import.meta.env.VITE_API_BASE_URL as string) ||
        (import.meta.env.VITE_API_URL as string) ||
        DEFAULT_API_BASE_URL) as string
    ).replace(/\/$/, '')
  }

  /**
   * Devuelve la URL absoluta para una ruta del API.
   */
  static apiUrl(path: string): string {
    const base = ApiRoutesUtil.getBaseUrl()
    const p = path.startsWith('/') ? path : `/${path}`
    return base ? `${base}${p}` : p
  }
}
