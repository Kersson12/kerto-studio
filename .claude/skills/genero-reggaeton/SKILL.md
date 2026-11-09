---
name: genero-reggaeton
description: "El pack de reggaetón de Kerto: dembow, tempo de 88 a 100 BPM, variaciones (clasico, movido, oscuro), capas de acordes (pad, teclado, arpegio), partes de la canción, sonidos y estilo de letra. Úsala siempre que el usuario pida un perreo, dembow o reggaetón, quiera cambiar cómo suena un beat de reggaetón (más movido, más oscuro, más melodía, coro más fuerte), escriba letra para reggaetón o toque generos/reggaeton/pack.yaml o sonidos.yaml."
---

# Reggaetón

Perreo, dembow y reggaetón son lo mismo para el motor: `genero: reggaeton`. Por defecto va en La menor (`Am`) a 95 BPM.

## Lo que lo define

- **Dembow**: el bombo pega en cada tiempo y la caja hace `...x ..x. ...x ..x.`. Todas las variaciones lo mantienen: sin él deja de ser reggaetón.
- **808**: el bajo toca la raíz de cada acorde y se agacha cuando pega el bombo, para que no choquen.
- Tonalidad menor y progresiones de cuatro acordes que se repiten.

## Variaciones

| Nombre | Acordes en Am | Cómo se siente | Cuándo |
| --- | --- | --- | --- |
| clasico | Am F C G | Directo, para bailar | perreo de siempre |
| movido | Am G F G | Hi-hat rápido y conga que empuja | más energía, más baile |
| oscuro | Am F Dm E | Más espacio y 808 largo | perreo oscuro de discoteca |

Capas de acordes (`acordes` en `crear_beat`) para que el beat tenga melodía y una referencia para cantar afinado:
- `teclado`: piano eléctrico al ritmo del dembow. Es la que eligió el usuario en Luna Negra.
- `pad`: acordes largos de fondo.
- `arpegio`: las notas del acorde saltando.

## Partes de la canción

Orden por defecto: `intro 4, verso 8, precoro 4, coro 8, verso 8, coro 8, puente 4, outro 4` (48 compases, unos 2 minutos).

- **intro y outro**: sin bombo, caja ni 808, para entrar y salir suave.
- **precoro**: `VI VII` sin bombo, para crear tensión.
- **coro**: `i VI III VII` con pad y arpegio encima: lo más fuerte.
- **puente**: `iv v` sin bombo ni caja: baja la energía antes del final.
- Antes de cada coro hay un corte (todo se calla en el último tiempo); las demás partes cierran con un relleno de caja y conga.

El orden de cada canción se cambia en `secciones:` de su `cancion.yaml`; el del pack, en `estructura:`.

## Sonido

`generos/reggaeton/sonidos.yaml`: Surge XT para bombo, caja, 808 (Sub Square, se oye hasta en el teléfono), pad (MKS-70 Warm Pad), teclado (EP 1) y arpegio. La reverb de sala va apagada: con sala el coro sonaba "a concierto" y no pegaba.

## Letra

- Frases cortas, una por compás, de 7 a 13 sílabas.
- Un gancho de pocas palabras que se repite en el coro; rima marcada al final de las líneas.
- Temas de noche, baile, deseo o desamor, contados con imágenes concretas.
- Letras originales: nada de copiar versos ni imitar a un artista concreto. Las canciones de referencia se analizan, nunca se copian.

## Cambiar el pack

Los patrones se escriben con un carácter por semicorchea y cuatro por tiempo (`X` fuerte, `x` normal, `o` suave, `.` silencio; skill `notacion-compacta`). Después de editar `pack.yaml` o `sonidos.yaml`, vuelve a generar con `crear_beat` o `renderizar_cancion` para escucharlo. Los cambios de sonido son decisión del usuario: propón dos o tres opciones.
