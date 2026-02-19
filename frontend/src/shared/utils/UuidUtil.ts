/**
 * Utilidad para generación y validación de UUID v4 (RFC 4122).
 */
export default class UuidUtil {
  /**
   * Genera un UUID v4.
   * Usa crypto.randomUUID() si está disponible; si no, genera uno compatible.
   */
  static generate(): string {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID()
    }
    const hex = '0123456789abcdef'
    const randomHex = (n: number) =>
      Array.from(crypto.getRandomValues(new Uint8Array(n)))
        .map((b) => hex[b % 16])
        .join('')
    return [
      randomHex(8),
      randomHex(4),
      '4' + randomHex(3),
      hex[8 + ((crypto.getRandomValues(new Uint8Array(1))[0] ?? 0) % 4)] + randomHex(3),
      randomHex(12),
    ].join('-')
  }

  /**
   * Comprueba si una cadena tiene formato UUID v4.
   */
  static isUuid(value: string): boolean {
    const uuidV4Regex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
    return uuidV4Regex.test(value)
  }
}
