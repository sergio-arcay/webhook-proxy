# ------------------------------------------------------------------------------
# Configuración del logger para depuración y seguimiento
# ------------------------------------------------------------------------------
import logging


logging.basicConfig(
    level=logging.DEBUG,  # Nivel DEBUG para trazar el flujo completo
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger("GenericIntegrationServer")
