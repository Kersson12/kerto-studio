"""Motor de patrones: arma el beat compás a compás a partir del pack del género.

Los tiempos van en redondas desde el principio (un compás de 4/4 dura 1).
La humanización mueve cada golpe en pasos de 1/1920 de redonda, la misma
resolución del MIDI a 480 pulsos por negra, para que todo siga siendo exacto.
"""

import itertools
import math
import random
from collections import defaultdict
from dataclasses import dataclass, replace
from fractions import Fraction

from kerto.notacion import Golpe, Patron, duracion_compas
from kerto.ritmos.pack import Instrumento, Pack, Variacion
from kerto.teoria.acordes import Acorde, parse_tonalidad
from kerto.teoria.acordes import progresion as _progresion
from kerto.teoria.escalas import ErrorTeoria, clase_de_altura

RESOLUCION = 1920
BPM_MINIMO = 40
BPM_MAXIMO = 220
COMPASES_POR_DEFECTO = 8


class ErrorBeat(ValueError):
    """Argumentos con los que no se puede armar un beat."""


@dataclass(frozen=True)
class Nota:
    """Una nota del beat: cuándo empieza y cuánto dura, en redondas."""

    inicio: Fraction
    duracion: Fraction
    tono: int
    velocidad: int


@dataclass(frozen=True)
class Pista:
    """Las notas de un instrumento. La batería va al canal 10 del MIDI."""

    nombre: str
    bateria: bool
    programa: int | None
    notas: tuple[Nota, ...]


@dataclass(frozen=True)
class Beat:
    """El beat completo de una variación, listo para exportar."""

    genero: str
    variacion: str
    bpm: int
    tonalidad: str
    compas: str
    compases: int
    acordes: tuple[str, ...]
    pistas: tuple[Pista, ...]

    @property
    def duracion(self) -> Fraction:
        return self.compases * duracion_compas(self.compas)


def estructura(compases: int, frase: int) -> tuple[str, ...]:
    """Tipo de cada compás: relleno al cerrar cada frase y corte en el último.

    estructura(8, 4) -> base base base relleno base base base corte.
    Si el beat es más corto que una frase, todo es base.
    """
    if compases < 1 or frase < 1:
        raise ErrorBeat("los compases y la frase deben ser mayores que 0")
    tipos = []
    for numero in range(1, compases + 1):
        if numero == compases and compases >= frase:
            tipos.append("corte")
        elif numero % frase == 0 and numero < compases:
            tipos.append("relleno")
        else:
            tipos.append("base")
    return tuple(tipos)


def crear_beat(
    pack: Pack,
    variacion: int | str = 0,
    *,
    bpm: int | None = None,
    tonalidad: str | None = None,
    compases: int = COMPASES_POR_DEFECTO,
    progresion: str | None = None,
    semilla: int = 0,
    humanizar: bool = True,
) -> Beat:
    """Arma el beat de una variación del pack (por posición desde 0 o por nombre)."""
    elegida = _elegir_variacion(pack, variacion)
    tempo = pack.bpm_defecto if bpm is None else bpm
    if not BPM_MINIMO <= tempo <= BPM_MAXIMO:
        raise ErrorBeat(
            f"bpm {tempo} fuera de rango: usa de {BPM_MINIMO} a {BPM_MAXIMO}"
        )
    tipos = estructura(compases, pack.frase)
    clave, acordes = _acordes(
        tonalidad or pack.tonalidad, progresion or elegida.progresion, compases
    )
    pistas = []
    for instrumento in pack.instrumentos.values():
        notas = _notas(pack, instrumento, elegida, tipos, acordes)
        if humanizar:
            azar = random.Random(f"{semilla}:{elegida.nombre}:{instrumento.nombre}")
            notas = _humanizar(
                notas, azar, pack.humanizar_tiempo, pack.humanizar_fuerza
            )
        pistas.append(
            Pista(
                instrumento.nombre,
                instrumento.bateria,
                instrumento.programa,
                _sin_solapes(notas),
            )
        )
    return Beat(
        genero=pack.nombre,
        variacion=elegida.nombre,
        bpm=tempo,
        tonalidad=clave,
        compas=pack.compas,
        compases=compases,
        acordes=tuple(str(acorde) for acorde in acordes),
        pistas=tuple(pistas),
    )


def _elegir_variacion(pack: Pack, variacion: int | str) -> Variacion:
    nombres = [v.nombre for v in pack.variaciones]
    if isinstance(variacion, str):
        if variacion not in nombres:
            raise ErrorBeat(
                f"variación desconocida {variacion!r}: usa {', '.join(nombres)}"
            )
        return pack.variaciones[nombres.index(variacion)]
    if not 0 <= variacion < len(nombres):
        raise ErrorBeat(
            f"el pack {pack.nombre!r} tiene {len(nombres)} variaciones;"
            f" la {variacion + 1} no existe"
        )
    return pack.variaciones[variacion]


def _acordes(
    tonalidad: str, grados: str, compases: int
) -> tuple[str, tuple[Acorde, ...]]:
    """Un acorde por compás, repitiendo la progresión."""
    try:
        clave = parse_tonalidad(tonalidad)
        ciclo = _progresion(clave, grados)
    except ErrorTeoria as error:
        raise ErrorBeat(str(error)) from error
    if not ciclo:
        raise ErrorBeat("la progresión está vacía: usa grados como i VI III VII")
    return str(clave), tuple(ciclo[indice % len(ciclo)] for indice in range(compases))


def _golpes_del_compas(patron: Patron, indice: int, largo: Fraction) -> list[Golpe]:
    """Los golpes que tocan en el compás `indice` si el patrón dura varios compases."""
    compases = int(patron.duracion / largo)
    desde = (indice % compases) * largo
    return [
        Golpe(golpe.inicio - desde, golpe.velocidad)
        for golpe in patron.golpes
        if desde <= golpe.inicio < desde + largo
    ]


def _notas(
    pack: Pack,
    instrumento: Instrumento,
    variacion: Variacion,
    tipos: tuple[str, ...],
    acordes: tuple[Acorde, ...],
) -> list[Nota]:
    largo = pack.largo_compas
    golpes: list[tuple[Fraction, int, int]] = []
    for indice, tipo in enumerate(tipos):
        cambio = pack.transiciones.get(tipo, {}).get(instrumento.nombre)
        del_compas = (
            list(cambio.golpes)
            if cambio
            else _golpes_del_compas(
                variacion.patrones[instrumento.nombre], indice, largo
            )
        )
        golpes.extend(
            (indice * largo + golpe.inicio, golpe.velocidad, indice)
            for golpe in del_compas
        )
    if instrumento.bateria:
        return [
            Nota(inicio, pack.paso, instrumento.nota, velocidad)
            for inicio, velocidad, _ in golpes
        ]
    fin = len(tipos) * largo
    inicios = [inicio for inicio, _, _ in golpes] + [fin]
    return [
        Nota(
            inicio,
            min(inicios[k + 1] - inicio, instrumento.largo),
            _tono_grave(acordes[indice], instrumento.grave),
            velocidad,
        )
        for k, (inicio, velocidad, indice) in enumerate(golpes)
    ]


def _tono_grave(acorde: Acorde, grave: int | None) -> int:
    """La raíz del acorde en la primera octava desde la nota más grave del instrumento."""
    base = 0 if grave is None else grave
    return base + (clase_de_altura(acorde.raiz) - base) % 12


def _humanizar(
    notas: list[Nota], azar: random.Random, tiempo: Fraction, fuerza: int
) -> list[Nota]:
    """Mueve cada golpe un poquito en tiempo y en fuerza, siempre igual con la misma semilla."""
    maximo = math.floor(tiempo * RESOLUCION)
    humanas = []
    for nota in notas:
        corrimiento = Fraction(azar.randint(-maximo, maximo), RESOLUCION)
        velocidad = nota.velocidad + azar.randint(-fuerza, fuerza)
        humanas.append(
            replace(
                nota,
                inicio=max(Fraction(0), nota.inicio + corrimiento),
                velocidad=min(127, max(1, velocidad)),
            )
        )
    return humanas


def _sin_solapes(notas: list[Nota]) -> tuple[Nota, ...]:
    """Recorta cada nota para que no pise a la siguiente del mismo tono."""
    por_tono: dict[int, list[int]] = defaultdict(list)
    for posicion, nota in enumerate(notas):
        por_tono[nota.tono].append(posicion)
    recortadas = list(notas)
    for posiciones in por_tono.values():
        orden = sorted(posiciones, key=lambda p: notas[p].inicio)
        for actual, siguiente in itertools.pairwise(orden):
            hueco = notas[siguiente].inicio - notas[actual].inicio
            if notas[actual].duracion > hueco:
                recortadas[actual] = replace(notas[actual], duracion=hueco)
    return tuple(nota for nota in recortadas if nota.duracion > 0)
