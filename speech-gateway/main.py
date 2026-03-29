"""
speech-gateway/main.py — Multi-satellite con descubrimiento Zeroconf automático
=================================================================================

PROBLEMA RESUELTO
-----------------
No hay IPs hardcodeadas. No importa cuántos satellites haya ni qué IP tengan.
Cualquier Orange Pi (o cualquier dispositivo) que ejecute wyoming-satellite
y esté en la misma red será descubierto y gestionado automáticamente.

ARQUITECTURA
------------
  ┌─────────────────────────────────────────────────────────────────┐
  │  speech-gateway (este script)                                   │
  │                                                                 │
  │  ① Zeroconf escucha _wyoming._tcp.local. en la red             │
  │     → Detecta cualquier satellite que aparezca o desaparezca   │
  │                                                                 │
  │  ② Por cada satellite descubierto → lanza SatelliteSession     │
  │     → Se conecta como cliente a satellite:puerto               │
  │     → Handshake: envía Info + RunSatellite                     │
  │     → Recibe AudioChunks → VAD → STT → LLM → TTS → responde   │
  │     → Si el satellite desconecta → sesión termina limpiamente  │
  │                                                                 │
  │  ③ Servidor de eventos en :10420 (notificaciones one-way)      │
  │     → detection, streaming-started → mueve la calavera/LEDs    │
  │     → NUNCA llega audio aquí                                    │
  └─────────────────────────────────────────────────────────────────┘

PROTOCOLO WYOMING (flujo real)
------------------------------
  El satellite ES el servidor (escucha en su puerto, por defecto 10700/10721/...).
  Este script ES el cliente que se conecta a él.

  Conexión →
    [satellite envía Describe, opcional]
    ← script responde Info (capacidades ASR+TTS)
    ← script envía RunSatellite
  Wake word detectada:
    → satellite envía RunPipeline
    → satellite envía AudioStart + AudioChunks (audio infinito)
  VAD server-side detecta silencio:
    → script procesa: Whisper STT → Ollama LLM → Coqui TTS
    → script envía Transcript + AudioStart + AudioChunks + AudioStop
    → satellite reproduce el audio por aplay
    → satellite envía Transcript (confirmación)
    ← script envía RunSatellite (listo para el siguiente wake word)
"""

import asyncio
import io
import logging
import os
import random
import socket
import wave
from typing import Dict, Optional

import requests
import webrtcvad
from zeroconf import ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.asr import Transcript
from wyoming.client import AsyncClient
from wyoming.event import Event
from wyoming.info import (
    AsrModel, AsrProgram, Attribution,
    Describe, Info, TtsProgram, TtsVoice,
)
from wyoming.pipeline import RunPipeline
from wyoming.satellite import RunSatellite
from wyoming.server import AsyncEventHandler, AsyncServer

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────────────────────
WHISPER_URL   = os.getenv("WHISPER_URL",       "http://whisper:9000/asr")
OLLAMA_URL    = os.getenv("OLLAMA_URL",         "http://ollama:11434")
COQUI_URL     = os.getenv("COQUI_URL",          "http://coqui-tts:5002")
DEFAULT_MODEL = os.getenv("DEFAULT_LLM_MODEL",  "qwen2.5:7b-instruct")
EVENT_URI     = os.getenv("EVENT_URI",          "tcp://0.0.0.0:10420")

WYOMING_SERVICE_TYPE = "_wyoming._tcp.local."

# ── Parámetros de audio ───────────────────────────────────────────────────────
SAMPLE_RATE  = 16000
SAMPLE_WIDTH = 2
CHANNELS     = 1

# ── VAD server-side ───────────────────────────────────────────────────────────
VAD_FRAME_MS        = 20
VAD_FRAME_SAMPLES   = int(SAMPLE_RATE * VAD_FRAME_MS / 1000)  # 320
VAD_FRAME_BYTES     = VAD_FRAME_SAMPLES * SAMPLE_WIDTH          # 640
VAD_AGGRESSIVENESS  = 2    # 0–3. Sube a 3 en entornos ruidosos.
VAD_SILENCE_FRAMES  = 40   # 20 × 20ms = 400ms de silencio → fin de frase
VAD_MAX_RECORD_SECS = 10   # timeout si el usuario no habla tras la wake word

# ── Modo conversación ─────────────────────────────────────────────────────────
CONVERSATION_TIMEOUT_SECS = 45   # segundos sin actividad → despedida y reset
CONVERSATION_MAX_TURNS    = 10   # turnos máximos de historial enviados a Ollama

CONVERSATION_GOODBYE = "Ha sido un placer. Hasta pronto."

# Frases de saludo al detectar wake word (se elige una al azar).
# Su duración actúa de período de gracia natural antes de escuchar.
GREETINGS = [
    "Dime.",
    "Te escucho.",
    "¿Qué necesitas?",
    "Aquí estoy.",
    "A tus órdenes.",
    "Cuéntame.",
    "Soy todo oídos.",
]

# ── Capacidades que anunciamos al satellite ───────────────────────────────────
_GATEWAY_INFO = Info(
    asr=[AsrProgram(
        name="speech-gateway",
        description="Whisper ASR via speech-gateway",
        attribution=Attribution(name="speech-gateway", url=""),
        installed=True,
        version="1.0",
        models=[AsrModel(
            name="whisper",
            description="Whisper ASR",
            attribution=Attribution(name="OpenAI", url=""),
            installed=True,
            version="1.0",
            languages=["es"],
        )],
    )],
    tts=[TtsProgram(
        name="speech-gateway",
        description="Coqui TTS via speech-gateway",
        attribution=Attribution(name="speech-gateway", url=""),
        installed=True,
        version="1.0",
        voices=[TtsVoice(
            name="default",
            description="Default voice",
            attribution=Attribution(name="Coqui", url=""),
            installed=True,
            version="1.0",
            languages=["es"],
        )],
    )],
)


# ── Helpers HTTP (síncronos → run_in_executor) ────────────────────────────────

def transcribe_with_whisper(pcm_bytes: bytes) -> Optional[str]:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_bytes)
    buf.seek(0)
    try:
        resp = requests.post(
            WHISPER_URL,
            params={"language": "es", "output": "txt"},
            files={"audio_file": ("audio.wav", buf, "audio/wav")},
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.text.strip()
        _LOGGER.info("📝 Transcripción: %s", text)
        return text
    except Exception as exc:
        _LOGGER.error("❌ Whisper error: %s", exc)
        return None


def ask_ollama(messages: list) -> Optional[str]:
    """
    Llama a Ollama con historial completo de conversación.
    messages = lista de {"role": "user"|"assistant", "content": "..."}
    """
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": DEFAULT_MODEL,
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Eres Calavera, un asistente de voz conciso y amigable. "
                            "Responde siempre en español, en 1-3 frases cortas y naturales. "
                            "Recuerda el contexto de la conversación."
                        ),
                    }
                ] + messages,
            },
            timeout=60,
        )
        resp.raise_for_status()
        answer = resp.json()["message"]["content"].strip()
        _LOGGER.info("🤖 LLM: %s", answer)
        return answer
    except Exception as exc:
        _LOGGER.error("❌ Ollama error: %s", exc)
        return None


def synthesize_with_coqui(text: str) -> Optional[bytes]:
    try:
        resp = requests.get(
            f"{COQUI_URL}/api/tts",
            params={"text": text},
            timeout=30,
        )
        resp.raise_for_status()
        _LOGGER.info("🔊 TTS generado (%d bytes)", len(resp.content))
        return resp.content
    except Exception as exc:
        _LOGGER.error("❌ Coqui TTS error: %s", exc)
        return None


# ── Sesión con un satellite concreto ──────────────────────────────────────────

class SatelliteSession:
    """
    Gestiona la conexión completa con un satellite Wyoming.
    Se instancia una vez por satellite descubierto.
    Si la conexión cae, el SatelliteManager la relanza automáticamente.
    """

    def __init__(self, name: str, host: str, port: int) -> None:
        self.name  = name
        self.host  = host
        self.port  = port
        self._uri  = f"tcp://{host}:{port}"
        self._vad  = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self._reset_audio_state()
        self._reset_conversation()
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        """Señaliza a la sesión que debe terminar (satellite desapareció)."""
        self._stop_event.set()

    def _reset_audio_state(self) -> None:
        self._recording       = False
        self._leftover        = bytearray()
        self._speech_buffer   = bytearray()
        self._silence_count   = 0
        self._speech_detected = False
        self._timeout_task: Optional[asyncio.Task] = None
        # _busy: True mientras hay un saludo o pipeline en curso.
        # Bloquea RunPipeline adicionales hasta que el ciclo complete.
        if not hasattr(self, '_busy'):
            self._busy = False
        if not hasattr(self, '_greet_task'):
            self._greet_task: Optional[asyncio.Task] = None
        if not hasattr(self, '_pipeline_task'):
            self._pipeline_task: Optional[asyncio.Task] = None

    def _reset_conversation(self) -> None:
        """Borra el historial y cancela el timer de conversación."""
        self._conversation: list = []          # historial de mensajes para Ollama
        self._in_conversation: bool = False    # True mientras hay conversación activa
        if getattr(self, "_conv_timeout_task", None):
            self._conv_timeout_task.cancel()
        self._conv_timeout_task: Optional[asyncio.Task] = None

    # ── Loop de sesión ────────────────────────────────────────────────────────

    async def run(self) -> None:
        """Mantiene la conexión con el satellite, reconectando si cae."""
        _LOGGER.info("🛰️  [%s] Iniciando sesión con %s", self.name, self._uri)
        retry_delay = 3
        while not self._stop_event.is_set():
            try:
                await self._connect_and_run()
                retry_delay = 3  # reset tras conexión exitosa
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                _LOGGER.warning(
                    "⚠️  [%s] Conexión perdida (%s) — reconectando en %ds",
                    self.name, exc, retry_delay,
                )
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)  # backoff hasta 30s
        _LOGGER.info("🔌 [%s] Sesión terminada", self.name)

    async def _connect_and_run(self) -> None:
        client = AsyncClient.from_uri(self._uri)
        await client.connect()
        _LOGGER.info("✅ [%s] Conectado", self.name)
        self._reset_audio_state()
        self._reset_conversation()

        try:
            # Handshake: verificar que es satellite y arrancar
            if not await self._handshake(client):
                # No es un satellite Wyoming — no reintentar
                self._stop_event.set()
                return

            # Loop de eventos
            while not self._stop_event.is_set():
                try:
                    event = await asyncio.wait_for(client.read_event(), timeout=2.0)
                except asyncio.TimeoutError:
                    continue

                if event is None:
                    _LOGGER.warning("⚠️  [%s] Satellite cerró la conexión", self.name)
                    break

                await self._handle_event(event, client)
        finally:
            await client.disconnect()

    async def _handshake(self, client: AsyncClient) -> bool:
        """
        Handshake Wyoming correcto (igual que Home Assistant):

          1. Nosotros  → Describe       (pedimos capacidades al satellite)
          2. Satellite → Info           (responde con su Info, satellite != None)
          3. Nosotros  → RunSatellite   (arranca en modo wake word)

        Si Info.satellite es None es otro servicio Wyoming → termina sin reintentar.
        """
        # Paso 1: preguntar capacidades
        await client.write_event(Describe().event())

        # Paso 2: leer Info del satellite y verificar que es un satellite real
        try:
            event = await asyncio.wait_for(client.read_event(), timeout=5.0)
        except asyncio.TimeoutError:
            _LOGGER.warning("[%s] Sin respuesta a Describe — abortando", self.name)
            return False

        if event is None or not Info.is_type(event.type):
            _LOGGER.warning("[%s] Respuesta inesperada al Describe: %s", self.name,
                            event.type if event else None)
            return False

        satellite_info = Info.from_event(event)
        if satellite_info.satellite is None:
            _LOGGER.info("[%s] ⏭️  No es satellite Wyoming (sin campo satellite en Info)",
                         self.name)
            return False

        _LOGGER.info("[%s] 🛰️  Satellite: %s", self.name, satellite_info.satellite.name)

        # Paso 3: arrancar en modo wake word
        await client.write_event(RunSatellite().event())
        _LOGGER.info("[%s] ▶️  RunSatellite enviado — esperando wake word", self.name)
        return True

    # ── Gestión de eventos del satellite ─────────────────────────────────────

    async def _handle_event(self, event: Event, client: AsyncClient) -> None:
        _LOGGER.debug("[%s] ← %s", self.name, event.type)

        if Describe.is_type(event.type):
            # Durante el pipeline el satellite no manda Describe,
            # pero si llega respondemos con nuestras capacidades
            await client.write_event(_GATEWAY_INFO.event())
            return  # no procesar más este evento

        elif RunPipeline.is_type(event.type):
            # Wake word detectada — el satellite empieza a mandarnos AudioChunks.
            # NOTA: el satellite NO manda AudioStart antes de los chunks.
            p = RunPipeline.from_event(event)

            # Guard: si ya hay un saludo o pipeline en curso, ignorar.
            # Evita que el altavoz retroalimente al micro y dispare una segunda
            # detección de wake word mientras Calavera está hablando.
            if getattr(self, '_busy', False):
                _LOGGER.warning("[%s] ⚠️  RunPipeline ignorado — ciclo en curso", self.name)
                return

            _LOGGER.info("[%s] 🚀 Pipeline start=%s end=%s",
                         self.name, p.start_stage, p.end_stage)

            # Cancelar timeout de conversación si estaba corriendo
            if getattr(self, "_conv_timeout_task", None):
                self._conv_timeout_task.cancel()
                self._conv_timeout_task = None
            self._in_conversation = False

            # Cancelar cualquier tarea previa huérfana por si acaso
            for attr in ('_greet_task', '_pipeline_task'):
                t = getattr(self, attr, None)
                if t and not t.done():
                    t.cancel()

            self._reset_audio_state()
            self._busy = True  # bloquear hasta que termine el ciclo completo

            # _recording permanece False — se activará al terminar el saludo.
            # Los chunks que llegan durante el saludo se descartan automáticamente.
            self._greet_task = asyncio.create_task(self._greet_and_listen(client))

        elif AudioStart.is_type(event.type):
            # Algunos satellites sí mandan AudioStart — lo manejamos por si acaso
            _LOGGER.debug("[%s] AudioStart recibido", self.name)
            if not self._recording:
                self._recording = True
                if self._timeout_task:
                    self._timeout_task.cancel()
                self._timeout_task = asyncio.create_task(
                    self._recording_timeout(client)
                )

        elif AudioChunk.is_type(event.type):
            if self._recording:
                chunk = AudioChunk.from_event(event)
                await self._process_chunk(chunk.audio, client)

        elif AudioStop.is_type(event.type):
            if self._recording and self._speech_detected:
                await self._end_of_speech(client)

        elif Transcript.is_type(event.type):
            # El satellite reenvió nuestro Transcript al event-uri.
            # No genera respuesta hacia nosotros — solo logging.
            _LOGGER.debug("[%s] ← transcript (reenviado por satellite)", self.name)

    # ── VAD ───────────────────────────────────────────────────────────────────

    async def _process_chunk(self, raw: bytes, client: AsyncClient) -> None:
        self._leftover.extend(raw)
        self._speech_buffer.extend(raw)

        while len(self._leftover) >= VAD_FRAME_BYTES:
            frame = bytes(self._leftover[:VAD_FRAME_BYTES])
            del self._leftover[:VAD_FRAME_BYTES]
            await self._evaluate_frame(frame, client)

    async def _evaluate_frame(self, frame: bytes, client: AsyncClient) -> None:
        try:
            is_speech = self._vad.is_speech(frame, SAMPLE_RATE)
        except webrtcvad.Error as exc:
            _LOGGER.warning("[%s] VAD error: %s", self.name, exc)
            return

        if is_speech:
            self._speech_detected = True
            self._silence_count   = 0
        elif self._speech_detected:
            self._silence_count += 1
            _LOGGER.debug("[%s] 🤫 silencio %d/%d", self.name, self._silence_count, VAD_SILENCE_FRAMES)
            if self._silence_count >= VAD_SILENCE_FRAMES:
                await self._end_of_speech(client)

    async def _end_of_speech(self, client: AsyncClient) -> None:
        if not self._recording:
            return
        self._recording = False
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None

        audio = bytes(self._speech_buffer)
        self._speech_buffer.clear()
        secs = len(audio) / (SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS)
        _LOGGER.info("[%s] ✅ Fin de voz — %.1fs", self.name, secs)
        # Guardar referencia para poder cancelar si llega un RunPipeline nuevo
        self._pipeline_task = asyncio.create_task(self._run_pipeline(audio, client))

    async def _recording_timeout(self, client: AsyncClient) -> None:
        await asyncio.sleep(VAD_MAX_RECORD_SECS)
        if self._recording:
            _LOGGER.warning("[%s] ⏰ Timeout sin voz — abortando ciclo", self.name)
            self._recording = False
            self._speech_buffer.clear()
            self._busy = False
            # Transcript vacío hace que el satellite vuelva a wake word mode
            # (igual que una respuesta normal, sin bloquear el sistema)
            await client.write_event(Transcript(text="").event())

    # ── Pipeline STT → LLM → TTS ──────────────────────────────────────────────

    async def _run_pipeline(self, pcm_bytes: bytes, client: AsyncClient) -> None:
        loop = asyncio.get_event_loop()

        # ── STT ───────────────────────────────────────────────────────────────
        transcript = await loop.run_in_executor(None, transcribe_with_whisper, pcm_bytes)
        if not transcript:
            _LOGGER.warning("[%s] ⚠️ Transcripción vacía — abortando", self.name)
            self._reset_conversation()
            self._busy = False
            await client.write_event(Transcript(text="").event())
            return

        # Añadir turno del usuario al historial
        self._conversation.append({"role": "user", "content": transcript})
        # Limitar historial a los últimos N turnos
        if len(self._conversation) > CONVERSATION_MAX_TURNS * 2:
            self._conversation = self._conversation[-(CONVERSATION_MAX_TURNS * 2):]

        # Notificar transcript al satellite (lo muestra en logs y event-uri)
        await client.write_event(Transcript(text=transcript).event())

        # ── LLM con historial ─────────────────────────────────────────────────
        answer = await loop.run_in_executor(None, ask_ollama, self._conversation)
        if not answer:
            self._reset_conversation()
            self._busy = False
            await client.write_event(Transcript(text="").event())
            return

        # Añadir respuesta del asistente al historial
        self._conversation.append({"role": "assistant", "content": answer})

        # ── TTS ───────────────────────────────────────────────────────────────
        wav_bytes = await loop.run_in_executor(None, synthesize_with_coqui, answer)
        if not wav_bytes:
            self._reset_conversation()
            self._busy = False
            await client.write_event(Transcript(text="").event())
            return

        tts_duration = await self._send_audio(wav_bytes, client)

        # Liberar _busy tras duración real del TTS + margen de refractory.
        # El satellite vuelve a wake word mode al recibir el Transcript,
        # pero el altavoz sigue sonando. Sin el delay, el altavoz podría
        # disparar otra detección de wake word antes de terminar de hablar.
        asyncio.create_task(self._release_busy_after_delay(tts_duration + 0.5))

        # ── Timeout de conversación ───────────────────────────────────────────
        self._in_conversation = True
        if self._conv_timeout_task:
            self._conv_timeout_task.cancel()
        self._conv_timeout_task = asyncio.create_task(
            self._conversation_timeout(client)
        )
        _LOGGER.info(
            "[%s] 💬 Conversación activa (%d turnos) — esperando %ds",
            self.name, len(self._conversation) // 2, CONVERSATION_TIMEOUT_SECS,
        )

    async def _release_busy_after_delay(self, delay: float) -> None:
        """
        Libera el guard _busy tras un delay en segundos.

        El delay cubre el tiempo que tarda el altavoz en reproducir la respuesta
        TTS más el período de refractory de openwakeword (2s). Sin este delay,
        el satellite podría detectar la voz del altavoz como wake word y abrir
        un segundo ciclo mientras el primero aún está sonando.
        """
        await asyncio.sleep(delay)
        self._busy = False
        _LOGGER.debug("[%s] 🔓 Guard liberado", self.name)

    async def _greet_and_listen(self, client: AsyncClient) -> None:
        """
        Sintetiza un saludo corto y, al terminar, activa la grabación.

        El satellite sigue enviando chunks durante el saludo, pero como
        self._recording es False se descartan solos — el saludo actúa
        de período de gracia natural sin necesitar timers adicionales.
        """
        greeting = random.choice(GREETINGS)
        _LOGGER.info("[%s] 💬 Saludo: %s", self.name, greeting)

        loop = asyncio.get_event_loop()
        wav_bytes = await loop.run_in_executor(None, synthesize_with_coqui, greeting)
        audio_duration = 0.0
        if wav_bytes:
            audio_duration = await self._send_audio(wav_bytes, client)

        # Esperar a que el altavoz termine de reproducir el saludo.
        # _send_audio termina en cuanto el último chunk sale por TCP,
        # pero el DAC de la Orange Pi aún está reproduciendo. Sin este
        # sleep, _recording se activa mientras suena el saludo y el VAD
        # acumula la propia voz de Calavera como input del usuario.
        # Añadimos 0.3s extra sobre la duración para el padding de cola.
        if audio_duration > 0:
            await asyncio.sleep(audio_duration + 0.3)

        # Ahora sí activamos la grabación real
        _LOGGER.info("[%s] 🎤 Escuchando al usuario...", self.name)
        self._leftover.clear()
        self._speech_buffer.clear()
        self._silence_count   = 0
        self._speech_detected = False
        self._recording = True
        if self._timeout_task:
            self._timeout_task.cancel()
        self._timeout_task = asyncio.create_task(
            self._recording_timeout(client)
        )

    async def _conversation_timeout(self, client: AsyncClient) -> None:
        """Despide cordialmente si el usuario no vuelve en CONVERSATION_TIMEOUT_SECS."""
        await asyncio.sleep(CONVERSATION_TIMEOUT_SECS)
        if not self._in_conversation:
            return
        _LOGGER.info(
            "[%s] ⏰ Timeout de conversación — despidiendo", self.name
        )
        self._in_conversation = False
        self._busy = False  # permitir nueva wake word tras despedida
        # Sintetizar despedida
        loop = asyncio.get_event_loop()
        wav_bytes = await loop.run_in_executor(
            None, synthesize_with_coqui, CONVERSATION_GOODBYE
        )
        if wav_bytes:
            await self._send_audio(wav_bytes, client)
        # Decirle al satellite que vuelva a wake word mode.
        # Sin esto, el satellite sigue en is_streaming=True mandando
        # chunks infinitamente porque nadie le dijo que terminó.
        await client.write_event(Transcript(text="").event())
        self._reset_conversation()

    async def _send_audio(self, wav_bytes: bytes, client: AsyncClient) -> float:
        """Envía el audio al satellite. Devuelve la duración real en segundos."""
        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                rate     = wf.getframerate()
                width    = wf.getsampwidth()
                channels = wf.getnchannels()
                nframes  = wf.getnframes()
                raw      = wf.readframes(nframes)
        except Exception as exc:
            _LOGGER.error("[%s] ❌ Error WAV: %s", self.name, exc)
            return 0.0

        duration_secs = nframes / rate

        # Padding de silencio: 300ms al inicio y 500ms al final.
        #
        # INICIO: el DAC de la Orange Pi necesita unos ciclos para arrancar;
        #         sin padding el primer fragmento de voz se pierde.
        # FINAL:  Coqui no añade cola de silencio — el audio acaba en la última
        #         muestra de voz real y aplay cierra el dispositivo antes de que
        #         el DAC termine de reproducirla, cortando el final de la frase.
        silence_bytes = lambda ms: b'\x00' * (int(rate * ms / 1000) * width * channels)
        raw_with_padding = silence_bytes(300) + raw + silence_bytes(500)

        await client.write_event(AudioStart(rate=rate, width=width, channels=channels).event())
        chunk_size = 1024 * width * channels
        for i in range(0, len(raw_with_padding), chunk_size):
            await client.write_event(
                AudioChunk(rate=rate, width=width, channels=channels,
                           audio=raw_with_padding[i:i+chunk_size]).event()
            )
        await client.write_event(AudioStop().event())
        _LOGGER.info("[%s] ✅ Audio enviado (%.1fs)", self.name, duration_secs)
        return duration_secs


# ── Gestor de satellites (Zeroconf discovery) ─────────────────────────────────

class SatelliteManager:
    """
    Escucha la red con Zeroconf y lanza/termina SatelliteSession
    automáticamente cuando los satellites aparecen o desaparecen.
    Funciona con cualquier número de satellites y sin IPs fijas.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, SatelliteSession] = {}
        self._tasks:    Dict[str, asyncio.Task]     = {}

    async def run(self) -> None:
        aiozc = AsyncZeroconf()
        _LOGGER.info("🔍 Buscando satellites Wyoming en la red...")

        browser = AsyncServiceBrowser(
            aiozc.zeroconf,
            WYOMING_SERVICE_TYPE,
            handlers=[self._on_service_state_change],
        )

        try:
            # Esperar indefinidamente — el browser llama a _on_service_state_change
            await asyncio.Event().wait()
        finally:
            await aiozc.async_close()

    def _on_service_state_change(
        self,
        zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        if state_change == ServiceStateChange.Added:
            asyncio.create_task(self._add_satellite(zeroconf, service_type, name))
        elif state_change == ServiceStateChange.Removed:
            # No matamos la sesión — ella misma reconecta cuando el satellite vuelva.
            # Un Removed de Zeroconf puede ser un simple glitch de mDNS en la red,
            # no una desconexión real. Si el satellite desaparece para siempre,
            # la sesión lo detectará al fallar la reconexión TCP y esperará.
            _LOGGER.debug("📡 Zeroconf Removed (ignorado): %s", name)
        elif state_change == ServiceStateChange.Updated:
            # El satellite actualizó su anuncio mDNS (p.ej. cambio de IP).
            # Terminamos la sesión antigua y creamos una nueva con la IP actualizada.
            if name in self._sessions:
                _LOGGER.info("📡 Satellite actualizado (IP/puerto cambiado): %s", name)
                self._sessions[name].stop()
                del self._sessions[name]
                task = self._tasks.pop(name, None)
                if task:
                    task.cancel()
            asyncio.create_task(self._add_satellite(zeroconf, service_type, name))

    async def _add_satellite(
        self, zeroconf, service_type: str, name: str
    ) -> None:
        """
        Lanza una sesión para el servicio Wyoming descubierto.

        NO hacemos una conexión de verificación previa porque el satellite
        solo admite un servidor a la vez (server_id): una conexión extra
        ocuparía el slot y la sesión real sería rechazada.

        SatelliteSession verifica durante el handshake normal si el servicio
        es realmente un satellite (Info.satellite != None). Si no lo es,
        termina limpiamente sin reintentar.
        """
        if name in self._sessions:
            return

        info = AsyncServiceInfo(service_type, name)
        await info.async_request(zeroconf, timeout=3000)

        if not info.addresses or not info.port:
            _LOGGER.warning("⚠️  Servicio sin dirección: %s", name)
            return

        host = socket.inet_ntoa(info.addresses[0])
        port = info.port

        _LOGGER.info("📡 Servicio Wyoming en %s:%d (%s) — conectando", host, port, name)
        session = SatelliteSession(name=name, host=host, port=port)
        self._sessions[name] = session
        self._tasks[name] = asyncio.create_task(session.run())


# ── Servidor de eventos en puerto 10420 (notificaciones one-way) ──────────────

class EventNotificationHandler(AsyncEventHandler):
    """
    Recibe notificaciones del satellite: detection, streaming-started, etc.
    Útil para efectos físicos (LEDs, motores). Nunca recibe audio.
    """
    async def handle_event(self, event: Event) -> bool:
        _LOGGER.debug("Notificación: %s", event.type)
        if event.type == "detection":
            _LOGGER.info("💀 ¡WAKE WORD! Moviendo calavera...")
            # AQUÍ: activa GPIO / motores / LEDs
        return True


# ── Entrypoint ────────────────────────────────────────────────────────────────

async def main() -> None:
    event_server     = AsyncServer.from_uri(EVENT_URI)
    satellite_manager = SatelliteManager()

    _LOGGER.info("👂 Servidor de eventos en %s", EVENT_URI)
    _LOGGER.info("🔍 Iniciando descubrimiento Zeroconf de satellites")

    await asyncio.gather(
        event_server.run(EventNotificationHandler),
        satellite_manager.run(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
