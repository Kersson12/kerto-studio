---
name: teoria-musical
description: "Teoría musical de Kerto explicada en simple: tonalidades (La menor = Am), escalas, acordes, grados como i VI III VII, transponer y qué acordes o notas pegan en una melodía. Úsala siempre que haya que elegir o cambiar la tonalidad, el tono o los acordes de un beat o canción, explicar por qué una progresión suena oscura, alegre o con tensión, traducir nombres de notas (Do, Re, La menor) al cifrado del motor, o editar `progresion:` en un pack.yaml, aunque el usuario no diga 'teoría'."
---

# Teoría musical en Kerto

El usuario no sabe de música: cada término va con su traducción en una frase. La teoría la calcula el motor (`kerto/teoria/`); tú decides y explicas.

## Nombres de las notas

| Español | Do | Re | Mi | Fa | Sol | La | Si |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Motor | C | D | E | F | G | A | B |

- `#` es sostenido (medio tono arriba) y `b` es bemol (medio tono abajo): `F#` = Fa sostenido, `Bb` = Si bemol.
- Tonalidad: la letra sola es mayor y con `m` es menor. `Am` = La menor, `C` = Do mayor, `G#m` = Sol sostenido menor.
- Las notas sueltas llevan octava: `C4` es el Do del centro del piano. Para escribir notas usa la skill `notacion-compacta`.

## Tonalidad: mayor o menor

- **Menor** suena oscura, nostálgica o sensual: es la base del reggaetón y del trap (los packs usan Am y Cm).
- **Mayor** suena alegre y luminosa.
- Cambiar de tonalidad no cambia el ritmo ni la canción: la sube o la baja entera, como subir o bajar el tono de voz.

## Grados: así escribe acordes el pack

Una progresión se escribe con números romanos relativos a la tonalidad, para que funcione en cualquier tono. **Minúscula = acorde menor, mayúscula = mayor**; `°` es disminuido.

En una tonalidad menor, los acordes de la escala son: `i ii° III iv v VI VII`. En La menor: Am, B°, C, Dm, Em, F, G. Un `V` en mayúscula (E en La menor) toma prestada la nota de la escala menor armónica y crea mucha tensión antes de volver al `i`.

| Progresión | En Am | Cómo se siente | Dónde está |
| --- | --- | --- | --- |
| `i VI III VII` | Am F C G | Épica, la de siempre: pega en coros | reggaetón clasico y coro, trap suave |
| `i VII VI VII` | Am G F G | Movida, va y vuelve | reggaetón movido, trap melodico |
| `i VI iv V` | Am F Dm E | Oscura, con tensión al final | reggaetón oscuro |
| `i iv VI VII` | Am Dm F G | Nocturna, de espacio | trap nocturno |
| `VI VII` | F G | Sube la tensión: pide que llegue el coro | reggaetón precoro |
| `iv v` | Dm Em | Baja la energía | reggaetón puente |

Para ver los acordes reales de una canción no los calcules: `estado_cancion` o `listar_generos` ya los traen, y `crear_beat` los devuelve en su resumen. En Python: `kerto.teoria.acordes.progresion("Am", "i VI III VII")`.

## Transponer a la voz

- Un semitono es el paso más chico (de A a A#). Bajar de Am a G#m es bajar un semitono: todo suena igual, un poco más grave.
- La tonalidad correcta es la que cae en la zona cómoda de la voz del usuario (`voz.comodo` y `voz.tonalidades` en `cancion.yaml`, salen de `analizar_voz`). Si la melodía le queda aguda, baja uno o dos semitonos; si le queda grave, súbela.
- Para cambiarla usa `transponer`: reescribe `tonalidad:` y vuelve a renderizar. Nunca más de 3 o 4 semitonos sin probar: el beat cambia de color.

## Qué notas pegan en la melodía

- Las notas del acorde que suena en ese momento son las más seguras: el motor pone ahí las sílabas acentuadas y la última de cada frase, por eso la melodía "aterriza" bien.
- Las demás notas de la escala sirven de paso entre esas.
- Una nota fuera de la escala suena a error salvo que sea muy corta.

## Ritmo y tiempo, en simple

- BPM es la velocidad: reggaetón de 88 a 100, trap de 130 a 160 (se siente a la mitad).
- Un compás son 4 tiempos (4/4); 4 compases a 95 BPM duran unos 10 segundos.
- Las partes de la canción se miden en compases: `coro 8` son 8 compases.

## Cómo explicarlo

Usa comparaciones del día a día ("el V es como una pregunta que el i responde") y una sola idea por frase. Si el usuario pide un cambio de "sentimiento" (más oscuro, más alegre, más tenso), tradúcelo a una progresión de la tabla y explica en una línea por qué.
