# Notación compacta: referencia

## Reglas finas

- Duración y velocidad son opcionales y van en cualquier orden: `C4`, `C4:1/8`, `C4:v90`, `C4:1/8:v90`. Al escribir, el motor siempre pone la duración y omite `v100`.
- Las notas de un acorde se ordenan de grave a agudo y no se repiten. Un silencio (`R`) no va dentro de un acorde ni lleva velocidad.
- Al escribir se usan sostenidos (`C#4`); `Db4` se lee igual (MIDI 61).
- Compases: `4/4` dura 1 redonda; `3/4` y `6/8` duran 3/4. Sin `|` no se valida nada. Con `|`, ninguna nota cruza la barra y no quedan compases incompletos.
- Velocidades de los patrones: `X` = 120, `x` = 100, `o` = 60.

## Errores típicos

| Mal | Bien | Por qué |
| --- | --- | --- |
| `c4`, `H4` | `C4`, `B4` | Letras A–G en mayúscula |
| `C4:0.25` | `C4:1/4` | La duración va en fracción, no en decimal |
| `C4:1/4:v0` | `R:1/4` | `v0` no existe: para no sonar, usa un silencio |
| `R:1/4:v90` | `R:1/4` | El silencio no lleva velocidad |
| `C4:1 \| E4:1/2` | `C4:1 \| E4:1/2 R:1/2` | Cada compás debe completarse |

## API de Python (`kerto/notacion.py`)

- `parse_evento(texto) -> Evento` y `formatear_evento(evento) -> str`
- `parse_secuencia(texto, compas="4/4") -> list[Evento]` y `formatear_secuencia(eventos, compas=None) -> str`
- `parse_patron(texto, paso="1/16") -> Patron`, con golpes que tienen `inicio` (en redondas) y `velocidad`
- `nota_a_midi("C4") -> 60` y `midi_a_nota(61, bemoles=True) -> "Db4"`
- `duracion_compas("6/8") -> Fraction(3, 4)` y `resumir_secuencia(eventos) -> str`
- `Evento(tonos, duracion, velocidad)` es inmutable y su duración es una `Fraction` en redondas. Todo error es `ErrorNotacion`, subclase de `ValueError`.
