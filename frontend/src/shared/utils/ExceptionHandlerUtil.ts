/**
 * Utilidad para manejo de excepciones con modales.
 * Por ahora es un placeholder; se puede integrar con AppModal cuando exista.
 */
export class ExceptionHandlerUtil {
  /**
   * Maneja una excepción mostrando un modal de error.
   * @param error Error a manejar
   * @param modalRef Referencia al modal (opcional, por ahora solo console.error)
   */
  static handleWithModal(error: unknown, modalRef?: unknown): void {
    const message = error instanceof Error ? error.message : 'Error desconocido'
    console.error('[ExceptionHandlerUtil]', message, error)
    // TODO: Integrar con AppModal cuando esté disponible
    // if (modalRef) {
    //   modalRef.show(message)
    // }
  }
}
