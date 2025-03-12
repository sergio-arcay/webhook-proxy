#!/usr/bin/env python3
"""
Servidor Flask para integrar webhooks de origen (por ejemplo, Gitea) y enviarlos
transformados a destinos (por ejemplo, Google Chat), utilizando una configuración
definida en un fichero YAML (integrations.yml).

La configuración define para cada integración:
  - name: Nombre identificativo de la integración.
  - source_url: URL origen (opcional o informativo).
  - destination_url: URL destino para enviar el mensaje (por ejemplo, el webhook de Google Chat).
  - event_name: Nombre del evento esperado en el origen, por ejemplo "pull_request" ó "push".
  - message_format: Formato de string con palabras clave delimitadas con llaves, por ejemplo:
      "PR {action} por el usuario {pr_user} en el repositorio {repository} – Título: {pr_title}"
  - secret: Valor secreto que debe acompañar la petición (en el header "X-Integration-Secret").

La idea es que este fichero YAML defina todo lo necesario para configurar la integración.
"""
from ..logger import logger
from services.integration_service import IntegrationService
from .integration_manager import IntegrationManager
from flask import Flask, request


# ------------------------------------------------------------------------------
# Inicialización de la aplicación Flask y servicios
# ------------------------------------------------------------------------------

# Cargamos la configuración de integraciones desde el fichero YAML.
INTEGRATIONS_CONFIG_FILE = "integrations.yml"
integration_manager = IntegrationManager(INTEGRATIONS_CONFIG_FILE)
integration_service = IntegrationService(integration_manager, logger)

# Creamos la aplicación Flask.
app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """
    Endpoint para recibir eventos del origen.
    Se espera:
      - Un header "X-Integration-Secret" con el secret definido en el fichero de integraciones.
      - Un payload JSON con la estructura del evento (por ejemplo, de Gitea).

    El endpoint procesa el evento transformándolo según la configuración y enviándolo
    al destino definido (por ejemplo, Google Chat).
    """
    logger.debug("Nuevo request recibido en /webhook.")

    # Extraer el secret de la petición del header de Authorization como Bearer Token
    secret = request.headers.get('Authorization')
    if not secret:
        logger.error("Falta el header 'Authorization'.")
        return "Falta el header 'Authorization'.", 401
    # Elimina el Bearer del token
    secret = secret.replace("Bearer ", "")

    # Extraer el payload JSON
    payload = request.get_json()
    if not payload:
        logger.error("Payload JSON inválido o ausente.")
        return "Payload JSON inválido o ausente.", 400

    logger.debug("Secret recibido: %s", secret)
    logger.debug("Payload recibido: %s", payload)

    # Procesamos el evento (transformación y envío)
    try:
        response = integration_service.process_event(secret, payload)
        if response.ok:
            logger.info("Mensaje enviado exitosamente al destino.")
        else:
            logger.error("Error al enviar mensaje. Código: %s, Respuesta: %s",
                         response.status_code, response.text)
        return "Mensaje reenviado exitosamente.", response.status_code
    except Exception as e:
        logger.exception("Error durante el procesamiento del evento.")
        return f"Error procesando el evento: {str(e)}", 500


# ------------------------------------------------------------------------------
# Arranque de la aplicación Flask
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    # Se configura el servidor para escuchar en todas las interfaces en el puerto 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
