"""Alturas y escalas bien escritas: La menor es A B C D E F G y Fa mayor lleva Bb."""

import re

LETRAS = "CDEFGAB"
SEMITONOS_LETRA = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Escalas de siete notas: semitonos desde la tónica.
ESCALAS: dict[str, tuple[int, ...]] = {
    "mayor": (0, 2, 4, 5, 7, 9, 11),
    "menor": (0, 2, 3, 5, 7, 8, 10),
    "menor_armonica": (0, 2, 3, 5, 7, 8, 11),
    "dorica": (0, 2, 3, 5, 7, 9, 10),
    "frigia": (0, 1, 3, 5, 7, 8, 10),
}
# Pentatónicas: escala madre y los grados (desde 0) que se quedan.
PENTATONICAS: dict[str, tuple[str, tuple[int, ...]]] = {
    "pentatonica_mayor": ("mayor", (0, 1, 2, 4, 5)),
    "pentatonica_menor": ("menor", (0, 2, 3, 4, 6)),
}
MAX_ALTERACIONES = 2

_RE_NOMBRE = re.compile(r"([A-G])(#{1,2}|b{1,2})?")


class ErrorTeoria(ValueError):
    """Nota, escala, acorde o tonalidad que no existe o no se puede escribir."""


def desplazamiento(nombre: str) -> int:
    """Semitonos desde el Do de la misma octava: 'C' -> 0, 'Cb' -> -1, 'B#' -> 12."""
    coincidencia = _RE_NOMBRE.fullmatch(nombre)
    if coincidencia is None:
        raise ErrorTeoria(f"nota inválida {nombre!r}: usa A-G con # o b, como F# o Bb")
    letra, alteracion = coincidencia.group(1), coincidencia.group(2) or ""
    signo = 1 if alteracion.startswith("#") else -1
    return SEMITONOS_LETRA[letra] + signo * len(alteracion)


def clase_de_altura(nombre: str) -> int:
    """La nota sin octava, de 0 a 11: 'C' -> 0, 'Bb' -> 10, 'B#' -> 0."""
    return desplazamiento(nombre) % 12


def deletrear(letra: str, clase: int) -> str:
    """Escribe una clase de altura con la letra pedida: ('F', 6) -> 'F#'."""
    diferencia = (clase - SEMITONOS_LETRA[letra] + 6) % 12 - 6
    if abs(diferencia) > MAX_ALTERACIONES:
        raise ErrorTeoria(f"la clase {clase} no se puede escribir con la letra {letra}")
    return letra + ("#" * diferencia if diferencia > 0 else "b" * -diferencia)


def escala(tonica: str, modo: str = "menor") -> tuple[str, ...]:
    """Notas de la escala, una por letra: escala('F', 'mayor') -> F G A Bb C D E."""
    if modo in PENTATONICAS:
        madre, grados = PENTATONICAS[modo]
        completa = escala(tonica, madre)
        return tuple(completa[grado] for grado in grados)
    if modo not in ESCALAS:
        modos = ", ".join([*ESCALAS, *PENTATONICAS])
        raise ErrorTeoria(f"escala desconocida {modo!r}: usa {modos}")
    base = clase_de_altura(tonica)
    inicio = LETRAS.index(tonica[0])
    return tuple(
        deletrear(LETRAS[(inicio + paso) % 7], (base + intervalo) % 12)
        for paso, intervalo in enumerate(ESCALAS[modo])
    )
