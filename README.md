# 🛠️ DeepLocal Forge

**Soberanía Digital · Laboratorio de IA Local · Agnóstico de IDE**

`DeepLocal Forge` es una infraestructura de IA local diseñada para centralizar el razonamiento de modelos de última generación en hardware personal (12 GB VRAM). Proporciona endpoints locales optimizados para que orquestadores externos —de terminal o de IDE— consuman modelos con una arquitectura de separación de funciones (Arquitecto / Editor).

---

## 📑 Filosofía

- **Agnóstico de herramientas** — alimenta a Aider, Continue, Roo Code y cualquier cliente compatible con la API OpenAI/Ollama.
- **Soberanía de datos** — todo el procesamiento ocurre dentro de tu red local.
- **Eficiencia de VRAM** — modos de arranque granulares para no saturar el sistema cuando no se usa.

---

## 🔌 Orquestadores compatibles

| Orquestador | Flujo recomendado | Modelo de referencia |
|---|---|---|
| **Aider** | Refactorización y gestión de Git | `r1-architect` + `qwen-editor` |
| **Continue** | Autocompletado (Tab) y chat contextual en IDE | `qwen2.5-coder:1.5b` (fast) / `qwen-editor` |
| **Roo Code** | Agente autónomo basado en herramientas | `qwen2.5-coder:14b` |

---

## 🏗️ Estructura del repositorio

```
deeplocal-forge/
├── assets/
│   ├── ollama/              # Modelfiles — r1-architect, qwen-editor, rag-bot
│   └── mcp/                 # Dockerfiles de los servidores MCP
├── ai-specs/                # Especificaciones y estándares (fuente de verdad)
│   ├── specs/
│   │   ├── base-standards.mdc          # Reglas core (todos los agentes la leen)
│   │   ├── backend-standards.mdc
│   │   ├── frontend-standards.mdc
│   │   ├── documentation-standards.mdc
│   │   ├── api-spec.yml                # Plantilla OpenAPI 3.0
│   │   ├── data-model.md
│   │   ├── prompts.md                  # Prompts reutilizables
│   │   ├── ARCHITECTURE.md.template
│   │   └── CONSTRAINTS.md.template
│   └── changes/             # Planes de implementación por ticket
├── skills/                  # Skills de agente (de skills.sh)
│   ├── process/             # Debugging, TDD, verificación, multiagentes
│   ├── quality/             # API design, seguridad, code review
│   ├── languages/           # Python, TypeScript, Node.js
│   └── frontend/            # React, Next.js
├── .aider/
│   └── commands/            # Comandos personalizados de Aider
│       ├── prevalidate      # Pipeline pre-LLM (detecta lenguaje automáticamente)
│       ├── critic           # Critic Pass estandarizado
│       ├── enrich-us        # Enriquecer una user story
│       ├── plan             # Generar plan de implementación
│       └── update-arch      # Actualizar ARCHITECTURE.md
├── scripts/
├── doc/
│   └── blueprint.md
├── AGENTS.md / CLAUDE.md / GEMINI.md / codex.md   # Config por agente
├── docker-compose.yml
├── justfile
└── .env.example
```
---

## 🚀 Setup inicial

```bash
# 1. Crear la red Docker externa (solo la primera vez)
just network-create

# 2. Arrancar el stack (detecta GPU automáticamente)
just up

# 3. Descargar modelos y crear instancias personalizadas
just setup-models
```

---

## ⚡ Modos de operación

| Comando | Servicios activos |
|---|---|
| `just up-dev` | Ollama + Qdrant |
| `just up-comfy` | Ollama + ComfyUI |
| `just up-mcp` | Qdrant + MCP servers base |
| `just up-mcp-optional` | MCP servers con credenciales (SearXNG…) |
| `just up` | Stack completo |

Para cambiar de modo liberando VRAM primero: `just switch-mode dev`

---

## 📡 Servicios expuestos (via Traefik)

| Servicio | URL local |
|---|---|
| Ollama | `https://ollama.dominio.local` |
| Qdrant | `https://qdrant.dominio.local` |
| TTS (Coqui) | `https://tts.dominio.local` |
| STT (Whisper) | `https://stt.dominio.local` |
| ComfyUI | `https://comfyui.dominio.local` |
| MCP Playwright | `https://mcp-playwright.dominio.local` |
| MCP Filesystem | `https://mcp-filesystem.dominio.local` |
| MCP Memory | `https://mcp-memory.dominio.local` |

> El dominio `dominio.local` se configura en `MAIN_DOMAIN` dentro de `.env`.