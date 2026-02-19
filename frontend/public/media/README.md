# Media

Carpeta para archivos asociados al chat.

- **Frontend:** al enviar un mensaje, los archivos se guardan en memoria en el store de `src/features/chat/media/` y desde ahí se envían por REST al backend.
- **Backend:** puede usar esta ruta (o una equivalente en el servidor) para guardar los archivos recibidos al subir mensajes.
