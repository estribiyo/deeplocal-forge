# 🚀 AI Voice Gateway Orchestrator

Este proyecto implementa un **Gateway de Voz con IA** diseñado para conectar dispositivos de hardware limitado (como la **Orange Pi Zero**) con un stack potente de Inteligencia Artificial autohospedado en un servidor externo.

## 🏗️ Arquitectura del Sistema

El sistema se divide en dos capas principales para optimizar recursos y latencia:

### 1. Edge Layer (Orange Pi Zero + Placa de Expansión)
* **Hardware:** Orange Pi Zero (512MB RAM) + Expansion Board (Audio Jack/Mic).
* **Sistema Operativo:** Armbian (Minimal/CLI).
* **Software:** Cliente ligero en Python o Rhasspy.
* **Función:** * Detección de palabra de activación (**Wake Word**: "Claw").
    * Captura de audio ambiental y digitalización.
    * Envío de buffers de audio al servidor vía HTTP/REST.
    * Reproducción de la respuesta de voz recibida.

### 2. Brain Layer (Servidor de IA - Docker Stack)
* **Speech Gateway (Orquestador):** Contenedor FastAPI que coordina el flujo.
* **Whisper:** Motor de ASR (Automatic Speech Recognition) para convertir audio en texto.
* **Ollama:** Motor de LLM (Inferencia) utilizando modelos como `deepseek-r1:14b` o `qwen2.5:7b`.
* **CoquiTTS:** Motor de síntesis de voz para convertir la respuesta de texto en audio real.

---

## 🛠️ Stack Tecnológico (Servidor)

| Servicio | Tecnología | Función |
| :--- | :--- | :--- |
| **Gateway** | Python (FastAPI) | Orquestación y lógica de negocio |
| **ASR** | OpenAI Whisper | Transcripción de voz a texto |
| **LLM** | Ollama | Razonamiento y generación de respuesta |
| **TTS** | Coqui TTS | Generación de audio (Voz) |
| **Container** | Docker & Compose | Aislamiento y despliegue |

---

## 📂 Estructura del Proyecto (Gateway)

```text
speech-gateway/
├── main.py              # Lógica principal y conexión con microservicios
├── Dockerfile           # Configuración de imagen (Python 3.11-slim)
└── docker-compose.yml   # Definición del stack y redes internas
```

---

## ⚙️ Configuración del Gateway

El contenedor se configura mediante variables de entorno para permitir la comunicación interna en la red de Docker:

* `WHISPER_URL`: URL del contenedor de Whisper (ej. `http://whisper:9000/asr`).
* `OLLAMA_URL`: URL del servicio Ollama (ej. `http://ollama:11434`).
* `COQUI_URL`: URL del servicio Coqui (ej. `http://coqui:5002/api/tts`).
* `MODEL_NAME`: Modelo a usar en Ollama (Recomendado: `deepseek-r1:14b` o `qwen2.5:7b-instruct`).

---

## 🔄 Flujo de una Petición

1.  El usuario dice **"Claw"**. La Orange Pi detecta la frecuencia y activa la grabación.
2.  El audio se envía al endpoint `/ask` del **Speech Gateway**.
3.  El Gateway envía el audio a **Whisper** y recibe el texto transcrito.
4.  El texto se envía a **Ollama**. La IA genera una respuesta coherente.
5.  La respuesta se envía a **CoquiTTS**, que genera un archivo de audio `.wav`.
6.  El Gateway devuelve un JSON a la Orange Pi con la respuesta en texto y el audio en formato **Hexadecimal**.
7.  La Orange Pi decodifica el Hex y reproduce el sonido por la **Placa de Expansión**.

---

## 🛡️ Ventajas de este Diseño
* **Escalabilidad:** Se pueden conectar múltiples dispositivos (Orange Pi, móviles, ESP32) al mismo gateway.
* **Baja Latencia:** Al estar todo en una red interna de Docker en el servidor, el intercambio de datos entre Whisper, Ollama y Coqui es casi instantáneo.
* **Privacidad:** Todo el procesamiento ocurre de forma local en tu infraestructura, sin enviar datos a la nube.

