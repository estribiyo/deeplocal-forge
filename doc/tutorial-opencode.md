# Tutorial: OpenCode + DeepLocal Forge
**Desarrollo asistido con modelos locales — Guía completa**

> Para el proyecto Gramola (Rust/Axum + React/TypeScript)
> Stack: OpenCode · Ollama en thebeast.local · qwen-editor · r1-architect

---

## Índice

1. [Qué es OpenCode y en qué se diferencia de Aider](#1-qué-es-opencode)
2. [Setup: instalación y configuración](#2-setup)
3. [Arrancar el stack local](#3-arrancar-el-stack)
4. [La interfaz de OpenCode](#4-la-interfaz)
5. [Los dos modelos y cuándo usar cada uno](#5-los-dos-modelos)
6. [Cómo dar contexto al modelo](#6-contexto)
7. [Anatomía de un buen prompt](#7-anatomía-de-un-prompt)
8. [Flujo de sesión completo](#8-flujo-de-sesión)
9. [Prompts por tipo de tarea](#9-prompts-por-tarea)
10. [Cómo evitar los errores más comunes](#10-errores-comunes)
11. [Critic pass: revisar antes de aceptar](#11-critic-pass)
12. [Checklist de cierre de sesión](#12-checklist)
13. [Referencia rápida de comandos](#13-referencia-rápida)

---

## 1. Qué es OpenCode

OpenCode es un cliente de terminal para LLMs centrado en código, similar a Aider pero con interfaz TUI (texto interactivo). Se conecta a cualquier backend compatible con la API de OpenAI — en tu caso, Ollama corriendo en `thebeast.local`.

### Diferencias clave respecto a Aider

| Característica | Aider | OpenCode |
|---|---|---|
| Modo arquitecto/editor | Nativo (`architect: true`) | **No existe** — cambio manual de modelo |
| Contexto de ficheros | `/add <fichero>` | `/add <fichero>` (igual) |
| Comandos personalizados | `.aider/commands/` | No soporta comandos personalizados |
| Auto-commits | Configurable | No hace commits automáticos |
| Formato de diff | unified diff o whole file | Propone cambios en texto, tú los aplicas |
| Interfaz | Línea de comandos clásica | TUI con paneles |
| Lint automático | `auto-lint: true` | **No existe** — ejecutar manualmente |

### Lo que esto implica para tu flujo

Con Aider, el ciclo era: arquitecto propone → editor aplica diff → lint automático.
Con OpenCode, el ciclo es: **tú cambias de modelo manualmente** según la tarea, y **ejecutas el lint tú** después de cada cambio. Más control, más pasos manuales.

---

## 2. Setup

### 2.1 Instalación

```bash
# Instalar OpenCode (Node.js requerido)
npm install -g opencode-ai

# Verificar instalación
opencode --version
```

### 2.2 Configuración global

El fichero de configuración vive en `~/.config/opencode/config.json`.
Tu configuración correcta para DeepLocal Forge:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "ollama/qwen-editor",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "https://ollama.thebeast.local/v1"
      },
      "models": {
        "qwen-editor": {
          "name": "Editor — qwen2.5-coder 14b (12k ctx)",
          "tools": true
        },
        "r1-architect": {
          "name": "Arquitecto — deepseek-r1 14b (6k ctx)",
          "tools": true
        }
      }
    }
  }
}
```

**Notas importantes:**
- `"model": "ollama/qwen-editor"` define el modelo por defecto al arrancar
- Los nombres `qwen-editor` y `r1-architect` deben coincidir exactamente con lo que devuelve `ollama list` en thebeast.local
- Si los Modelfiles de DeepLocal Forge ya existen en tu Ollama, esos nombres ya están disponibles

### 2.3 Verificar que Ollama tiene los modelos

Desde tu máquina:

```bash
# Ver qué modelos tiene Ollama en thebeast.local
curl https://ollama.thebeast.local/v1/models | jq '.data[].id'

# Debe aparecer:
# "qwen-editor"
# "r1-architect"
# "rag-bot"
```

Si no aparecen, crear las instancias desde thebeast.local con `just setup-models` (DeepLocal Forge).

### 2.4 Variables de entorno necesarias

```bash
# Añadir a ~/.bashrc o ~/.zshrc
export OLLAMA_KEEP_ALIVE=0   # Descarga el modelo de VRAM al terminar — crítico para no colisionar los 14B
```

Sin esta variable, si cambias de modelo en OpenCode, el anterior puede seguir ocupando VRAM y los dos modelos compiten por los 12GB.

---

## 3. Arrancar el stack

Antes de abrir OpenCode, el stack de DeepLocal Forge tiene que estar corriendo.

```bash
# En thebeast.local (o vía SSH)
cd /ruta/a/deeplocal-forge

# Solo necesitas el modo dev para trabajar con código
just up-dev

# Verificar que Ollama responde
curl https://ollama.thebeast.local/v1/models
```

Si ves los modelos, el stack está listo.

---

## 4. La interfaz de OpenCode

Arrancar OpenCode en el directorio del proyecto:

```bash
# Para trabajar en el servidor Rust
cd /ruta/a/gramola/server
opencode

# Para trabajar en el cliente React
cd /ruta/a/gramola/client
opencode
```

**Importante: arrancar siempre desde el directorio raíz del componente** que vas a tocar.
OpenCode usa esa ruta como base para encontrar ficheros y para el contexto del proyecto.

### Paneles principales

```
┌────────────────────────────────────────────────────┐
│  CONTEXTO (ficheros añadidos)          [Ctrl+F]    │
├────────────────────────────────────────────────────┤
│                                                    │
│  CONVERSACIÓN                                      │
│  (historial de la sesión)                          │
│                                                    │
├────────────────────────────────────────────────────┤
│  > Tu mensaje aquí                     [Enter]     │
└────────────────────────────────────────────────────┘
```

### Comandos de navegación básicos

| Acción | Tecla / Comando |
|---|---|
| Enviar mensaje | `Enter` |
| Nueva línea en el mensaje | `Shift+Enter` |
| Añadir fichero al contexto | `/add ruta/al/fichero.rs` |
| Ver ficheros en contexto | `/files` o `Ctrl+F` |
| Cambiar modelo | `/models` |
| Limpiar contexto | `/clear` |
| Salir | `/exit` o `Ctrl+C` |

---

## 5. Los dos modelos y cuándo usar cada uno

OpenCode no tiene modo arquitecto/editor nativo. La separación la haces tú cambiando de modelo con `/models`.

### qwen-editor — modelo por defecto

**Cuándo usarlo:**
- Implementar una función con firma ya definida
- Aplicar un cambio pequeño y concreto
- Escribir tests unitarios
- Corregir un error de compilación específico
- Refactoring mecánico (renombrar, mover código sin cambiar lógica)
- Añadir una ruta HTTP siguiendo el patrón existente

**Características:**
- `num_ctx: 12288` — puede ver varios ficheros a la vez
- `temperature: 0.1` — casi determinista, aplica lo que le dices sin improvisar
- Rápido y preciso para cambios de código concretos

### r1-architect — modelo de diseño

**Cuándo usarlo:**
- Diseñar cómo estructurar algo nuevo antes de implementarlo
- Analizar deuda técnica o dependencias entre módulos
- Decidir cómo conectar dos partes del sistema
- Razonar sobre lifetimes, ownership o traits en Rust
- Planificar un refactoring que afecta a varios ficheros

**Características:**
- `num_ctx: 6144` — contexto más pequeño, dale solo los ficheros relevantes
- `temperature: 0.5` — razona más, pero puede divagar; acótar el razonamiento con el prompt
- Más lento; úsalo solo cuando necesites pensamiento estructurado

### Cómo cambiar de modelo

```
/models
```

Aparece una lista de los modelos configurados. Selecciona el que necesitas.
El cambio es efectivo para los mensajes siguientes en la misma sesión.

### Tabla de selección rápida

| Tarea | Modelo |
|---|---|
| Implementar stub vacío | qwen-editor |
| Escribir tests | qwen-editor |
| Corregir error de compilación | qwen-editor |
| Añadir campo a struct + query SQL | qwen-editor |
| Diseñar ownership de un módulo nuevo | r1-architect |
| Analizar qué ficheros afecta un refactoring | r1-architect |
| Decidir cómo conectar MPD por usuario | r1-architect |
| Refactoring del AppContext (misiones 1-6) | r1-architect primero, luego qwen-editor |

---

## 6. Contexto

El modelo no sabe nada del proyecto excepto lo que tú le das en la sesión.
**No recuerda sesiones anteriores. Cada sesión arranca desde cero.**

### Qué añadir siempre al empezar

```
/add ARCHITECTURE.md
/add CONSTRAINTS.md
```

Estos dos ficheros son la memoria del proyecto. Sin ellos, el modelo puede proponer
decisiones que contradicen lo que ya existe.

### Qué más añadir según la tarea

Regla: **el mínimo necesario para la tarea, y nada más**.
Si añades ficheros irrelevantes, el modelo los "usa" para hacer cambios no pedidos.

```bash
# Para trabajar en el Player (audio/plyr.rs)
/add ARCHITECTURE.md
/add CONSTRAINTS.md
/add src/audio/plyr.rs

# Para añadir un endpoint HTTP nuevo
/add ARCHITECTURE.md
/add CONSTRAINTS.md
/add src/server/http.rs
/add src/server/routes/<módulo>.rs

# Para corregir un error en la capa de datos
/add ARCHITECTURE.md
/add CONSTRAINTS.md
/add src/data/pg/<tabla>.rs
/add src/data/models.rs
```

### Con r1-architect: menos es más

R1 tiene `num_ctx: 6144`. Si le das cinco ficheros grandes, el contexto se llena
y el modelo trunca o degrada el razonamiento. Para diseño:

```bash
/add ARCHITECTURE.md
/add CONSTRAINTS.md
/add src/audio/plyr.rs   # solo el fichero sobre el que quieres razonar
```

Luego pregunta. Si necesita ver algo más, te lo dirá.

---

## 7. Anatomía de un buen prompt

Un prompt que funciona tiene cuatro partes. Ninguna es opcional.

```
ROL — quién eres en este contexto
CONTEXTO MÍNIMO — qué ficheros son relevantes (ya añadidos con /add)
TAREA EXACTA — qué debe hacer (y qué NO debe tocar)
RESTRICCIONES — qué reglas aplican
```

### Ejemplo real — implementar un stub

**Prompt malo:**
```
Implementa delete_song en el Player
```

→ El modelo no sabe la firma, no sabe las dependencias, puede inventar
una implementación que no use get_client() o que cambie cosas no pedidas.

**Prompt bueno:**
```
Eres un programador Rust senior. Has leído ARCHITECTURE.md y CONSTRAINTS.md.

El método Player::delete_song en src/audio/plyr.rs es actualmente un stub:

    pub async fn delete_song(&mut self, song_id: i32) -> Result<(), mpd::error::Error> {
        // TODO: Pendiente de implementación en frontend.
        let _ = song_id; Ok(())
    }

Impleméntalo para que:
1. Conecte a MPD con get_client(self.host, self.port, self.max_connection_retries)
2. Obtenga la cola con c.queue()
3. Encuentre la entrada cuyo QueuePlace.id corresponda a song_id
4. La elimine con c.delete(place.id)
5. Si la canción no está en la cola, devuelva Ok(()) sin error

NO cambies la firma del método.
NO toques ningún otro método de Player.
NO crees ficheros nuevos.

Restricciones de CONSTRAINTS.md: no unwrap(), propagar errores con ?, errores descriptivos.
```

### El patrón "qué NO debe tocar"

Esta línea es la más importante del prompt para evitar daños colaterales:

```
NO cambies la firma del método.
NO toques ningún otro método de Player.
NO crees ficheros nuevos.
Si para implementar esto necesitas cambiar algo más, DETENTE y pregúntame antes.
```

### Reasoning budget para r1-architect

R1 tiende a razonar demasiado si no lo acota. Añade esto al principio del mensaje
cuando uses r1-architect para que no genere 1000 tokens de `<think>` antes de responder:

```
Think briefly (max 6 steps). Focus on the final answer.
```

Para tareas de diseño en Rust específicamente:

```
Reason briefly about: (1) ownership (2) lifetimes (3) trait bounds. Max 6 steps.
```

Si R1 entra en bucle y no converge, escribe:

```
Give the answer with minimal reasoning.
```

---

## 8. Flujo de sesión completo

### Antes de abrir OpenCode

```bash
# 1. Verificar que el stack está corriendo
curl -s https://ollama.thebeast.local/v1/models | jq '.data[].id'

# 2. Pre-validar el código (limpiarlo antes de que el modelo lo vea)
cd gramola/server
cargo fmt && cargo clippy --fix --allow-dirty && cargo check
```

Si `cargo check` falla antes de empezar la sesión, corrige los errores a mano primero.
No le des al modelo código que ya tiene errores de compilación — gastará tokens en ruido.

### Arrancar la sesión

```bash
cd gramola/server   # o gramola/client
opencode
```

### Al inicio de cada sesión

```
/add ARCHITECTURE.md
/add CONSTRAINTS.md
```

Y luego los ficheros específicos de la tarea.

### Ciclo de trabajo dentro de la sesión

```
1. /add ficheros relevantes para la tarea concreta
2. Enviar prompt con rol + contexto + tarea + restricciones
3. Revisar la respuesta — ¿propone tocar algo que no debías?
4. Si sí: rechazar y refinar el prompt
5. Si no: copiar los cambios propuestos al fichero real
6. cargo check  (o tsc --noEmit para el cliente)
7. Si hay errores: pegárselos al modelo para que los corrija
8. Critic pass sobre los cambios aplicados
9. Si el critic no encuentra problemas: commit
```

### Aplicar cambios

A diferencia de Aider, OpenCode no aplica diffs directamente al fichero.
El modelo propone el código en el chat. Tú lo copias.

Dos formas de hacerlo:

**Opción A — copiar el bloque completo** si el modelo reescribió la función entera:
```bash
# El modelo muestra la función completa. La copias sobre el fichero.
```

**Opción B — aplicar como diff manual** si los cambios son pequeños:
```bash
# El modelo muestra: "en la línea X, cambiar Y por Z"
# Lo haces con tu editor o con sed
```

**Consejo práctico:** pide siempre el código completo de la función modificada,
no fragmentos. Es más fácil de aplicar:

```
Dame el método completo Player::delete_song con los cambios.
No me des solo las líneas que cambian — dame todo el método.
```

### Después de aplicar cambios

```bash
# Servidor Rust
cargo fmt
cargo check
cargo clippy -- -D warnings

# Cliente React
pnpm tsc --noEmit
pnpm run lint
```

Si hay errores, pégalos en el chat:

```
cargo check devuelve este error:

error[E0502]: cannot borrow `self.player` as mutable because it is also borrowed as immutable
  --> src/audio/plyr.rs:142:9
   |
141|         let queue = self.queue()?;
   |                     ----------- immutable borrow occurs here
142|         self.delete_from_queue(id)?;
   |         ^^^^ mutable borrow occurs here

Corrige solo este error. No cambies nada más.
```

---

## 9. Prompts por tipo de tarea

### Implementar un stub vacío (Rust)

```
[contexto: ARCHITECTURE.md, CONSTRAINTS.md, src/audio/plyr.rs]

El método <nombre> en src/audio/plyr.rs es actualmente un stub que devuelve Ok(()) sin hacer nada.

Lo que debe hacer:
1. <paso 1>
2. <paso 2>
3. <paso 3>

NO cambies la firma del método.
NO toques ningún otro método.
NO crees ficheros nuevos.

Dame el método completo con la implementación.
Restringe a CONSTRAINTS.md: no unwrap(), errores con ?.
```

### Corregir un error de compilación

```
[contexto: src/audio/plyr.rs]

cargo check devuelve este error:
<pegar el error exacto con número de línea>

Analiza solo el error. Explica por qué se produce en un comentario inline.
Dame la función completa corregida.
No cambies nada más del fichero.
```

### Añadir un endpoint HTTP (Rust)

```
[contexto: ARCHITECTURE.md, CONSTRAINTS.md, src/server/http.rs, src/server/routes/<módulo>.rs]

Añade el endpoint PATCH /queue/move/:from/:to que mueva una canción en la cola MPD.

Pasos:
1. En src/server/routes/queue.rs, crea el handler:
   - Firma: pub(crate) async fn move_song(AuthUser(_): AuthUser, State(state): State<AppState>, Path((from, to)): Path<(usize, usize)>) -> impl IntoResponse
   - Llama a state.player.lock().await.move_song(from, to).await
   - En error: devuelve { "status": "error", "message": "..." }
   - En éxito: devuelve { "status": "ok" }

2. En src/server/http.rs, registra la ruta en el router de queue:
   .route("/queue/move/:from/:to", patch(queue::move_song))

Solo añade esas dos cosas. No reorganices el router. No añadas lógica extra.
Dame los dos fragmentos de código: el handler completo y la línea de ruta.
```

### Escribir tests unitarios (Rust)

```
[contexto: CONSTRAINTS.md, src/auth/service.rs]

Escribe tests unitarios para las funciones hash_password y verify_password
en src/auth/service.rs.

Tests requeridos:
- hash_password: dado un string, el hash resultante no es igual al input
- hash_password: dos llamadas con el mismo input producen hashes distintos (salt aleatorio)
- verify_password: con el hash correcto devuelve Ok(true)
- verify_password: con contraseña incorrecta devuelve Ok(false)
- verify_password: con hash malformado devuelve Err

Los tests van en #[cfg(test)] mod tests al final del mismo fichero.
No uses .unwrap() en los tests. Usa .expect("descripción del fallo").
No añadas dependencias nuevas.
Dame el bloque de tests completo.
```

### Refactoring: mover código sin cambiar comportamiento

```
[contexto: ARCHITECTURE.md, src/<origen>.rs, src/<destino>.rs]

Quiero mover la función <nombre> de src/<origen>.rs a src/<destino>.rs.
El comportamiento no debe cambiar. Los tests existentes deben seguir pasando.

Pasos exactos:
1. Copia la función a src/<destino>.rs con la misma firma
2. En src/<origen>.rs, reemplaza la implementación por una llamada a src/<destino>.rs
3. Actualiza los imports necesarios en ambos ficheros

No reescribas la lógica. No la "mejores". Solo muévela.
Dame: la función en destino, la función wrapper en origen, los imports actualizados.
```

### Diseño con r1-architect

```
[modelo: r1-architect]
[contexto: ARCHITECTURE.md, CONSTRAINTS.md, src/server/app_state.rs, src/audio/plyr.rs]

Think briefly (max 6 steps). Focus on the final answer.

Necesito vincular el Player de cada handler al MPD de la instancia del usuario autenticado.
Actualmente hay un único Player global en AppState.
La tabla mpd_instances tiene: id, owner_id, host, port.

Propón solo el diseño de la solución — sin código de implementación todavía.
Describe: qué cambiaría en AppState, cómo el handler obtendría el Player correcto,
y si habría algún riesgo de concurrencia con la estrategia propuesta.
```

### Análisis de código existente

```
[modelo: r1-architect]
[contexto: ARCHITECTURE.md, src/audio/plyr.rs]

Think briefly (max 4 steps).

¿Ya existe alguna función o método en estos ficheros que conecte a MPD
y obtenga el cliente listo para usar?
Si existe, dame su nombre, firma y dónde está.
Si no existe, di simplemente "no existe".
No escribas código nuevo.
```

### Análisis del cliente React

```
[modelo: qwen-editor]
[contexto: ARCHITECTURE_CLIENT.md, CONSTRAINTS_CLIENT.md, src/contexts/AppContext.tsx, src/hooks/useSongData.ts]

Analiza la duplicación de estado entre AppContext.tsx y useSongData.ts.
Lista qué campos de estado están duplicados en los dos ficheros.
No propongas cambios todavía. Solo lista las duplicaciones.
```

---

## 10. Errores comunes y cómo evitarlos

### El modelo toca ficheros que no debías

**Síntoma:** La respuesta incluye cambios en funciones o ficheros que no mencionaste.

**Causa:** Diste demasiado contexto o no especificaste qué no debe tocar.

**Solución:**
- Añadir al prompt: `NO modifiques ningún fichero excepto los que te he indicado explícitamente`
- Reducir el contexto: si añadiste 5 ficheros y solo necesitabas 2, quita los 3

### El modelo reimplementa algo que ya existe

**Síntoma:** Propone crear una función nueva que hace lo mismo que una que ya existe.

**Solución:** Antes de pedir la implementación, pregunta primero:

```
[contexto: src/lib.rs, src/audio/plyr.rs, src/infra/mod.rs]

¿Ya existe alguna función o método que conecte a un cliente MPD dado host y port?
Busca en los ficheros que te he dado. Responde solo: sí/no y el nombre si existe.
```

### El modelo propone una abstracción nueva no pedida

**Síntoma:** Propone un trait, un módulo o una struct nueva que no planificaste.

**Solución:** Añadir al prompt:

```
No introduzcas abstracciones nuevas (traits, módulos, structs intermedios).
Usa los tipos y patrones que ya existen en el proyecto.
Si crees que hace falta algo nuevo, explícalo ANTES de escribir código y espera mi confirmación.
```

### El modelo cambia la firma de una función pública

**Síntoma:** El diff cambia el tipo de retorno o los parámetros de una función usada en otros módulos.

**Solución:** Añadir al prompt:

```
No cambies la firma (nombre, parámetros, tipo de retorno) de ninguna función existente.
Si el cambio de firma es necesario, explícalo antes y espera confirmación.
```

### R1 no converge (bloque `<think>` interminable)

**Síntoma:** La respuesta tarda mucho y produce un razonamiento muy largo sin llegar a una conclusión.

**Solución:**
1. Escribir: `Give the answer with minimal reasoning.`
2. Si sigue igual: `/models` → cambiar a `qwen-editor` para esa tarea concreta

### El modelo da respuestas inconsistentes entre sesiones

**Síntoma:** En una sesión propone usar `Arc<Mutex<T>>` y en otra propone `Rc<RefCell<T>>` para el mismo problema.

**Causa:** No cargaste ARCHITECTURE.md al inicio de la sesión.

**Solución:** Siempre empezar con `/add ARCHITECTURE.md /add CONSTRAINTS.md`.

---

## 11. Critic pass

Después de aplicar cualquier cambio no trivial, antes de hacer commit,
pasa el siguiente prompt al modelo activo con los ficheros modificados en contexto:

```
[contexto: CONSTRAINTS.md, <ficheros que acabas de modificar>]

Revisa críticamente los cambios que acabas de proponer.
Para cada problema encontrado usa este formato:

Bug/Riesgo: descripción
Fichero: nombre.rs
Línea: número o rango
Explicación: por qué es un problema
Corrección: qué cambiar exactamente

Busca específicamente:
- unwrap() o expect() fuera de #[cfg(test)]
- Errores silenciados con let _ = o .ok() sin justificación
- Endpoints nuevos sin AuthUser/AdminUser que deberían tenerlo
- Queries SQL con format!() o concatenación de strings
- clone() que podría evitarse con una referencia
- Cambios en firmas de funciones públicas no solicitados
- Lógica de negocio colocada en handlers en lugar de en MusicDB o Player
- Violaciones de CONSTRAINTS.md

Si no hay problemas, responde únicamente: "Sin problemas encontrados."
```

**Cuándo ejecutarlo:**

| Tipo de cambio | Critic pass |
|---|---|
| Formateo, renombrado, comentarios | No necesario |
| Nueva función con firma simple | Recomendado |
| Refactor de módulo o API pública | Obligatorio |
| Cambio en concurrencia o mutexes | Obligatorio |
| Nuevo endpoint HTTP | Obligatorio |
| Cambio en manejo de errores | Obligatorio |

---

## 12. Checklist de cierre de sesión

```
[ ] cargo check pasa sin errores
[ ] cargo clippy -- -D warnings pasa sin warnings
[ ] Critic pass ejecutado sobre los ficheros modificados
[ ] No hay unwrap() nuevo fuera de tests
[ ] No hay rutas nuevas sin autenticación que deberían tenerla
[ ] ARCHITECTURE.md actualizado si se añadió algo estructural
[ ] Commit hecho con mensaje descriptivo
[ ] Solo se modificaron los ficheros que se pretendía modificar
```

Para el cliente React:
```
[ ] pnpm tsc --noEmit pasa sin errores
[ ] pnpm run lint pasa sin warnings
[ ] Critic pass ejecutado
[ ] No hay useState nuevo que duplique estado de AppContext
[ ] No hay llamadas fetch() directas en componentes (solo endpoints de src/api/)
[ ] Commit hecho
```

---

## 13. Referencia rápida de comandos

### Comandos de OpenCode

| Comando | Efecto |
|---|---|
| `/add src/audio/plyr.rs` | Añade un fichero al contexto de la sesión |
| `/files` | Lista los ficheros actualmente en contexto |
| `/clear` | Limpia el historial de conversación y el contexto |
| `/models` | Muestra los modelos disponibles y permite cambiar |
| `/exit` | Cierra OpenCode |

### Pipeline de pre-validación (Rust)

```bash
cargo fmt && cargo clippy --fix --allow-dirty && cargo check
```

Ejecutar **antes** de abrir OpenCode. El modelo recibe código limpio.

### Pipeline de post-cambio (Rust)

```bash
cargo check
cargo clippy -- -D warnings
```

Ejecutar **después** de aplicar cada cambio propuesto.

### Pipeline cliente React

```bash
# Pre y post
pnpm tsc --noEmit
pnpm run lint
```

### Secuencia de inicio de sesión (copiar y pegar)

```
/add ARCHITECTURE.md
/add CONSTRAINTS.md
/add src/<módulo>/<fichero>.rs
```

Luego el primer mensaje:

```
Eres un programador Rust senior trabajando en el proyecto Gramola.
Has leído ARCHITECTURE.md y CONSTRAINTS.md.
Antes de hacer cualquier cambio, confirma que entiendes las restricciones del proyecto.
```

### Secuencia de inicio para el cliente

```
/add ARCHITECTURE.md
/add CONSTRAINTS.md
/add src/contexts/AppContext.tsx
```

Primer mensaje:

```
Eres un programador React/TypeScript senior trabajando en el proyecto Gramola.
Has leído ARCHITECTURE.md y CONSTRAINTS.md del cliente.
El estado global de canción y reproductor vive únicamente en AppContext — no se duplica en otros hooks ni componentes.
Confirma que entiendes esto antes de empezar.
```

---

## Apéndice — Ejemplo de sesión real comentada

Esta es una sesión completa trabajando en el stub `Player::move_song`.

```
# Arrancar
cd gramola/server
cargo fmt && cargo clippy --fix --allow-dirty && cargo check
# → pasa sin errores

opencode

# Cargar contexto
/add ARCHITECTURE.md
/add CONSTRAINTS.md
/add src/audio/plyr.rs

# Verificar que el stub existe
> ¿Existe el método move_song en Player? Dame su firma y el cuerpo actual.

# Respuesta del modelo: sí, es un stub con let _ = (from, to); Ok(())

# Cambiar al editor si estamos en r1 (no hace falta aquí, es implementación directa)
# Quedarse en qwen-editor que es el default

> Eres un programador Rust senior. Has leído ARCHITECTURE.md y CONSTRAINTS.md.
>
> El método Player::move_song en src/audio/plyr.rs es un stub que no hace nada.
>
> Impleméntalo:
> 1. Conecta a MPD con get_client usando self.host, self.port, self.max_connection_retries
> 2. Usa c.move_(from as u32, mpd::song::QueuePlace::Id(to as u32)) — ese es el método correcto de la crate mpd
> 3. Si MPD devuelve error, propágalo con ?
>
> NO cambies la firma: async fn move_song(&mut self, from: usize, to: usize) -> Result<(), mpd::error::Error>
> NO toques ningún otro método.
> NO crees ficheros nuevos.
>
> Dame el método completo.

# El modelo propone la implementación. La copio a plyr.rs.

# Validar
cargo check
# → error: método move_ no existe en la crate mpd, el correcto es c.mv(from, to)

# Pegar el error al modelo
> cargo check devuelve:
> error[E0599]: no method named `move_` found for mutable reference `&mut Client<TcpStream>`
>
> El método correcto de la crate mpd para mover en la cola es c.mv(from, to).
> Corrige solo esta línea. Dame el método completo corregido.

# El modelo corrige. Aplico de nuevo.

cargo check
# → pasa

# Critic pass
> Revisa el método move_song que acabas de escribir.
> Busca: unwrap(), errores silenciados, cambios no pedidos, violaciones de CONSTRAINTS.md.
> Si no hay problemas, di solo: "Sin problemas encontrados."

# El modelo responde: "Sin problemas encontrados."

# Commit
git add src/audio/plyr.rs
git commit -m "feat: implementar Player::move_song (stub → MPD mv)"

/exit
```

Esta sesión tomó ~8 minutos. Un stub implementado, validado, revisado y commiteado.