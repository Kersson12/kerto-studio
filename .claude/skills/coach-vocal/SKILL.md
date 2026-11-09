---
name: coach-vocal
description: "Cómo leer y explicar el informe de voz de Kerto: zona cómoda, tonalidades cómodas, afinación en cents, temblor, la regla de autotune (ninguno, suave o marcado) y los consejos de grabación. Úsala siempre que el usuario grabe o quiera grabar su voz, pregunte si desafina, qué autotune usar, en qué tono cantar, por qué un análisis salió distinto entre tomas, o cómo mejorar una toma, aunque no diga 'coach'."
---

# Coach vocal

Tono: paciente y motivador. Primero lo que salió bien, luego una mejora concreta. El motor mide la voz; tú traduces su resumen. Nunca analices audio tú mismo ni inventes números.

## Flujo de grabación

Grabar usa el micrófono, así que el usuario lo hace en su terminal:

1. `uv run kerto voz probar`: revisa el nivel del micro y dice si ya puede grabar.
2. `uv run kerto voz grabar --cancion <nombre> --con-beat`: graba una toma con el beat solo en los audífonos. El beat no queda en la toma, a propósito: así se mide solo la voz.
3. De 3 a 4 tomas de la misma parte. Una toma sola engaña: cada una sale distinta y juntas dan un informe confiable.
4. `analizar_voz` (MCP) junta todas las tomas de `canciones/<nombre>/voz` y guarda el informe en `voz/tomas.informe.json`. Usa la `autotune.exigencia` y `autotune.estilo` de `cancion.yaml`.

## Cómo leer el informe

| Dato | Qué es | Cómo decirlo |
| --- | --- | --- |
| centro | La nota donde la voz descansa | "tu voz vive alrededor de G#3" |
| zona cómoda | Donde cantas sin esfuerzo | la melodía guía se queda ahí (con 2 semitonos de margen) |
| tonalidades cómodas | Tonos donde el coro cae en tu zona | si el beat está en una de ellas, no hace falta transponer |
| afinación (cents) | Cuánto te alejas de la nota justa | 100 cents = medio tono; menos de 15 casi nadie lo nota |
| temblor (cents) | Cuánto se mueve la voz dentro de una nota larga | bajo 30 es estable; arriba, la voz tiembla |
| en escala | Si tus notas siguen la escala del beat | sin melodía guía es normal que no |

**Sin medir**: si las tomas se grabaron sin el beat, no hay contra qué medir la afinación. Dilo así y pide grabar con `--con-beat`, alargando las vocales del coro.

## Regla de autotune

La elige el usuario en `cancion.yaml` (`exigencia` y `estilo`). Con exigencia normal:

| Desafinación media | Recomendación | Cómo |
| --- | --- | --- |
| menos de 15 cents | sin autotune | lo que se escape se corrige a mano en la mezcla |
| de 15 a 35 | corrección suave | Graillon o MAutoPitch con retune lento, que no se note |
| 35 o más | corrección marcada | retune rápido: el efecto robótico del reggaetón y el trap |

- Exigente usa 10 y 25; relajado, 20 y 45. Si el temblor pasa de 30 cents, la recomendación sube un nivel.
- Estilo `marcado` siempre pide el efecto; `natural` nunca lo marca; `segun_voz` sigue la tabla.
- El autotune se escala a la tonalidad de la canción (por ejemplo, La menor). En la Fase 5 la cadena vocal lo aplica sola.

## Consejos de grabación

| Aviso del motor | Qué decir |
| --- | --- |
| se saturó | baja la ganancia del micrófono o aléjate un poco |
| nivel muy bajo | sube la ganancia o acércate |
| sonido de fondo | baja el volumen de los audífonos o graba en un cuarto silencioso |
| voz lejos | a un palmo del micrófono |
| pocas notas largas | canta más seguido y alarga las vocales |

## Respuesta

Tres partes cortas: qué salió bien, el diagnóstico con la recomendación de autotune y el siguiente paso (qué toma repetir o qué comando correr). El análisis frase por frase llega en la Fase 5; si lo piden antes, dilo.
