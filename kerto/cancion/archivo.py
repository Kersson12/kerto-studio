"""cancion.yaml: la única fuente de verdad de cada canción (canciones/<nombre>/)."""

import re
from pathlib import Path
from typing import Any

import yaml

CANCIONES = Path("canciones")
ARCHIVO_CANCION = "cancion.yaml"
_RE_NOMBRE = re.compile(r"[a-z0-9][a-z0-9_-]*")


class ErrorCancion(ValueError):
    """Canción que no existe o cuyo cancion.yaml no tiene lo que se pide."""


def carpeta_cancion(nombre: str) -> Path:
    """canciones/<nombre>, con un nombre simple como luna-negra."""
    if not _RE_NOMBRE.fullmatch(nombre):
        raise ErrorCancion(
            f"nombre de canción inválido {nombre!r}: usa algo como luna-negra"
        )
    return CANCIONES / nombre


def leer_cancion(nombre: str) -> dict[str, Any]:
    """El contenido de canciones/<nombre>/cancion.yaml."""
    ruta = carpeta_cancion(nombre) / ARCHIVO_CANCION
    if not ruta.is_file():
        raise ErrorCancion(f"no existe {ruta.as_posix()}")
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ErrorCancion(f"{ruta.as_posix()} debe ser un mapa de claves")
    return datos


def beat_base(nombre: str) -> Path:
    """El WAV del beat elegido como base (base.wav en cancion.yaml)."""
    base = leer_cancion(nombre).get("base")
    if not isinstance(base, dict) or not base.get("wav"):
        raise ErrorCancion(
            f"la canción {nombre!r} todavía no tiene base con wav en cancion.yaml:"
            " elige un beat o usa --con-beat <archivo.wav>"
        )
    ruta = carpeta_cancion(nombre) / str(base["wav"])
    if not ruta.is_file():
        raise ErrorCancion(f"no existe el beat base {ruta.as_posix()}")
    return ruta
