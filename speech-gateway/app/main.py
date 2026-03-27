import os
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="Speech Gateway Generic")

# Configuramos las URLs mediante variables de entorno (con valores por defecto)
WHISPER_URL = os.getenv("WHISPER_URL", "http://whisper:9000/asr")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")
COQUI_URL = os.getenv("COQUI_URL", "http://coqui:5002/api/tts")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")


@app.post("/ask")
async def ask_assistant(file: UploadFile = File(...)):
    try:
        # 1. Leer audio
        audio_bytes = await file.read()

        # 2. Whisper: Transcripción
        # Nota: Algunos contenedores de Whisper esperan el parámetro 'audio_file' o 'file'
        res_asr = requests.post(WHISPER_URL, files={"file": audio_bytes})
        res_asr.raise_for_status() # Lanza error si el microservicio está caído

        prompt = res_asr.json().get("text", "").strip()
        if not prompt:
            return JSONResponse(content={"error": "No se detectó habla en el audio"}, status_code=400)

        # 3. Ollama: Inferencia
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }
        res_llm = requests.post(OLLAMA_URL, json=payload)
        res_llm.raise_for_status()
        answer = res_llm.json().get("response", "")

        # 4. CoquiTTS: Síntesis de voz
        # Importante: Coqui suele devolver el audio directamente en el body
        res_tts = requests.get(COQUI_URL, params={"text": answer})
        res_tts.raise_for_status()

        # Devolvemos JSON con el texto y el audio en hex (o base64 si prefieres)
        return {
            "text_in": prompt,
            "text_out": answer,
            "audio_hex": res_tts.content.hex()
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error de conexión con microservicios: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
