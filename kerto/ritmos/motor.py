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
from kerto.ritmos.pack import CapaAcordes, Instrumento, Pack, Variacion
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
    secciones: tuple["Marca", ...] = ()  # solo en una canción completa

    @property
    def duracion(self) -> Fraction:
        return self.compases * duracion_compas(self.compas)


@dataclass(frozen=True)
class Marca:
    """Dónde empieza una parte de la canción, en compases desde 0."""

    nombre: str
    compas: int
    compases: int


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
    acordes: str | None = None,
) -> Beat:
    """Arma el beat de una variación del pack (por posición desde 0 o por nombre).

    `acordes` suma una capa de acordes del pack (pad, teclado, arpegio...).
    """
    elegida = _elegir_variacion(pack, variacion)
    tempo = _tempo(pack, bpm)
    tipos = estructura(compases, pack.frase)
    clave, por_compas = _acordes(
        tonalidad or pack.tonalidad, progresion or elegida.progresion, compases
    )
    capa = _elegir_capa(pack, acordes)
    crudas = [
        (i.nombre, i.bateria, i.programa, _notas(pack, i, elegida, tipos, por_compas))
        for i in pack.instrumentos.values()
    ]
    if capa is not None:
        notas_capa = _notas_capa(pack, capa, tipos, por_compas)
        crudas.append((capa.nombre, False, capa.programa, notas_capa))
    return Beat(
        genero=pack.nombre,
        variacion=elegida.nombre,
        bpm=tempo,
        tonalidad=clave,
        compas=pack.compas,
        compases=compases,
        acordes=tuple(str(acorde) for acorde in por_compas),
        pistas=_pistas(crudas, pack, f"{semilla}:{elegida.nombre}", humanizar),
    )


def tipos_de_seccion(
    compases: int, frase: int, corte_al_final: bool
) -> tuple[str, ...]:
    """Relleno al cerrar cada frase; la sección termina en corte o en relleno."""
    tipos = []
    for numero in range(1, compases + 1):
        if numero == compases:
            tipos.append("corte" if corte_al_final else "relleno")
        elif numero % frase == 0:
            tipos.append("relleno")
        else:
            tipos.append("base")
    return tuple(tipos)


def crear_cancion(
    pack: Pack,
    partes: tuple[tuple[str, int], ...] | None = None,
    variacion: int | str = 0,
    *,
    bpm: int | None = None,
    tonalidad: str | None = None,
    semilla: int = 0,
    humanizar: bool = True,
    acordes: str | None = None,
) -> Beat:
    """La canción entera, sección por sección (por defecto, la estructura del pack).

    Cada sección toma el ritmo de la variación, su propia progresión y calla los
    instrumentos que diga el pack. Antes de cada coro y al final hay un corte.
    """
    partes = partes or pack.estructura
    if not partes:
        raise ErrorBeat(f"el pack {pack.nombre!r} no tiene estructura ni secciones")
    elegida = _elegir_variacion(pack, variacion)
    tempo = _tempo(pack, bpm)
    desconocidas = [nombre for nombre, _ in partes if nombre not in pack.secciones]
    if desconocidas:
        raise ErrorBeat(f"secciones desconocidas: {', '.join(desconocidas)}")
    capa = _elegir_capa(pack, acordes)
    instrumentos = list(pack.instrumentos.values())
    crudas: dict[str, list[Nota]] = {i.nombre: [] for i in instrumentos}
    if capa is not None:
        crudas[capa.nombre] = []
    todos: list[Acorde] = []
    marcas: list[Marca] = []
    vistas: dict[str, int] = {}
    clave = ""
    for posicion, (nombre, compases) in enumerate(partes):
        seccion = pack.secciones[nombre]
        siguiente = partes[posicion + 1][0] if posicion + 1 < len(partes) else None
        tipos = tipos_de_seccion(compases, pack.frase, siguiente in (None, "coro"))
        clave, por_compas = _acordes(
            tonalidad or pack.tonalidad,
            seccion.progresion or elegida.progresion,
            compases,
        )
        corrimiento = len(todos) * pack.largo_compas
        for instrumento in instrumentos:
            if instrumento.nombre not in seccion.sin:
                hechas = _notas(pack, instrumento, elegida, tipos, por_compas)
                crudas[instrumento.nombre] += _correr(hechas, corrimiento)
        if capa is not None and seccion.acordes:
            hechas = _notas_capa(pack, capa, tipos, por_compas)
            crudas[capa.nombre] += _correr(hechas, corrimiento)
        vistas[nombre] = vistas.get(nombre, 0) + 1
        etiqueta = nombre if vistas[nombre] == 1 else f"{nombre} {vistas[nombre]}"
        marcas.append(Marca(etiqueta, len(todos), compases))
        todos.extend(por_compas)
    filas = [(i.nombre, i.bateria, i.programa, crudas[i.nombre]) for i in instrumentos]
    if capa is not None:
        filas.append((capa.nombre, False, capa.programa, crudas[capa.nombre]))
    return Beat(
        genero=pack.nombre,
        variacion=elegida.nombre,
        bpm=tempo,
        tonalidad=clave,
        compas=pack.compas,
        compases=len(todos),
        acordes=tuple(str(acorde) for acorde in todos),
        pistas=_pistas(filas, pack, f"{semilla}:{elegida.nombre}", humanizar),
        secciones=tuple(marcas),
    )


def _correr(notas: list[Nota], corrimiento: Fraction) -> list[Nota]:
    return [replace(nota, inicio=nota.inicio + corrimiento) for nota in notas]


def _tempo(pack: Pack, bpm: int | None) -> int:
    tempo = pack.bpm_defecto if bpm is None else bpm
    if not BPM_MINIMO <= tempo <= BPM_MAXIMO:
        raise ErrorBeat(
            f"bpm {tempo} fuera de rango: usa de {BPM_MINIMO} a {BPM_MAXIMO}"
        )
    return tempo


def _pistas(
    crudas: list[tuple[str, bool, int | None, list[Nota]]],
    pack: Pack,
    semilla: str,
    humanizar: bool,
) -> tuple[Pista, ...]:
    """Humaniza cada pista (siempre igual con la misma semilla) y quita solapes."""
    pistas = []
    for nombre, bateria, programa, notas in crudas:
        if humanizar:
            azar = random.Random(f"{semilla}:{nombre}")
            notas = _humanizar(
                notas, azar, pack.humanizar_tiempo, pack.humanizar_fuerza
            )
        pistas.append(Pista(nombre, bateria, programa, _sin_solapes(notas)))
    return tuple(pistas)


def _elegir_capa(pack: Pack, nombre: str | None) -> CapaAcordes | None:
    if nombre is None:
        return None
    if nombre not in pack.acordes:
        disponibles = ", ".join(pack.acordes) or "ninguna"
        raise ErrorBeat(f"capa de acordes desconocida {nombre!r}: usa {disponibles}")
    return pack.acordes[nombre]


def _notas_capa(
    pack: Pack, capa: CapaAcordes, tipos: tuple[str, ...], acordes: tuple[Acorde, ...]
) -> list[Nota]:
    """La progresión con el ritmo de la capa.

    En el corte se calla en el último tiempo, igual que la batería.
    """
    largo = pack.largo_compas
    corte = largo - largo / int(pack.compas.split("/")[0])
    golpes = []
    for indice, tipo in enumerate(tipos):
        for orden, golpe in enumerate(_golpes_del_compas(capa.patron, indice, largo)):
            if tipo == "corte" and golpe.inicio >= corte:
                continue
            golpes.append(
                (indice * largo + golpe.inicio, golpe.velocidad, indice, orden)
            )
    notas = []
    for k, (inicio, velocidad, indice, orden) in enumerate(golpes):
        siguiente = golpes[k + 1][0] if k + 1 < len(golpes) else len(tipos) * largo
        fin = min(siguiente, inicio + capa.largo)
        if tipos[indice] == "corte":
            fin = min(fin, indice * largo + corte)
        tonos = acordes[indice].midi(capa.octava)
        if capa.arpegio:
            ciclo = (*tonos, tonos[0] + 12)
            tonos = (ciclo[orden % len(ciclo)],)
        notas.extend(Nota(inicio, fin - inicio, tono, velocidad) for tono in tonos)
    return notas


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
