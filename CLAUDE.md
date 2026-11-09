# Kerto Studio

Motor open source (GPL-3.0) que convierte a Claude Code en un equipo de producción musical: beat, voz, autotune, mezcla y master. El motor en Python (`kerto/`) hace el trabajo pesado; Claude nunca toca el audio. Cada género es un pack en `generos/`; el primero es reggaetón.

**Lee `PLAN.md` al empezar cada sesión y al cambiar de fase.** Trabaja solo en la fase actual: la primera con casillas sin marcar en "Lista cuando". No pases de fase hasta que el usuario las marque todas.

## Comandos
- `uv sync`: instala dependencias (uv baja Python 3.12)
- `uv run pytest`: tests; `uv run pytest --cov=kerto` para ver cobertura
- `uv run ruff format . && uv run ruff check .`: formato y lint
- `uv run kerto --help`: el motor en la terminal; grabar la voz (`kerto voz grabar`) se hace desde aquí porque necesita el micrófono

## Motor desde Claude Code
- Para crear beats y canciones, analizar la voz, transponer o ver cómo va una canción usa las herramientas del MCP `kerto` (`.mcp.json`): `listar_generos`, `crear_beat`, `renderizar_cancion`, `generar_seccion`, `transponer`, `analizar_voz` y `estado_cancion`. No uses Bash para eso.
- Un pedido como "hazme un perreo en La menor a 95" se resuelve con `crear_beat` (perreo = reggaetón); después dile al usuario qué escuchar y dónde están los archivos.
- Los agentes de `.claude/agents/` tienen solo las herramientas que necesita cada uno.

## Cómo trabajar
- Ciclo de cada paso: plan corto, tests primero, código, commit y checkpoint con algo para escuchar o probar.
- Un commit por paso y uno antes de cada loop de Ralph. Ralph solo donde la fase lo indica, siempre con `--max-iterations`.
- Cada módulo nuevo se construye con planificación y TDD (flujo de ECC).
- Las decisiones de gusto (sonido, letra, personalidad de los agentes) las toma el usuario: pregunta.
- Habla en español y en simple: el usuario no sabe de música.
- Trabaja solo dentro del proyecto. Nunca borres audio del usuario.
- Documentación de librerías con Context7, en vez de adivinar APIs.

## Ahorro de tokens
- Herramientas de alto nivel (`crear_beat(...)`, no nota por nota). El análisis de audio y la teoría se calculan en Python; a Claude le llega un resumen de pocas líneas.
- Notas en notación compacta (`C4:1/4:v90`, skill `notacion-compacta`). Nunca pegues audio, arrays ni JSON grandes en el chat.
- De una canción lee `canciones/<nombre>/cancion.yaml`, su única fuente de verdad; no los MIDI ni el audio.
- Subagentes solo para tareas puntuales: cada uno arranca sin contexto.

## Legal
- Todo el repo es GPL-3.0. Los plugins gratis se descargan de sus sitios oficiales; nunca redistribuyas binarios ajenos.
- Sin samples de canciones ajenas: las referencias se analizan, nunca se copian. Nada de clonar voces de artistas ni de usar software pirata.
