/**
 * Clase base para servicios de API.
 * Proporciona el método makeRequest para realizar llamadas HTTP.
 */
export class BaseService {
  /**
   * Realiza una petición HTTP.
   * @param url URL completa de la petición
   * @param useJsonParser Si es true, parsea la respuesta como JSON
   * @param method Método HTTP (GET, POST, PUT, DELETE, etc.)
   * @param body Cuerpo de la petición (se serializa a JSON si es objeto)
   * @param headers Headers adicionales
   */
  protected async makeRequest<T>(
    url: string,
    useJsonParser = true,
    method: string = 'GET',
    body?: unknown,
    headers?: Record<string, string>
  ): Promise<T> {
    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
    }

    if (body) {
      options.body = typeof body === 'string' ? body : JSON.stringify(body)
    }

    const response = await fetch(url, options)

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    if (useJsonParser) {
      return response.json() as Promise<T>
    }

    return response.text() as Promise<T>
  }
}
