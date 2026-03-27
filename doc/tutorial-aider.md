
# Tutorial: Aider + DeepLocal Forge
**Desarrollo asistido con modelos locales — Guía completa**

> Para el proyecto Gramola (Rust/Axum + React/TypeScript)
> Stack: Aider · Ollama en thebeast.local · qwen-editor · r1-architect

---

## Índice

1. [Qué es Aider y cómo funciona](#1-qué-es-aider)
2. [Setup: instalación y configuración](#2-setup)
3. [El fichero .aider.conf.yml](#3-aider-conf-yml)
4. [Arrancar el stack local](#4-arrancar-el-stack)
5. [La interfaz de Aider](#5-la-interfaz)
6. [Los cuatro modos de chat](#6-modos-de-chat)
7. [Los dos modelos y cuándo usar cada uno](#7-los-dos-modelos)
8. [Cómo dar contexto al modelo](#8-contexto)
9. [/load: reutilizar prompts desde fichero](#9-load)
10. [Anatomía de un buen prompt](#10-anatomía-de-un-prompt)
11. [Flujo de sesión completo](#11-flujo-de-sesión)
12. [Prompts por tipo de tarea](#12-prompts-por-tarea)
13. [Cómo evitar los errores más comunes](#13-errores-comunes)
14. [Critic pass: revisar antes de aceptar](#14-critic-pass)
15. [Checklist de cierre de sesión](#15-checklist)
16. [Referencia rápida de comandos](#16-referencia-rápida)

---

## 1. Qué es Aider

Aider es un cliente de terminal para LLMs especializado en editar código. Su particularidad más importante es que **aplica los cambios directamente a los ficheros** mediante diffs — no tienes que copiar código del chat. También hace commits automáticos de cada cambio.

El flujo básico es:

1. Abres Aider con los ficheros que quieres editar
2. Pides cambios en lenguaje natural
3. Aider genera el diff, lo aplica al fichero y hace un commit de git
4. Si configuras lint/test, los ejecuta y le muestra los errores al modelo para que los corrija

---

## 2. Setup

### 2.1 Instalación

```bash
python -m pip install aider-install
aider-install
```

Verificar:
```bash
aider --version
```

### 2.2 Variable de entorno para Ollama remoto

Aider necesita saber dónde está tu Ollama. Añadir a `~/.bashrc` o `~/.zshrc`:

```bash
export OLLAMA_API_BASE=https://ollama.thebeast.local
export OLLAMA_KEEP_ALIVE=0   # Descarga el modelo de VRAM al terminar — crítico con 12GB
```

`OLLAMA_KEEP_ALIVE=0` evita que el modelo anterior se quede en VRAM cuando Aider cambia entre arquitecto y editor. Con dos modelos de 14B y 12GB, sin esto colisionan.

### 2.3 Verificar que Ollama tiene los modelos

```bash
curl https://ollama.thebeast.local/v1/models | jq '.data[].id'
# Debe aparecer: "qwen-editor" y "r1-architect"
```

Si no aparecen, crear las instancias desde thebeast.local con `just setup-models` (DeepLocal Forge).

---

## 3. El fichero .aider.conf.yml

Aider busca `.aider.conf.yml` en el directorio raíz del repositorio git (o en `~`).
Pon uno en `gramola/server/` y otro en `gramola/client/` para que cada componente tenga su configuración.

### Para gramola/server/

```yaml
# gramola/server/.aider.conf.yml

# Modelo principal: r1-architect para el razonamiento
model: ollama_chat/r1-architect

# Modelo editor: qwen-editor para aplicar los diffs
editor-model: ollama_chat/qwen-editor

# Modo architect activado por defecto
architect: true

# Aceptar cambios del arquitecto automáticamente sin pedir confirmación
auto-accept-architect: true

# Formato de diff del editor (más fiable con modelos locales)
editor-edit-format: editor-whole

# Ficheros de referencia cargados en cada sesión (read-only)
read:
  - ARCHITECTURE.md
  - CONSTRAINTS.md

# Lint: ejecutar después de cada cambio
lint-cmd: cargo clippy -- -D warnings

# Test (opcional, desactivar si los tests tardan mucho)
# test-cmd: cargo test

# No hacer auto-commit (hacerlo manualmente para revisar antes)
auto-commits: false

# Contexto del repo (desactivar si el repo es grande y ralentiza el arranque)
# map-tokens: 0
```

### Para gramola/client/

```yaml
# gramola/client/.aider.conf.yml

model: ollama_chat/r1-architect
editor-model: ollama_chat/qwen-editor
architect: true
auto-accept-architect: true
editor-edit-format: editor-whole

read:
  - ARCHITECTURE.md
  - CONSTRAINTS.md

lint-cmd: pnpm tsc --noEmit && pnpm run lint

auto-commits: false
```

### Notas sobre la configuración

**`editor-edit-format: editor-whole`** es el más fiable con modelos locales. El formato `editor-diff` requiere que el modelo produzca diffs bien formateados, lo que falla con frecuencia con Qwen y R1. Con `editor-whole`, el editor reescribe el fichero completo — más tokens, menos errores de formato.

**`auto-commits: false`** te da control sobre qué va al historial de git. Cuando el cambio funciona y pasa el lint, haces el commit tú con `/git commit -m "mensaje"` o en otra terminal.

**`read:`** carga ARCHITECTURE.md y CONSTRAINTS.md como ficheros de **solo lectura** en cada sesión. El modelo los ve pero no puede modificarlos. Es equivalente a ejecutar `/read-only ARCHITECTURE.md CONSTRAINTS.md` al inicio de cada sesión.

---

## 4. Arrancar el stack

Antes de abrir Aider, el stack de DeepLocal Forge tiene que estar corriendo en thebeast.local:

```bash
# En thebeast.local
cd /ruta/a/deeplocal-forge
just up-dev

# Verificar
curl https://ollama.thebeast.local/v1/models
```

---

## 5. La interfaz de Aider

Arrancar desde el directorio del componente:

```bash
# Servidor Rust
cd gramola/server
aider

# Cliente React
cd gramola/client
aider
```

Al arrancar verás algo así:

```
Aider v0.x.x
Models: ollama_chat/r1-architect with editor-whole edit format,
        editor model ollama_chat/qwen-editor
Git repo: .git with 180 files
Repo-map: using 1024 tokens
Added ARCHITECTURE.md to the chat. (read only)
Added CONSTRAINTS.md to the chat. (read only)
Use /help to see in-chat commands
────────────────────────────────────────────────────────
>
```

El prompt `>` es donde escribes. Aider ya cargó ARCHITECTURE.md y CONSTRAINTS.md automáticamente gracias al `read:` del config.

### Cómo escribir mensajes largos

El input de Aider es de una sola línea por defecto. Para mensajes largos con saltos de línea:

```
{
Este es un mensaje
con varias líneas
}
```

O usa `/editor` para abrir tu editor de texto y escribir el prompt ahí.

---

## 6. Los cuatro modos de chat

Aider tiene cuatro modos. El que más usarás es **architect** (ya activado en el config), pero conviene entender todos.

| Modo | Comando | Para qué |
|---|---|---|
| **code** | `/code` | Implementación directa con un solo modelo |
| **architect** | `/architect` | r1 diseña → qwen-editor aplica (tu flujo habitual) |
| **ask** | `/ask` | Preguntas sobre el código sin modificar nada |
| **context** | `/context` | Ver código circundante sin editar |

### Modo architect (el principal)

Con `architect: true` en el config, **cada mensaje que envíes pasa por el flujo de dos modelos**:

1. r1-architect recibe tu petición, analiza el código y propone qué cambiar
2. qwen-editor recibe la propuesta y genera el diff para aplicar al fichero
3. Con `auto-accept-architect: true`, los cambios se aplican sin pedirte confirmación
4. Con `lint-cmd` configurado, ejecuta el lint automáticamente y si falla, le muestra el error al modelo para que lo corrija

### Cómo cambiar de modo puntualmente

Para un mensaje concreto en otro modo sin cambiar el modo permanente:

```
/ask ¿Ya existe alguna función que conecte al cliente MPD dado host y port?
/architect Implementa el método Player::move_song
/code Corrige solo este error de compilación: ...
```

Para cambiar el modo de forma permanente en la sesión:

```
/chat-mode ask
/chat-mode architect
/chat-mode code
```

---

## 7. Los dos modelos y cuándo usar cada uno

Con `architect: true`, los dos modelos trabajan en tándem automáticamente. Pero hay situaciones donde querrás usar solo uno de ellos.

### El flujo normal (architect mode)

```
Tu petición → r1-architect (qué cambiar) → qwen-editor (cómo editar el fichero)
```

Úsalo para: implementar stubs, añadir endpoints, escribir tests, refactoring.

### Solo ask mode (r1 sin qwen)

```
Tu pregunta → r1-architect (responde sin editar nada)
```

Úsalo para: entender código existente, diseño antes de implementar, analizar deuda técnica.

```
/ask ¿Qué módulos dependen de audio/plyr.rs? ¿Hay riesgo de ciclo si muevo esta función?
```

### Solo code mode (qwen sin r1)

```
Tu petición → qwen-editor (implementa directamente)
```

Úsalo para: cambios muy pequeños y mecánicos donde el razonamiento de R1 es excesivo.

```
/code Añade un println! de depuración al inicio de este método
```

### Tabla de selección rápida

| Tarea | Modo |
|---|---|
| Implementar stub vacío | architect |
| Añadir endpoint HTTP | architect |
| Escribir tests unitarios | architect |
| Corregir error de compilación | architect o code |
| Refactoring multi-fichero | architect |
| Analizar diseño antes de implementar | ask |
| Entender código existente | ask |
| Cambio de una línea trivial | code |

### Razonamiento con R1: acotar el thinking

R1 con razonamiento extendido puede tardar y no necesariamente mejora en tareas simples. Para controlarlo:

```bash
# En el config o como flag al arrancar
reasoning-effort: low    # para tareas de implementación directa
reasoning-effort: high   # para diseño complejo o debugging de lifetimes
```

O en la sesión:
```
/reasoning-effort low
/reasoning-effort high
```

---

## 8. Contexto

El modelo solo ve lo que tú le das. ARCHITECTURE.md y CONSTRAINTS.md ya están cargados (read-only). Para los ficheros que quieres editar:

### Añadir ficheros para editar

```
/add src/audio/plyr.rs
```

### Añadir ficheros de referencia (sin editar)

```
/read-only src/server/http.rs
```

Útil cuando el modelo necesita ver cómo están definidas las rutas existentes para añadir una nueva, pero no debe tocar ese fichero.

### Ver qué ficheros están en el contexto

```
/ls
```

### Eliminar ficheros del contexto

```
/drop src/audio/plyr.rs
```

Útil cuando terminas una tarea y vas a empezar otra — el contexto grande ralentiza las llamadas y confunde al modelo.

### Regla: mínimo necesario

Añade solo los ficheros que la tarea requiere. Si añades cinco ficheros y la tarea afecta a uno, el modelo puede "arreglar" cosas en los otros cuatro que nadie le pidió.

```bash
# Para implementar un método en Player:
/add src/audio/plyr.rs
# ARCHITECTURE.md y CONSTRAINTS.md ya están — suficiente

# Para añadir un endpoint HTTP nuevo:
/add src/server/routes/queue.rs
/read-only src/server/http.rs        # ver el router, no modificarlo
# ARCHITECTURE.md y CONSTRAINTS.md ya están
```

### Con el modo ask: aún menos contexto

En modo ask, R1 tiene `num_ctx: 6144`. Si le das tres ficheros grandes el contexto se llena y trunca. Para análisis y diseño, un fichero a la vez.

---

## 9. /load: reutilizar prompts desde fichero

`/load` es el mecanismo de Aider para ejecutar prompts reutilizables guardados en fichero.
No hay "comandos personalizados" en el sentido de `.aider/commands/` — simplemente guardas
el texto del prompt en un fichero `.md` y lo cargas con `/load`.

### Estructura recomendada

Crea un directorio `prompts/` en la raíz del proyecto:

```
gramola/server/
  prompts/
    prevalidar.md
    critic.md
    analizar-stub.md
    nuevo-endpoint.md
```

### Ejemplo: prompts/prevalidar.md

```
/ask Antes de empezar, verifica que entiendes el proyecto.
Resume en 3 líneas: (1) qué hace el módulo que voy a modificar,
(2) qué restricciones aplican de CONSTRAINTS.md para ese módulo,
(3) qué NO debes tocar.
No propongas cambios todavía.
```

### Ejemplo: prompts/critic.md

```
/ask Revisa críticamente los últimos cambios aplicados.
Para cada problema encontrado usa este formato:
Bug/Riesgo: descripción
Fichero: nombre.rs
Línea: número o rango
Explicación: por qué es un problema
Corrección: qué cambiar exactamente

Busca específicamente:
- unwrap() o expect() fuera de #[cfg(test)]
- Errores silenciados con let _ = o .ok() sin justificación
- Endpoints sin AuthUser/AdminUser que deberían tenerlo
- Queries SQL con format!() o concatenación de strings
- clone() que podría evitarse con una referencia
- Cambios en firmas de funciones públicas no solicitados
- Lógica de negocio en handlers en lugar de en MusicDB o Player
- Violaciones de CONSTRAINTS.md

Si no hay problemas, responde únicamente: "Sin problemas encontrados."
```

### Cómo usar /load

```
/load prompts/critic.md
```

Aider lee el fichero y ejecuta su contenido como si lo hubieras escrito en el chat.
Si el fichero empieza con `/ask`, entra en modo ask para ese mensaje.
Si empieza con `/architect`, usa el flujo architect/editor.

### Combinando /load con contexto específico

Puedes añadir ficheros justo antes de cargar el prompt:

```
/add src/audio/plyr.rs
/load prompts/critic.md
```

### /save: guardar el estado de la sesión

El comando inverso — guarda los ficheros actuales en el chat a un fichero:

```
/save prompts/sesion-player.md
```

Genera un fichero con los `/add` y `/read-only` de la sesión actual.
Útil para retomar exactamente la misma sesión más tarde:

```
/load prompts/sesion-player.md
```

---

## 10. Anatomía de un buen prompt

Un prompt que funciona tiene cuatro partes:

```
ROL — quién eres en este contexto
CONTEXTO MÍNIMO — ya dado con /add (no necesitas repetirlo)
TAREA EXACTA — qué debe hacer y qué NO debe tocar
RESTRICCIONES — qué reglas aplican (referencia a CONSTRAINTS.md)
```

### Ejemplo malo

```
Implementa delete_song en el Player
```

→ Aider no sabe la firma esperada, puede inventar implementaciones que no usen
los patrones existentes, puede cambiar otras funciones "de paso".

### Ejemplo bueno

```
{
Eres un programador Rust senior. Has leído ARCHITECTURE.md y CONSTRAINTS.md.

El método Player::delete_song en src/audio/plyr.rs es un stub que devuelve Ok(()).

Impleméntalo para que:
1. Conecte a MPD con get_client(self.host, self.port, self.max_connection_retries)
2. Obtenga la cola con c.queue()
3. Encuentre la entrada cuyo QueuePlace.id corresponda a song_id
4. La elimine con c.delete(place.id)
5. Si la canción no está en la cola, devuelva Ok(()) sin error

NO cambies la firma del método.
NO toques ningún otro método de Player.
NO crees ficheros nuevos.
Si para implementar esto necesitas cambiar algo más, DETENTE y pregúntame.

Restricciones: no unwrap(), propagar errores con ?, sin clone() innecesario.
}
```

### El patrón "qué NO debe tocar"

Esta línea es la más importante para evitar daños colaterales:

```
NO cambies la firma del método.
NO toques ningún otro método.
NO crees ficheros nuevos.
Si necesitas cambiar algo más, explícalo antes y espera confirmación.
```

### Interrumpir si algo va mal

Si Aider empieza a hacer cambios que no pediste, `Ctrl-C` interrumpe la respuesta.
El estado parcial queda en el chat — puedes referenciarlo en el siguiente mensaje.

---

## 11. Flujo de sesión completo

### Antes de abrir Aider

```bash
# 1. Verificar stack
curl -s https://ollama.thebeast.local/v1/models | jq '.data[].id'

# 2. Pre-validar el código — dárselo limpio al modelo
cd gramola/server
cargo fmt && cargo clippy --fix --allow-dirty && cargo check
```

Si `cargo check` falla antes de empezar, corrige los errores a mano primero.
No le des al modelo código que ya tiene errores — gasta tokens en ruido.

### Arrancar

```bash
cd gramola/server
aider
```

ARCHITECTURE.md y CONSTRAINTS.md se cargan solos gracias al config.

### Primer mensaje de la sesión

Antes de pedir ningún cambio, una comprobación rápida:

```
/ask Confirma que has leído ARCHITECTURE.md y CONSTRAINTS.md.
¿Cuáles son las tres reglas más importantes de CONSTRAINTS.md para el módulo audio/?
```

Esto verifica que el modelo tiene el contexto correcto y descubre si algo no cargó bien.

### Ciclo de trabajo dentro de la sesión

```
1. /add ficheros relevantes para la tarea
2. Opcional: /load prompts/prevalidar.md
3. Enviar prompt con rol + tarea + restricciones
4. Aider aplica el diff automáticamente
5. El lint se ejecuta solo (lint-cmd en config)
6. Si hay errores de lint, Aider los ve y los corrige automáticamente
7. Si el lint pasa: /diff para revisar los cambios
8. /load prompts/critic.md para el critic pass
9. Si el critic no encuentra problemas: /git commit -m "mensaje"
10. /drop de los ficheros de la tarea anterior antes de la siguiente
```

### Revisar los cambios antes de hacer commit

```
/diff
```

Muestra todos los cambios desde el último commit. Revísalos antes de hacer el commit.

### Deshacer el último commit

Si el cambio no fue lo que querías:

```
/undo
```

Deshace el último commit de Aider. El código vuelve al estado anterior.

### Ver cuántos tokens está consumiendo el contexto

```
/tokens
```

Si está cerca del límite, haz `/drop` de los ficheros que ya no necesitas.

---

## 12. Prompts por tipo de tarea

### Implementar un stub vacío (Rust)

```
{
Eres un programador Rust senior. Has leído ARCHITECTURE.md y CONSTRAINTS.md.

El método <nombre> en src/<ruta>.rs es un stub que devuelve Ok(()) sin hacer nada.

Impleméntalo para que:
1. <paso 1>
2. <paso 2>
3. <paso 3>

NO cambies la firma del método.
NO toques ningún otro método.
NO crees ficheros nuevos.

Restricciones: no unwrap(), errores con ?, sin clone() innecesario.
}
```

### Corregir un error de compilación

Aider con `lint-cmd` configurado intentará corregirlo solo si el error viene del lint.
Para errores que surjan de un cambio puntual:

```
{
cargo check devuelve este error:

<pegar el error exacto con número de línea>

Analiza solo este error. Explica en un comentario inline por qué se produce.
Corrige solo este error. No cambies nada más del fichero.
}
```

### Añadir un endpoint HTTP (Rust)

```
{
Eres un programador Rust senior. Has leído ARCHITECTURE.md y CONSTRAINTS.md.

Añade el endpoint PATCH /queue/move/:from/:to que mueva una canción en la cola MPD.

1. En src/server/routes/queue.rs, crea el handler:
   - Firma: pub(crate) async fn move_song(AuthUser(_): AuthUser, State(state): State<AppState>, Path((from, to)): Path<(usize, usize)>) -> impl IntoResponse
   - Llama a state.player.lock().await.move_song(from, to).await
   - En error: devuelve { "status": "error", "message": "..." } con StatusCode::INTERNAL_SERVER_ERROR
   - En éxito: devuelve { "status": "ok" }

2. En src/server/http.rs, registra la ruta en el router de queue:
   .route("/queue/move/:from/:to", patch(queue::move_song))

Solo añade esas dos cosas. No reorganices el router. No añadas lógica extra.
No toques ningún otro fichero.
}
```

### Escribir tests unitarios (Rust)

```
{
Eres un programador Rust senior. Has leído CONSTRAINTS.md.

Escribe tests unitarios para las funciones <función1> y <función2>
en src/<ruta>.rs.

Tests requeridos:
- <test 1: descripción>
- <test 2: descripción>
- <test 3: descripción>

Los tests van en #[cfg(test)] mod tests al final del mismo fichero.
No uses .unwrap() en los tests — usa .expect("descripción del fallo").
No añadas dependencias nuevas.
}
```

### Refactoring: mover código sin cambiar comportamiento

```
{
Eres un programador Rust senior. Has leído ARCHITECTURE.md y CONSTRAINTS.md.

Quiero mover la función <nombre> de src/<origen>.rs a src/<destino>.rs.
El comportamiento no debe cambiar. Los tests existentes deben seguir pasando.

Pasos exactos:
1. Copia la función a src/<destino>.rs con la misma firma
2. En src/<origen>.rs, reemplaza la implementación por una llamada a la función movida
3. Actualiza los imports necesarios en ambos ficheros

No reescribas la lógica. No la mejores. Solo muévela.
}
```

### Análisis de diseño (ask mode)

```
/ask
{
Necesito vincular el Player de cada handler al MPD de la instancia del usuario autenticado.
Actualmente hay un único Player global en AppState.
La tabla mpd_instances tiene: id, owner_id, host, port.

Propón solo el diseño de la solución — sin código de implementación todavía.
Describe: qué cambiaría en AppState, cómo el handler obtendría el Player correcto,
y si habría algún riesgo de concurrencia.
}
```

### Verificar si algo ya existe (ask mode, antes de implementar)

```
/ask ¿Ya existe en el proyecto alguna función o método que conecte a MPD dado host y port?
Busca en los ficheros que tienes en contexto.
Responde solo: sí/no, el nombre, y dónde está. No escribas código nuevo.
```

### Análisis del cliente React

```
{
Eres un programador React/TypeScript senior. Has leído ARCHITECTURE.md y CONSTRAINTS.md del cliente.

Analiza la duplicación de estado entre AppContext.tsx y useSongData.ts.
Lista qué campos de estado están duplicados en los dos ficheros.
No propongas cambios todavía. Solo lista las duplicaciones.
}
```

---

## 13. Errores comunes y cómo evitarlos

### Aider toca ficheros que no debías

**Síntoma:** El diff incluye cambios en funciones o ficheros que no mencionaste.

**Causa:** Demasiado contexto, o no especificaste qué no debe tocar.

**Solución:**
- Añadir: `NO modifiques ningún fichero excepto src/<ruta>.rs`
- Reducir contexto: hacer `/drop` de ficheros que añadiste por si acaso
- `Ctrl-C` para interrumpir si lo ves pasar, luego `/undo`

### El modelo reimplementa algo que ya existe

**Síntoma:** Propone crear una función nueva idéntica a una que ya existe.

**Solución:** Preguntar primero en modo ask:

```
/ask ¿Ya existe alguna función que haga X? Busca en los ficheros en contexto.
```

### El modelo propone una abstracción nueva no pedida

**Síntoma:** Propone un trait, módulo o struct nuevo sin que lo hayas pedido.

**Solución:** Añadir al prompt:

```
No introduzcas abstracciones nuevas (traits, módulos, structs).
Usa los tipos y patrones que ya existen.
Si crees que hace falta algo nuevo, explícalo antes y espera confirmación.
```

### El lint automático entra en bucle

**Síntoma:** Aider aplica el cambio, el lint falla, corrige, el lint vuelve a fallar, en bucle.

**Solución:** `Ctrl-C` para interrumpir. Luego:

```
/undo
```

E intenta con un prompt más preciso o con `/code` en lugar de architect.

### El diff es correcto pero muy grande (editor-whole reescribe el fichero entero)

**Síntoma:** Con `editor-edit-format: editor-whole`, el diff muestra el fichero completo aunque solo cambió una función.

**Esto es normal** — `editor-whole` reescribe el fichero para garantizar que no hay errores de formato. Revisa con `/diff` que solo los cambios esperados están ahí. Si hay algo extraño, `/undo`.

### R1 tarda demasiado en razonar

**Síntoma:** El modelo está varios minutos en el bloque `<think>` antes de responder.

**Solución:**

```
/reasoning-effort low
```

Para diseño complejo donde sí quieres el razonamiento profundo:

```
/reasoning-effort high
```

---

## 14. Critic pass

Después de aplicar cualquier cambio no trivial, antes de hacer commit, ejecutar:

```
/load prompts/critic.md
```

Con el contenido de `prompts/critic.md` (ver sección 9).

El critic usa `/ask` — no modifica ficheros, solo analiza. Si encuentra problemas, los corriges con un nuevo prompt en modo architect.

### Cuándo es obligatorio

| Tipo de cambio | Critic pass |
|---|---|
| Formateo, comentarios, renombrado | No necesario |
| Nueva función con firma simple | Recomendado |
| Refactor de módulo o API pública | Obligatorio |
| Cambio en concurrencia o mutexes | Obligatorio |
| Nuevo endpoint HTTP | Obligatorio |
| Cambio en manejo de errores | Obligatorio |

---

## 15. Checklist de cierre de sesión

```
[ ] cargo check pasa sin errores
[ ] cargo clippy -- -D warnings pasa sin warnings
[ ] /diff revisado — solo los cambios esperados
[ ] Critic pass ejecutado sobre los ficheros modificados
[ ] No hay unwrap() nuevo fuera de tests
[ ] No hay rutas nuevas sin autenticación que deberían tenerla
[ ] ARCHITECTURE.md actualizado si se añadió algo estructural
[ ] /git commit -m "mensaje descriptivo"
[ ] Solo se modificaron los ficheros que se pretendía modificar
```

Para el cliente React:
```
[ ] pnpm tsc --noEmit pasa sin errores
[ ] pnpm run lint pasa sin warnings
[ ] /diff revisado
[ ] Critic pass ejecutado
[ ] No hay useState nuevo que duplique estado de AppContext
[ ] No hay llamadas fetch() directas en componentes (solo en src/api/)
[ ] /git commit -m "mensaje descriptivo"
```

---

## 16. Referencia rápida de comandos

### Comandos de uso más frecuente

| Comando | Efecto |
|---|---|
| `/add src/audio/plyr.rs` | Añade fichero editable al contexto |
| `/read-only src/server/http.rs` | Añade fichero de solo referencia |
| `/drop src/audio/plyr.rs` | Elimina fichero del contexto |
| `/ls` | Lista todos los ficheros en contexto |
| `/ask <pregunta>` | Pregunta sin modificar ficheros |
| `/architect <petición>` | Flujo architect → editor |
| `/code <petición>` | Implementa directamente con un modelo |
| `/diff` | Muestra cambios desde el último commit |
| `/undo` | Deshace el último commit de Aider |
| `/load prompts/critic.md` | Ejecuta el prompt del fichero |
| `/save prompts/sesion.md` | Guarda el contexto actual a fichero |
| `/lint` | Ejecuta el lint manualmente |
| `/tokens` | Muestra uso de tokens del contexto |
| `/clear` | Limpia el historial de chat (no los ficheros) |
| `/reset` | Limpia historial y quita todos los ficheros |
| `/git commit -m "msg"` | Commit manual |
| `/reasoning-effort low` | Reduce el razonamiento de R1 |
| `/reasoning-effort high` | Aumenta el razonamiento de R1 |
| `/exit` | Cierra Aider |

### Arrancar con ficheros ya incluidos (sin /add manual)

```bash
# Equivalente a /add src/audio/plyr.rs al arrancar
aider src/audio/plyr.rs

# Varios ficheros
aider src/audio/plyr.rs src/server/routes/queue.rs
```

### Mensaje multilínea

```
{
línea 1
línea 2
línea 3
}
```

O con etiqueta personalizada (si el mensaje contiene `}`):

```
{rust
código aquí con llaves }
rust}
```

---

## Apéndice — Ejemplo de sesión real comentada

Implementar `Player::move_song` desde stub hasta commit.

```bash
# Pre-validación
cd gramola/server
cargo fmt && cargo clippy --fix --allow-dirty && cargo check
# → pasa sin errores

aider
# → carga ARCHITECTURE.md y CONSTRAINTS.md automáticamente
```

```
# Verificar contexto
/ask Confirma que has leído ARCHITECTURE.md y CONSTRAINTS.md.
¿Cuáles son las reglas más relevantes de CONSTRAINTS.md para el módulo audio/?
```

```
# El modelo confirma: no unwrap(), errores con ?, sin SQL interpolado, etc.
# Bien. Añadir el fichero a editar.

/add src/audio/plyr.rs
```

```
# Verificar que el stub existe antes de pedir implementación
/ask ¿Existe el método move_song en Player? Dame su firma y cuerpo actual.
```

```
# Respuesta: sí, es pub async fn move_song(&mut self, from: usize, to: usize) -> Result<(), mpd::error::Error>
# cuerpo: let _ = (from, to); Ok(())

# Implementar
{
Eres un programador Rust senior. Has leído ARCHITECTURE.md y CONSTRAINTS.md.

El método Player::move_song en src/audio/plyr.rs es un stub que no hace nada.

Impleméntalo:
1. Conecta a MPD con get_client usando self.host, self.port, self.max_connection_retries
2. Usa c.mv(from as u32, to as u32) — ese es el método correcto de la crate mpd
3. Si MPD devuelve error, propágalo con ?

NO cambies la firma: async fn move_song(&mut self, from: usize, to: usize) -> Result<(), mpd::error::Error>
NO toques ningún otro método.
NO crees ficheros nuevos.

Restricciones: no unwrap(), errores con ?.
}
```

```
# Aider aplica el diff. El lint-cmd (cargo clippy) se ejecuta automáticamente.
# Si hay error: Aider lo ve y corrige solo.
# Si pasa: revisar el diff.

/diff
```

```
# El diff se ve correcto. Critic pass.

/load prompts/critic.md
```

```
# El modelo responde: "Sin problemas encontrados."

# Commit manual
/git commit -m "feat: implementar Player::move_song (stub → MPD mv)"

# Limpiar contexto antes de la siguiente tarea
/drop src/audio/plyr.rs
```

Sesión completa: ~6 minutos. Un stub implementado, lint pasado, critic pasado, commit hecho.