# Receta por defecto para mostrar la ayuda.
default:
    @just --list

# `just network-create` — crea la red externa ai_network si no existe.
# Ejecutar una sola vez antes del primer `just up`.
network-create:
    docker network inspect ai_network >/dev/null 2>&1 || \
    docker network create ai_network
    @echo "✅ Red ai_network lista"

# `just clean` detiene y elimina los contenedores y volúmenes de ambos perfiles.
clean:
    docker compose --profile cpu down --volumes
    docker compose --profile gpu down --volumes

prepare-environment:
    #!/bin/bash
    if [ ! -f ./.env ]; then
        cp ./.env.example ./.env;
    fi
    echo "🔍 Detectando GPU..."
    PROFILE_VAR="cpu"
    LLM_MODEL_NAME_VAR="deepseek-r1:8b"
    if command -v nvidia-smi &> /dev/null && nvidia-smi -L | grep -q "GPU"; then
        echo "✅ GPU detectada";
        PROFILE_VAR="gpu";
        VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1);
        echo "💾 VRAM detectada: ${VRAM} MB";
        if [ "$VRAM" -ge 12000 ]; then
            LLM_MODEL_NAME_VAR="deepseek-r1:14b";
        fi;
    else
        echo "⚠️  No se detectó GPU";
    fi;
    if grep -q "^PROFILE_VAR=" .env; then
        sed -i "s|^PROFILE_VAR=.*|PROFILE_VAR=${PROFILE_VAR}|" .env;
    else
        echo "\nPROFILE_VAR=${PROFILE_VAR}\n" >> .env;
    fi;
    if grep -q "^LLM_MODEL_NAME=" .env; then
        sed -i "s|^LLM_MODEL_NAME=.*|LLM_MODEL_NAME=${LLM_MODEL_NAME_VAR}|" .env;
    else
        echo "LLM_MODEL_NAME=${LLM_MODEL_NAME_VAR}" >> .env;
    fi;
    echo "✅ Variables de entorno actualizadas en .env";

# `just down` detiene y elimina los contenedores de ambos perfiles.
down:
    docker compose --profile cpu down
    docker compose --profile gpu down

# `just logs` muestra los logs en tiempo real para el perfil detectado.
logs:
    just prepare-environment
    export $(grep -v '^#' .env | xargs) && docker compose --profile ${PROFILE_VAR} logs -f

restart: down up

# `just up` detecta la GPU y levanta el stack completo del perfil correspondiente.
up:
    @just prepare-environment
    export $(grep -v '^#' .env | xargs) && docker compose --profile ${PROFILE_VAR} up --build -d

# `just up-dev` — solo Ollama + Qdrant (modo desarrollo con Aider)
up-dev:
    @just prepare-environment
    export $(grep -v '^#' .env | xargs) && \
    docker compose --profile ${PROFILE_VAR} down && \
    docker compose up ollama-${PROFILE_VAR} qdrant --build -d
    @echo "✅ Modo DEV activo: Ollama + Qdrant"

# `just up-comfy` — Ollama + ComfyUI (generación de imágenes, uso puntual)
up-comfy:
    @just prepare-environment
    export $(grep -v '^#' .env | xargs) && \
    docker compose --profile ${PROFILE_VAR} down && \
    docker compose up ollama-${PROFILE_VAR} comfyui-${PROFILE_VAR} --build -d
    @echo "✅ Modo COMFY activo: Ollama + ComfyUI"

# `just switch-mode MODE` — cambia de modo haciendo down primero para liberar VRAM
# Uso: just switch-mode dev | comfy | full | mcp | mcp-optional
switch-mode mode:
    #!/bin/bash
    echo "🔄 Cambiando a modo: {{mode}}"
    just down
    case "{{mode}}" in
        dev)          just up-dev ;;
        comfy)        just up-comfy ;;
        full)         just up ;;
        mcp)          just up-mcp ;;
        mcp-optional) just up-mcp-optional ;;
        *)            echo "❌ Modo desconocido: {{mode}}. Usa: dev | comfy | full | mcp | mcp-optional" && exit 1 ;;
    esac

# `just download-comfy` — descarga modelos ComfyUI al host (COMFY_PATH)
download-comfy:
    bash scripts/download_comfy.sh

# `just download-ollama` — descarga modelos Ollama dentro del contenedor
download-ollama:
    @just prepare-environment
    bash scripts/download_ollama.sh

# `just download-models` — descarga todos los modelos (ComfyUI + Ollama)
download-models:
    @just download-comfy
    @just download-ollama

# `just setup-models` — descarga modelos base y crea las instancias personalizadas
# del blueprint (r1-architect, qwen-editor, rag-bot) desde los Modelfiles.
# IMPORTANTE: ejecutar DESPUÉS de `just up` y cuando el contenedor esté healthy.
setup-models:
    #!/bin/bash
    export $(grep -v '^#' .env | xargs)

    # 1. Identificamos el nombre del servicio basándonos en el perfil detectado
    SERVICE_NAME="ollama-${PROFILE_VAR}"

    # 2. Buscamos el nombre REAL del contenedor que Docker Compose ha asignado
    # Filtramos por la etiqueta interna que pone Compose automáticamente
    CONTAINER_NAME=$(docker ps --filter "label=com.docker.compose.service=${SERVICE_NAME}" --format "{{ '{.Names}}' }}" | head -n 1)
   
    echo "⏳ Esperando a que Ollama esté operativo..."
    until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
        sleep 3
    done
    echo "✅ Ollama responde."

    just download-ollama

    echo ""
    echo "🔧 Creando instancia r1-architect..."
    if docker exec ${CONTAINER_NAME} ollama list | grep -q "r1-architect"; then
        echo "✅ r1-architect ya existe."
    else
        docker exec ${CONTAINER_NAME} ollama create r1-architect -f /modelfiles/Modelfile.architect
        echo "✅ r1-architect creado."
    fi

    echo "🔧 Creando instancia qwen-editor..."
    if docker exec ${CONTAINER_NAME} ollama list | grep -q "qwen-editor"; then
        echo "✅ qwen-editor ya existe."
    else
        docker exec ${CONTAINER_NAME} ollama create qwen-editor -f /modelfiles/Modelfile.editor
        echo "✅ qwen-editor creado."
    fi

    echo "🔧 Descargando modelo de embeddings..."
    docker exec ${CONTAINER_NAME} ollama pull nomic-embed-text

    echo "🔧 Creando instancia rag-bot..."
    if docker exec ${CONTAINER_NAME} ollama list | grep -q "rag-bot"; then
        echo "✅ rag-bot ya existe."
    else
        docker exec ${CONTAINER_NAME} ollama create rag-bot -f /modelfiles/Modelfile.rag
        echo "✅ rag-bot creado."
    fi

    echo ""
    echo "✅ Setup completo. Instancias disponibles:"
    docker exec ${CONTAINER_NAME} ollama list

# `just up-mcp` — levanta los servidores MCP base + Qdrant
# playwright, filesystem, memory — sin credenciales, siempre válidos.
up-mcp:
    @just prepare-environment
    export $(grep -v '^#' .env | xargs) && \
    docker compose --profile ${PROFILE_VAR} down && \
    docker compose up qdrant mcp-playwright mcp-filesystem mcp-memory --build -d
    @echo "✅ Modo MCP activo (servidores base)"
    @echo "   http://mcp-playwright.${MAIN_DOMAIN}  — scraping JS"
    @echo "   http://mcp-filesystem.${MAIN_DOMAIN}  — archivos locales"
    @echo "   http://mcp-memory.${MAIN_DOMAIN}      — memoria persistente"

# `just up-mcp-optional` — levanta servidores MCP que requieren credenciales
# Requiere MCP_SEARXNG_URL configurada en .env
up-mcp-optional:
    @just prepare-environment
    export $(grep -v '^#' .env | xargs) && \
    docker compose --profile mcp-optional up --build -d
    @echo "✅ Servidores MCP opcionales activos"
    @echo "   http://mcp-searxng.${MAIN_DOMAIN}     — búsqueda web (requiere MCP_SEARXNG_URL)"

# `just up-rag` — Ollama + Qdrant + Langflow + n8n (modo RAG / bot de consultas)
up-rag:
    @just prepare-environment
    export $(grep -v '^#' .env | xargs) && \
    docker compose --profile ${PROFILE_VAR} down && \
    docker compose up ollama-${PROFILE_VAR} qdrant langflow-${PROFILE_VAR} n8n-workflow --build -d
    @echo "✅ Modo RAG activo: Ollama + Qdrant + Langflow + n8n"

# `just init-project NAME` — inicializa un proyecto nuevo con la estructura spec-driven
# Uso: just init-project mi-proyecto
# Crea: ARCHITECTURE.md, CONSTRAINTS.md, ai-specs/, .aider/commands/, skills/ (symlink)
init-project name:
    #!/bin/bash
    set -e
    PROJECT_DIR="../{{name}}"

    if [ -d "$PROJECT_DIR" ]; then
        echo "❌ El directorio $PROJECT_DIR ya existe. Elige otro nombre."
        exit 1
    fi

    echo "🚀 Inicializando proyecto: {{name}}"
    mkdir -p "$PROJECT_DIR/ai-specs/specs"
    mkdir -p "$PROJECT_DIR/ai-specs/changes"
    mkdir -p "$PROJECT_DIR/.aider/commands"

    # Copiar plantillas de specs
    cp ai-specs/specs/base-standards.mdc    "$PROJECT_DIR/ai-specs/specs/"
    cp ai-specs/specs/backend-standards.mdc "$PROJECT_DIR/ai-specs/specs/"
    cp ai-specs/specs/frontend-standards.mdc "$PROJECT_DIR/ai-specs/specs/"
    cp ai-specs/specs/documentation-standards.mdc "$PROJECT_DIR/ai-specs/specs/"
    cp ai-specs/specs/api-spec.yml          "$PROJECT_DIR/ai-specs/specs/"
    cp ai-specs/specs/data-model.md         "$PROJECT_DIR/ai-specs/specs/"
    cp ai-specs/specs/prompts.md            "$PROJECT_DIR/ai-specs/specs/"

    # Crear ARCHITECTURE.md y CONSTRAINTS.md desde plantillas
    cp ai-specs/specs/ARCHITECTURE.md.template "$PROJECT_DIR/ARCHITECTURE.md"
    cp ai-specs/specs/CONSTRAINTS.md.template  "$PROJECT_DIR/CONSTRAINTS.md"

    # Copiar configuraciones de agentes
    cp AGENTS.md   "$PROJECT_DIR/"
    cp CLAUDE.md   "$PROJECT_DIR/"
    cp GEMINI.md   "$PROJECT_DIR/"
    cp codex.md    "$PROJECT_DIR/"

    # Copiar comandos de Aider
    cp .aider/commands/prevalidate  "$PROJECT_DIR/.aider/commands/"
    cp .aider/commands/critic       "$PROJECT_DIR/.aider/commands/"
    cp .aider/commands/enrich-us    "$PROJECT_DIR/.aider/commands/"
    cp .aider/commands/plan         "$PROJECT_DIR/.aider/commands/"
    cp .aider/commands/update-arch  "$PROJECT_DIR/.aider/commands/"

    # Copiar skills (copia completa — no symlinks, para que el proyecto sea portable)
    cp -r skills "$PROJECT_DIR/"

    echo ""
    echo "✅ Proyecto '{{name}}' inicializado en $PROJECT_DIR"
    echo ""
    echo "📋 Próximos pasos:"
    echo "   1. cd $PROJECT_DIR"
    echo "   2. Edita ARCHITECTURE.md con las decisiones iniciales de tu stack"
    echo "   3. Edita CONSTRAINTS.md con las restricciones del proyecto"
    echo "   4. Edita ai-specs/specs/api-spec.yml con tus endpoints reales"
    echo "   5. Inicia Aider: aider (leerá .aider/commands/ automáticamente)"
    echo ""
    echo "💡 Primer flujo recomendado:"
    echo "   /enrich-us [describe tu user story]"
    echo "   /plan [describe el ticket]"
