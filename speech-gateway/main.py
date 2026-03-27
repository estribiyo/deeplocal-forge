import asyncio
import logging
from wyoming.server import AsyncServer, AsyncEventHandler
from wyoming.event import Event

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

class OpenClawHandler(AsyncEventHandler):
    """Esta clase gestiona lo que pasa cuando llega un evento"""
    async def handle_event(self, event: Event) -> bool:
        _LOGGER.debug("Evento recibido: %s", event.type)
        
        # Este es el evento que envía el servidor cuando detecta 'alexa' o 'hey_jarvis'
        if event.type == "detection":
            _LOGGER.info("💀 ¡WAKE WORD DETECTADA! Moviendo calavera...")
            # AQUÍ va tu lógica de motores/luz

        # Cuando el sistema termina de pensar y genera el audio de respuesta
        if event.type == "synthesize":
            _LOGGER.info("🔊 Generando voz de respuesta...")

        # Cuando el audio está listo para enviarse de vuelta a la Orange Pi
        if event.type == "recorded":
             _LOGGER.info("✨ Respuesta enviada a la Calavera.")           
        
        if event.type == "streaming-stopped":
            _LOGGER.info("⏹️ La grabación ha terminado. Enviando a Whisper...")

        return True

async def run_server():
    _LOGGER.info("🚀 Servidor OpenClaw escuchando eventos en puerto 10420")
    # IMPORTANTE: Pasamos la clase 'OpenClawHandler', sin paréntesis.
    server = AsyncServer.from_uri("tcp://0.0.0.0:10420")
    await server.run(OpenClawHandler)

if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass
