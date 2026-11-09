"""Melodía guía: una nota por sílaba de la letra, siempre dentro del rango de la voz.

Cada línea de la letra ocupa un compás y termina en el cuarto tiempo con una nota
larga, del acorde de ese compás, para sostener la vocal. Las sílabas acentuadas
caen en notas del acorde; las demás se mueven paso a paso por la escala. El coro
va más agudo que el verso. Con la misma semilla, siempre sale igual.
"""

import random
from fractions import Fraction

from kerto.letra.letra import lineas_de
from kerto.letra.silabas import Silaba, cantar
from kerto.notacion import duracion_compas, midi_a_nota
from kerto.ritmos.motor import Beat, Nota, Pista
from kerto.teoria.acordes import parse_acorde, parse_tonalidad
from kerto.teoria.escalas import clase_de_altura

PASO = Fraction(1, 16)
NOTAS_MINIMAS = 4  # notas de la escala que necesita el rango
PROGRAMA_GUIA = 53  # Voice Oohs (General MIDI, desde 0)
VELOCIDAD_TONICA = 112
VELOCIDAD = 96
# Qué tan arriba del rango canta cada sección (0 = lo más grave, 1 = lo más agudo).
REGISTRO = {"coro": 0.75, "precoro": 0.6, "verso": 0.4, "puente": 0.35}


class ErrorMelodia(ValueError):
    """Letra o rango con los que no se puede armar la melodía."""


def ritmo_de_linea(silabas: int, pasos: int) -> list[int]:
    """En qué semicorchea empieza cada sílaba: la última cae en el cuarto tiempo.

    Hasta 7 sílabas van en corcheas, hasta 13 en semicorcheas; más, desde el
    principio del compás.
    """
    if silabas > pasos:
        raise ErrorMelodia(
            f"una línea de {silabas} sílabas no cabe en un compás:"
            f" máximo {pasos}; pártela en dos"
        )
    fin = pasos - pasos // 4
    if silabas <= fin // 2 + 1:
        return [fin - 2 * (silabas - 1 - i) for i in range(silabas)]
    if silabas <= fin + 1:
        return [fin - (silabas - 1 - i) for i in range(silabas)]
    return list(range(silabas))


def _cercana(opciones: list[int], objetivo: float) -> int:
    return min(opciones, key=lambda tono: (abs(tono - objetivo), tono))


def _contorno(
    silabas: list[Silaba],
    escala: list[int],
    del_acorde: list[int],
    centro: float,
    anterior: int | None,
    azar: random.Random,
) -> list[int]:
    """Alturas de una línea: empieza cerca de donde quedó la anterior, camina por
    la escala y termina en una nota del acorde cerca del centro de la sección."""
    punto = centro if anterior is None else (anterior + centro) / 2
    inicio = _cercana(del_acorde, punto)
    final = _cercana(del_acorde, centro + azar.choice((-2, 0, 2)))
    if len(silabas) == 1:
        return [final]
    alturas = [inicio]
    indice, meta = escala.index(inicio), escala.index(final)
    for posicion, silaba in enumerate(silabas[1:-1], start=1):
        faltan = len(silabas) - 1 - posicion
        rumbo = (meta > indice) - (meta < indice)
        paso = rumbo if azar.random() < 0.6 else azar.choice((-1, 0, 1))
        if faltan <= abs(meta - indice):
            paso = rumbo
        indice = min(max(indice + paso, 0), len(escala) - 1)
        tono = escala[indice]
        if silaba.tonica:
            tono = _cercana(del_acorde, tono)
            indice = escala.index(tono)
        alturas.append(tono)
    alturas.append(final)
    return alturas


def crear_melodia(
    beat: Beat,
    letra: dict[str, list[str]],
    rango: tuple[int, int],
    semilla: int = 0,
) -> Pista:
    """La pista "melodia" de la canción, con la sílaba de cada nota en `letras`."""
    grave, aguda = rango
    clases = {clase_de_altura(n) for n in parse_tonalidad(beat.tonalidad).escala}
    escala = [tono for tono in range(grave, aguda + 1) if tono % 12 in clases]
    if len(escala) < NOTAS_MINIMAS:
        raise ErrorMelodia(
            f"el rango {midi_a_nota(grave)}–{midi_a_nota(aguda)} es muy chico:"
            f" hacen falta al menos {NOTAS_MINIMAS} notas de la escala"
        )
    largo = duracion_compas(beat.compas)
    pasos = int(largo / PASO)
    notas: list[Nota] = []
    letras: list[str] = []
    for marca in beat.secciones:
        lineas = lineas_de(letra, marca.nombre)
        if not lineas:
            continue
        centro = grave + REGISTRO.get(marca.nombre.split()[0], 0.5) * (aguda - grave)
        azar = random.Random(f"{semilla}:{marca.nombre}")
        anterior = None
        for k in range(marca.compases):
            silabas = cantar(lineas[k % len(lineas)])
            if not silabas:
                continue
            compas = marca.compas + k
            acorde = {
                clase_de_altura(n) for n in parse_acorde(beat.acordes[compas]).notas
            }
            opciones = sorted(
                {t for t in range(grave, aguda + 1) if t % 12 in clases | acorde}
            )
            del_acorde = [t for t in opciones if t % 12 in acorde] or opciones
            alturas = _contorno(silabas, opciones, del_acorde, centro, anterior, azar)
            anterior = alturas[-1]
            posiciones = ritmo_de_linea(len(silabas), pasos)
            inicio = compas * largo
            for i, (posicion, tono, silaba) in enumerate(
                zip(posiciones, alturas, silabas, strict=True)
            ):
                fin = posiciones[i + 1] if i + 1 < len(posiciones) else pasos
                velocidad = VELOCIDAD_TONICA if silaba.tonica else VELOCIDAD
                notas.append(
                    Nota(
                        inicio + posicion * PASO,
                        (fin - posicion) * PASO,
                        tono,
                        velocidad,
                    )
                )
                letras.append(silaba.texto)
    return Pista("melodia", False, PROGRAMA_GUIA, tuple(notas), tuple(letras))
