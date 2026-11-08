"""Notación compacta de Kerto: notas, acordes, silencios, secuencias y patrones.

Evento    TONO[:DURACIÓN][:vVELOCIDAD]   C4:1/4:v90 · C4+E4+G4:1/2 · R:1/8
Secuencia eventos separados por espacios; `|` separa compases
Patrón    un carácter por paso: X acento, x golpe, o suave, . silencio

Las duraciones son fracciones de redonda (1/4 = negra). C4 es el MIDI 60.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction

DURACION_POR_DEFECTO = Fraction(1, 4)
VELOCIDAD_POR_DEFECTO = 100
SILENCIO = "R"
VELOCIDADES_PATRON = {"X": 120, "x": 100, "o": 60}
PASO_POR_DEFECTO = "1/16"

_NOTAS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_ALTERACIONES = {"": 0, "#": 1, "b": -1}
_SOSTENIDOS = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_BEMOLES = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
_RE_NOTA = re.compile(r"([A-G])([#b]?)(-1|[0-9])")
_RE_FRACCION = re.compile(r"[1-9][0-9]*(?:/[1-9][0-9]*)?")
_RE_VELOCIDAD = re.compile(r"v([0-9]{1,3})")


class ErrorNotacion(ValueError):
    """Texto o valor que no cumple la notación compacta."""


# --- Notas y números MIDI ---


def nota_a_midi(nombre: str) -> int:
    """'C4' -> 60. Acepta # y b; octavas de -1 a 9."""
    coincidencia = _RE_NOTA.fullmatch(nombre)
    if coincidencia is None:
        raise ErrorNotacion(f"nota inválida {nombre!r}: usa C4, F#3 o Bb2")
    letra, alteracion, octava = coincidencia.groups()
    numero = (int(octava) + 1) * 12 + _NOTAS[letra] + _ALTERACIONES[alteracion]
    if not 0 <= numero <= 127:
        raise ErrorNotacion(f"nota {nombre!r} fuera del rango MIDI (C-1 a G9)")
    return numero


def midi_a_nota(numero: int, bemoles: bool = False) -> str:
    """60 -> 'C4'. Con bemoles=True, 61 -> 'Db4' en vez de 'C#4'."""
    if not 0 <= numero <= 127:
        raise ErrorNotacion(f"número MIDI {numero} fuera de rango (0 a 127)")
    octava, clase = divmod(numero, 12)
    nombres = _BEMOLES if bemoles else _SOSTENIDOS
    return f"{nombres[clase]}{octava - 1}"


# --- Eventos: notas, acordes y silencios ---


@dataclass(frozen=True)
class Evento:
    """Nota (un tono), acorde (varios) o silencio (ninguno).

    La duración va en redondas; los tonos se guardan ordenados de grave a agudo.
    """

    tonos: tuple[int, ...]
    duracion: Fraction = DURACION_POR_DEFECTO
    velocidad: int = VELOCIDAD_POR_DEFECTO

    def __post_init__(self) -> None:
        tonos = tuple(sorted(self.tonos))
        if len(set(tonos)) != len(tonos):
            raise ErrorNotacion(f"tono repetido en el acorde {tonos}")
        for tono in tonos:
            if not 0 <= tono <= 127:
                raise ErrorNotacion(f"tono {tono} fuera de rango (0 a 127)")
        duracion = Fraction(self.duracion)
        if duracion <= 0:
            raise ErrorNotacion(f"la duración debe ser positiva, no {duracion}")
        if not 1 <= self.velocidad <= 127:
            raise ErrorNotacion(f"velocidad {self.velocidad} fuera de rango (1 a 127)")
        if not tonos and self.velocidad != VELOCIDAD_POR_DEFECTO:
            raise ErrorNotacion("un silencio no lleva velocidad")
        object.__setattr__(self, "tonos", tonos)
        object.__setattr__(self, "duracion", duracion)

    @property
    def es_silencio(self) -> bool:
        return not self.tonos


def parse_evento(texto: str) -> Evento:
    """'C4+E4+G4:1/2:v80' -> Evento. Duración y velocidad son opcionales."""
    tono_texto, *campos = texto.strip().split(":")
    duracion: Fraction | None = None
    velocidad: int | None = None
    for campo in campos:
        if campo.startswith("v"):
            coincidencia = _RE_VELOCIDAD.fullmatch(campo)
            if coincidencia is None:
                raise ErrorNotacion(
                    f"velocidad inválida {campo!r} en {texto!r}: usa v1 a v127"
                )
            if velocidad is not None:
                raise ErrorNotacion(f"velocidad repetida en {texto!r}")
            velocidad = int(coincidencia.group(1))
        else:
            if _RE_FRACCION.fullmatch(campo) is None:
                raise ErrorNotacion(
                    f"duración inválida {campo!r} en {texto!r}: usa una fracción de redonda, como 1/4"
                )
            if duracion is not None:
                raise ErrorNotacion(f"duración repetida en {texto!r}")
            duracion = Fraction(campo)

    if not tono_texto:
        raise ErrorNotacion(f"evento sin tono: {texto!r}")
    nombres = tono_texto.split("+")
    if SILENCIO in nombres:
        if len(nombres) > 1:
            raise ErrorNotacion(f"un silencio (R) no va dentro de un acorde: {texto!r}")
        if velocidad is not None:
            raise ErrorNotacion(f"un silencio no lleva velocidad: {texto!r}")
        tonos: tuple[int, ...] = ()
    else:
        tonos = tuple(nota_a_midi(nombre) for nombre in nombres)

    return Evento(
        tonos,
        DURACION_POR_DEFECTO if duracion is None else duracion,
        VELOCIDAD_POR_DEFECTO if velocidad is None else velocidad,
    )


def formatear_evento(evento: Evento) -> str:
    """Evento -> texto. Siempre escribe la duración; la velocidad solo si no es 100."""
    if evento.es_silencio:
        return f"{SILENCIO}:{evento.duracion}"
    texto = "+".join(midi_a_nota(tono) for tono in evento.tonos) + f":{evento.duracion}"
    if evento.velocidad != VELOCIDAD_POR_DEFECTO:
        texto += f":v{evento.velocidad}"
    return texto


# --- Compases y secuencias ---


def duracion_compas(compas: str) -> Fraction:
    """'4/4' -> 1 redonda; '6/8' -> 3/4 de redonda."""
    coincidencia = re.fullmatch(r"([1-9][0-9]*)/([1-9][0-9]*)", compas)
    if coincidencia is None:
        raise ErrorNotacion(f"compás inválido {compas!r}: usa 4/4, 3/4 o 6/8")
    return Fraction(int(coincidencia.group(1)), int(coincidencia.group(2)))


def _duracion_total(eventos: Iterable[Evento]) -> Fraction:
    return sum((evento.duracion for evento in eventos), Fraction(0))


def parse_secuencia(texto: str, compas: str | None = "4/4") -> list[Evento]:
    """Eventos separados por espacios.

    Si el texto usa `|` y hay compás, cada compás debe sumar justo su duración.
    """
    bloques = [[parse_evento(t) for t in bloque.split()] for bloque in texto.split("|")]
    if compas is not None and len(bloques) > 1:
        largo = duracion_compas(compas)
        if not bloques[0]:  # `|` al inicio
            bloques = bloques[1:]
        if bloques and not bloques[-1]:  # `|` al final
            bloques = bloques[:-1]
        for numero, bloque in enumerate(bloques, start=1):
            dura = _duracion_total(bloque)
            if dura != largo:
                raise ErrorNotacion(
                    f"el compás {numero} dura {dura} y en {compas} debe durar {largo}"
                )
    return [evento for bloque in bloques for evento in bloque]


def formatear_secuencia(eventos: Iterable[Evento], compas: str | None = None) -> str:
    """Eventos -> texto. Con compás marca las barras y exige compases completos."""
    if compas is None:
        return " ".join(formatear_evento(evento) for evento in eventos)
    largo = duracion_compas(compas)
    partes: list[str] = []
    posicion = Fraction(0)
    for evento in eventos:
        if posicion > 0 and posicion % largo == 0:
            partes.append("|")
        numero = posicion // largo + 1  # compás donde empieza el evento
        posicion += evento.duracion
        if posicion > numero * largo:
            raise ErrorNotacion(
                f"{formatear_evento(evento)} cruza la barra del compás {numero}"
            )
        partes.append(formatear_evento(evento))
    if posicion % largo != 0:
        raise ErrorNotacion(
            f"la secuencia dura {posicion}: no completa compases de {compas}"
        )
    return " ".join(partes)


def resumir_secuencia(eventos: Sequence[Evento], compas: str = "4/4") -> str:
    """Una línea para Claude: cuántos eventos, cuánto dura y qué rango cubre."""
    partes = [_plural(len(eventos), "evento", "eventos")]
    total = _duracion_total(eventos)
    compases = total / duracion_compas(compas)
    if compases.denominator == 1:
        partes.append(
            f"{_plural(compases.numerator, 'compás', 'compases')} de {compas}"
        )
    else:
        partes.append(f"duración {total}")
    tonos = [tono for evento in eventos for tono in evento.tonos]
    if tonos:
        grave, agudo = midi_a_nota(min(tonos)), midi_a_nota(max(tonos))
        partes.append(f"rango {grave}" if grave == agudo else f"rango {grave}–{agudo}")
    return " · ".join(partes)


def _plural(cantidad: int, singular: str, plural: str) -> str:
    return f"{cantidad} {singular if cantidad == 1 else plural}"


# --- Patrones de batería ---


@dataclass(frozen=True)
class Golpe:
    """Un golpe del patrón: cuándo empieza (en redondas) y con qué fuerza."""

    inicio: Fraction
    velocidad: int


@dataclass(frozen=True)
class Patron:
    """Patrón de un instrumento: sus golpes y la rejilla de pasos que lo mide."""

    golpes: tuple[Golpe, ...]
    pasos: int
    paso: Fraction

    @property
    def duracion(self) -> Fraction:
        return self.pasos * self.paso


def parse_patron(texto: str, paso: str | Fraction = PASO_POR_DEFECTO) -> Patron:
    """'x...x...' -> Patron. Los espacios y `|` solo sirven para leer mejor."""
    limpio = "".join(texto.split()).replace("|", "")
    if not limpio:
        raise ErrorNotacion("patrón vacío")
    invalidos = set(limpio) - set(VELOCIDADES_PATRON) - {"."}
    if invalidos:
        raise ErrorNotacion(
            f"caracteres inválidos {''.join(sorted(invalidos))!r} en el patrón: usa X x o ."
        )
    try:
        largo_paso = Fraction(paso)
    except (ValueError, ZeroDivisionError):
        raise ErrorNotacion(
            f"paso inválido {paso!r}: usa una fracción como 1/16"
        ) from None
    if largo_paso <= 0:
        raise ErrorNotacion(f"el paso debe ser positivo, no {paso!r}")
    golpes = tuple(
        Golpe(indice * largo_paso, VELOCIDADES_PATRON[caracter])
        for indice, caracter in enumerate(limpio)
        if caracter != "."
    )
    return Patron(golpes, len(limpio), largo_paso)
