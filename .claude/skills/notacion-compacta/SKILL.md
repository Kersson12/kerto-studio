---
name: notacion-compacta
description: Notación compacta de Kerto para notas, acordes, silencios, secuencias por compás y patrones de batería (C4:1/4:v90, C4+E4+G4:1/2, R:1/8, x...x...). Úsala siempre que leas, escribas o propongas notas, melodías, acordes, bajos o ritmos en este proyecto, o cuando toques kerto/notacion.py.
---

# Notación compacta

En Kerto toda nota se escribe así: nunca listas, arrays ni JSON de notas. Antes de entregar una secuencia, valídala:

```bash
uv run kerto notacion "C4:1/2 E4:1/2 | G4:1"   # OK · 3 eventos · 2 compases de 4/4 · rango C4–G4
```

## Eventos: `TONO[:DURACIÓN][:vVELOCIDAD]`

| Ejemplo | Significa |
| --- | --- |
| `C4:1/4:v90` | Do central, negra, velocidad 90 |
| `F#3:1/8` | Fa sostenido 3, corchea, velocidad 100 (por defecto) |
| `Bb2` | Si bemol 2, negra (duración por defecto 1/4) |
| `C4+E4+G4:1/2:v80` | Acorde de Do mayor, blanca |
| `R:1/8` | Silencio de corchea (sin velocidad) |

- **Tono**: letra A–G en mayúscula, `#` o `b` opcional y octava de -1 a 9. `C4` = MIDI 60; `A4` = 440 Hz.
- **Duración**: fracción de redonda. `1` redonda, `1/2` blanca, `1/4` negra, `1/8` corchea, `1/16` semicorchea, `3/8` negra con puntillo, `1/12` corchea de tresillo.
- **Velocidad**: `v1` a `v127`, la fuerza de la nota.

## Secuencias

Eventos separados por espacios. `|` separa compases y cada compás debe sumar justo su duración (4/4 por defecto):
`A3+C4+E4:1/2 R:1/4 E4:1/8 G4:1/8 | F3+A3+C4:1`

## Patrones de batería

Un carácter por paso, semicorchea por defecto: `X` acento, `x` golpe, `o` golpe suave, `.` silencio. Los espacios y `|` solo ayudan a leer: `x... x... x... x...` son cuatro golpes en un compás de 4/4.

Reglas finas, errores típicos y la API de Python: [referencia.md](referencia.md).
