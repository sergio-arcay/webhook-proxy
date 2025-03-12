# ------------------------------------------------------------------------------
# Clase IntegrationManager: carga y gestiona las configuraciones definidas en YAML
# ------------------------------------------------------------------------------
from ..logger import logger
import yaml


class IntegrationManager:
    """
    Gestiona la carga y búsqueda de integraciones definidas en el fichero YAML.
    """

    def __init__(self, config_filepath: str):
        """
        Inicializa el gestor cargando la configuración de integraciones.

        :param config_filepath: Ruta al fichero YAML con la configuración.
        """
        try:
            with open(config_filepath, "r") as f:
                self.config = yaml.safe_load(f)
            logger.info("Archivo de integraciones '%s' cargado exitosamente.", config_filepath)
        except Exception as e:
            logger.exception("Error al cargar el fichero de integraciones '%s': %s", config_filepath, str(e))
            # Si falla la carga, se inicializa con una lista vacía
            self.config = {"integrations": []}

    def get_integration(self, secret: str, payload: dict) -> dict:
        """
        Busca la configuración de integración que coincide con el *secret* enviado en la petición,
        y que se espere que procese el tipo de evento recibido en el payload.

        La comparación se realiza de la siguiente forma:
          - Se recorre la lista de integraciones y se consideran solo aquellas cuyo 'secret' coincide.
          - Según el valor de 'event_name' definido:
              • Para "pull_request": se requiere que el payload incluya la llave "pull_request".
              • Para "push": se requiere que el payload incluya la llave "commits".
              • Para otros casos, se busca que el valor de 'event_name' aparezca en el payload.

        :param secret: Valor secreto enviado en el header "X-Integration-Secret".
        :param payload: Payload JSON recibido en la petición.
        :return: Diccionario con la configuración de la integración que corresponde.
        :raises ValueError: Si se detectan múltiples coincidencias.
        """
        candidatos = []
        for integ in self.config.get("integrations", []):
            if integ.get("secret") != secret:
                continue  # No coincide el secret
            event_name = integ.get("event_name", "")
            # Verificamos según el tipo de evento definido
            if event_name == "pull_request":
                if "pull_request" in payload:
                    candidatos.append(integ)
            elif event_name == "push":
                if "commits" in payload:
                    candidatos.append(integ)
            else:
                # Si se definió otro nombre, se busca directamente si esa clave existe en el payload.
                if event_name in payload:
                    candidatos.append(integ)
        if len(candidatos) == 0:
            logger.error("No se encontró configuración de integración para el secret '%s' y payload recibido.", secret)
            return None
        elif len(candidatos) > 1:
            logger.error("Múltiples configuraciones de integración coinciden para el secret '%s'.", secret)
            raise ValueError("Se encontraron múltiples integraciones para el secret proporcionado.")
        logger.debug("Integración encontrada: %s", candidatos[0])
        return candidatos[0]
