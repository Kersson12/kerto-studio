"""Surge XT: dónde está instalado y cómo cargar sus patches de fábrica en DawDreamer.

DawDreamer no abre los patches .fxp de Surge XT en VST3, así que se arma a mano
el estado que guarda JUCE (el framework de Surge XT): un XML VST3PluginState
con el patch dentro, codificado con la variante de base64 de JUCE.
"""

import os
import struct
import sys
from collections.abc import Sequence
from pathlib import Path

_TABLA_JUCE = ".ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+"
_CABECERA_FXP = (
    60  # CcnK, tamaño, FPCh, versión, id, versión, programas, nombre, tamaño del chunk
)
_MAGIA_XML_JUCE = b"VC2!"


class ErrorSurge(ValueError):
    """Patch de Surge XT que no se puede leer."""


def _candidatos_vst3() -> list[Path]:
    if sys.platform == "win32":
        comunes = Path(
            os.environ.get("CommonProgramFiles", r"C:\Program Files\Common Files")
        )
        return [
            comunes / "VST3" / "Surge Synth Team" / "Surge XT.vst3",
            comunes / "VST3" / "Surge XT.vst3",
        ]
    if sys.platform == "darwin":
        return [
            Path("/Library/Audio/Plug-Ins/VST3/Surge XT.vst3"),
            Path.home() / "Library/Audio/Plug-Ins/VST3/Surge XT.vst3",
        ]
    return [
        Path("/usr/lib/vst3/Surge XT.vst3"),
        Path("/usr/local/lib/vst3/Surge XT.vst3"),
        Path.home() / ".vst3/Surge XT.vst3",
    ]


def _candidatos_patches() -> list[Path]:
    if sys.platform == "win32":
        datos = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
        return [datos / "Surge XT" / "patches_factory"]
    if sys.platform == "darwin":
        return [Path("/Library/Application Support/Surge XT/patches_factory")]
    return [
        Path("/usr/share/surge-xt/patches_factory"),
        Path("/usr/local/share/surge-xt/patches_factory"),
    ]


def buscar_surge(
    vst3: Sequence[Path] | None = None, patches: Sequence[Path] | None = None
) -> tuple[Path, Path] | None:
    """(plugin VST3, carpeta de patches de fábrica) si Surge XT está instalado."""
    plugin = next((r for r in vst3 or _candidatos_vst3() if r.exists()), None)
    fabrica = next((r for r in patches or _candidatos_patches() if r.is_dir()), None)
    if plugin is None or fabrica is None:
        return None
    return plugin, fabrica


def base64_juce(datos: bytes) -> str:
    """'<bytes>.<texto>': grupos de 6 bits desde el bit más bajo, con la tabla de JUCE."""
    caracteres = (len(datos) * 8 + 5) // 6
    relleno = datos + b"\0\0"
    salida: list[str] = []
    for i in range(0, len(datos), 3):
        valor = relleno[i] | relleno[i + 1] << 8 | relleno[i + 2] << 16
        salida.extend(_TABLA_JUCE[(valor >> bits) & 63] for bits in (0, 6, 12, 18))
    return f"{len(datos)}." + "".join(salida[:caracteres])


def estado_desde_fxp(crudo: bytes) -> bytes:
    """El estado JUCE que hace que Surge XT cargue el patch de este .fxp."""
    if len(crudo) < _CABECERA_FXP or crudo[:4] != b"CcnK" or crudo[8:12] != b"FPCh":
        raise ErrorSurge("no es un patch .fxp de Surge XT")
    (tamano,) = struct.unpack(">I", crudo[_CABECERA_FXP - 4 : _CABECERA_FXP])
    chunk = crudo[_CABECERA_FXP : _CABECERA_FXP + tamano]
    if len(chunk) != tamano:
        raise ErrorSurge("el patch .fxp está cortado")
    xml = (
        f"<VST3PluginState><IComponent>{base64_juce(chunk)}</IComponent>"
        "</VST3PluginState>"
    )
    cuerpo = xml.encode("utf-8") + b"\0"
    return _MAGIA_XML_JUCE + struct.pack("<I", len(cuerpo) - 1) + cuerpo


def cargar_patch(fabrica: Path, nombre: str) -> bytes:
    """Estado JUCE del patch 'Carpeta/Nombre' de la carpeta de fábrica."""
    ruta = (fabrica / f"{nombre}.fxp").resolve()
    if not ruta.is_relative_to(fabrica.resolve()) or not ruta.is_file():
        raise ErrorSurge(f"no existe el patch de Surge XT {nombre!r}")
    return estado_desde_fxp(ruta.read_bytes())
