
#!/bin/bash
# download_ollama.sh — Descarga modelos Ollama dentro del contenedor
#
# Este script corre en el HOST pero ejecuta los comandos dentro del
# contenedor Ollama via docker exec. Requiere que el contenedor esté
# healthy antes de llamarlo (just setup-models se encarga de esperar).
#
# Invocado por:
#   just download-ollama   — solo descarga modelos base
#   just setup-models      — descarga + crea instancias personalizadas
#
# No ejecutar directamente si usas el justfile.

set -e

export $(grep -v '^#' .env | xargs)

SERVICE_NAME="ollama-${PROFILE_VAR}"
CONTAINER_NAME=$(docker ps --filter "label=com.docker.compose.service=${SERVICE_NAME}" --format "{{.Names}}" | head -n 1)

echo "📦 Comprobando modelos en ${CONTAINER_NAME}..."
MODELS=$(docker exec ${CONTAINER_NAME} ollama list 2>/dev/null || echo "")

# ─────────────────────────────────────────────
# Función auxiliar: pull si no existe
# ─────────────────────────────────────────────
pull_if_missing() {
    local model=$1
    if [ -z "$model" ]; then return; fi
    if echo "${MODELS}" | grep -q "${model}"; then
        echo "✅ ${model} ya está descargado."
    else
        echo "📦 Descargando ${model}..."
        docker exec ${CONTAINER_NAME} ollama pull "${model}"
    fi
}

# ── Modelos del stack principal (Langflow, Gradio, n8n) ──────────────────────
pull_if_missing "${LLM_MODEL_NAME}"
pull_if_missing "${LLM_EMBEDDING_MODEL_NAME}"
pull_if_missing "${LLM_TOOLS_MODEL_NAME}"

# ── Modelos del blueprint de desarrollo Aider ────────────────────────────────
pull_if_missing "qwen2.5-coder:14b"      # base de qwen-editor
pull_if_missing "qwen2.5:7b-instruct"    # base de rag-bot
pull_if_missing "nomic-embed-text"       # embeddings RAG
pull_if_missing "deepseek-r1:14b"        # base de r1-architect

echo "✅ Todos los modelos Ollama están disponibles."
