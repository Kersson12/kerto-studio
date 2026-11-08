"""Render de un beat a WAV con DawDreamer.

Cada pista se renderiza por separado con su patch de Surge XT, o con la voz
interna de Faust si Surge XT no está o no suena. Luego cada pista se lleva a
su nivel, se suman y la mezcla se deja con el pico en -1 dBFS.
"""

import math
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import dawdreamer as daw
import numpy as np

from kerto.render.faust import dsp
from kerto.render.sonidos import ErrorSonidos, Sonido
from kerto.render.surge import buscar_surge, cargar_patch
from kerto.render.wav import escribir_wav
from kerto.ritmos.motor import Beat, Pista

FRECUENCIA = 44100
BLOQUE = 512
# Surge XT carga el patch en los primeros bloques y se come las notas de ese
# instante: todo suena PREROLL segundos más tarde y luego se recorta.
PREROLL = 0.25
PICO_MEZCLA_DB = -1.0
VOCES_FAUST = 16

Creador = Callable[[daw.RenderEngine], object]


@dataclass(frozen=True)
class Render:
    """Resultado del render: archivo, motor de cada pista, duración y pico."""

    ruta: Path
    motores: dict[str, str]
    segundos: float
    pico_db: float


def renderizar(
    beat: Beat,
    ruta: Path,
    sonidos: dict[str, Sonido],
    usar_surge: bool = True,
    frecuencia: int = FRECUENCIA,
) -> Render:
    """Renderiza el beat a un WAV estéreo de 24 bits y devuelve el resumen."""
    faltan = [pista.nombre for pista in beat.pistas if pista.nombre not in sonidos]
    if faltan:
        raise ErrorSonidos(f"faltan los sonidos de: {', '.join(faltan)}")
    segundos = float(_segundos(beat.duracion, beat.bpm))
    muestras = round(segundos * frecuencia)
    surge = buscar_surge() if usar_surge else None
    mezcla = np.zeros((2, muestras))
    motores: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="kerto-") as temporal:
        for pista in beat.pistas:
            sonido = sonidos[pista.nombre]
            audio, motor = _renderizar_pista(
                pista, beat.bpm, sonido, surge, muestras, frecuencia, Path(temporal)
            )
            motores[pista.nombre] = motor
            mezcla += _a_nivel(audio, sonido.nivel)
    pico = float(np.abs(mezcla).max())
    if pico > 0:
        mezcla *= 10 ** (PICO_MEZCLA_DB / 20) / pico
    escribir_wav(ruta, mezcla, frecuencia)
    return Render(ruta, motores, segundos, _db(float(np.abs(mezcla).max())))


def _segundos(tiempo: Fraction, bpm: int) -> Fraction:
    """Redondas a segundos: el BPM cuenta negras."""
    return tiempo * 4 * 60 / bpm


def _db(pico: float) -> float:
    return 20 * math.log10(pico) if pico > 0 else -math.inf


def _a_nivel(audio: np.ndarray, nivel_db: float) -> np.ndarray:
    pico = float(np.abs(audio).max())
    return audio if pico == 0 else audio * (10 ** (nivel_db / 20) / pico)


def _renderizar_pista(
    pista: Pista,
    bpm: int,
    sonido: Sonido,
    surge: tuple[Path, Path] | None,
    muestras: int,
    frecuencia: int,
    temporal: Path,
) -> tuple[np.ndarray, str]:
    if surge is not None and sonido.surge is not None and pista.notas:
        try:
            crear = _creador_surge(pista.nombre, surge, sonido.surge, temporal)
            audio = _renderizar_con(crear, pista, bpm, muestras, frecuencia)
        except Exception:  # noqa: BLE001 - si Surge XT falla, suena el respaldo
            audio = None
        if audio is not None and np.abs(audio).max() > 0:
            return audio, "surge"
    crear = _creador_faust(pista.nombre, sonido.faust)
    return _renderizar_con(crear, pista, bpm, muestras, frecuencia), "faust"


def _creador_surge(
    nombre: str, surge: tuple[Path, Path], patch: str, temporal: Path
) -> Creador:
    vst3, fabrica = surge
    estado = temporal / f"{nombre}.state"
    estado.write_bytes(cargar_patch(fabrica, patch))

    def crear(engine: daw.RenderEngine) -> object:
        synth = engine.make_plugin_processor(nombre, str(vst3))
        synth.load_state(str(estado))
        return synth

    return crear


def _creador_faust(nombre: str, voz: str) -> Creador:
    def crear(engine: daw.RenderEngine) -> object:
        synth = engine.make_faust_processor(nombre)
        synth.num_voices = VOCES_FAUST
        synth.set_dsp_string(dsp(voz))
        synth.compile()
        return synth

    return crear


def _renderizar_con(
    crear: Creador, pista: Pista, bpm: int, muestras: int, frecuencia: int
) -> np.ndarray:
    engine = daw.RenderEngine(frecuencia, BLOQUE)
    synth = crear(engine)
    for nota in pista.notas:
        synth.add_midi_note(
            nota.tono,
            nota.velocidad,
            PREROLL + float(_segundos(nota.inicio, bpm)),
            float(_segundos(nota.duracion, bpm)),
        )
    engine.load_graph([(synth, [])])
    engine.render(PREROLL + muestras / frecuencia)
    audio = np.asarray(engine.get_audio(), dtype=np.float64)
    inicio = round(PREROLL * frecuencia)
    recorte = audio[:2, inicio : inicio + muestras]
    return np.pad(recorte, ((0, 0), (0, muestras - recorte.shape[1])))
