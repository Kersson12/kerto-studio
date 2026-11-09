"""Sonido de cada instrumento al renderizar: generos/<genero>/sonidos.yaml."""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from kerto.render.faust import VOCES
from kerto.ritmos.pack import GENEROS

ARCHIVO_SONIDOS = "sonidos.yaml"
_RE_GENERO = re.compile(r"[a-z0-9_-]+")


class ErrorSonidos(ValueError):
    """Archivo de sonidos que falta o está mal escrito."""


@dataclass(frozen=True)
class Sonido:
    """Patch de Surge XT (opcional), voz interna de respaldo y nivel de la pista."""

    surge: str | None
    faust: str
    nivel: float
    # (pista, dB, ms): baja tantos dB cuando suena esa pista y se recupera en ms.
    agacha: tuple[str, float, float] | None = None


def cargar_sonidos(genero: str, carpeta: Path = GENEROS) -> dict[str, Sonido]:
    """Lee y valida generos/<genero>/sonidos.yaml."""
    ruta = carpeta / genero / ARCHIVO_SONIDOS
    if not _RE_GENERO.fullmatch(genero) or not ruta.is_file():
        raise ErrorSonidos(f"no hay {ARCHIVO_SONIDOS} para el género {genero!r}")
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ErrorSonidos(f"{ruta} no es YAML válido: {error}") from error
    if not isinstance(datos, dict):
        raise ErrorSonidos(f"{ruta} debe ser un mapa instrumento: sonido")
    return {str(nombre): _sonido(str(nombre), valor) for nombre, valor in datos.items()}


def _sonido(nombre: str, datos: object) -> Sonido:
    if not isinstance(datos, dict):
        raise ErrorSonidos(
            f"el sonido de {nombre!r} debe ser un mapa, como {{faust: bombo}}"
        )
    voz = datos.get("faust")
    if voz is None:
        raise ErrorSonidos(
            f"el sonido de {nombre!r} necesita faust: la voz de respaldo"
        )
    if voz not in VOCES:
        raise ErrorSonidos(
            f"voz faust desconocida {voz!r} en {nombre!r}: usa {', '.join(VOCES)}"
        )
    surge = datos.get("surge")
    if surge is not None and not isinstance(surge, str):
        raise ErrorSonidos(f"surge de {nombre!r} debe ser un patch como Basses/Sub 1")
    nivel = datos.get("nivel", -6)
    if not isinstance(nivel, int | float) or isinstance(nivel, bool) or nivel > 0:
        raise ErrorSonidos(
            f"nivel de {nombre!r} debe ser 0 o negativo (dBFS), no {nivel!r}"
        )
    return Sonido(surge, voz, float(nivel), _agacha(nombre, datos.get("agacha")))


def _agacha(nombre: str, datos: object) -> tuple[str, float, float] | None:
    """agacha: {con: bombo, db: 8, ms: 120} -> ('bombo', 8.0, 120.0)."""
    if datos is None:
        return None
    if not isinstance(datos, dict):
        raise ErrorSonidos(
            f"agacha de {nombre!r} debe ser un mapa, como {{con: bombo}}"
        )
    con = datos.get("con")
    if not isinstance(con, str):
        raise ErrorSonidos(f"agacha de {nombre!r} necesita con: la pista que lo agacha")
    valores = []
    for clave, defecto in (("db", 8), ("ms", 120)):
        valor = datos.get(clave, defecto)
        if not isinstance(valor, int | float) or isinstance(valor, bool) or valor <= 0:
            raise ErrorSonidos(f"agacha.{clave} de {nombre!r} debe ser mayor que 0")
        valores.append(float(valor))
    return con, valores[0], valores[1]
