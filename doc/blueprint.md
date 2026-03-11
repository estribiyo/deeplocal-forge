# AI-Assisted Development
**Especificación Técnica · Rust · Python · PHP · JS/TS / Aider · Ollama**
`GPU 12GB VRAM · Inferencia Local · Flujo Secuencial Arquitecto / Editor · v1.8`

---

## Índice

1. [Arquitectura del Sistema](#1-arquitectura-del-sistema)
2. [Configuración de Modelos](#2-configuración-de-modelos)
3. [Gestión de Memoria (VRAM)](#3-gestión-de-memoria-vram)
4. [Configuración de Aider](#4-configuración-de-aider-aiderconfyml)
5. [Control del Razonamiento de R1 (Reasoning Budget)](#5-control-del-razonamiento-de-r1-reasoning-budget)
6. [Metodología de Trabajo](#6-metodología-de-trabajo)
7. [Cobertura Multi-Lenguaje](#7-cobertura-multi-lenguaje)
8. [RAG — Retrieval-Augmented Generation](#8-rag--retrieval-augmented-generation)
9. [Modos de Operación — Gestión del Stack](#9-modos-de-operación--gestión-del-stack)
10. [Resolución de Problemas](#10-resolución-de-problemas)
- [Apéndice — Setup Rápido](#apéndice--setup-rápido)

---

## 1. Arquitectura del Sistema

Flujo de inferencia secuencial para maximizar razonamiento en 12 GB de VRAM. Las responsabilidades de planificación y edición están estrictamente separadas.

| Componente | Especificación | Rol |
|---|---|---|
| GPU | 12 GB VRAM — Q4_K_M target | Inferencia modelos 14B |
| Orquestador | Aider en modo `/architect` | Separa diseño de implementación |
| Servidor | Ollama (API OpenAI compatible) | Gestión local de modelos |
| Lenguaje target | Rust (principal), Python, PHP, JS/TS | Fuerte dependencia de lints y tipos |

---

## 2. Configuración de Modelos

Tres instancias personalizadas (Modelfiles) para funciones distintas. Nunca coexisten en VRAM simultáneamente.

### A. El Arquitecto — `r1-architect`

> **Modelo base:** DeepSeek-R1-14B (Q4_K_M) · Razonamiento lógico y arquitectónico

| Parámetro | Valor | Razón |
|---|---|---|
| `num_ctx` | **6 144** | Con `/add` explícito y `map-tokens: 256` no se necesita más. R1 razona mejor con menos distracciones estructurales. Usar **8192** como fallback si el proyecto tiene dependencias muy dispersas o notas respuestas truncadas. |
| `temperature` | **0.5** | Reducido desde 0.6. Menos divagación, razonamiento más dirigido. Por debajo de 0.5 aparece degeneración repetitiva. |
| `num_keep` | 64 | Mantiene los tokens del prompt de sistema en KV cache entre turnos. |

> ⚠️ **R1 no admite System Prompts extensos.** Usa los prompts por defecto de Aider. Instrucciones adicionales van en el mensaje de usuario, nunca en el system.

```
# Modelfile: r1-architect  (assets/ollama/Modelfile.architect)
FROM deepseek-r1:14b
PARAMETER num_ctx    6144
PARAMETER temperature 0.5
PARAMETER num_keep   64
```

---

### B. El Editor — `qwen-editor`

> **Modelo base:** Qwen2.5-Coder-**14B** (Q4_K_M) · Aplicación de diffs, refactors y coherencia multi-archivo

El editor sube de 7B a 14B. Con `OLLAMA_KEEP_ALIVE=0` e inferencia secuencial cabe en 12GB. El impacto es directo en refactors complejos, gestión de tipos en Rust y cambios multi-archivo donde el 7B cometía errores de imports y lifetimes.

| Parámetro | Valor | Razón |
|---|---|---|
| `num_ctx` | **12 288** | Aumentado desde 8k. El editor necesita ver varios archivos simultáneamente para mantener coherencia en diffs multi-archivo. |
| `temperature` | 0.1 | Casi determinista. Elimina variabilidad en la aplicación de bloques diff. |

```
# Modelfile: qwen-editor  (assets/ollama/Modelfile.editor)
FROM qwen2.5-coder:14b
PARAMETER num_ctx    12288
PARAMETER temperature 0.1
```

---

### C. El Bot RAG — `rag-bot`

> **Modelo base:** Qwen2.5:7B-Instruct (Q4_K_M) · Instruction-following estricto, citación fiel al contexto

Sustituye a `llama3.1:8b`. Qwen2.5-Instruct tiene mejor adherencia al contexto, menos tendencia a mezclar conocimiento propio, y mejor rendimiento en español — crítico para documentos de oposiciones, manuales comerciales, etc.

| Parámetro | Valor | Razón |
|---|---|---|
| `num_ctx` | 32 768 | RAG necesita más contexto que el arquitecto — permite recibir múltiples chunks sin truncar. Subido de 16 384 en v1.10. |
| `temperature` | 0.0 | Totalmente determinista. En RAG la variabilidad es el enemigo. |
| `num_keep` | 64 | Mantiene el system prompt de restricción en KV cache entre turnos. |

```
# Modelfile: rag-bot  (assets/ollama/Modelfile.rag)
FROM qwen2.5:7b-instruct
PARAMETER num_ctx     32768
PARAMETER temperature 0.0
PARAMETER num_keep    64
```

---

### Resumen de parámetros

| Instancia | Modelo base | num_ctx | temperature | Rol |
|---|---|---|---|---|
| `r1-architect` | deepseek-r1:14b Q4_K_M | 6 144 (8 192 fallback) | 0.5 | Planificación y diseño |
| `qwen-editor` | qwen2.5-coder:14b Q4_K_M | 12 288 | 0.1 | Edición y diffs |
| `rag-bot` | qwen2.5:7b-instruct Q4_K_M | 32 768 | 0.0 | Consultas sobre documentos |

> **Modelo rápido opcional:** Si el flujo incluye uso intensivo de `/ask` para consultas triviales (explicar una función, interpretar un error, generar un regex), añadir `qwen2.5:3b` como instancia `fast-ask` (`num_ctx: 4096`, `temperature: 0.3`). Solo merece la pena si el tiempo de respuesta de R1 o Qwen-14B se convierte en fricción real en el día a día — no añadirlo por defecto.

---

### D. Modelos Alternativos — Protocolo A/B

Los modelos base del stack son los mejores disponibles en el momento de escribir este blueprint, pero el ecosistema local evoluciona rápido. Esta sección documenta los candidatos actuales para cada rol y cómo evaluar si merece la pena un swap.

**Candidatos para el Arquitecto (planificación / razonamiento):**

| Modelo | Ventaja sobre R1-14B | Desventaja | Estado |
|---|---|---|---|
| `deepseek-r1:14b` | Referencia — CoT probado en Rust | Verboso, lento | **Actual** |
| `deepseek-r1-distill-qwen:14b` | Menos verbosidad, mejor instruction-following, base Qwen | Razonamiento ligeramente menos profundo que R1 puro | Candidato fuerte |
| `qwen3:14b` (o `qwen3-coder:14b`) | Supera R1 en benchmarks de matemáticas, código y razonamiento general | Más reciente, menos probado en Rust real | Candidato si disponible |
| `phi4-reasoning:14b` | Lógica estructurada más limpia, menos divagación | Menor soporte de herramientas en español | Candidato para proyectos Python/TS |

**Candidatos para el Editor:**

| Modelo | Ventaja | Estado |
|---|---|---|
| `qwen2.5-coder:14b` | Referencia — dominante en benchmarks de edición multi-archivo | **Actual** |
| `qwen3-coder:14b` | Evolución directa — mejora en refactors multi-archivo | Candidato cuando esté disponible en Ollama |

**Protocolo de evaluación A/B (hacer antes de hacer swap definitivo):**

```bash
# 1. Crear Modelfile alternativo con los mismos parámetros
# assets/ollama/Modelfile.architect-alt
FROM deepseek-r1-distill-qwen:14b
PARAMETER num_ctx    6144
PARAMETER temperature 0.5
PARAMETER num_keep   64

# 2. Registrar en Ollama
docker exec Ollama-GPU ollama create r1-architect-alt -f /modelfiles/Modelfile.architect-alt

# 3. Cambiar en Aider para la sesión de prueba
# En .aider.conf.yml temporalmente:
# model: ollama/r1-architect-alt

# 4. Usar el mismo prompt de benchmark en ambos modelos:
```

```
/architect

Think briefly (max 6 steps). Focus on the final answer.

Design the ownership model for a concurrent Rust module that:
- Shares read access to a config struct across threads
- Writes to a log buffer from multiple producers
- Exposes a public API without leaking internal types

Produce: trait definitions, ownership annotations, no implementation code.
```

> **Criterios de decisión:** velocidad de respuesta, tamaño del `<think>` sin reasoning budget, corrección de los tipos Rust propuestos, ausencia de imports inexistentes. Si el candidato iguala o supera en los tres, hacer el swap y actualizar el Modelfile.

> **Nota sobre Qwen3:** la serie completa no estaba disponible en Ollama en el momento de escribir este blueprint. Verificar con `ollama search qwen3` antes de intentar el pull.

---

## 3. Gestión de Memoria (VRAM)

Tres directivas críticas para evitar colisiones en GPU. Sin ellas, el swap de modelos es no determinista.

### Directiva 1 — `OLLAMA_KEEP_ALIVE=0`

Por defecto, Ollama retiene el modelo en VRAM 5 minutos tras la inferencia. Si Aider lanza el editor antes de que expire ese timer, ambos modelos compiten por los 12 GB.

```bash
# Añadir a .bashrc o al entorno de sesión
export OLLAMA_KEEP_ALIVE=0

# Verificar que se descargó correctamente
ollama ps   # debe devolver lista vacía tras la inferencia
```

### Directiva 2 — `map-tokens: 256`

El Repo Map que Aider inyecta en el contexto tiene un efecto contraintuitivo con modelos de reasoning: **cuanto más grande, peor razona R1**. El modelo intenta procesar la estructura completa del repo antes de pensar en el problema, expandiendo el `<think>` innecesariamente.

Con `256` el arquitecto recibe estructura mínima y se centra en los archivos que le das explícitamente con `/add`. Esto mejora la precisión del razonamiento en proyectos de cualquier tamaño.

> **map-tokens adaptativo según tamaño de proyecto:**
>
> | Tipo de proyecto | map-tokens recomendado |
> |---|---|
> | Microservicio (<20 archivos) | 512 |
> | Proyecto mediano (20-100 archivos) | 256 |
> | Monorepo (>100 archivos) | 128 |
>
> **Flujo correcto con map-tokens bajo:**
> ```
> /add src/parser.rs
> /add src/ast.rs
> /architect Refactor the ownership model
> ```
> El modelo razona sobre los archivos relevantes, no sobre todo el proyecto.

> ⚠️ Si trabajas en un proyecto con dependencias muy dispersas y R1 no encuentra referencias, sube a 512 de forma empírica. No más.

### Directiva 3 — Inferencia Secuencial

El modo `/architect` de Aider garantiza el orden:
1. R1 planifica y produce instrucciones
2. Ollama descarga R1 (gracias a `KEEP_ALIVE=0`)
3. Qwen-14B aplica los diffs

Nunca coexisten en ejecución.

---

## 4. Configuración de Aider (`.aider.conf.yml`)

Este archivo reside en la raíz del proyecto. Automatiza el flujo completo sin flags manuales.

```yaml
model: ollama/r1-architect
architect: true
editor-model: ollama/qwen-editor
editor-edit-format: diff

# Límites de Contexto
map-tokens: 256
# cache-prompts: false  ← OMITIR: solo funciona con API Anthropic, no con Ollama local

# Integración con Rust (ajustar lint-cmd según el lenguaje del proyecto)
lint-cmd: cargo clippy
auto-lint: true      # ejecuta lint automáticamente tras cada cambio del editor
auto-commits: true
suggest-shell-commands: true

# Conexión Local (gestionar vía entorno, no en este archivo)
# export OLLAMA_API_BASE=http://localhost:11434
```

> **`auto-lint: true`** cierra el ciclo de corrección: LLM aplica cambio → lint detecta errores → LLM los ve y corrige en el siguiente turno. Sin esto, los errores de lint solo se ven si los ejecutas manualmente.

> **Por lenguaje:** cambiar `lint-cmd` según el proyecto — `ruff check --fix {files}` para Python, `phpstan analyse --level=6 {files}` para PHP, `eslint --fix {files}` para JS/TS.

---

## 5. Control del Razonamiento de R1 (Reasoning Budget)

DeepSeek-R1 fue entrenado con Chain-of-Thought reinforcement. Puede producir razonamientos cortos y correctos, pero tiende a ser exhaustivo si no se le acota. Sin un presupuesto explícito, el bloque `<think>` puede alcanzar 800–1500 tokens en tareas simples.

> ⚠️ **El reasoning budget va SIEMPRE en el mensaje de usuario** (lo que escribes en `/architect`). Nunca en el Modelfile como `SYSTEM` — eso sí degrada el modelo.

### Tabla de Patrones por Tipo de Tarea

| Situación | Prompt de Control | Tokens `<think>` típicos |
|---|---|---|
| Sin control (defecto) | Sin instrucción adicional | 800 – 1500 (muy lento) |
| Diseño general de API | `Think briefly (max 6 steps). Focus on the final answer.` | 80 – 200 |
| Problema de lifetimes / traits | `Reason briefly about: (1) ownership (2) lifetimes (3) trait bounds. Max 6 steps.` | 100 – 250 |
| Rescate de bucle activo | `Give the answer with minimal reasoning.` | < 80 (recuperación inmediata) |

### Plantillas de Prompt

**Patrón 1 — Diseño general con reasoning gate**
```
/architect

Goal:
[describe el objetivo]

Constraints:
- [restricción 1]
- [restricción 2]

Focus reasoning on:
1. [aspecto clave 1]
2. [aspecto clave 2]

Use at most 6 reasoning steps. Then give the final plan.
```

**Patrón 2 — Lifetimes y ownership (Rust específico)**
```
/architect

Before answering, reason briefly about:
1. ownership model
2. lifetime relationships
3. trait boundaries

Keep reasoning under 6 steps.
Then produce the final Rust solution.
```

**Patrón 3 — Plan separado de implementación**
```
# Paso 1: pedir solo el plan
/architect
Think briefly (max 6 steps). Produce a concise plan only. Do not write code yet.
Goal: [objetivo]

# Paso 2: implementar sobre el plan
/architect
Use the previous plan. Generate the code changes required.
```

**Patrón 4 — Rescate de bucle activo (sin Ctrl+C)**
```
# Si el bloque <think> no converge, escribe en el chat:
Give the answer with minimal reasoning.
# R1 reutiliza el reasoning interno y responde sin perder el contexto.
```

> **Impacto en VRAM:** El KV cache crece linealmente con los tokens generados. Un `<think>` de 1500 tokens consume ~3x más cache que uno de 150. Con `num_ctx` reducido a 8192, acotar el razonamiento es aún más importante.

---

## 6. Metodología de Trabajo

### Pipeline de Pre-validación (ejecutar ANTES del LLM)

Antes de invocar al arquitecto o editor, el código debe pasar por esta secuencia. El objetivo es que el LLM reciba contexto limpio: sin ruido de estilo, sin advertencias triviales. Cada token gastado en problemas que el compilador resuelve solo es un token que no se gasta en razonamiento real.

```bash
# Secuencia obligatoria antes de /architect o /ask (Rust)
cargo fmt                        # normaliza estilo — idempotente, sin riesgo
cargo clippy --fix --allow-dirty # resuelve advertencias automáticas
cargo check                      # valida tipos y borrowck sin compilar

# En Aider — una sola línea:
# /run cargo fmt && cargo clippy --fix --allow-dirty && cargo check
```

| Comando | Qué resuelve solo | Qué deja para el LLM |
|---|---|---|
| `cargo fmt` | Indentación, espacios, imports desordenados | Nada — solo normaliza. Siempre primero. |
| `cargo clippy --fix` | Unwraps obvios, clones innecesarios, patrones redundantes | Warnings que requieren decisión de diseño |
| `cargo check` | Confirma que el código compila tras los fixes | Errores de tipos, lifetimes, traits no resueltos |

---

### Memoria Arquitectónica del Proyecto

Los LLM no recuerdan decisiones entre sesiones. Sin memoria explícita, iteraciones sucesivas producen inconsistencias — el modelo puede proponer `Arc<Mutex<T>>` en una sesión y `Rc<RefCell<T>>` en la siguiente para el mismo problema.

La solución es mantener dos archivos en la raíz del proyecto que Aider incluye como contexto estable:

> **Propósito principal:** `ARCHITECTURE.md` y `CONSTRAINTS.md` están pensados para los **proyectos que se desarrollan con este stack**, no solo para el stack en sí. Al iniciar un proyecto nuevo, se copian estos archivos a la raíz del nuevo repositorio y se adaptan al contexto específico. El stack incluye versiones base para proyectos Rust/axum que sirven como punto de partida.

**`ARCHITECTURE.md`** — decisiones técnicas adoptadas:
```markdown
# Architecture Decisions

## Concurrency
- Use Arc<Mutex<T>> for shared state across threads
- Async runtime: tokio

## Error handling
- Use thiserror for library errors
- Use anyhow for application errors

## Memory
- Parser uses arena allocation (bumpalo)
- Prefer zero-copy parsing where possible
```

**`CONSTRAINTS.md`** — restricciones del proyecto:
```markdown
# Project Constraints

- No unsafe Rust without explicit justification
- Prefer iterators over manual loops
- All public APIs must have doc comments
- No unwrap() in production paths — use proper error propagation
- Async must use tokio, not async-std
```

> **Cuándo actualizar:** después de cualquier decisión arquitectónica relevante, añade una línea. No es un proceso automático — es un hábito deliberado. El comando útil:
> ```
> /add ARCHITECTURE.md
> /ask Append the architectural decisions introduced in the last change.
> ```

> **En otros lenguajes:** los mismos archivos funcionan para Python, PHP y JS/TS. Adaptar el contenido al ecosistema (ej. "usar Pydantic para validación", "PSR-12 obligatorio", "hooks de React deben seguir reglas de eslint-plugin-react-hooks").

---

### Critic Pass — paso estándar post-compilación

Después de que el editor aplica cambios y `cargo check` pasa sin errores, el pipeline no está completo. El compilador valida tipos y lifetimes, pero no detecta bugs lógicos, regresiones de rendimiento ni asunciones incorrectas sobre el comportamiento del código.

El Critic Pass es un `/ask` obligatorio tras cada cambio significativo — no tras cada diff trivial, pero sí tras cualquier refactor, cambio de API o modificación de lógica de concurrencia:

```
/ask

Critically review the last code modification.
Focus on:
- hidden bugs or incorrect logic
- performance regressions
- incorrect ownership or lifetime assumptions
- edge cases not covered
- violations of CONSTRAINTS.md

Be concise. List only real issues, not style.
```

**Cuándo ejecutarlo:**

| Tipo de cambio | Critic Pass |
|---|---|
| Formateo, renombrado, comentarios | No necesario |
| Nueva función con firma definida | Recomendado |
| Refactor de módulo o API pública | **Obligatorio** |
| Cambio en lógica de concurrencia | **Obligatorio** |
| Modificación de manejo de errores | **Obligatorio** |

> **Importante:** el Critic Pass no es un bucle automático de autocorrección. Si detecta un problema real, el siguiente paso es siempre validar manualmente el plan de corrección antes de pedir al editor que lo aplique. Un bucle LLM → corrección → LLM sin supervisión puede entrar en regresión infinita si el error es de diseño base.

---

### Tabla A — Selección de Modelo por Situación

| Situación | Modelo | Razón Técnica |
|---|---|---|
| Diseño de tipos / traits / lifetimes | `r1-architect` | Razonamiento profundo sobre contratos de tipos |
| Refactor de estructura de módulos | `r1-architect` | Visión global del proyecto via Repo Map mínimo + `/add` |
| Implementar función con firma definida | `qwen-editor` directo | Velocidad — el arquitecto ya produjo el plan |
| Aplicar diff, tests unitarios, formateo | `qwen-editor` | Baja latencia, alta precisión en formato |
| Debugging de error de compilador | `qwen-editor` + `/run cargo check` | Ver el error real antes de pedir la corrección |
| R1 entra en bucle | `qwen2.5-coder:14b` via `/model` | Fallback estable sin reiniciar sesión |

### Tabla B — Comandos de Flujo de Trabajo

| Comando / Acción | Cuándo usarlo | Efecto |
|---|---|---|
| `/run cargo fmt && cargo clippy --fix --allow-dirty && cargo check` | Antes de cualquier `/architect` | Limpia el código para que el LLM solo vea problemas reales |
| `/add ARCHITECTURE.md CONSTRAINTS.md` | Al inicio de cada sesión de diseño | Da contexto estable al arquitecto sobre decisiones previas |
| `/architect [instrucción con reasoning gate]` | Refactor complejo, diseño de API | R1 con razonamiento acotado |
| `/run grep -r 'symbol'` | Antes de eliminar código | Confirma ausencia de referencias |
| `/ask [critic pass prompt]` | Tras refactors significativos | Segunda pasada de revisión sin modelo adicional |
| `/model ollama/qwen2.5-coder:14b` | R1 en bucle o tarea de implementación directa | Swap manual sin reiniciar sesión |
| `/add <archivo>` | Antes de pedir un diff | Sin `/add` el editor no puede aplicar cambios |

### Comandos Personalizados de Aider

Aider permite definir comandos `/nombre` propios en `.aider/commands/`. Reducen fricción al eliminar la necesidad de recordar y escribir los prompts de pipeline y critic en cada sesión.

**Estructura:**
```
.aider/
  commands/
    prevalidate    ← ejecuta el pipeline pre-LLM
    critic         ← lanza el Critic Pass
```

**`.aider/commands/prevalidate`** (Rust — adaptar por proyecto):
```
/run cargo fmt && cargo clippy --fix --allow-dirty && cargo check
```

**`.aider/commands/critic`**:
```
/ask Critically review the last code modification. For each issue found, use exactly this format:

Bug: <one-line description>
File: <filename>
Line: <line number or range>
Explanation: <why it is a problem>
Fix: <concrete suggestion>

Focus on: hidden bugs or incorrect logic, performance regressions, incorrect ownership or lifetime assumptions, edge cases not covered, violations of CONSTRAINTS.md. If no issues found, respond only: "No issues found."
```

**Uso en sesión:**
```
/prevalidate      ← antes de cada /architect
/critic           ← después de cada cargo check exitoso en cambios significativos
```

> **Por lenguaje:** crear un `.aider/commands/prevalidate` distinto por proyecto con el pipeline del ecosistema correspondiente (`ruff + mypy`, `php-cs-fixer + phpstan`, `prettier + eslint + tsc`). El comando `/critic` es universal — funciona igual en todos los lenguajes.

El flujo arquitecto/editor y el pipeline de pre-validación son agnósticos al lenguaje. Lo que cambia por ecosistema es el conjunto de herramientas que alimentan al LLM con señal real antes de que intervenga.

### Tabla Comparativa — Equivalencias por Ecosistema

| Rol | Rust | Python | PHP | JS / TS |
|---|---|---|---|---|
| Formatear | `cargo fmt` | `ruff format` | `php-cs-fixer fix` | `prettier --write .` |
| Lint / fix auto | `cargo clippy --fix` | `ruff check --fix` | `phpstan` (no fix) | `eslint --fix` |
| Verificar tipos | `cargo check` | `mypy .` | `phpstan analyse` | `tsc --noEmit` |
| Tests | `cargo test` | `pytest` | `phpunit` | `vitest run` |
| Modelo recomendado | Fast o Deep según tarea | Fast (tipos) / Deep (lógica) | Deep (PHP legacy) | Fast (TS) / Deep (JS puro) |

> **Regla general:** A más señal del compilador/tipado, más autonomía puede tener el LLM. TypeScript estricto y Python con mypy permiten usar el editor directamente. PHP sin tipos o JS puro requieren pasar por el arquitecto incluso para implementación.

---

### A. Python

```bash
# Pipeline pre-LLM para proyectos Python
ruff format .                  # formatea (equivale a black)
ruff check --fix .             # lint + fix automático
mypy .                         # verificación de tipos

# En Aider:
# /run ruff format . && ruff check --fix . && mypy .
```

| Herramienta | Qué resuelve solo | Qué deja para el LLM |
|---|---|---|
| `ruff format` | Indentación, comillas, imports | Nada — solo normaliza |
| `ruff check --fix` | Imports no usados, f-strings incorrectos, patrones obsoletos | Errores lógicos, type mismatches complejos |
| `mypy` | Informa de type errors — no los corrige solo | Todos los errores de tipos que mypy reporta |

> ⚠️ Usar `mypy --strict` o `strict = true` en `pyproject.toml`. Sin strict, el LLM recibe menos contexto sobre los contratos de tipos.

**`.aider.conf.yml` para Python:**
```yaml
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

---

### B. PHP

```bash
# Pipeline pre-LLM para proyectos PHP
php-cs-fixer fix               # formatea según PSR-12
phpstan analyse --level=6      # análisis estático

# En Aider:
# /run php-cs-fixer fix && phpstan analyse --level=6
```

| Herramienta | Qué resuelve solo | Qué deja para el LLM |
|---|---|---|
| `php-cs-fixer` | Estilo PSR-12, espacios, llaves, imports | Nada — solo normaliza |
| `phpstan` nivel 1-3 | Clases inexistentes, métodos no definidos | La mayoría de errores lógicos |
| `phpstan` nivel 6+ | Type mismatches, nullable sin check, retornos incorrectos | Errores de lógica de negocio y arquitectura |

> ⚠️ En proyectos PHP legacy (sin tipos declarados), usar modo Deep (`r1-architect`) incluso para tareas de implementación.

**`.aider.conf.yml` para PHP:**
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

---

### C. JavaScript / TypeScript (React, Node)

```bash
# Pipeline pre-LLM — TypeScript (recomendado)
prettier --write .             # formatea
eslint --fix .                 # lint + fix automático
tsc --noEmit                   # verifica tipos sin compilar

# Pipeline pre-LLM — JavaScript puro
prettier --write .
eslint --fix .

# En Aider (TS):
# /run prettier --write . && eslint --fix . && tsc --noEmit
```

| Stack | Herramienta | Señal al LLM | Modelo recomendado |
|---|---|---|---|
| TypeScript estricto | `tsc --noEmit` | Alta — errores de tipos explícitos | Editor directo para la mayoría de tareas |
| TypeScript relajado | `tsc` + `eslint` | Media — algunos tipos inferidos | Arquitecto para refactor, editor para implementación |
| JavaScript + React | `eslint` (react-hooks) | Baja — solo reglas de hooks y patrones | Arquitecto siempre para diseño |
| JavaScript puro | `eslint` únicamente | Mínima — sin tipado estático | Arquitecto siempre. Evaluar migrar a TS. |

**`.aider.conf.yml` para TypeScript:**
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

> **React + hooks:** Añadir `eslint-plugin-react-hooks`. Las reglas de dependencias de `useEffect` son el error más común que un LLM introduce en React.

---

## 8. RAG — Retrieval-Augmented Generation

El RAG es un caso de uso radicalmente distinto al de desarrollo. El objetivo no es razonar ni generar código: es recuperar fragmentos precisos de documentos y citarlos sin contaminación del conocimiento propio del modelo.

### A. Modelo para RAG — `rag-bot`

> **Modelo base:** Qwen2.5:7B-Instruct (Q4_K_M) · Instruction-following estricto, mejor español, fidelidad al contexto

`qwen2.5:7b-instruct` sustituye a `llama3.1:8b` por tres razones concretas: mejor adherencia a instrucciones de restricción, menor tendencia a mezclar conocimiento propio con el contexto recuperado, y mejor rendimiento en español — crítico para documentos de oposiciones, manuales comerciales y temarios.

Los modelos de código (`r1-architect`, `qwen-editor`) son contraproducentes para RAG estricto: R1 razona sobre si el fragmento es correcto en lugar de citarlo, y Qwen-Coder está afinado para generar, no para restringirse.

---

### B. Prompt Anti-Alucinación (plantilla parametrizable)

```
SYSTEM:
Eres un asistente especializado en {TEMA}.
REGLAS ESTRICTAS — debes seguirlas sin excepción:
1. Responde ÚNICAMENTE con información del contexto proporcionado.
2. Si la respuesta está en el contexto, cita el fragmento exacto entre comillas
   e indica de qué parte del documento procede.
3. Si la información NO está en el contexto, responde exactamente:
   "No encuentro información sobre esto en los documentos disponibles."
4. NUNCA uses tu conocimiento propio. NUNCA inventes ni infieras.
5. NUNCA digas "según mis conocimientos" o frases similares.
6. SIEMPRE incluye citas textuales del documento en tu respuesta, aunque la
   información parezca obvia. Sin cita, no hay respuesta válida.

CONTEXTO RECUPERADO:
{CHUNKS_DEL_RETRIEVER}

USER:
{PREGUNTA_DEL_USUARIO}
```

> **Parametrizable:** Sustituir `{TEMA}` por el ámbito del bot. Langflow o n8n inyectan `{CHUNKS_DEL_RETRIEVER}` desde Qdrant antes de enviar al modelo.

---

### C. Pipeline de Ingesta de Documentos

| Tipo de documento | Herramienta de extracción | Chunk / Overlap | Consideraciones |
|---|---|---|---|
| PDF digital (texto) | Langflow PDF loader nativo | **512 / 64** | Para documentos explicativos (manuales, normativa). Chunks más largos preservan el contexto semántico. |
| PDF técnico denso | Langflow PDF loader nativo | **384 / 80** | Para documentación técnica, especificaciones, temarios de oposición. Overlap mayor mejora el recall en español. |
| PDF escaneado (OCR) | Tesseract / OCRmyPDF antes de ingestar | 384 / 80 | Limpiar ruido antes del chunking. OCR con errores produce chunks inutilizables. Preprocesar fuera de Langflow. |
| Markdown / HTML | Langflow text loader + **split por headers** | Por sección | Respetar la estructura de headers como límite de chunk. Mejor que split por tokens para documentos estructurados. |
| CSV / datos tabulares | Convertir a texto narrativo antes de ingestar | Por fila/grupo | No chunkear filas crudas. Describir cada fila como texto narrativo. |

> **Regla práctica:** usar 512/64 por defecto. Bajar a 384/80 si el bot devuelve respuestas cortadas o fragmentos que parecen perder el hilo entre chunks consecutivos.

> ⚠️ **Documentos > 100 páginas:** dividir por temas en colecciones Qdrant separadas. Una colección por tema reduce el espacio vectorial y mejora la precisión del retriever.

> **Truco para mejorar recuperación:** añadir un título al inicio de cada chunk antes de ingestarlo:
> ```
> [SECCIÓN] Procedimiento de baja laboral
> El trabajador deberá presentar...
> ```
> Esto mejora la similitud semántica en las consultas.

---

### D. Reranker (mejora de precisión del retriever)

El pipeline RAG estándar recupera los N chunks más similares semánticamente, pero "similar semánticamente" no siempre significa "más relevante para la pregunta". Un reranker evalúa cada chunk recuperado contra la pregunta real y reordena por relevancia real antes de enviar al LLM.

**Pipeline sin reranker:**
```
Pregunta → Qdrant → top 10 chunks → LLM
```

**Pipeline con reranker:**
```
Pregunta → Qdrant → top 20 chunks → bge-reranker → top 5 chunks → LLM
```

El LLM recibe menos chunks pero más relevantes — reduce alucinaciones por contexto ruidoso y mejora la calidad de las citas.

**Modelo recomendado:** `BAAI/bge-reranker-v2-m3` — buen soporte multilingüe (español incluido), ligero (~570MB), compatible con Langflow vía componente de reranking.

**Integración en Langflow:**
```
[PDF Loader] → [Chunker] → [Embeddings → Qdrant]
                                    ↓
[Pregunta usuario] → [Qdrant retriever (top 20)] → [BGE Reranker (top 5)] → [rag-bot]
```

> **Nota:** El reranker corre en CPU sin problema dado su tamaño. No compite por VRAM con Ollama.

---

### E. Modelo de Embeddings

| Modelo | Tamaño | Recomendado para |
|---|---|---|
| `nomic-embed-text` | ~274 MB | **Actual** — uso general en español e inglés. El más equilibrado para este stack. |
| `BAAI/bge-m3` | ~570 MB | **Alternativa recomendada** — mejor recall en vocabulario técnico y corpus mixtos. Misma familia que `bge-reranker-v2-m3`, coherencia garantizada entre embedding y reranker. |
| `Qwen3-Embedding-8B` | ~5 GB | Candidato de upgrade — líder en benchmarks multilingüe. Requiere ~5GB RAM (CPU offload). |
| `all-minilm` | ~46 MB | Solo si velocidad de ingesta es prioritaria sobre calidad. |

> **Importante:** El modelo de embeddings usado en la ingesta debe ser el mismo en las consultas. Cambiar de modelo requiere re-ingestar todos los documentos.

---

### F. Reranker

| Modelo | Tamaño | Recomendado para |
|---|---|---|
| `BAAI/bge-reranker-v2-m3` | ~570 MB | **Actual** — buen soporte multilingüe, ligero, compatible con Langflow. Corre en CPU sin competir con VRAM de Ollama. |
| `Qwen3-Reranker-8B` (o 4B) | ~5 GB / ~2.5 GB | Mejor precisión que BGE en español. Upgrade natural si se usa `Qwen3-Embedding-8B`. La variante 4B cabe cómodamente en CPU RAM. |

---

### G. Hybrid Search en Qdrant (mejora avanzada)

El retriever estándar opera solo sobre similitud vectorial. Hybrid search combina búsqueda vectorial + BM25 (keyword), lo que mejora el recall especialmente en consultas con términos técnicos o nombres propios que los embeddings semánticos tienden a diluir.

**Pipeline sin hybrid search:**
```
Pregunta → embedding → similitud coseno → top N chunks
```

**Pipeline con hybrid search:**
```
Pregunta → [embedding → similitud coseno] + [BM25 → keyword match] → RRF fusion → top N chunks → reranker
```

**Activación en Qdrant** (requiere colección con índice de texto):
```python
# Al crear la colección — añadir índice de texto para BM25
client.create_collection(
    collection_name="docs",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
)
client.create_payload_index(
    collection_name="docs",
    field_name="text",
    field_schema=TextIndexParams(
        type=TextIndexType.TEXT,
        tokenizer=TokenizerType.MULTILINGUAL,  # importante para español
        min_token_len=2,
        max_token_len=20,
    )
)
```

**En Langflow:** activar el parámetro `sparse_vectors` o `hybrid` en el componente de Qdrant retriever si está disponible en la versión del stack.

> **Cuándo vale la pena:** en colecciones con vocabulario técnico denso (normativa legal, manuales industriales, código). Para documentos conversacionales o narrativos, el retriever vectorial puro ya es suficiente.

---

## 9. Modos de Operación — Gestión del Stack

Con 12GB de VRAM no es viable ejecutar todos los servicios simultáneamente. Cada modo levanta solo los servicios necesarios y hace `down` del modo anterior.

### A. Definición de Modos

| Modo | Servicios activos | Modelo Ollama | Uso típico |
|---|---|---|---|
| `dev` | Ollama + Qdrant | `r1-architect` + `qwen-editor` | Sesiones de desarrollo con Aider. Sin Langflow ni n8n. |
| `rag` | Ollama + Qdrant + Langflow + n8n | `rag-bot` + `nomic-embed-text` | Servicio del bot de consultas. Sin ComfyUI. |
| `comfy` | Ollama + ComfyUI | Modelo generativo | Generación de imágenes. Servicio puntual y exclusivo. |
| `full` (cpu/gpu) | Todo el stack | Según hardware detectado | Solo para pruebas de integración. |

> ⚠️ Siempre hacer `down` antes de cambiar de modo. Servicios residuales compiten por VRAM aunque no estén en uso activo.

---

### B. Extensión del justfile

```bash
# just up-dev  — solo Ollama + Qdrant (modo desarrollo con Aider)
up-dev:
    @just prepare-environment
    export $(grep -v '^#' .env | xargs) && \
    docker compose --profile ${PROFILE_VAR} down && \
    docker compose up ollama-${PROFILE_VAR} qdrant --build -d
    @echo '✅ Modo DEV activo: Ollama + Qdrant'

# just up-rag  — Ollama + Qdrant + Langflow + n8n
up-rag:
    @just prepare-environment
    export $(grep -v '^#' .env | xargs) && \
    docker compose --profile ${PROFILE_VAR} down && \
    docker compose up ollama-${PROFILE_VAR} qdrant langflow-${PROFILE_VAR} n8n-workflow --build -d
    @echo '✅ Modo RAG activo: Ollama + Qdrant + Langflow + n8n'

# just up-comfy — Ollama + ComfyUI (uso puntual)
up-comfy:
    @just prepare-environment
    export $(grep -v '^#' .env | xargs) && \
    docker compose --profile ${PROFILE_VAR} down && \
    docker compose up ollama-${PROFILE_VAR} comfyui-${PROFILE_VAR} --build -d
    @echo '✅ Modo COMFY activo: Ollama + ComfyUI'
```

---

### C. Actualización de `setup-models`

```bash
# Añadir al bloque de creación de instancias en setup-models:

echo '🔧 Descargando modelo de embeddings...'
docker exec ${CONTAINER_NAME} ollama pull nomic-embed-text

echo '🔧 Creando instancia rag-bot...'
if docker exec ${CONTAINER_NAME} ollama list | grep -q 'rag-bot'; then
    echo '✅ rag-bot ya existe.'
else
    docker exec ${CONTAINER_NAME} ollama create rag-bot -f /modelfiles/Modelfile.rag
    echo '✅ rag-bot creado.'
fi
```

---

## 10. Resolución de Problemas

| Síntoma | Diagnóstico | Solución |
|---|---|---|
| `< 1 tok/s` (generación muy lenta) | KV cache saturado — `num_ctx` demasiado alto o `<think>` sin acotar | Verificar reasoning budget en el prompt. Si persiste, `ollama ps` para confirmar que no hay dos modelos cargados. Reducir `num_ctx` a 6144 en `r1-architect`. |
| Bloque `<think>` > 500 tokens sin conclusión | R1 sin presupuesto de razonamiento acotado | Escribe `Give the answer with minimal reasoning.` Si no converge en 1 turno: Ctrl+C y `/model ollama/qwen2.5-coder:14b`. |
| Editor rompe imports o tipos en refactor | 7B insuficiente para cambios multi-archivo | Confirmar que el Modelfile.editor usa `qwen2.5-coder:14b` (no 7B). Recrear instancia si es necesario. |
| Errores de formato en el diff aplicado | Temperatura del editor demasiado alta o archivo no cargado | Verificar `temperature: 0.1` en `qwen-editor` y que el archivo está en `/add`. |
| `model not found / connection refused` | Ollama no está corriendo o el Modelfile no fue creado | `ollama serve` en otra terminal. Ejecutar `ollama create r1-architect -f Modelfile`. |
| Dos modelos compitiendo (OOM en GPU) | `OLLAMA_KEEP_ALIVE` no está en 0 | `echo $OLLAMA_KEEP_ALIVE` debe devolver `0`. Relanzar el entorno. |
| R1 propone decisiones contradictorias entre sesiones | Sin memoria arquitectónica | Crear `ARCHITECTURE.md` y `CONSTRAINTS.md`. Añadirlos con `/add` al inicio de cada sesión. |
| RAG responde con conocimiento propio | `temperature` > 0 o prompt de sistema incompleto | Verificar `temperature: 0.0` en `rag-bot`. Revisar las 5 reglas del system prompt. |
| Chunks irrelevantes en respuestas RAG | Colección Qdrant demasiado grande o chunking por tokens en documentos estructurados | Separar por tema en colecciones distintas. Usar split por headers para Markdown/HTML. |

---

## 11. MCP Servers — Herramientas para el LLM

MCP (Model Context Protocol) permite al LLM **actuar**, no solo responder. La distinción clave respecto a n8n:

- **n8n** ejecuta una herramienta porque tú lo programas en un workflow
- **El LLM via MCP** decide autónomamente qué herramienta usar, cuándo y con qué argumentos

### Dos categorías

**Contenedores siempre activos** (`just up-mcp`) — requieren infraestructura propia:

| Servidor | Justificación |
|---|---|
| `mcp-playwright` | Necesita Chromium — no instalable en n8n |
| `mcp-filesystem` | Necesita bind mounts del host |
| `mcp-qdrant` | Necesita red interna con Qdrant y coherencia de embeddings |
| `mcp-memory` | Necesita volumen persistente |

**Contenedores opcionales** (`just up-mcp-optional`) — requieren credenciales en `.env`:

| Servidor | Capacidad |
|---|---|
| `mcp-searxng` | Búsqueda web via instancia SearXNG propia |

**Procesos en n8n — sin contenedor propio** — credenciales configuradas por nodo en n8n:

| Herramienta | Comando stdio | Paquete |
|---|---|---|
| fetch | `python3 -m mcp_server_fetch` | `mcp-server-fetch` (PyPI) |
| time | `python3 -m mcp_server_time` | `mcp-server-time` (PyPI) |
| postgres | `node .../server-postgres/dist/index.js <URL>` | `@modelcontextprotocol/server-postgres` (npm) |
| email | `email-mcp stdio` | `@codefuturist/email-mcp` (npm) |
| forgejo | `forgejo-mcp stdio` | `ronmi/forgejo-mcp` (imagen Docker) |

El n8n de desarrollo (`assets/n8n/Dockerfile`) extiende la imagen oficial con todos estos paquetes preinstalados. Para n8n de producción externo: configurar el nodo MCP Client Tool con transporte stdio y el comando correspondiente, o usar los contenedores opcionales expuestos via Traefik.

### Transporte

Todos los contenedores MCP exponen SSE en puerto 8000 via supergateway:

```
Cliente (n8n) → HTTP/SSE → supergateway → stdio → servidor MCP → recurso
```

Endpoint interno: `http://mcp-<nombre>:8000/sse`
Endpoint externo: `https://mcp-<nombre>.MAIN_DOMAIN/sse`

### mcp-qdrant — coherencia de embeddings

El modelo de embeddings de mcp-qdrant **debe coincidir** con el usado en la ingesta RAG. Si difieren, las búsquedas vectoriales producen resultados incorrectos — los vectores viven en espacios distintos.

```bash
# En .env
MCP_QDRANT_EMBEDDING_MODEL=nomic-embed-text   # debe coincidir con el modelo de ingesta
```

Si cambias el modelo de embeddings: actualizar esta variable **y re-ingestar todos los documentos**.

---

## 12. Configuración de Tools MCP en n8n

Ver [`docs/n8n-mcp-tools.md`](docs/n8n-mcp-tools.md) para la guía completa paso a paso.

### Prerequisito crítico

```bash
N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true  # ya en x-n8n-base del docker-compose
```

### Modelo recomendado para agentes con Tools

- `qwen2.5-coder:14b` o `qwen2.5:7b-instruct` — function calling fiable
- Evitar `deepseek-r1:14b` para agentes con muchas tools — function calling limitado

### Endpoints de los 4 contenedores base

```
http://mcp-playwright:8000/sse
http://mcp-filesystem:8000/sse
http://mcp-qdrant:8000/sse
http://mcp-memory:8000/sse
```

### Agentes recomendados

| Agente | Tools |
|---|---|
| Investigación web | playwright, memory, searxng (opcional) |
| Gestión documental | filesystem, qdrant, memory |
| Desarrollo | qdrant, memory, forgejo (stdio) |
| Asistente general | memory, fetch (stdio), time (stdio) |

---

## Apéndice — Setup Rápido

```bash
# 1. Estructura de Modelfiles
mkdir -p ./assets/ollama
# Crear: Modelfile.architect, Modelfile.editor, Modelfile.rag
# (contenido en Sección 2)

# 2. Levantar el stack
just up-dev      # desarrollo con Aider
just up-rag      # bot de consultas RAG
just up          # stack completo (cpu o gpu según hardware)

# 3. Setup de modelos (ejecutar una vez, o al cambiar Modelfiles)
just setup-models

# 4. Verificar instancias
docker exec Ollama-GPU ollama list
# Debe mostrar: r1-architect, qwen-editor, rag-bot, nomic-embed-text

# 5. Variable de entorno para uso fuera de Docker
export OLLAMA_KEEP_ALIVE=0   # añadir a .bashrc

# 6. Archivos de memoria por proyecto (crear en la raíz de cada proyecto)
touch ARCHITECTURE.md CONSTRAINTS.md

# 7. Lanzar Aider
cd /tu/proyecto
aider
```

### Resumen de Modelfiles (`assets/ollama/`)

| Archivo | Modelo base | num_ctx | temp | Uso |
|---|---|---|---|---|
| `Modelfile.architect` | `deepseek-r1:14b` Q4_K_M | 6 144 | 0.5 | Planificación, diseño, razonamiento |
| `Modelfile.editor` | `qwen2.5-coder:14b` Q4_K_M | 12 288 | 0.1 | Diffs, edición, refactors |
| `Modelfile.rag` | `qwen2.5:7b-instruct` Q4_K_M | 32 768 | 0.0 | Bot de consultas sobre documentos |

### Modelos a descargar

```bash
ollama pull deepseek-r1:14b
ollama pull qwen2.5-coder:14b        # editor + fallback arquitecto
ollama pull qwen2.5:7b-instruct      # RAG
ollama pull nomic-embed-text         # embeddings
```

### Changelog

| Versión | Cambios principales |
|---|---|
| v1.0 | Versión inicial consolidada — Aider + Ollama (R1 arquitecto, Qwen editor, rag-bot) · RAG con Qdrant + Langflow + n8n · MCP servers (playwright, filesystem, qdrant, memory, searxng) · Multi-lenguaje (Rust, Python, PHP, JS/TS) · docker-compose completo con perfiles cpu/gpu |