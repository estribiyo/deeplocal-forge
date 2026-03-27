"""
speech-gateway/main.py — Pipeline Wyoming con VAD server-side
--------------------------------------------------------------
Soluciona el problema de la Orange Pi Zero (ARMv7/H3) que no puede
ejecutar Silero VAD por falta de onnxruntime compatible.

En lugar de esperar AudioStop del satellite (que nunca llega),
este handler implementa su propio VAD usando webrtcvad —
una librería en C puro sin dependencias de ONNX ni binarios ARM.

Flujo:
  Orange Pi → audio infinito → [VAD server-side detecta silencio]
  → corta internamente → Whisper STT → Ollama LLM → Coqui TTS
  → audio de vuelta a Orange Pi
"""

import asyncio
import io
import logging
import os
import wave
from typing import Optional

import requests
import webrtcvad

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.asr import Transcript
from wyoming.event import Event
from wyoming.server import AsyncEventHandler, AsyncServer

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

# ── Configuración de servicios ────────────────────────────────────────────────
WHISPER_URL   = os.getenv("WHISPER_URL",       "http://whisper:9000/asr")
OLLAMA_URL    = os.getenv("OLLAMA_URL",         "http://ollama:11434")
COQUI_URL     = os.getenv("COQUI_URL",          "http://coqui-tts:5002")
DEFAULT_MODEL = os.getenv("DEFAULT_LLM_MODEL",  "qwen2.5:7b-instruct")

# ── Parámetros de audio (deben coincidir con --mic-command del satellite) ─────
SAMPLE_RATE  = 16000
SAMPLE_WIDTH = 2      # S16_LE = 2 bytes por muestra
CHANNELS     = 1

# ── Parámetros del VAD server-side ────────────────────────────────────────────
#
# webrtcvad solo acepta frames de exactamente 10ms, 20ms o 30ms.
# Usamos 20ms → 320 samples × 2 bytes = 640 bytes por frame.
#
VAD_FRAME_MS       = 20
VAD_FRAME_SAMPLES  = int(SAMPLE_RATE * VAD_FRAME_MS / 1000)   # 320
VAD_FRAME_BYTES    = VAD_FRAME_SAMPLES * SAMPLE_WIDTH          # 640
VAD_AGGRESSIVENESS = 2   # 0=permisivo … 3=agresivo. Ajusta si hay falsos positivos.

# Cuántos frames de silencio consecutivos = fin de frase.
# 20 frames × 20ms = 400ms de silencio. Sube a 25-30 si corta demasiado pronto.
VAD_SILENCE_FRAMES = 20

# Timeout de seguridad: si el usuario no habla nada tras la wake word, abortar.
VAD_MAX_RECORD_SECS = 10


# ── Helpers HTTP (síncronos → se llaman desde run_in_executor) ────────────────

def transcribe_with_whisper(pcm_bytes: bytes) -> Optional[str]:
    """Convierte PCM raw a WAV y lo envía al servicio Whisper ASR."""
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


def ask_ollama(text: str) -> Optional[str]:
    """Envía el texto al LLM y devuelve la respuesta."""
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": DEFAULT_MODEL,
                "prompt": text,
                "stream": False,
                "system": (
                    "Eres Calavera, un asistente de voz conciso y útil. "
                    "Responde siempre en español, en 1-3 frases cortas."
                ),
            },
            timeout=60,
        )
        resp.raise_for_status()
        answer = resp.json().get("response", "").strip()
        _LOGGER.info("🤖 Respuesta LLM: %s", answer)
        return answer
    except Exception as exc:
        _LOGGER.error("❌ Ollama error: %s", exc)
        return None


def synthesize_with_coqui(text: str) -> Optional[bytes]:
    """Convierte texto a WAV con Coqui TTS."""
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


# ── Handler principal ─────────────────────────────────────────────────────────

class CalaveraHandler(AsyncEventHandler):
    """
    Handler Wyoming que sustituye el VAD del satellite con uno propio.

    El satellite de la Orange Pi envía audio de forma continua una vez
    detectada la wake word (nunca manda AudioStop porque no puede correr
    Silero VAD en ARMv7). Este handler:

      1. Acumula chunks en un buffer sobrante (leftover) para alinear frames.
      2. Extrae frames exactos de 20ms para webrtcvad.
      3. Cuenta frames de silencio consecutivos DESPUÉS de haber detectado voz.
      4. Al superar VAD_SILENCE_FRAMES, da la frase por terminada y dispara
         el pipeline STT→LLM→TTS sin esperar AudioStop.
      5. Tiene un timeout máximo por si el usuario no habla tras la wake word.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self._reset_state()

    def _reset_state(self) -> None:
        """Vuelve al estado inicial, listo para el siguiente turno."""
        self._recording       = False
        self._pipeline_active = False
        self._leftover        = bytearray()  # bytes sobrantes entre chunks
        self._speech_buffer   = bytearray()  # audio acumulado completo para STT
        self._silence_count   = 0
        self._speech_detected = False
        self._pipeline_task: Optional[asyncio.Task] = None
        self._timeout_task:  Optional[asyncio.Task] = None

    # ── Eventos Wyoming ───────────────────────────────────────────────────────

    async def handle_event(self, event: Event) -> bool:
        _LOGGER.debug("Evento: %s", event.type)

        if event.type == "run-pipeline":
            await self._on_run_pipeline(event)

        elif AudioStart.is_type(event.type):
            await self._on_audio_start()

        elif AudioChunk.is_type(event.type):
            if self._recording:
                chunk = AudioChunk.from_event(event)
                await self._process_chunk(chunk.audio)

        elif AudioStop.is_type(event.type):
            # El satellite NO debería mandar esto con la config actual, pero
            # si llega (satellite con VAD propio) lo tratamos igualmente.
            _LOGGER.info("⏹️ AudioStop recibido del satellite")
            if self._recording and self._speech_detected:
                await self._end_of_speech()

        elif event.type == "detection":
            _LOGGER.info("💀 ¡WAKE WORD DETECTADA! Moviendo calavera...")
            # AQUÍ: activa GPIO / motores / LEDs

        return True

    # ── Lógica interna ────────────────────────────────────────────────────────

    async def _on_run_pipeline(self, event: Event) -> None:
        data = event.data or {}
        _LOGGER.info(
            data
        )
        data.get("start_stage"),
        data.get("end_stage"),
        data.get("wake_word_name"),

    async def _on_audio_start(self) -> None:
        _LOGGER.info("🎤 Grabación iniciada (VAD server-side activo)")
        self._recording       = True
        self._speech_buffer.clear()
        self._leftover.clear()
        self._silence_count   = 0
        self._speech_detected = False

        # Timeout de seguridad
        if self._timeout_task:
            self._timeout_task.cancel()
        self._timeout_task = asyncio.create_task(self._recording_timeout())

    async def _process_chunk(self, raw: bytes) -> None:
        """
        Recibe bytes crudos del satellite (tamaño variable) y los alinea
        en frames exactos de VAD_FRAME_BYTES para webrtcvad.
        """
        self._leftover.extend(raw)
        self._speech_buffer.extend(raw)  # guardamos TODO para STT

        while len(self._leftover) >= VAD_FRAME_BYTES:
            frame = bytes(self._leftover[:VAD_FRAME_BYTES])
            del self._leftover[:VAD_FRAME_BYTES]
            await self._evaluate_frame(frame)

    async def _evaluate_frame(self, frame: bytes) -> None:
        """Pasa un frame de 20ms por el VAD y actualiza el estado."""
        try:
            is_speech = self._vad.is_speech(frame, SAMPLE_RATE)
        except webrtcvad.Error as exc:
            _LOGGER.warning("VAD frame error: %s", exc)
            return

        if is_speech:
            self._speech_detected = True
            self._silence_count   = 0
            _LOGGER.debug("🗣️  voz detectada")
        elif self._speech_detected:
            # Solo contamos silencio DESPUÉS de haber oído voz real.
            # Así no disparamos el pipeline si hay ruido ambiental al inicio.
            self._silence_count += 1
            _LOGGER.debug("🤫 silencio %d/%d", self._silence_count, VAD_SILENCE_FRAMES)
            if self._silence_count >= VAD_SILENCE_FRAMES:
                await self._end_of_speech()

    async def _end_of_speech(self) -> None:
        """El VAD ha decidido que el usuario terminó de hablar."""
        if not self._recording:
            return  # evitar doble disparo

        self._recording = False
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None

        audio = bytes(self._speech_buffer)
        secs = len(audio) / (SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS)
        _LOGGER.info("✅ Fin de voz — %.1fs capturados", secs)

        self._pipeline_task = asyncio.create_task(self._run_pipeline(audio))
        self._speech_buffer.clear()

    async def _recording_timeout(self) -> None:
        """Aborta si el usuario no habla nada en VAD_MAX_RECORD_SECS segundos."""
        await asyncio.sleep(VAD_MAX_RECORD_SECS)
        if self._recording:
            _LOGGER.warning(
                "⏰ Timeout (%ds sin voz), cancelando grabación", VAD_MAX_RECORD_SECS
            )
            self._recording = False
            self._speech_buffer.clear()

    # ── Pipeline STT → LLM → TTS ──────────────────────────────────────────────

    async def _run_pipeline(self, pcm_bytes: bytes) -> None:
        loop = asyncio.get_event_loop()

        # 1. STT
        _LOGGER.info("🔍 Enviando a Whisper (%d bytes)...", len(pcm_bytes))
        transcript = await loop.run_in_executor(None, transcribe_with_whisper, pcm_bytes)
        if not transcript:
            _LOGGER.warning("⚠️ Transcripción vacía, abortando")
            return

        await self.write_event(Transcript(text=transcript).event())

        # 2. LLM
        _LOGGER.info("🤔 Consultando Ollama...")
        answer = await loop.run_in_executor(None, ask_ollama, transcript)
        if not answer:
            _LOGGER.warning("⚠️ Sin respuesta del LLM")
            return

        # 3. TTS
        _LOGGER.info("🔊 Sintetizando con Coqui...")
        wav_bytes = await loop.run_in_executor(None, synthesize_with_coqui, answer)
        if not wav_bytes:
            _LOGGER.warning("⚠️ Sin audio TTS")
            return

        # 4. Enviar audio al satellite
        await self._send_audio_response(wav_bytes)

    async def _send_audio_response(self, wav_bytes: bytes) -> None:
        """Trocea el WAV y lo envía como stream Wyoming al satellite."""
        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                rate     = wf.getframerate()
                width    = wf.getsampwidth()
                channels = wf.getnchannels()
                raw      = wf.readframes(wf.getnframes())
        except Exception as exc:
            _LOGGER.error("❌ Error leyendo WAV TTS: %s", exc)
            return

        await self.write_event(
            AudioStart(rate=rate, width=width, channels=channels).event()
        )

        chunk_size = 1024 * width * channels
        for i in range(0, len(raw), chunk_size):
            await self.write_event(
                AudioChunk(
                    rate=rate, width=width, channels=channels,
                    audio=raw[i : i + chunk_size],
                ).event()
            )

        await self.write_event(AudioStop().event())
        _LOGGER.info("✅ Respuesta de audio enviada al satellite")


# ── Entrypoint ────────────────────────────────────────────────────────────────

async def run_server() -> None:
    _LOGGER.info("🚀 Servidor Calavera escuchando en tcp://0.0.0.0:10420")
    server = AsyncServer.from_uri("tcp://0.0.0.0:10420")
    await server.run(CalaveraHandler)


if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass
