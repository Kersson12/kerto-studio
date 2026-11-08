"""Análisis de la voz: tono con pYIN (librosa), rango, afinación, estabilidad y tonalidades.

El audio va como canales x muestras (igual que el resto de Kerto) o mono.
A Claude solo le llega `resumir_informe`; los arrays nunca salen de Python.
"""

import math
from dataclasses import dataclass

import librosa
import numpy as np

from kerto.notacion import midi_a_nota

FRECUENCIA_ANALISIS = 22050
NOTA_MINIMA = "C2"  # 65 Hz: más grave que casi cualquier voz
NOTA_MAXIMA = "C6"  # 1047 Hz
PERCENTIL_EXTREMO = 2  # ignora el 2 % más grave y más agudo (ruidos, quiebres)
PERCENTIL_COMODO = 20  # la zona cómoda: del 20 % al 80 % de lo cantado
SALTO_DE_NOTA = 50  # cents entre cuadros: más que esto es otra nota
TONALIDADES_MENOR = (
    "Cm",
    "C#m",
    "Dm",
    "Ebm",
    "Em",
    "Fm",
    "F#m",
    "Gm",
    "G#m",
    "Am",
    "Bbm",
    "Bm",
)
TONALIDADES_MAYOR = ("C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")


class ErrorVoz(ValueError):
    """Audio en el que no se puede analizar la voz."""


@dataclass(frozen=True)
class Tono:
    """Tono cuadro a cuadro: Hz (nan donde no hay voz) y si el cuadro es voz."""

    tiempos: np.ndarray
    hz: np.ndarray
    sonoro: np.ndarray


@dataclass(frozen=True)
class Informe:
    """Lo que el coach necesita saber de una muestra de voz."""

    segundos: float
    cantado: float
    nota_grave: str
    nota_aguda: str
    comoda_grave: str
    comoda_aguda: str
    centro: str
    desafinacion: float
    temblor: float
    tonalidades: tuple[str, ...]


def hz_a_midi(hz: float | np.ndarray) -> float | np.ndarray:
    """440 Hz -> 69.0 (La4), con decimales: 445 Hz -> 69.196."""
    return 69 + 12 * np.log2(np.asarray(hz) / 440.0)


def hz_a_nota(hz: float) -> tuple[str, float]:
    """445 Hz -> ('A4', +19.6): la nota más cercana y los cents de diferencia."""
    midi = float(hz_a_midi(hz))
    cercana = round(midi)
    return midi_a_nota(cercana), (midi - cercana) * 100


def _mono(audio: np.ndarray) -> np.ndarray:
    senal = np.asarray(audio, dtype=np.float32)
    if senal.ndim == 2:
        senal = senal.mean(axis=0)
    if senal.size == 0:
        raise ErrorVoz("el audio está vacío")
    return senal


def detectar_tono(audio: np.ndarray, frecuencia: int) -> Tono:
    """pYIN cuadro a cuadro, entre C2 y C6."""
    senal = _mono(audio)
    if frecuencia != FRECUENCIA_ANALISIS:
        senal = librosa.resample(
            senal, orig_sr=frecuencia, target_sr=FRECUENCIA_ANALISIS
        )
    hz, sonoro, _ = librosa.pyin(
        senal,
        fmin=librosa.note_to_hz(NOTA_MINIMA),
        fmax=librosa.note_to_hz(NOTA_MAXIMA),
        sr=FRECUENCIA_ANALISIS,
    )
    tiempos = librosa.times_like(hz, sr=FRECUENCIA_ANALISIS)
    return Tono(tiempos, hz, sonoro & np.isfinite(hz))


def analizar_voz(audio: np.ndarray, frecuencia: int) -> Informe:
    """Rango, zona cómoda, desafinación, temblor y tonalidades de una muestra."""
    segundos = _mono(audio).size / frecuencia
    tono = detectar_tono(audio, frecuencia)
    if not tono.sonoro.any():
        raise ErrorVoz("no se detectó voz: canta más cerca del micrófono o más fuerte")
    midi = hz_a_midi(tono.hz[tono.sonoro])
    grave, aguda = np.percentile(midi, [PERCENTIL_EXTREMO, 100 - PERCENTIL_EXTREMO])
    comoda = np.percentile(midi, [PERCENTIL_COMODO, 100 - PERCENTIL_COMODO])
    centro = float(np.median(midi))
    return Informe(
        segundos=segundos,
        cantado=float(tono.sonoro.mean()),
        nota_grave=midi_a_nota(round(grave)),
        nota_aguda=midi_a_nota(round(aguda)),
        comoda_grave=midi_a_nota(round(comoda[0])),
        comoda_aguda=midi_a_nota(round(comoda[1])),
        centro=midi_a_nota(round(centro)),
        desafinacion=float(np.mean(np.abs(midi - np.round(midi))) * 100),
        temblor=_temblor(midi),
        tonalidades=tonalidades_comodas(centro),
    )


def _temblor(midi: np.ndarray) -> float:
    """Cuánto se mueve el tono dentro de cada nota sostenida, en cents (desvío estándar)."""
    cents = midi * 100
    cortes = np.nonzero(np.abs(np.diff(cents)) > SALTO_DE_NOTA)[0] + 1
    desvios = [
        tramo - np.median(tramo) for tramo in np.split(cents, cortes) if tramo.size > 1
    ]
    if not desvios:
        return 0.0
    return float(np.std(np.concatenate(desvios)))


def tonalidades_comodas(centro: float, modo: str = "menor") -> tuple[str, ...]:
    """Tres tonalidades con la tónica más cerca del centro de la voz (en MIDI)."""
    nombres = TONALIDADES_MENOR if modo == "menor" else TONALIDADES_MAYOR

    def distancia(clase: int) -> tuple[float, bool]:
        diferencia = (clase - centro + 6) % 12 - 6
        return abs(diferencia), diferencia < 0

    return tuple(nombres[clase] for clase in sorted(range(12), key=distancia)[:3])


def resumir_informe(informe: Informe) -> str:
    """Cuatro líneas para Claude: duración, rango, afinación y tonalidades."""
    voz = f"Voz: {informe.segundos:.1f} s, {informe.cantado:.0%} cantado"
    rango = (
        f"Rango: {informe.nota_grave}–{informe.nota_aguda}"
        f" · cómodo: {informe.comoda_grave}–{informe.comoda_aguda}"
        f" · centro: {informe.centro}"
    )
    desafinacion = math.floor(informe.desafinacion + 0.5)
    temblor = math.floor(informe.temblor + 0.5)
    afinacion = (
        f"Afinación: {desafinacion} cents de desviación media · temblor {temblor} cents"
    )
    tonalidades = f"Tonalidades cómodas (menor): {', '.join(informe.tonalidades)}"
    return f"{voz}\n{rango}\n{afinacion}\n{tonalidades}"
