"""El cancion.yaml inicial de una canción nueva, a partir de sus primeros beats.

Solo se escribe si la canción todavía no tiene uno: nunca pisa decisiones del
usuario. Lo demás (base elegida de oído, voz y letra) se llena fase por fase.
"""

from pathlib import Path
from typing import Any

import yaml

from kerto.beat import Beats, ciclo_de_acordes
from kerto.cancion.archivo import ARCHIVO_CANCION, carpeta_cancion
from kerto.ritmos.motor import Beat
from kerto.ritmos.pack import cargar_pack

CABECERA = (
    "# {titulo}: la única fuente de verdad de la canción.\n"
    "# Claude lee este archivo, no los MIDI ni el audio. Los campos vacíos se"
    " llenan fase por fase.\n"
    "# base: el beat que elijas de oído (variacion, acordes y wav).\n"
)
AUTOTUNE_POR_DEFECTO = {"exigencia": "normal", "estilo": "segun_voz"}


def iniciar_cancion(
    nombre: str, beats: Beats, vibe: str | None = None, capa: str | None = None
) -> Path | None:
    """Escribe canciones/<nombre>/cancion.yaml si no existe; None si ya existía.

    `capa` es la capa de acordes con la que se generaron los beats (teclado...).
    """
    carpeta = carpeta_cancion(nombre)
    ruta = carpeta / ARCHIVO_CANCION
    if ruta.exists():
        return None
    datos = _datos(nombre, beats, carpeta, vibe, capa)
    texto = yaml.safe_dump(
        datos, allow_unicode=True, sort_keys=False, default_flow_style=None, width=88
    )
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta.write_text(CABECERA.format(titulo=datos["nombre"]) + texto, encoding="utf-8")
    return ruta


def _datos(
    nombre: str, beats: Beats, carpeta: Path, vibe: str | None, capa: str | None
) -> dict[str, Any]:
    primero = beats.beats[0]
    por_beat = len(beats.archivos) // len(beats.beats)
    grupos = [
        [
            ruta.relative_to(carpeta).as_posix()
            for ruta in beats.archivos[i : i + por_beat]
        ]
        for i in range(0, len(beats.archivos), por_beat)
    ]
    entradas = [
        _entrada(beat, rutas, capa)
        for beat, rutas in zip(beats.beats, grupos, strict=True)
    ]
    estructura = cargar_pack(primero.genero).estructura
    return {
        "nombre": nombre.replace("-", " ").replace("_", " ").title(),
        "vibe": vibe or "",
        "genero": primero.genero,
        "tonalidad": primero.tonalidad,
        "bpm": primero.bpm,
        # Con una sola variación no hay nada que elegir: esa es la base.
        "base": _base(beats.beats[0], grupos[0], capa) if len(entradas) == 1 else None,
        "beats": entradas,
        "autotune": dict(AUTOTUNE_POR_DEFECTO),
        "voz": None,
        "letra": {"archivo": "letra.md", "estado": "sin escribir"},
        "secciones": [f"{parte} {compases}" for parte, compases in estructura],
    }


def _entrada(beat: Beat, rutas: list[str], capa: str | None) -> dict[str, Any]:
    entrada: dict[str, Any] = {
        "variacion": beat.variacion,
        "acordes": " ".join(ciclo_de_acordes(beat.acordes)),
    }
    if capa:
        entrada["capa"] = capa
    entrada["archivos"] = ", ".join(rutas)
    return entrada


def _base(beat: Beat, rutas: list[str], capa: str | None) -> dict[str, Any]:
    base: dict[str, Any] = {"variacion": beat.variacion}
    if capa:
        base["acordes"] = capa
    wav = next((ruta for ruta in rutas if ruta.endswith(".wav")), None)
    if wav:
        base["wav"] = wav
    return base
