"""Generar beats de punta a punta: pack -> variaciones -> MIDI y WAV -> resumen.

Es la herramienta de alto nivel que usan el comando `kerto beat` y, desde la
Fase 4, el MCP: una llamada y vuelve un resumen de tres líneas.
"""

from dataclasses import dataclass
from pathlib import Path

from kerto.midi import exportar_midi
from kerto.render.motor import renderizar
from kerto.render.sonidos import cargar_sonidos
from kerto.ritmos.motor import COMPASES_POR_DEFECTO, Beat, ErrorBeat, crear_beat
from kerto.ritmos.pack import GENEROS, cargar_pack

SALIDA_POR_DEFECTO = Path("canciones/borrador/beats")
VARIACIONES_POR_DEFECTO = 3
_NOMBRE_MOTOR = {"surge": "Surge XT", "faust": "Faust"}


@dataclass(frozen=True)
class Beats:
    """Lo que se generó: carpeta, archivos, beats y motor de sonido por instrumento."""

    salida: Path
    archivos: tuple[Path, ...]
    beats: tuple[Beat, ...]
    motores: dict[str, str]


def generar_beats(
    genero: str = "reggaeton",
    *,
    bpm: int | None = None,
    tonalidad: str | None = None,
    compases: int = COMPASES_POR_DEFECTO,
    variaciones: int = VARIACIONES_POR_DEFECTO,
    semilla: int = 0,
    salida: Path = SALIDA_POR_DEFECTO,
    wav: bool = True,
    usar_surge: bool = True,
    sobrescribir: bool = False,
    carpeta: Path = GENEROS,
) -> Beats:
    """Crea las variaciones del género y escribe beat-N-nombre.mid (y .wav)."""
    pack = cargar_pack(genero, carpeta=carpeta)
    total = len(pack.variaciones)
    if not 1 <= variaciones <= total:
        raise ErrorBeat(
            f"el pack {genero!r} tiene {total} variaciones: pide de 1 a {total}"
        )
    beats = tuple(
        crear_beat(
            pack,
            indice,
            bpm=bpm,
            tonalidad=tonalidad,
            compases=compases,
            semilla=semilla,
        )
        for indice in range(variaciones)
    )
    sonidos = cargar_sonidos(genero, carpeta=carpeta) if wav else {}
    extensiones = (".mid", ".wav") if wav else (".mid",)
    bases = [salida / f"beat-{n}-{b.variacion}" for n, b in enumerate(beats, 1)]
    archivos = tuple(base.with_suffix(ext) for base in bases for ext in extensiones)
    existentes = [a.name for a in archivos if a.exists()]
    if existentes and not sobrescribir:
        raise FileExistsError(
            f"ya existen {', '.join(existentes)} en {salida.as_posix()}:"
            " usa --sobrescribir u otra --salida"
        )
    motores: dict[str, str] = {}
    for base, beat in zip(bases, beats, strict=True):
        exportar_midi(beat, base.with_suffix(".mid"))
        if wav:
            render = renderizar(
                beat, base.with_suffix(".wav"), sonidos, usar_surge=usar_surge
            )
            for instrumento, motor in render.motores.items():
                motores[instrumento] = motores.get(instrumento, motor)
    return Beats(salida, archivos, beats, motores)


def resumir(beats: Beats) -> str:
    """Tres líneas: archivos creados, género y sonido, BPM y tonalidad."""
    primero = beats.beats[0]
    nombres = list(dict.fromkeys(a.stem for a in beats.archivos))
    extensiones = " y ".join(dict.fromkeys(a.suffix for a in beats.archivos))
    archivos = (
        f"Archivos: {len(beats.archivos)} en {beats.salida.as_posix()}/"
        f" · {', '.join(nombres)} ({extensiones})"
    )
    genero = (
        f"Género: {primero.genero} · {len(beats.beats)} variaciones"
        f" · {primero.compases} compases de {primero.compas}"
        f" · sonido: {_sonido(beats.motores)}"
    )
    acordes = " / ".join(" ".join(_ciclo(b.acordes)) for b in beats.beats)
    tempo = f"BPM: {primero.bpm} · Tonalidad: {primero.tonalidad} · acordes: {acordes}"
    return f"{archivos}\n{genero}\n{tempo}"


def _sonido(motores: dict[str, str]) -> str:
    if not motores:
        return "solo MIDI"
    grupos: dict[str, list[str]] = {}
    for instrumento, motor in motores.items():
        grupos.setdefault(motor, []).append(instrumento)
    return " + ".join(
        f"{_NOMBRE_MOTOR[motor]} ({', '.join(instrumentos)})"
        for motor, instrumentos in grupos.items()
    )


def _ciclo(acordes: tuple[str, ...]) -> tuple[str, ...]:
    """La progresión sin repetir: (Am F C G Am F C G) -> (Am F C G)."""
    for periodo in range(1, len(acordes) + 1):
        if all(acordes[i] == acordes[i % periodo] for i in range(len(acordes))):
            return acordes[:periodo]
    return acordes  # pragma: no cover - el periodo completo siempre coincide
