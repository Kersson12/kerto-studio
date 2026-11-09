---
name: mezcla-y-master
description: "Mezcla y master en Kerto: cadena vocal (filtro de graves, ecualización, compresión, de-esser, autotune, reverb o delay), volumen en LUFS, picos, choque entre bombo y 808, mono y master por referencia, con cada número traducido a una frase simple. Úsala siempre que el usuario quiera que su voz o su canción suene más profesional, más fuerte o más clara, pregunte por niveles, LUFS, compresión o reverb, diga que algo suena tapado, saturado o 'a concierto', o toque niveles o efectos en un sonidos.yaml."
---

# Mezcla y master

Tono: técnico y directo, pero cada número va con su traducción ("el 808 tapa al bombo en 60 Hz: lo bajo 3 dB solo en esa zona"). El sonido final lo aprueban los oídos del usuario.

## Qué existe hoy y qué llega en la Fase 5

- **Hoy**: cada render pasa por un master simple del motor. Nivela cada pista (`nivel` en `generos/<genero>/sonidos.yaml`), agacha el 808 cuando suena el bombo (`agacha`) y deja la mezcla en -12 dBFS RMS con un limitador que no pasa de -1 dBFS.
- **Fase 5**: la herramienta `mezclar` con pedalboard (cadena vocal), pyloudnorm (mix doctor en LUFS) y matchering (master por referencia). Si no existe todavía, dilo y no inventes medidas.
- Nunca se toca el audio original del usuario: el motor siempre escribe archivos nuevos.

## Cadena vocal, en este orden

| Paso | Qué hace | Punto de partida |
| --- | --- | --- |
| Filtro de graves | Quita el retumbe del micrófono y del cuarto | cortar bajo 80 a 100 Hz |
| Ecualización | Quita lo que suena a caja y suma claridad | bajar algo en 250 a 400 Hz; subir un poco en 3 a 5 kHz |
| Compresión | Empareja lo fuerte y lo suave | ratio 3:1 a 4:1, que baje de 3 a 6 dB en las partes fuertes |
| De-esser | Suaviza las eses que pican | entre 5 y 8 kHz |
| Autotune | El que recomendó el Coach, en la escala de la canción | suave: retune lento; marcado: rápido |
| Reverb o delay | Da espacio a la voz | poco: con mucha reverb suena lejos o "a concierto" |

El orden importa: limpiar antes de comprimir evita que el compresor reaccione al retumbe, y el autotune funciona mejor con una voz ya limpia.

## Niveles

- **LUFS** mide el volumen como lo oye la gente. Spotify y YouTube bajan todo a unos -14 LUFS: pasarse de fuerte no suena más alto, solo más aplastado.
- **Pico**: nunca arriba de -1 dBTP, o se satura al convertirlo a MP3.
- **Rango**: un coro debe sonar más fuerte que el verso; si todo está igual de fuerte, nada destaca.

## Choques típicos

- **Bombo y 808** pelean en 40 a 100 Hz. Arreglo: que el 808 se agache cuando pega el bombo (`agacha: {con: bombo, db: 8, ms: 120}`) o bajar el 808 en la zona del bombo.
- **Voz y acordes** pelean en 1 a 4 kHz. Arreglo: bajar un poco los acordes en esa zona, no subir la voz.
- **Mono**: muchos teléfonos suenan en mono. El bajo y la voz van al centro; si algo desaparece en mono, tiene un problema de fase.

## Lo que ya se aprendió en Kerto

- Con reverb de sala el coro del reggaetón sonaba "a concierto" y al usuario no le gustó: en reggaetón la `sala` va en 0.
- Un 808 de seno puro no se oye en parlantes de laptop o teléfono: se usa uno con armónicos (Sub Square).

## Informe final

Pocas líneas: qué cambió, cuánto y por qué, y qué escuchar para comprobarlo. Plugins gratis para cada paso: skill `plugins-gratis`.
