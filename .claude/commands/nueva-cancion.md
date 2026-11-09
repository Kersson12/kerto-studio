---
description: Empieza una canción nueva desde una idea, como "perreo oscuro en La menor a 95"
argument-hint: "[idea: género, vibe, tonalidad o tempo]"
---

El usuario quiere empezar una canción nueva: $ARGUMENTS

1. Si no dijo nada, pregúntale en una línea qué quiere (un género o una vibe basta; el resto lo decides tú).
2. Con `listar_generos` elige el pack: perreo o dembow es reggaetón; trap es trap. Usa la tonalidad y el BPM que pidió, o los del pack si no dijo. La menor se escribe Am; Do mayor, C.
3. Elige un nombre corto en minúsculas con guiones a partir de la idea, como `luna-negra`. Si `canciones/<nombre>` ya existe, usa otro.
4. Llama a `crear_beat` con el género, el BPM, la tonalidad, `cancion` con ese nombre y `vibe` con la idea en pocas palabras. Escribe las variaciones y el `cancion.yaml` inicial.
5. Responde en pocas líneas: una frase simple por variación (cómo se siente cada una), la carpeta de los WAV y la pregunta de cuál le gusta. No elijas por el usuario: el sonido lo decide quien canta.
6. Cuando elija, anota la base en `cancion.yaml` (variacion y wav, y acordes si pidió una capa como teclado o pad). Después, la letra con el agente `letrista` o la voz con /analiza-mi-voz.
