# Tutorial: DeepLocal Forge
## Desarrollo asistido por IA — sin costes de API, sin nube, sin límites

`v1.0 · Rust · Python · JS/TS · React · PHP · Aider · Roo Code · Continue · OpenCode`

---

## Índice

1. [¿Qué es esto y para qué sirve?](#1-qué-es-esto-y-para-qué-sirve)
2. [Requisitos de hardware](#2-requisitos-de-hardware)
3. [Requisitos de software](#3-requisitos-de-software)
4. [Setup inicial del stack](#4-setup-inicial-del-stack)
5. [Conceptos clave antes de empezar](#5-conceptos-clave-antes-de-empezar)
6. [Orquestador 1 — Aider (terminal)](#6-orquestador-1--aider-terminal)
7. [Orquestador 2 — Roo Code / Continue (VSCode)](#7-orquestador-2--roo-code--continue-vscode)
8. [Orquestador 3 — OpenCode (TUI)](#8-orquestador-3--opencode-tui)
9. [Skills: conocimiento reutilizable para el agente](#9-skills-conocimiento-reutilizable-para-el-agente)
10. [Flujo spec-driven: de la idea al código](#10-flujo-spec-driven-de-la-idea-al-código)
11. [Ejemplo end-to-end: API Python + Frontend React](#11-ejemplo-end-to-end-api-python--frontend-react)
12. [Recetario: situaciones habituales](#12-recetario-situaciones-habituales)
13. [Resolución de problemas](#13-resolución-de-problemas)

---

## 1. ¿Qué es esto y para qué sirve?

**DeepLocal Forge es infraestructura, no un IDE ni un asistente.**

Es un servidor de IA local que corre en tu máquina y al que se conectan las herramientas de desarrollo que ya usas: tu terminal, VSCode, o una TUI. Proporciona modelos de lenguaje grandes (LLMs) con endpoints compatibles con la API de OpenAI, de forma que cualquier herramienta que sepa hablar con ChatGPT también sabe hablar con tu stack local.

### Qué puedes hacer con esto

- **Programar con asistencia de IA** en Rust, Python, JavaScript/TypeScript, React, PHP, HTML/CSS sin pagar por cada token
- **Revisar y refactorizar código** con un modelo que entiende el contexto completo de tu proyecto
- **Consultar documentación propia** mediante RAG (Retrieval-Augmented Generation): ingestas tus docs, preguntas en lenguaje natural, el modelo responde citando tus propios documentos
- **Orquestar agentes** que ejecutan tareas complejas en paralelo
- **Trabajar offline** una vez descargados los modelos

### Qué NO es

- No es una plataforma de pago con límites de uso
- No envía tu código a ningún servidor externo
- No requiere cuenta en OpenAI, Anthropic ni ningún otro servicio
- No sustituye al programador — es una herramienta que amplifica tu capacidad

### Arquitectura en una frase

```
Tu herramienta (Aider / VSCode / OpenCode)
        ↓  API compatible con OpenAI
    Ollama (servidor local de modelos)
        ↓
    GPU / CPU de tu máquina
```

El stack también incluye Qdrant (base de datos vectorial para RAG) y servidores MCP (herramientas que el LLM puede invocar: navegar web, gestionar archivos, consultar documentos).

---

## 2. Requisitos de hardware

### Configuración objetivo (óptima)

| Componente | Especificación              | Notas                                    |
|------------|-----------------------------|------------------------------------------|
| GPU        | NVIDIA RTX 3060 · 12 GB VRAM | Stack completo tal como está configurado |
| RAM        | 32 GB                        | Margen para Docker + IDE + modelos       |
| Disco      | 80 GB libres                 | Modelos (~40 GB) + datos + Docker        |
| OS         | Linux (Ubuntu 22.04+)        | Recomendado. WSL2 y macOS: ver nota      |

### Configuración mínima viable

| VRAM disponible | Modelo arquitecto        | Modelo editor           | Calidad resultante          |
|-----------------|--------------------------|-------------------------|-----------------------------|
| 12 GB           | `deepseek-r1:14b` Q4_K_M | `qwen2.5-coder:14b` Q4  | Óptima — stack completo     |
| 8 GB            | `deepseek-r1:7b` Q4_K_M  | `qwen2.5-coder:7b` Q4   | Buena — refactors complejos pueden fallar |
| 6 GB            | `qwen2.5:7b` Q4_K_M      | `qwen2.5-coder:7b` Q4   | Funcional — tareas simples y medianas |
| 4 GB            | `qwen2.5:3b` Q4_K_M      | `qwen2.5-coder:3b` Q4   | Limitada — solo tareas simples; no recomendado para Rust |
| Sin GPU (CPU)   | `qwen2.5:7b` Q4_K_M      | `qwen2.5-coder:7b` Q4   | Muy lento (minutos por respuesta). Solo para pruebas. |

> **Nota sobre 8 GB y 6 GB:** el blueprint usa inferencia secuencial (`OLLAMA_KEEP_ALIVE=0`), lo que significa que arquitecto y editor nunca coexisten en VRAM. Con 8 GB puedes usar modelos 7B con resultados razonables. Los modelos 14B requieren 12 GB.

> **macOS con Apple Silicon (M1/M2/M3/M4):** Ollama soporta Metal. La VRAM compartida cuenta — un M2 Pro con 16 GB de memoria unificada puede correr los modelos 7B con buen rendimiento. Cambia el perfil `gpu` del docker-compose por `cpu` y configura Ollama nativo (sin Docker).

> **WSL2 (Windows):** funciona con NVIDIA GPU si tienes instalados los drivers WSL2 de NVIDIA. Docker Desktop con WSL2 backend es la vía recomendada. Rendimiento similar a Linux nativo.

### Cómo ajustar los Modelfiles para menos VRAM

Si tienes 8 GB o menos, edita `assets/ollama/Modelfile.architect` y `Modelfile.editor`:

```
# Para 8 GB — sustituir los modelos base
# Modelfile.architect
FROM deepseek-r1:7b
PARAMETER num_ctx    4096
PARAMETER temperature 0.5
PARAMETER num_keep   64

# Modelfile.editor
FROM qwen2.5-coder:7b
PARAMETER num_ctx    8192
PARAMETER temperature 0.1
```

Después de editar, recrea las instancias:
```bash
just setup-models
```

---

## 3. Requisitos de software

### Obligatorios

| Software        | Versión mínima | Instalación                                  |
|-----------------|---------------|----------------------------------------------|
| Docker Engine   | 24+           | https://docs.docker.com/engine/install/      |
| Docker Compose  | 2.20+         | Incluido con Docker Engine en Linux          |
| just            | 1.14+         | `cargo install just` o gestor de paquetes    |
| Git             | 2.x           | `apt install git`                            |
| NVIDIA drivers  | 525+          | Solo si tienes GPU NVIDIA                    |
| nvidia-container-toolkit | Cualquiera | Solo GPU — https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html |

### Por orquestador (instala solo el que vayas a usar)

| Orquestador    | Instalación                                       |
|----------------|---------------------------------------------------|
| Aider          | `pip install aider-chat`                          |
| Roo Code       | Extensión de VSCode: buscar "Roo Code" en el marketplace |
| Continue       | Extensión de VSCode: buscar "Continue" en el marketplace |
| OpenCode       | `npm install -g opencode-ai` o ver https://opencode.ai |

### Sobre red / proxy (Traefik y Step CA)

El stack usa Traefik como proxy inverso con TLS (`https://servicio.tu-dominio.local`).
Esto requiere tener Traefik y Step CA ya configurados en tu entorno.

**Si no tienes Traefik:** puedes acceder a todos los servicios directamente por puerto:

| Servicio  | Puerto local     |
|-----------|-----------------|
| Ollama    | `http://localhost:11434` |
| Qdrant    | `http://localhost:6333`  |
| Langflow  | `http://localhost:7860`  |
| n8n       | `http://localhost:5678`  |

Para usar los puertos directos en los orquestadores, configura la URL de Ollama como `http://localhost:11434` (ver secciones 6, 7 y 8).

---

## 4. Setup inicial del stack

### Paso 1: Clonar el repositorio

```bash
git clone <url-del-repo> deeplocal-forge
cd deeplocal-forge
```

### Paso 2: Crear la red Docker externa

Solo se hace una vez. La red `ai_network` es compartida entre todos los servicios del stack.

```bash
just network-create
```

### Paso 3: Arrancar el stack

```bash
# Detecta GPU automáticamente y arranca el perfil correcto
just up
```

Si tienes GPU NVIDIA, verás: `✅ GPU detectada`. El stack arranca el perfil `gpu`.
Sin GPU, arranca el perfil `cpu` — los modelos corren más lentos pero funciona.

Para verificar que todo está corriendo:
```bash
docker ps
# Debes ver: ollama-gpu (o ollama), qdrant, y otros servicios
```

### Paso 4: Descargar modelos y crear instancias

Este paso descarga los modelos (varios GB) y configura las instancias personalizadas del blueprint. Solo hace falta ejecutarlo una vez, o cuando cambies los Modelfiles.

```bash
just setup-models
```

El proceso descarga `deepseek-r1:14b`, `qwen2.5-coder:14b`, `qwen2.5:7b-instruct` y `nomic-embed-text`, y crea tres instancias: `r1-architect`, `qwen-editor` y `rag-bot`.

Para verificar que las instancias están listas:
```bash
docker exec $(docker ps -qf "name=ollama") ollama list
# Debe mostrar: r1-architect, qwen-editor, rag-bot, nomic-embed-text, y los modelos base
```

### Paso 5: Configurar la variable de entorno (solo para uso fuera de Docker)

Para que Aider y los orquestadores de terminal encuentren Ollama:

```bash
export OLLAMA_API_BASE=http://localhost:11434
# Añadir a ~/.bashrc o ~/.zshrc para que persista
echo 'export OLLAMA_API_BASE=http://localhost:11434' >> ~/.bashrc
```

### Modos de operación

No tienes que arrancar todo el stack siempre. Usa el modo que necesites:

```bash
just up-dev      # Solo Ollama + Qdrant — para sesiones de desarrollo con Aider/VSCode
just up-rag      # Ollama + Qdrant + Langflow + n8n — para el bot de consultas RAG
just up-mcp      # Qdrant + servidores MCP (playwright, filesystem, memory)
just up-comfy    # Ollama + ComfyUI — generación de imágenes
just up          # Stack completo
```

Para cambiar de modo liberando VRAM primero:
```bash
just switch-mode dev    # down de lo que haya + up-dev
just switch-mode rag
just switch-mode full
```

---

## 5. Conceptos clave antes de empezar

### El flujo Arquitecto / Editor

El stack separa dos funciones que normalmente hace un solo modelo:

- **Arquitecto (`r1-architect`)**: razona sobre el problema, diseña la solución, produce instrucciones. Basado en DeepSeek-R1 14B. Lento pero preciso en planificación.
- **Editor (`qwen-editor`)**: recibe las instrucciones del arquitecto y aplica los cambios al código. Basado en Qwen2.5-Coder 14B. Rápido y preciso en diffs.

Nunca coexisten en VRAM. El editor entra cuando el arquitecto termina y se descarga (`OLLAMA_KEEP_ALIVE=0`).

### El pipeline pre-LLM

Antes de pedirle nada al modelo, el código debe pasar por las herramientas automáticas del lenguaje: formateador, linter y verificador de tipos. El objetivo es que el modelo solo vea problemas que las herramientas no pueden resolver solas.

```bash
# Rust
cargo fmt && cargo clippy --fix --allow-dirty && cargo check

# Python
ruff format . && ruff check --fix . && mypy .

# TypeScript
prettier --write . && eslint --fix . && tsc --noEmit
```

En Aider esto es `/prevalidate`. En Roo Code y Continue, ejecútalo en el terminal antes de abrir el chat.

### El Critic Pass

Después de que el editor aplica cambios, un paso de revisión explícita:

```
Bug: <descripción>
File: <fichero>
Line: <línea>
Explanation: <por qué es un problema>
Fix: <sugerencia concreta>
```

En Aider: `/critic`. Ver sección 12 para cuándo es obligatorio.

### Memory files: ARCHITECTURE.md y CONSTRAINTS.md

Dos ficheros en la raíz de cada proyecto que el agente lee al inicio de cada sesión. Registran decisiones técnicas adoptadas y restricciones del proyecto. Sin ellos, el LLM puede proponer soluciones contradictorias entre sesiones.

### Skills

Ficheros Markdown con instrucciones procedimentales que el agente lee como contexto. No son plugins ni ejecutables — son texto que el modelo entiende. La carpeta `skills/` incluye los más útiles para este stack. Ver sección 9.

---

## 6. Orquestador 1 — Aider (terminal)

Aider es un asistente de código que opera desde la terminal, lee y modifica ficheros directamente, y se integra con Git. Es el orquestador principal del blueprint.

### Configuración

El fichero `.aider.conf.yml` en la raíz de tu proyecto configura todo el comportamiento. Crea uno para cada proyecto según el lenguaje:

**Para Python:**
```yaml
# .aider.conf.yml en la raíz de tu proyecto Python
model: ollama/r1-architect
architect: true
editor-model: ollama/qwen-editor
editor-edit-format: diff
map-tokens: 256
lint-cmd: ruff check --fix {files}
auto-lint: true
test-cmd: pytest
auto-commits: true
```

**Para TypeScript/React:**
```yaml
model: ollama/r1-architect
architect: true
editor-model: ollama/qwen-editor
editor-edit-format: diff
map-tokens: 256
lint-cmd: eslint --fix {files}
auto-lint: true
test-cmd: vitest run
auto-commits: true
```

**Para Rust:**
```yaml
model: ollama/r1-architect
architect: true
editor-model: ollama/qwen-editor
editor-edit-format: diff
map-tokens: 256
lint-cmd: cargo clippy
auto-lint: true
test-cmd: cargo test
auto-commits: true
```

**Para PHP:**
```yaml
model: ollama/r1-architect
architect: true
editor-model: ollama/qwen-editor
editor-edit-format: diff
map-tokens: 256
lint-cmd: phpstan analyse --level=6 {files}
auto-lint: true
test-cmd: phpunit
auto-commits: true
```

### Arrancar Aider

```bash
cd /tu/proyecto
# La primera vez: copiar los ficheros del stack
# (o usar just init-project si inicias desde cero)

aider
# Aider detecta .aider.conf.yml automáticamente
```

### Comandos esenciales

| Comando | Qué hace |
|---------|----------|
| `/add src/main.py` | Añade un fichero al contexto del modelo |
| `/add ARCHITECTURE.md CONSTRAINTS.md` | Carga la memoria del proyecto |
| `/architect [instrucción]` | Activa el modo arquitecto (R1 planifica, Qwen edita) |
| `/ask [pregunta]` | Pregunta sin modificar código |
| `/run [comando]` | Ejecuta un comando de shell y añade el output al contexto |
| `/model ollama/qwen-editor` | Cambia al editor directamente (sin arquitecto) |
| `/read skills/process/systematic-debugging.md` | Carga una skill como contexto |
| `/prevalidate` | Ejecuta el pipeline pre-LLM (comando personalizado del stack) |
| `/critic` | Ejecuta el Critic Pass (comando personalizado del stack) |
| `/enrich-us` | Enriquece una user story |
| `/plan` | Genera un plan de implementación |
| `/update-arch` | Actualiza ARCHITECTURE.md tras la sesión |
| `/exit` | Sale de Aider |

### Flujo de sesión estándar

```bash
# 1. Arrancar el stack en modo dev
just up-dev

# 2. Ir al proyecto
cd /mi/proyecto

# 3. Arrancar Aider
aider

# 4. Dentro de Aider: cargar contexto
/add ARCHITECTURE.md CONSTRAINTS.md

# 5. Pre-validar el estado actual
/prevalidate

# 6. Trabajar
/architect Think briefly (max 6 steps). [tu instrucción aquí]

# 7. Después de cambios significativos
/critic

# 8. Actualizar memoria
/update-arch
```

### Control del razonamiento de R1

DeepSeek-R1 razona extensamente por defecto. Para controlar cuánto:

```
# Diseño general — acota a 6 pasos
/architect Think briefly (max 6 steps). Focus on the final answer.
[tu instrucción]

# Problema de lifetimes Rust — focaliza el razonamiento
/architect Before answering, reason briefly about:
1. Ownership model
2. Lifetime relationships
3. Trait boundaries
Keep reasoning under 6 steps. Then produce the final solution.

# R1 en bucle — recuperación sin Ctrl+C
Give the answer with minimal reasoning.

# Fallback si R1 no converge
/model ollama/qwen-editor
```

---

## 7. Orquestador 2 — Roo Code / Continue (VSCode)

Roo Code y Continue son extensiones de VSCode que se conectan al Ollama local. Roo Code actúa como agente autónomo con herramientas; Continue como asistente contextual con autocompletado.

### Roo Code

#### Instalación
Buscar "Roo Code" en el marketplace de VSCode e instalar.

#### Configuración

Abrir `Configuración de VSCode` → buscar `Roo Code` → `Edit in settings.json`:

```json
{
  "roo-cline.apiProvider": "openai-compatible",
  "roo-cline.openAiBaseUrl": "http://localhost:11434/v1",
  "roo-cline.openAiApiKey": "ollama",
  "roo-cline.openAiModelId": "qwen2.5-coder:14b",
  "roo-cline.customInstructions": "Read CLAUDE.md, ARCHITECTURE.md, and CONSTRAINTS.md at the start of every task. Run the pre-LLM pipeline before making changes. Follow ai-specs/specs/base-standards.mdc."
}
```

> **Nota sobre el modelo:** Roo Code actúa como agente con herramientas (crea ficheros, ejecuta comandos, navega el proyecto). Para esto, `qwen2.5-coder:14b` tiene mejor function calling que `deepseek-r1:14b`. Usa `r1-architect` solo si quieres planificación pura sin herramientas.

#### Uso con skills

En el chat de Roo Code, menciona el fichero de skill con `@`:

```
@skills/process/systematic-debugging.md
I'm seeing this error in the API: [pega el error]
Follow the debugging process described in the skill.
```

#### Flujo recomendado en Roo Code

1. Abre tu proyecto en VSCode
2. Abre el panel de Roo Code (`Ctrl+Shift+P` → "Roo Code: Open")
3. Carga contexto de arquitectura: menciona `@ARCHITECTURE.md @CONSTRAINTS.md` en el primer mensaje
4. Para tareas complejas, menciona también el plan: `@ai-specs/changes/TICKET-01_backend.md`

### Continue

#### Instalación
Buscar "Continue" en el marketplace de VSCode e instalar.

#### Configuración

El fichero de configuración está en `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "Qwen Editor (local)",
      "provider": "ollama",
      "model": "qwen2.5-coder:14b",
      "apiBase": "http://localhost:11434"
    },
    {
      "title": "R1 Architect (local)",
      "provider": "ollama",
      "model": "deepseek-r1:14b",
      "apiBase": "http://localhost:11434"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Qwen Fast (local)",
    "provider": "ollama",
    "model": "qwen2.5-coder:1.5b",
    "apiBase": "http://localhost:11434"
  },
  "contextProviders": [
    { "name": "file" },
    { "name": "code" },
    { "name": "docs" }
  ],
  "slashCommands": [
    {
      "name": "critic",
      "description": "Run Critic Pass on last change",
      "prompt": "Critically review the last code modification. Format: Bug/File/Line/Explanation/Fix. Focus on real issues only. If none: 'No issues found.'"
    }
  ]
}
```

> **Autocompletado:** `qwen2.5-coder:1.5b` es un modelo pequeño (< 1 GB) que responde en milisegundos. Es el más adecuado para el Tab de autocompletado — no uses un 14B para esto, sería demasiado lento.

Para descargar el modelo de autocompletado:
```bash
docker exec $(docker ps -qf "name=ollama") ollama pull qwen2.5-coder:1.5b
```

#### Uso con skills en Continue

```
@file:skills/process/test-driven-development.md
I need to add tests for the items module. Follow the TDD process.
```

#### Diferencia entre Roo Code y Continue

| Aspecto           | Roo Code                             | Continue                              |
|-------------------|--------------------------------------|---------------------------------------|
| Modo de trabajo   | Agente autónomo (crea, modifica, ejecuta) | Asistente contextual (propone, tú aplicas) |
| Autocompletado    | No                                   | Sí (Tab completion)                   |
| Mejor para        | Tareas complejas, multi-fichero      | Asistencia continua mientras escribes |
| Configuración     | Más compleja                         | Más sencilla                          |

---

## 8. Orquestador 3 — OpenCode (TUI)

OpenCode es una interfaz de terminal (TUI) para agentes de código. Similar a Aider pero con una interfaz visual en el terminal.

### Instalación

```bash
npm install -g opencode-ai
# o
npm install -g @opencode-ai/cli
```

### Configuración

OpenCode usa un fichero de configuración en `~/.config/opencode/config.json` o en el directorio del proyecto:

```json
{
  "model": "ollama/qwen2.5-coder:14b",
  "provider": {
    "ollama": {
      "baseURL": "http://localhost:11434/v1",
      "apiKey": "ollama"
    }
  }
}
```

### Uso con skills

```bash
# Lanzar OpenCode en tu proyecto
cd /mi/proyecto
opencode

# En el chat: menciona la skill que quieres aplicar
# "Read skills/process/systematic-debugging.md and apply it to debug this error: [error]"
```

### Skills.sh e instalación directa

OpenCode está listado como agente compatible en skills.sh. Para instalar skills directamente:

```bash
# Instala la skill en el directorio actual (genera SKILL.md)
npx skills add obra/superpowers --skill systematic-debugging

# Moverla a la carpeta del stack
mv SKILL.md skills/process/systematic-debugging-updated.md
```

---

## 9. Skills: conocimiento reutilizable para el agente

Las skills son ficheros Markdown que el agente lee como contexto. Describen procedimientos: cómo depurar, cómo hacer TDD, cómo diseñar una API. Son agnósticas al modelo y al orquestador.

### Skills incluidas en el stack

**Proceso** (`skills/process/`):

| Skill | Cuándo usarla |
|-------|---------------|
| `systematic-debugging.md` | Cualquier bug, antes de proponer cualquier fix |
| `test-driven-development.md` | Empezar una feature nueva o corregir una regresión |
| `verification-before-completion.md` | Antes de declarar una tarea terminada |
| `dispatching-parallel-agents.md` | Subtareas independientes que pueden ejecutarse en paralelo |

**Calidad** (`skills/quality/`):

| Skill | Cuándo usarla |
|-------|---------------|
| `api-design-principles.md` | Diseñar un endpoint nuevo |
| `security-best-practices.md` | Cualquier endpoint con auth, datos de usuario o input externo |

**Lenguajes** (`skills/languages/`):

| Skill | Cuándo usarla |
|-------|---------------|
| `python-performance-optimization.md` | Cuello de botella en un servicio Python |

**Frontend** (`skills/frontend/`):

| Skill | Cuándo usarla |
|-------|---------------|
| `vercel-react-best-practices.md` | Diseñar o revisar componentes React |

### Cómo cargarlas por orquestador

```bash
# Aider
/read skills/process/systematic-debugging.md

# Roo Code / Continue (VSCode)
@skills/process/systematic-debugging.md

# OpenCode
"Read skills/process/systematic-debugging.md and apply it to..."
```

### Instalar más skills desde skills.sh

El catálogo completo está en https://skills.sh. Para añadir una:

```bash
# 1. Instalar via npx (requiere Node.js)
npx skills add obra/superpowers --skill writing-plans

# 2. Revisar el SKILL.md generado y moverlo
mv SKILL.md skills/process/writing-plans.md

# 3. Actualizar skills/README.md con la nueva entrada
```

---

## 10. Flujo spec-driven: de la idea al código

El flujo spec-driven separa pensamiento e implementación. Evita el error más común del desarrollo asistido por IA: pedirle al modelo que haga algo mal especificado y luego pasarse horas corrigiendo alucinaciones.

### Para proyectos nuevos (Modelo B — spec asistida por IA)

```
1. Describir la idea en lenguaje natural
        ↓
2. /enrich-us  → el arquitecto genera user story enriquecida con criterios de aceptación
        ↓
3. Revisar y aprobar la user story (tú decides)
        ↓
4. /plan       → el arquitecto genera el plan de implementación en ai-specs/changes/
        ↓
5. Revisar y aprobar el plan (tú decides)
        ↓
6. Implementar siguiendo el plan (editor aplica los cambios)
        ↓
7. /critic     → revisión post-implementación
        ↓
8. /update-arch → actualizar memoria arquitectónica
```

### Para proyectos maduros (Modelo A — spec escrita por el humano)

```
1. Humano escribe la spec (api-spec.yml, data-model.md, ARCHITECTURE.md)
        ↓
2. /add ARCHITECTURE.md CONSTRAINTS.md ai-specs/specs/base-standards.mdc
        ↓
3. /architect [objetivo con reasoning budget]
        ↓
4. Editor aplica cambios
        ↓
5. /critic
```

### Inicializar un proyecto nuevo con el stack

```bash
# Desde la raíz de deeplocal-forge
just init-project nombre-del-proyecto

# Esto crea ../nombre-del-proyecto/ con:
# - ARCHITECTURE.md y CONSTRAINTS.md (plantillas)
# - ai-specs/ con todas las specs y plantillas
# - .aider/commands/ con todos los comandos personalizados
# - skills/ copiadas
# - AGENTS.md, CLAUDE.md, etc.

cd ../nombre-del-proyecto
# Editar ARCHITECTURE.md con las decisiones iniciales del stack
# Editar CONSTRAINTS.md con las restricciones del proyecto
# Editar ai-specs/specs/api-spec.yml con los endpoints reales
```

---

## 11. Ejemplo end-to-end: API Python + Frontend React

Este ejemplo construye un microservicio completo usando el flujo spec-driven. Muestra el proceso real de principio a fin: desde la idea hasta el código funcionando.

**El proyecto:** una API de gestión de tareas (FastAPI) con un frontend React.

### 11.1 Setup del proyecto

```bash
# Inicializar desde el stack
cd deeplocal-forge
just init-project task-manager

cd ../task-manager

# Inicializar el repositorio
git init
git add .
git commit -m "chore: initialize project from deeplocal-forge template"
```

### 11.2 Decidir las restricciones iniciales

Edita `CONSTRAINTS.md`:
```markdown
# Project Constraints

## Universal (inherited from base-standards.mdc)
- No TODO or FIXME in committed code without a ticket
- All public APIs must have documentation
- English only in code, comments, and commits

## Project-specific
- Python: FastAPI + SQLAlchemy + Pydantic — no otros frameworks de API
- TypeScript strict mode — no any
- No external API calls — todo local
- Test coverage mínima: 80%
- No autenticación en v1 (fuera de scope)

## Pre-LLM Pipeline
Backend:  ruff format . && ruff check --fix . && mypy .
Frontend: prettier --write . && eslint --fix . && tsc --noEmit
```

### 11.3 Enriquecer la user story (Modelo B)

Arranca Aider en el proyecto:
```bash
# Asegúrate de que el stack está corriendo
cd ~/deeplocal-forge && just up-dev
cd ~/task-manager && aider
```

Dentro de Aider:
```
/add ARCHITECTURE.md CONSTRAINTS.md

/enrich-us
As a user, I want to manage a list of tasks so I can track what I need to do.
```

El arquitecto genera criterios de aceptación, edge cases, requisitos técnicos y de seguridad. Léelo, ajusta lo que no encaje, y guárdalo.

### 11.4 Generar el plan de implementación

```
/plan
TASK-01: Task management API
Backend: FastAPI + SQLAlchemy (SQLite for dev). Endpoints: CRUD for tasks.
Each task has: id (UUID), title (str, max 255), done (bool), created_at, updated_at.
```

Aider genera el plan y lo muestra. Cópialo a `ai-specs/changes/TASK-01_backend.md`:
```
/run cp /dev/stdin ai-specs/changes/TASK-01_backend.md
# (o simplemente edita el fichero manualmente con el output)
```

### 11.5 Implementar el backend

```bash
# Estructura del proyecto Python
mkdir -p backend/src/{tasks,core}
mkdir -p backend/tests/tasks
```

De vuelta en Aider:
```
/add ai-specs/changes/TASK-01_backend.md
/add ai-specs/specs/backend-standards.mdc

/architect Think briefly (max 6 steps).
Implement the backend following the plan in TASK-01_backend.md.
Start with step 1 (schema). TDD: write failing tests first.
```

El flujo real en Aider:
1. El **arquitecto** (R1) analiza el plan y produce instrucciones para el editor
2. El arquitecto se descarga de VRAM
3. El **editor** (Qwen) aplica los diffs al código
4. `auto-lint: true` ejecuta `ruff check --fix` automáticamente
5. Repites para el siguiente paso del plan

Después de cada paso significativo:
```
/run python -m pytest backend/tests/ -v
/critic
```

### 11.6 Actualizar la memoria arquitectónica

Cuando terminas el backend:
```
/update-arch
```

Ejemplo de lo que genera y añade a `ARCHITECTURE.md`:
```markdown
## Data Layer
- **Decision**: SQLite para desarrollo, misma interface SQLAlchemy para producción con PostgreSQL
- **Reason**: Elimina dependencia de Docker para el entorno de desarrollo individual
- **Date**: 2025-03-12

## Error Handling
- **Decision**: HTTPException de FastAPI para errores de API; excepciones de dominio propias en la capa de servicio
- **Reason**: Separación clara entre errores de transporte (HTTP) y errores de negocio
- **Date**: 2025-03-12
```

### 11.7 Generar el plan del frontend

```
/plan
TASK-02: Task management frontend
React + TypeScript + Vite. Connects to localhost:8000/api/v1.
Features: list tasks, add task, mark as done, delete task.
State: TanStack Query for server state. Styling: Tailwind CSS.
```

Guarda el plan en `ai-specs/changes/TASK-02_frontend.md`.

### 11.8 Implementar el frontend

```bash
# En otra terminal (el stack de desarrollo no cambia)
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
npm install @tanstack/react-query tailwindcss @tailwindcss/vite
```

De vuelta en Aider:
```
/add ai-specs/changes/TASK-02_frontend.md
/add ai-specs/specs/frontend-standards.mdc
/read skills/frontend/vercel-react-best-practices.md

/architect Think briefly (max 6 steps).
Implement the frontend following TASK-02_frontend.md.
Apply React best practices from the loaded skill.
TDD: write component tests with vitest before implementation.
```

### 11.9 Verificación final

```
# Backend
/run cd backend && ruff format . && ruff check . && mypy . && pytest -v

# Frontend
/run cd frontend && tsc --noEmit && eslint . && vitest run

# Critic Pass final
/critic
```

Si el Critic Pass detecta algo, corrígelo antes de dar la tarea por terminada (`/verification-before-completion`).

### 11.10 Resultado

Al final del ejemplo tienes:
- `ai-specs/changes/TASK-01_backend.md` y `TASK-02_frontend.md` — los planes que guiaron la implementación
- `ARCHITECTURE.md` actualizado con las decisiones tomadas
- Backend: FastAPI con tests, tipos correctos, pipeline pasando
- Frontend: React con TanStack Query, TypeScript estricto, tests de componentes

---

## 12. Recetario: situaciones habituales

### Inicio de sesión

```
/add ARCHITECTURE.md CONSTRAINTS.md
/prevalidate
```

### Diseñar algo nuevo

```
/add ARCHITECTURE.md CONSTRAINTS.md ai-specs/specs/base-standards.mdc
/architect Think briefly (max 6 steps). Focus on the final answer.
Goal: [describe el objetivo]
Constraints: see CONSTRAINTS.md
```

### Corregir un error de compilación

```
/run cargo check 2>&1   # o: mypy . / tsc --noEmit
/add [fichero con el error]
/ask What is the root cause of this error? Do not suggest fixes yet. Trace the data flow first.
```

### Depurar un comportamiento inesperado

```
/read skills/process/systematic-debugging.md
/ask Follow the systematic debugging process for this issue:
[describe el comportamiento y el error]
```

### Refactorizar un módulo

```
/prevalidate
/add [ficheros a refactorizar] ARCHITECTURE.md CONSTRAINTS.md
/architect Think briefly (max 6 steps).
Refactor [módulo] to [objetivo].
Preserve all existing behavior.
/critic
```

### Escribir tests primero (TDD)

```
/read skills/process/test-driven-development.md
/add [fichero a testear]
/ask Write failing tests first. Do not write implementation yet.
Feature: [descripción]
```

### Añadir un endpoint nuevo

```
/read skills/quality/api-design-principles.md
/add ai-specs/specs/api-spec.yml ai-specs/specs/backend-standards.mdc
/architect Design the API contract for: [endpoint description]
Output: OpenAPI YAML snippet. No implementation code yet.
```

### Revisar seguridad de un endpoint

```
/read skills/quality/security-best-practices.md
/add [fichero del endpoint]
/ask Review this endpoint for security issues following the checklist in the skill.
```

### R1 entra en bucle (`<think>` interminable)

```
# Sin Ctrl+C, escribe en el chat:
Give the answer with minimal reasoning.

# Si no converge en el turno siguiente:
/model ollama/qwen-editor
```

### Trabajar en paralelo (dos features independientes)

```
# Terminal 1 — backend
cd /mi/proyecto
git worktree add ../mi-proyecto-frontend feature/frontend
cd ../mi-proyecto
aider  # trabaja en el backend

# Terminal 2 — frontend
cd ../mi-proyecto-frontend
aider  # trabaja en el frontend independientemente
```

Ver `skills/process/dispatching-parallel-agents.md` para el flujo completo.

### Después de cambios significativos

```
/critic
/update-arch
/run [suite de tests del proyecto]
```

### Cuándo es obligatorio el Critic Pass

| Tipo de cambio | Critic Pass |
|----------------|-------------|
| Formateo, renombrado, comentarios | No necesario |
| Nueva función con firma definida | Recomendado |
| Refactor de módulo o API pública | **Obligatorio** |
| Cambio en lógica de concurrencia | **Obligatorio** |
| Modificación de manejo de errores | **Obligatorio** |
| Cualquier endpoint con auth o datos de usuario | **Obligatorio** |

---

## 13. Resolución de problemas

### El stack no arranca

```bash
# Verificar que Docker está corriendo
docker info

# Verificar que la red existe
docker network inspect ai_network
# Si no existe:
just network-create

# Ver logs del servicio que falla
just logs
# o filtrar por servicio:
docker compose logs ollama-gpu
```

### Ollama no responde

```bash
# Verificar que el contenedor está healthy
docker ps
# La columna STATUS debe mostrar "(healthy)"

# Si no está healthy, ver los logs
docker compose logs ollama-gpu --tail=50

# Verificar manualmente
curl http://localhost:11434/api/tags
```

### Los modelos no están disponibles (`model not found`)

```bash
# Verificar qué hay instalado
docker exec $(docker ps -qf "name=ollama") ollama list

# Si faltan r1-architect, qwen-editor o rag-bot:
just setup-models
```

### Generación muy lenta (< 1 tok/s)

Causas habituales:
1. **Dos modelos en VRAM**: `docker exec $(docker ps -qf "name=ollama") ollama ps` — debe estar vacío o mostrar solo uno
2. **`OLLAMA_KEEP_ALIVE` no es 0**: verificar con `docker exec $(docker ps -qf "name=ollama") env | grep KEEP_ALIVE`
3. **`<think>` sin acotar**: añade `Think briefly (max 6 steps).` al prompt
4. **num_ctx demasiado alto**: verifica los Modelfiles en `assets/ollama/`

### R1 produce respuestas truncadas

El contexto (`num_ctx: 6144`) es insuficiente para el proyecto. Opciones:
1. Usar `map-tokens: 128` para reducir el Repo Map
2. Subir `num_ctx` a `8192` en `Modelfile.architect` y recrear la instancia (`just setup-models`)
3. Añadir solo los ficheros relevantes con `/add` en lugar de depender del Repo Map

### El editor rompe imports o tipos en refactors

Síntoma habitual si el editor no ve todos los ficheros relacionados. Antes del siguiente `/architect`:
```
/add [todos los ficheros que el refactor toca]
/prevalidate
```

### Aider no encuentra los comandos personalizados (`/prevalidate`)

Los comandos deben estar en `.aider/commands/` **en la raíz del proyecto donde lanzas Aider**, no en el directorio de deeplocal-forge. `just init-project` los copia automáticamente. Para un proyecto existente:

```bash
mkdir -p .aider/commands
cp /ruta/a/deeplocal-forge/.aider/commands/* .aider/commands/
```

### Continue/Roo Code no se conecta a Ollama

```bash
# Verificar que Ollama está accesible desde el host
curl http://localhost:11434/api/tags

# Si usas Traefik:
curl https://ollama.tu-dominio.local/api/tags

# Verificar la config de Continue
cat ~/.continue/config.json | python3 -m json.tool

# Para Roo Code: abrir VSCode Output → seleccionar "Roo Code" en el dropdown
```

### Error de GPU / CUDA en el contenedor

```bash
# Verificar drivers NVIDIA en el host
nvidia-smi

# Verificar que nvidia-container-toolkit está instalado
nvidia-container-cli --version

# Probar que Docker puede acceder a la GPU
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
```

Si `nvidia-smi` funciona en el host pero falla en Docker, el problema es `nvidia-container-toolkit`. Seguir la guía oficial: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
