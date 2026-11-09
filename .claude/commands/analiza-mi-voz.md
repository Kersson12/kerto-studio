---
description: Analiza tus tomas de voz y te dice qué autotune usar y qué mejorar
argument-hint: "[canción, como luna-negra]"
---

Canción: $ARGUMENTS

1. Si no dijo la canción y en `canciones/` hay una sola, usa esa; si hay varias, pregunta cuál.
2. Llama al agente `coach-vocal` con el nombre de la canción. Él usa `analizar_voz` (todas las tomas juntas, con la exigencia y el estilo de autotune de `cancion.yaml`) y te devuelve el diagnóstico.
3. Si todavía no hay tomas, dale al usuario los comandos para su terminal, porque grabar necesita el micrófono: `uv run kerto voz probar` revisa el nivel, y `uv run kerto voz grabar --cancion <nombre> --con-beat` graba una toma con el beat en los audífonos. Pídele 3 o 4 tomas de la misma parte y vuelve a /analiza-mi-voz.
4. Pásale la respuesta del coach en pocas líneas. Si cambió su zona cómoda o el autotune recomendado, propón actualizar la sección voz de `cancion.yaml` y hazlo solo si dice que sí.
