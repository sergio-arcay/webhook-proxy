# ------------------------------------------------------------------------------
# Clase GenericIntegrationService: transforma y envía el mensaje según la integración
# ------------------------------------------------------------------------------
from ..integration_manager import IntegrationManager
import requests
import logging
import json


class IntegrationService:
    """
    Servicio genérico que procesa el evento: convierte el payload recibido en un mensaje
    utilizando el formato definido en la configuración y lo envía al destino.
    """

    def __init__(self, integration_manager: IntegrationManager, logger: logging.Logger):
        """
        :param integration_manager: Instancia de IntegrationManager para obtener la configuración.
        :param logger: Objeto logger.
        """
        self.integration_manager = integration_manager
        self.logger = logger

    def generate_message(self, integration: dict, payload: dict) -> str:
        """
        Genera el mensaje a enviar aplicando el formato definido en la integración.
        Extrae del payload las variables necesarias según el evento esperado.

        Para el evento "pull_request", se extraen las siguientes claves:
          - action: Acción realizada.
          - pr_user: Usuario que creó la PR (extraído de payload["pull_request"]["user"]["login"]).
          - repository: Nombre del repositorio (payload["repository"]["name"]).
          - pr_title: Título de la PR (payload["pull_request"]["title"]).

        Para el evento "push", se extraen:
          - pusher: Usuario que realizó el push (payload["pusher"]["name"]).
          - repository: Nombre del repositorio (payload["repository"]["name"]).
          - commit_count: Número de commits (len(payload["commits"])).

        Para otros casos se enviará un resumen del payload.

        :param integration: Configuración de la integración seleccionada.
        :param payload: Payload JSON recibido.
        :return: Cadena de texto con el mensaje formateado.
        """
        self.logger.debug("Generando mensaje para la integración '%s'.", integration.get("name", "sin_nombre"))
        event_name = integration.get("event_name", "")
        if event_name == "pull_request":
            # Extraemos las variables esperadas para un evento de Pull Request
            action = payload.get("action", "actualizó")
            pr_user = payload.get("pull_request", {}).get("user", {}).get("login", "usuario_desconocido")
            repository = payload.get("repository", {}).get("name", "repositorio_desconocido")
            pr_title = payload.get("pull_request", {}).get("title", "sin título")
            format_vars = {
                "action": action,
                "pr_user": pr_user,
                "repository": repository,
                "pr_title": pr_title
            }
        elif event_name == "push":
            # Extraemos las variables para un evento de push
            pusher = payload.get("pusher", {}).get("name", "usuario_desconocido")
            repository = payload.get("repository", {}).get("name", "repositorio_desconocido")
            commit_count = len(payload.get("commits", []))
            format_vars = {
                "pusher": pusher,
                "repository": repository,
                "commit_count": commit_count
            }
        else:
            # En otros casos se envía el JSON completo (o se podrían definir otros mapeos)
            format_vars = {"payload": json.dumps(payload)}

        # Se intenta formatear el mensaje utilizando el formato definido en la configuración.
        try:
            message = integration["message_format"].format(**format_vars)
        except KeyError as e:
            self.logger.error("Falta la clave %s para formatear el mensaje. Se enviará el payload completo.", e)
            message = "Evento recibido: " + json.dumps(payload)
        self.logger.debug("Mensaje generado: %s", message)
        return message

    def send_to_destination(self, integration: dict, message: str) -> requests.Response:
        """
        Envía el mensaje generado al URL destino especificado en la integración.

        :param integration: Configuración de la integración.
        :param message: Mensaje a enviar.
        :return: Objeto Response del requests.post.
        """
        destination_url = integration.get("destination_url")
        payload_data = {"text": message}
        self.logger.debug("Enviando mensaje al destino '%s' con payload: %s", destination_url, payload_data)
        try:
            response = requests.post(destination_url, json=payload_data)
            self.logger.debug("Respuesta del destino: %s", response.text)
            return response
        except Exception as e:
            self.logger.exception("Error al enviar mensaje al destino '%s': %s", destination_url, str(e))
            raise e

    def process_event(self, secret: str, payload: dict) -> requests.Response:
        """
        Orquesta el procesamiento del evento. Se obtiene la configuración de la integración,
        se genera el mensaje formateado y se envía al destino.

        :param secret: Valor secreto enviado en el header "X-Integration-Secret".
        :param payload: Payload JSON recibido del origen.
        :return: Objeto Response tras enviar el mensaje.
        :raises ValueError: Si no se encuentra una integración válida.
        """
        self.logger.debug("Procesando evento con secret '%s' y payload: %s", secret, payload)
        integration = self.integration_manager.get_integration(secret, payload)
        if integration is None:
            raise ValueError("No se encontró integración válida para el secret proporcionado.")
        message = self.generate_message(integration, payload)
        response = self.send_to_destination(integration, message)
        return response
