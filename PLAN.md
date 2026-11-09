# Plan Kerto

Nov 8, 2026 · @Diker

Kerto es un repo open source, licencia GPL-3.0, que convierte a Claude Code en un equipo de producción musical gratis, para cualquier género: compone el beat, analiza tu voz, recomienda autotune, mezcla y masteriza. Cada género llega como un pack, y el primero es reggaetón, el de tu canción. Tu canción se construye dentro del proyecto fase por fase y termina siendo la demo del repo. El plan está escrito para que Claude Code lo ejecute: descárgalo como Markdown y guárdalo como `PLAN.md` en la raíz del repo.

## Cómo usar este plan

Claude Code ejecuta el plan fase por fase, y tú validas con tus oídos al cierre de cada fase antes de seguir.

### Instrucciones para Claude Code

1. Lee este archivo completo al empezar cada sesión y al cambiar de fase. Trabaja solo en la fase actual.
2. Antes de programar, instala lo de la sección Instalación. Si un comando falla o cambió, lee el README oficial del repo enlazado y usa el comando vigente. Nunca instales desde copias o mirrors.
3. En cada fase sigue este ciclo: plan corto, tests primero, código, commit y checkpoint con el usuario (algo para escuchar o probar).
4. No pases a la siguiente fase hasta que el usuario marque todas las casillas de "Lista cuando".
5. Usa Ralph solo donde la fase lo indica, siempre con `--max-iterations`.

### Reglas de trabajo

- Git desde el primer minuto: un commit por paso, y un commit antes de cada loop de Ralph.
- Trabaja solo dentro de la carpeta del proyecto. Nunca borres audio del usuario.
- Pregunta antes de decisiones de gusto (sonido, letra, personalidad de los agentes): esas las toma el usuario.

### Ahorro de tokens

- Herramientas de alto nivel: una llamada como `crear_beat(genero="reggaeton", compases=8)` en vez de nota por nota.
- El análisis de audio y la teoría musical se calculan en Python; a Claude solo le llega un resumen de pocas líneas.
- Notación compacta de notas (`C4:1/4:v90`) en todo el proyecto. Nunca pegar audio, arrays ni JSON grandes en el chat.
- `CLAUDE.md` corto; el detalle vive en las skills, que se cargan solo cuando hacen falta.
- Context7 para leer la documentación vigente de las librerías en vez de adivinar APIs.
- Subagentes solo para tareas puntuales: cada uno arranca sin contexto y cuesta tokens.

### Reglas legales y éticas

- Todo el repo es GPL-3.0, porque varias librerías clave (pedalboard, DawDreamer, matchering) lo son.
- Los plugins gratis se descargan de sus sitios oficiales; el repo no redistribuye binarios ajenos.
- Sin samples de canciones ajenas. Las canciones de referencia solo se analizan, nunca se copian.
- Nada de clonar voces de artistas ni de usar software pirata.

## Instalación: plugins y skills de Claude Code

Se instalan cinco plugins escribiendo estos comandos en el chat de Claude Code. Requisitos previos: Node.js 18+, Git y Claude Code 2.1 o superior (los pide ECC).

| Plugin | Para qué sirve en este proyecto | Comandos (dentro de Claude Code) |
| --- | --- | --- |
| [ECC (Everything Claude Code)](https://github.com/affaan-m/ECC) | Agentes y comandos para planear, hacer TDD y revisar código y seguridad mientras se construye el motor | `/plugin marketplace add https://github.com/affaan-m/ECC` y luego `/plugin install ecc@ecc` |
| [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Diseño del panel visual, la landing y los visuales del README (Fases 6 y 7) | `/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill` y luego `/plugin install ui-ux-pro-max@ui-ux-pro-max-skill` |
| [Ralph Loop](https://github.com/anthropics/claude-plugins-official) | Ejecutar a Claude en loop hasta que los tests pasen | `/plugin install ralph-loop@claude-plugins-official` |
| [Context7](https://github.com/upstash/context7) | Documentación vigente de pedalboard, DawDreamer, librosa y demás, para no adivinar APIs | `/plugin install context7@claude-plugins-official` |
| [skill-creator](https://github.com/anthropics/claude-plugins-official) | Crear y probar las skills propias del proyecto (Fase 4) | `/plugin install skill-creator@claude-plugins-official` |

Si `/plugin install` no encuentra el marketplace oficial, agrégalo primero con `/plugin marketplace add anthropics/claude-plugins-official`.

### Reglas de ECC

Los plugins no pueden instalar reglas, así que se copian a mano solo las que sirven aquí (en Windows, desde Git Bash):

```bash
git clone https://github.com/affaan-m/ECC.git
cd ECC
mkdir -p ~/.claude/rules/ecc
cp -R rules/common ~/.claude/rules/ecc/
cp -R rules/python ~/.claude/rules/ecc/
```

### Avisos

- ECC se instala por una sola vía, plugin o instalador, nunca las dos. Si el contexto se llena, usa su perfil mínimo con el comando que indique el README.
- UI/UX Pro Max se activa sola cuando pides trabajo de interfaz; no necesita comando.
- Ralph siempre con `--max-iterations`: sin límite ni promesa de cierre, corre indefinidamente.
- Instala solo desde estos repos oficiales. ECC advierte que las copias no oficiales pueden traer malware.

## Software musical y librerías

Todo es gratis. El software musical lo instalas tú; las librerías las instala Claude Code con `uv` dentro del proyecto, con Python 3.11 o superior (lo pide DawDreamer).

### Software musical (lo instalas tú)

| Programa | Para qué | Notas |
| --- | --- | --- |
| [Waveform Free](https://www.tracktion.com) | DAW donde grabas la voz, escuchas y armas la canción | Gratis sin vencimiento, acepta VST |
| [Surge XT](https://github.com/surge-synthesizer/surge) | Sintetizador de bajos, pads y leads; el motor también lo usa para renderizar | Open source |
| [Vital](https://vital.audio) | Sintetizador para leads y 808 | Versión gratis |
| [Graillon](https://www.auburnsounds.com) | Autotune en vivo mientras grabas | Edición gratis |
| [MAutoPitch](https://www.meldaproduction.com) | Autotune alternativo | En el paquete gratis de MeldaProduction |
| [TDR Nova](https://www.tokyodawn.net) | Ecualizador dinámico para la voz | Gratis |
| [Valhalla Supermassive](https://valhalladsp.com) | Reverb y delay | Gratis |

### Librerías (las instala Claude Code)

| Librería | Para qué | Fase |
| --- | --- | --- |
| [uv](https://github.com/astral-sh/uv) | Entorno y dependencias de Python | 0 |
| [mido](https://github.com/mido/mido) | Escribir y leer MIDI | 1 |
| [pretty\_midi](https://github.com/craffel/pretty-midi) | Manipular notas, acordes y tiempos en MIDI | 1 |
| [DawDreamer](https://github.com/DBraun/DawDreamer) | Renderizar MIDI a WAV con plugins VST, sin abrir un DAW | 1 |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) | Grabar la muestra de voz desde el motor | 2 |
| [librosa](https://github.com/librosa/librosa) | Análisis de audio y detección de tono (pYIN) | 2 |
| [torchcrepe](https://github.com/maxrmorrison/torchcrepe) | Detección de tono más precisa; opcional porque instala PyTorch | 2 |
| [demucs](https://github.com/adefossez/demucs) | Separar la batería de una canción de referencia que tú aportes | 3 |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | Servidor que conecta el motor con Claude Code | 4 |
| [pedalboard](https://github.com/spotify/pedalboard) | Cadena de efectos de voz, incluidos plugins VST3 | 5 |
| [pyloudnorm](https://github.com/csteinmetz1/pyloudnorm) | Medir volumen en LUFS para el mix doctor | 5 |
| [matchering](https://github.com/sergree/matchering) | Masterizar comparándote con una canción de referencia | 5 |
| [Tracktion Engine](https://github.com/Tracktion/tracktion_engine) | Base de un DAW propio, solo si se llega a la Fase 8 | 8 |

## Arquitectura

&#91;embedded content: arquitectura · 7 piezas\]

Claude Code nunca toca el audio: le pide al MCP, el motor hace el trabajo pesado y escribe en la carpeta de la canción, que tú abres en Waveform Free para grabar y escuchar.

## Estructura del repo

El motor en Python es el cerebro; todo lo demás (Claude Code, el panel, el DAW) lo usa a través de él.

```
kerto-studio/
├── PLAN.md                  # este plan
├── CLAUDE.md                # reglas cortas para Claude Code
├── LICENSE                  # GPL-3.0
├── README.md / README.es.md
├── pyproject.toml           # uv, Python 3.11+
├── kerto/                   # el motor
│   ├── teoria/              # escalas, acordes, tonalidades
│   ├── ritmos/              # motor de patrones para cualquier género
│   ├── cancion/             # estructura, bajo, melodía, letras
│   ├── voz/                 # coach vocal
│   ├── mezcla/              # cadena vocal, mix doctor, master
│   ├── render/              # MIDI a WAV con DawDreamer
│   ├── notacion.py          # notación compacta de notas
│   └── cli.py               # comando `kerto`
├── mcp_server/              # herramientas para Claude Code (Fase 4)
├── studio/                  # panel visual local (Fase 6)
├── generos/                 # un pack por género: reggaeton/ primero, luego los que sumes
├── .claude/
│   ├── agents/              # productor, coach-vocal, ingeniero-mezcla, letrista, critico-ar
│   ├── skills/              # skills propias del proyecto
│   └── commands/            # /nueva-cancion, /analiza-mi-voz, /mezcla
├── canciones/               # tus canciones (fuera de git, salvo la demo)
├── tests/
└── .github/workflows/       # CI: tests en cada push
```

Cada canción vive en su carpeta con un `cancion.yaml` que describe tonalidad, BPM, secciones y pistas. Es la única fuente de verdad: Claude lee ese archivo corto en lugar de los MIDI o el audio, y eso ahorra tokens.

### Packs de género

El motor no sabe de ningún género en particular: todo lo propio de un estilo vive en `generos/<genero>/`, así que sumar uno nuevo no toca el código. Cada pack trae:

- Rango de BPM, compás y patrones de batería con sus variaciones
- Estructura típica de canción y compases por sección
- Progresiones de acordes y escalas habituales
- Instrumentos y presets para los sintetizadores gratis
- Cadena vocal y niveles objetivo de mezcla
- Una skill corta que le explica el estilo a Claude

El primer pack es reggaetón, porque es el de tu canción. Después pueden venir trap, pop, house, cumbia, rock o los que pida la comunidad.

## El equipo: agentes y skills propias

Cinco agentes con personalidad viven en `.claude/agents/` y vienen incluidos en el repo. El Productor hace casi todo el trabajo y llama a los especialistas solo para tareas puntuales, porque cada agente arranca sin contexto y gasta tokens.

| Agente | Personalidad | Qué hace | Herramientas | Modelo |
| --- | --- | --- | --- | --- |
| Productor | Líder con visión, decide rápido | Define género, vibe, estructura, BPM y tonalidad; coordina al resto | Todas las del motor | El de la sesión |
| Coach vocal | Paciente y motivador | Analiza tu voz, recomienda autotune, dice qué frases repetir | Voz | Sonnet |
| Ingeniero de mezcla | Técnico y directo, habla en dB y Hz | Cadena vocal, mix doctor y master | Mezcla | Sonnet |
| Letrista | Creativo, adapta su estilo al género | Rimas, métrica e historia de la canción | Solo lectura de la canción | Sonnet |
| Crítico A&R | Honesto sin piedad | Dice si el coro pega y qué falta para sonar a radio | Solo lectura | Sonnet |

### Skills propias (en `.claude/skills/`)

- `notacion-compacta`: cómo se escriben notas, acordes y ritmos en el proyecto. Se crea en la Fase 0.
- `teoria-musical`: escalas, acordes, progresiones, ritmo y estructura de canciones, sin atarse a un género.
- `genero-<nombre>`: una por pack de género, empezando por `genero-reggaeton`. Se carga solo cuando trabajas en ese estilo.
- `coach-vocal`: cómo leer el informe de voz y elegir autotune.
- `mezcla`: cadena vocal, balance entre bombo y bajo, y cómo usar los niveles objetivo de cada pack.
- `plugins-gratis`: catálogo de plugins gratis, para qué sirve cada uno y dónde se descarga.

Cada skill es corta y deja el detalle en archivos de referencia que se leen solo cuando hacen falta. Se crean y prueban con skill-creator.

## Ralph: loops sin quemar tokens

Ralph repite la misma tarea hasta que se cumple una condición verificable. Sirve para código con tests; no sirve para decidir si algo suena bien.

| Úsalo para | No lo uses para |
| --- | --- |
| Implementar un módulo hasta que sus tests pasen | Decidir si un beat, un coro o una mezcla suenan bien |
| Arreglar un bug que se reproduce con un test | Diseñar la personalidad de los agentes |
| Refactorizar sin romper tests | Decisiones de licencia, legales o de publicación |

1. Haz commit antes de empezar, para poder deshacer.
2. Escribe un prompt de alcance cerrado: qué archivo, qué tests y cómo se comprueba.
3. Usa siempre `--max-iterations` (entre 10 y 20 para una tarea de fase) y una promesa de cierre única.
4. Al terminar, revisa el diff antes de seguir. Para cortar un loop: `/cancel-ralph`.

```
/ralph-loop "Lee PLAN.md, Fase 1. Implementa kerto/ritmos/patrones.py y el pack generos/reggaeton/.
Escribe primero los tests en tests/test_patrones.py y corre uv run pytest tras cada cambio.
No toques otros módulos. Cuando todos los tests pasen y hayas hecho commit,
escribe <promise>FASE1_PATRONES_OK</promise>. Solo escríbela si es verdad." --max-iterations 15 --completion-promise "FASE1_PATRONES_OK"
```

La promesa se compara texto por texto: tiene que coincidir exacta con la de `--completion-promise`.

## Fase 0 — Cimientos

El repo queda listo para trabajar: plugins instalados, reglas claras y tests corriendo en la nube.

**Cómo se desarrolla**

1. Instala los plugins de la sección Instalación y copia las reglas de ECC.
2. Crea el repo público kerto-studio en GitHub con licencia GPL-3.0, un README mínimo y un `.gitignore` que deje fuera el audio y `canciones/`, salvo la demo.
3. Configura el proyecto con `uv` y Python 3.11+, y crea la estructura de carpetas del plan.
4. Escribe un `CLAUDE.md` corto: qué es el proyecto, comandos, reglas de tokens y legales, y la orden de leer `PLAN.md`.
5. Define la notación compacta en `kerto/notacion.py` con sus tests, y crea la skill `notacion-compacta`.
6. Crea los cinco agentes de la sección El equipo en `.claude/agents/`, en versión inicial. Hasta que exista el MCP (Fase 4), trabajan con el comando `kerto`.
7. Agrega CI con GitHub Actions que corra `uv run pytest` en Windows, Mac y Linux en cada push.
8. Desde aquí, cada módulo se construye con el flujo de planificación y TDD de ECC.

**Ralph:** solo para el paso 5, la notación con sus tests.

**Tu canción:** eliges un nombre de trabajo y describes la vibe en una frase (por ejemplo, "perreo oscuro de discoteca"). Queda guardada en `canciones/<nombre>/cancion.yaml`.

**Lista cuando**

- [x] Los plugins aparecen en `/plugin` y las reglas de ECC están copiadas
- [x] El repo está en GitHub con licencia GPL-3.0
- [x] `uv run pytest` pasa en tu PC y en CI
- [x] Existe el `cancion.yaml` de tu canción con la vibe escrita

## Fase 1 — Primer beat

Sale tu primer beat, en MIDI y en WAV, generado por el motor con un solo comando. El motor sirve para cualquier género; el primer pack es reggaetón.

**Cómo se desarrolla**

1. `kerto/teoria/`: escalas, acordes y tonalidades, con tests (por ejemplo, que La menor contenga La, Si, Do, Re, Mi, Fa y Sol).
2. `kerto/ritmos/`: un motor de patrones que lee el pack de cada género, con variaciones (relleno, corte antes del coro) y una humanización suave de tiempo y fuerza para que no suene robótico.
3. El primer pack, `generos/reggaeton/`, con el dembow y sus variaciones.
4. Exportación a MIDI con mido y pretty\_midi, una pista por instrumento (en reggaetón: bombo, caja, hi-hat, percusión y 808).
5. Render a WAV con DawDreamer y Surge XT. Si un plugin no carga en tu PC, el respaldo es un sintetizador interno de DawDreamer (Faust).
6. El comando: `kerto beat --genero reggaeton --bpm 95 --tonalidad Am --compases 8 --variaciones 3`.
7. El motor responde con un resumen de tres líneas: archivos creados, género, BPM y tonalidad.

**Ralph:** sí para los pasos 1 a 4, que tienen tests claros. El render se prueba a mano en tu PC.

**Tu canción:** escuchas las tres variaciones en Waveform Free y eliges la base. La elección queda en `cancion.yaml`.

**Lista cuando**

- [x] El comando genera MIDI y WAV sin errores en tu PC
- [x] Los tests de teoría, patrones y MIDI pasan en CI
- [x] Escuchaste las variaciones y elegiste la base de tu canción

## Fase 2 — Coach de voz

El motor escucha tu voz, te dice tu tono y qué autotune necesitas, y adapta el beat a ti.

**Cómo se desarrolla**

1. Muestra de voz: `kerto voz grabar` graba 30 segundos con sounddevice, o importas un WAV grabado en Waveform Free.
2. Detección de tono con pYIN de librosa; torchcrepe queda como opción de más precisión.
3. Informe: nota más grave y más aguda, tesitura, tonalidades cómodas, desviación media de afinación en cents y estabilidad.
4. Recomendación de autotune con reglas simples y explicadas: sin autotune, corrección suave (retune lento en Graillon o MAutoPitch) o efecto marcado estilo trap.
5. Transposición: el beat de la Fase 1 se mueve a la tonalidad donde mejor suena tu voz.
6. Consejos de grabación según lo que detecte: ruido de fondo, saturación o distancia al micrófono.
7. A Claude solo le llega el informe corto; el análisis completo queda en un JSON dentro de la carpeta de la canción.

**Ralph:** sí para los pasos 2 y 3, probados con audios sintéticos (un tono de 440 Hz debe dar La4 con menos de 5 cents de error). Los umbrales del paso 4 los decides tú con el Coach.

**Tu canción:** grabas tu muestra, lees tu informe y el beat queda en tu tonalidad.

**Lista cuando**

- [x] Con tonos sintéticos, el análisis acierta la nota con menos de 5 cents de error
- [x] Con tu voz, el informe tiene sentido para ti
- [x] Sabes qué autotune usar, o que no lo necesitas
- [x] El beat suena en tu tonalidad

## Fase 3 — Canción completa

La canción entera queda armada: estructura, acordes, bajo, melodía guía dentro de tu rango y letra.

**Cómo se desarrolla**

1. Estructura según el pack de género (en reggaetón: intro, verso, pre-coro, coro, verso 2, coro, puente y outro), con los compases de cada sección. Se ajusta en `cancion.yaml`.
2. Progresiones de acordes del pack, con variaciones por sección (en reggaetón, tonalidad menor por defecto).
3. Bajo que sigue los acordes y se acomoda al bombo para no chocar: 808, eléctrico o sintetizado según el género.
4. Melodía guía generada siempre dentro de tu rango vocal de la Fase 2, en MIDI y en WAV para cantar encima.
5. Letra con el Letrista: rimas, conteo de sílabas por frase de la melodía e historia coherente. La versión final la apruebas tú.
6. Referencia a ritmo, opcional: con un audio que tú aportes, demucs separa la batería y el motor extrae BPM, tonalidad y patrón para crear algo nuevo inspirado en eso, nunca una copia.
7. `kerto cancion render` junta todo en un WAV guía y en un MIDI por pista para Waveform Free.
8. Un segundo pack de género, por ejemplo pop o trap, para comprobar que el motor no depende del reggaetón.

**Ralph:** sí para los generadores con reglas comprobables: la melodía nunca sale de tu rango, los compases cuadran y el bajo sigue los acordes. No para decidir si el coro pega: eso lo dices tú, con la opinión del Crítico A&R.

**Tu canción:** eliges la estructura, cierras la letra y ensayas cantando sobre la melodía guía.

**Lista cuando**

- [x] `kerto cancion render` genera el WAV guía y los MIDI por pista
- [x] Un test garantiza que la melodía nunca sale de tu rango
- [x] Un segundo pack de género genera una canción sin tocar el motor
- [x] Tienes la letra completa y aprobada
- [x] Te sabes la melodía del coro

## Fase 4 — Claude Code conectado: MCP, comandos y skills

Le hablas a Claude Code en lenguaje normal y tu equipo usa el motor directamente, sin que escribas comandos.

**Cómo se desarrolla**

1. Servidor MCP en `mcp_server/` con el SDK oficial de Python y herramientas de alto nivel: `listar_generos`, `crear_beat`, `analizar_voz`, `generar_seccion`, `transponer`, `mezclar` y `estado_cancion`.
2. Cada herramienta devuelve un resumen corto y las rutas de los archivos, nunca audio ni datos crudos.
3. El MCP se registra en el `.mcp.json` del proyecto, para que funcione apenas alguien clone el repo.
4. Los agentes pasan del comando `kerto` a las herramientas del MCP, cada uno solo con las que necesita.
5. Skills propias con skill-creator: `teoria-musical`, `coach-vocal`, `mezcla`, `plugins-gratis` y una `genero-<nombre>` por pack, con pruebas de que se activan cuando toca.
6. Comandos del proyecto en `.claude/commands/`: `/nueva-cancion`, `/analiza-mi-voz` y `/mezcla`.
7. Ajuste de personalidades: pruebas cada agente y corriges su tono hasta que te guste.

**Ralph:** sí para los tests del servidor MCP, que comprueban que cada herramienta responde con el formato corto esperado. No para las personalidades.

**Tu canción:** desde aquí la trabajas hablando, por ejemplo "Productor, haz el coro más oscuro" o "Coach, ¿en qué frase desafino?".

**Lista cuando**

- [ ] En una sesión nueva, "hazme un perreo en La menor a 95" crea el beat sin que escribas comandos
- [x] Cada herramienta del MCP responde en menos de 10 líneas
- [ ] Cada agente habla con la personalidad que elegiste
- [ ] Las skills propias se activan en las pruebas de skill-creator

## Fase 5 — Grabación, mezcla y master

Grabas tu voz, el motor te ayuda a elegir las mejores tomas y la canción sale mezclada y masterizada.

**Cómo se desarrolla**

1. Grabación en Waveform Free con la melodía guía en los audífonos, y Graillon en vivo si el Coach lo recomendó. Cada toma se exporta en WAV a la carpeta de la canción.
2. Tomas asistidas: el Coach analiza cada toma frase por frase y te dice cuál usar y qué repetir.
3. Cadena vocal con pedalboard: filtro de graves, ecualización, compresión, control de sibilancia, el autotune elegido (cargado como VST3) y reverb o delay. Los presets de cada género viven en su pack.
4. Mix doctor: volumen en LUFS con pyloudnorm, balance por bandas de frecuencia, choques entre bombo y bajo, picos que saturan y compatibilidad en mono, comparado con los niveles objetivo del pack.
5. Master por referencia con matchering, usando como referencia una canción que tú elijas.
6. Informe final del Ingeniero de mezcla en pocas líneas: qué cambió y por qué.

**Ralph:** sí para el mix doctor, probado con audios generados con problemas conocidos (un pico que satura, un bajo demasiado fuerte). No para el sonido final: eso es de tus oídos.

**Tu canción:** queda grabada, mezclada y masterizada.

**Lista cuando**

- [ ] El mix doctor detecta los problemas de los audios de prueba
- [ ] Tu canción pasa el mix doctor sin alertas graves
- [ ] La comparas con tu referencia y te gusta cómo suena
- [ ] Exportaste el master final en WAV y MP3

## Fase 6 — Panel visual

Un panel en tu navegador muestra tu canción, tu voz y tu mezcla de un vistazo. No graba: la grabación sigue en Waveform Free.

**Cómo se desarrolla**

1. Identidad visual del proyecto con UI/UX Pro Max: paleta, tipografía, modo oscuro y logo. La misma identidad se usa en el README y la landing.
2. `kerto studio` levanta un servidor local y abre el panel en el navegador.
3. Vistas: mapa de la canción por secciones, teclado con tu rango vocal marcado, informe del mix doctor con gráficas y estado de cada fase.
4. Botones que llaman al motor: generar una variación, transponer y volver a renderizar.
5. Pruebas en pantalla de celular y de computador.

**Ralph:** sí para los componentes con tests. El diseño lo apruebas tú viendo capturas.

**Tu canción:** la ves completa en el panel y lo usas para grabar el video demo.

**Lista cuando**

- [ ] `kerto studio` abre el panel y muestra tu canción
- [ ] El panel se ve bien en celular y en computador
- [ ] Aprobaste la identidad visual

## Fase 7 — Publicación v0.1

El repo sale al público con tu canción como demo, y cualquier persona puede crear su primer beat siguiendo solo el README.

**Cómo se desarrolla**

1. README en español e inglés: qué es, un GIF o video de 60 segundos "de cero a canción", instalación en un comando, tu canción como demo si quieres compartirla, y los créditos de cada librería con su licencia.
2. Instalador para Windows, Mac y Linux que prepara Python y las librerías, y abre los sitios oficiales de los plugins gratis para descargarlos.
3. `CONTRIBUTING.md`, código de conducta e issues marcados como "good first issue". Los packs de género nuevos (pop, trap, house, rock, cumbia y los que pida la comunidad) son la contribución más fácil.
4. Landing en GitHub Pages con la identidad visual de la Fase 6.
5. Release v0.1 en GitHub con notas de versión.
6. Difusión: awesome-mcp-servers, comunidades de productores en Reddit y Discord, Product Hunt y clips cortos de la demo en TikTok o Reels.

**Ralph:** no. La publicación la revisas tú paso a paso.

**Tu canción:** es la demo del repo, y su historia cuenta cómo la hiciste sin saber de música.

**Lista cuando**

- [ ] Alguien que no eres tú instala el proyecto y crea un beat siguiendo solo el README
- [ ] El README tiene la demo y los créditos de licencias
- [ ] El release v0.1 está publicado

## Fase 8 — Futuro: DAW propio

Solo si el proyecto despega: una app de escritorio propia sobre Tracktion Engine, con grabación nativa y el motor de Kerto como cerebro.

**Cómo se desarrolla**

1. Decide con datos si vale la pena: estrellas, usuarios activos, contribuyentes y lo que piden en los issues.
2. Prototipo en C++ sobre Tracktion Engine, cuya licencia GPLv3 encaja con la del repo: reproducir la canción de `cancion.yaml`, grabar voz con punch y overdub, y cargar los plugins gratis.
3. El motor en Python sigue siendo el cerebro; la app lo llama igual que el MCP.
4. Alternativa más liviana: conectores opcionales para FL Studio, REAPER o LMMS, para quien ya tiene un DAW.

**Ralph:** sí para módulos con tests. La latencia y la grabación se prueban a mano en hardware real.

**Lista cuando, para arrancar esta fase**

- [ ] La v0.1 tiene usuarios activos que piden grabar dentro del proyecto
- [ ] Hay al menos una persona con experiencia en C++ dispuesta a colaborar

## Fuentes

- [README de ECC](https://github.com/affaan-m/ECC): instalación como plugin, reglas manuales y aviso sobre copias no oficiales.
- [README de UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill): comandos de marketplace y activación automática.
- [Ralph Loop en el marketplace oficial](https://www.claudemarket.ai/plugins/anthropics-claude-plugins-official/ralph-loop): instalación, sintaxis y aviso de loops sin límite.
- [skill-creator en el marketplace oficial](https://www.claudemarket.ai/plugins/anthropics-claude-plugins-official/skill-creator): instalación y funciones.
- [DawDreamer 0.9.0](https://github.com/DBraun/DawDreamer/releases/tag/v0.9.0): Python 3.11 mínimo, VST y Faust.
- [pedalboard](https://github.com/spotify/pedalboard): licencia GPL-3.0, plugins VST3 y escritura de MP3.
- [Demucs en 2026](https://aireiter.com/es/blog/demucs-stem-separation-models-flags-cost): el repo mantenido es adefossez/demucs.
