"""Acordes por cifrado (Am, G7) y por grado dentro de una tonalidad (i VI III VII)."""

import re
from dataclasses import dataclass

from kerto.teoria.escalas import (
    LETRAS,
    ErrorTeoria,
    clase_de_altura,
    deletrear,
    desplazamiento,
)
from kerto.teoria.escalas import escala as _escala

# Sufijo del cifrado -> semitonos desde la raíz.
CALIDADES: dict[str, tuple[int, ...]] = {
    "": (0, 4, 7),
    "m": (0, 3, 7),
    "dim": (0, 3, 6),
    "aug": (0, 4, 8),
    "7": (0, 4, 7, 10),
    "m7": (0, 3, 7, 10),
    "maj7": (0, 4, 7, 11),
}
_TRIADAS = {
    intervalos: sufijo
    for sufijo, intervalos in CALIDADES.items()
    if len(intervalos) == 3
}
_ROMANOS = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7}
_CALIDAD_MINUSCULA = {"": "m", "7": "m7", "°": "dim"}

_RE_ACORDE = re.compile(r"([A-G][#b]?)(maj7|m7|dim|aug|m|7)?")
_RE_TONALIDAD = re.compile(r"([A-G][#b]?)(m?)")
_RE_GRADO = re.compile(r"([ivIV]+)(°|7)?")


@dataclass(frozen=True)
class Acorde:
    """Acorde por su raíz y el sufijo del cifrado: Acorde('A', 'm') es La menor."""

    raiz: str
    calidad: str = ""

    def __post_init__(self) -> None:
        clase_de_altura(self.raiz)
        if self.calidad not in CALIDADES:
            sufijos = ", ".join(repr(sufijo) for sufijo in CALIDADES)
            raise ErrorTeoria(
                f"calidad de acorde desconocida {self.calidad!r}: usa {sufijos}"
            )

    @property
    def notas(self) -> tuple[str, ...]:
        """Notas apiladas por terceras y bien escritas: Am -> A C E."""
        base = clase_de_altura(self.raiz)
        inicio = LETRAS.index(self.raiz[0])
        return tuple(
            deletrear(LETRAS[(inicio + 2 * salto) % 7], (base + intervalo) % 12)
            for salto, intervalo in enumerate(CALIDADES[self.calidad])
        )

    def midi(self, octava: int = 3) -> tuple[int, ...]:
        """Tonos MIDI en posición fundamental, con la raíz en esa octava (C4 = 60)."""
        raiz = (octava + 1) * 12 + desplazamiento(self.raiz)
        return tuple(raiz + intervalo for intervalo in CALIDADES[self.calidad])

    def __str__(self) -> str:
        return self.raiz + self.calidad


def parse_acorde(cifrado: str) -> Acorde:
    """'Am' -> Acorde('A', 'm'); 'G7' -> Acorde('G', '7')."""
    coincidencia = _RE_ACORDE.fullmatch(cifrado)
    if coincidencia is None:
        raise ErrorTeoria(f"cifrado inválido {cifrado!r}: usa Am, F, G7, Cmaj7 o Bdim")
    return Acorde(coincidencia.group(1), coincidencia.group(2) or "")


@dataclass(frozen=True)
class Tonalidad:
    """Tonalidad mayor o menor: Tonalidad('A', 'menor') se escribe Am."""

    tonica: str
    modo: str = "mayor"

    def __post_init__(self) -> None:
        clase_de_altura(self.tonica)
        if self.modo not in ("mayor", "menor"):
            raise ErrorTeoria(f"modo de tonalidad {self.modo!r}: usa mayor o menor")

    @property
    def escala(self) -> tuple[str, ...]:
        return _escala(self.tonica, self.modo)

    @property
    def acordes_diatonicos(self) -> tuple[Acorde, ...]:
        """Las tríadas que salen de la escala, grado por grado: Am -> Am Bdim C Dm Em F G."""
        notas = self.escala
        return tuple(_triada(notas, grado) for grado in range(len(notas)))

    def acorde(self, grado: str) -> Acorde:
        """Grado en romanos: mayúscula mayor, minúscula menor, ° disminuido, 7 séptima."""
        coincidencia = _RE_GRADO.fullmatch(grado)
        romano = coincidencia.group(1) if coincidencia else ""
        numero = _ROMANOS.get(romano.lower())
        if (
            coincidencia is None
            or numero is None
            or not (romano.isupper() or romano.islower())
        ):
            raise ErrorTeoria(
                f"grado inválido {grado!r}: usa i a vii o I a VII, con ° o 7"
            )
        sufijo = coincidencia.group(2) or ""
        if romano.islower():
            calidad = _CALIDAD_MINUSCULA[sufijo]
        elif sufijo == "°":
            raise ErrorTeoria(
                f"grado inválido {grado!r}: el ° va en minúsculas, como ii°"
            )
        else:
            calidad = sufijo
        return Acorde(self.escala[numero - 1], calidad)

    def __str__(self) -> str:
        return self.tonica + ("m" if self.modo == "menor" else "")


def _triada(notas: tuple[str, ...], grado: int) -> Acorde:
    clases = [
        clase_de_altura(notas[(grado + salto) % len(notas)]) for salto in (0, 2, 4)
    ]
    intervalos = tuple((clase - clases[0]) % 12 for clase in clases)
    return Acorde(notas[grado], _TRIADAS[intervalos])


def parse_tonalidad(texto: str) -> Tonalidad:
    """'Am' -> La menor; 'C' -> Do mayor."""
    coincidencia = _RE_TONALIDAD.fullmatch(texto)
    if coincidencia is None:
        raise ErrorTeoria(f"tonalidad inválida {texto!r}: usa C, Am, F#m o Bb")
    return Tonalidad(
        coincidencia.group(1), "menor" if coincidencia.group(2) else "mayor"
    )


def progresion(tonalidad: str | Tonalidad, grados: str) -> tuple[Acorde, ...]:
    """'i VI III VII' en Am -> Am F C G."""
    clave = parse_tonalidad(tonalidad) if isinstance(tonalidad, str) else tonalidad
    return tuple(clave.acorde(grado) for grado in grados.split())
