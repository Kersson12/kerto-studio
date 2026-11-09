---
name: genero-trap
description: "El pack de trap de Kerto: medio tiempo a 130-160 BPM, redobles de hi-hat, 808 largo, variaciones suaves y melódicas (suave, melodico, nocturno) y duras (oscuro, rebote), capas (piano, campana, pad), partes de la canción y estilo de letra. Úsala siempre que el usuario pida trap, trap melódico o un beat lento y emotivo con 808, quiera cambiar cómo suena un beat de trap, escriba letra para trap o toque generos/trap/pack.yaml o sonidos.yaml."
---

# Trap

`genero: trap`. Por defecto va en Do menor (`Cm`) a 140 BPM.

## Lo que lo define

- **Medio tiempo**: a 140 BPM se siente como 70, porque la caja (aquí un clap) cae solo en el tercer tiempo.
- **Hi-hat** con redobles rápidos al final de cada compás.
- **808 largo**: se sostiene hasta medio compás y hace de bajo y de bombo largo a la vez; se agacha cuando pega el bombo.

## Variaciones

| Nombre | Acordes en Cm | Cómo se siente |
| --- | --- | --- |
| suave | Cm Ab Eb Bb | Suave y emotivo, la melodía manda |
| melodico | Cm Bb Ab Bb | Rebote suave, para cantar encima |
| nocturno | Cm Fm Ab Bb | De noche, con mucho espacio |
| oscuro | Cm Ab Bb Cm | Duro, el 808 manda |
| rebote | Cm Fm Bb Ab | Bombo sincopado y hi-hat que se acelera |

Las tres primeras son las suaves y melódicas, las que pidió el usuario: golpes suaves y casi sin redobles. Si pide trap "más suave" o "para cantar", empieza por ahí. Las dos últimas son las duras.

Capas de acordes (`acordes` en `crear_beat`): `piano` (acordes largos, Soft Suitcase), `campana` (notas que suenan como campanitas) y `pad` (fondo largo).

## Partes de la canción

Orden por defecto: `intro 4, coro 8, verso 16, coro 8, verso 16, coro 8, outro 4`.

- El coro llega pronto: en trap el gancho suena antes del primer verso.
- Los versos son largos (16 compases) y el coro suma la campana encima.
- Intro y outro van sin bombo, caja ni 808; el puente, sin bombo.

## Sonido

`generos/trap/sonidos.yaml`: bombo y clap con las voces internas (Faust), que son más suaves; 808 Sub Square de Surge XT; piano Soft Suitcase, campana Bell 1 y pad MKS-70 Warm Pad.

## Letra y voz

- Más sílabas por compás que en reggaetón: el flow va más pegado al hi-hat. Aun así, de 7 a 13 sílabas por línea suena mejor con la melodía guía.
- Coro melódico y repetido; versos que cuentan la historia.
- El autotune marcado es parte del sonido del género, pero solo si el usuario lo quiere (estilo `marcado` en `cancion.yaml`).
- Letras originales: nada de copiar versos ni imitar a un artista concreto.

## Cambiar el pack

Cuidado: en trap cada carácter de un patrón es una fusa (1/32), así que un tiempo son 8 caracteres y un compás 32. Después de editar `pack.yaml` o `sonidos.yaml`, vuelve a generar con `crear_beat` o `renderizar_cancion`. Los cambios de sonido los decide el usuario.
