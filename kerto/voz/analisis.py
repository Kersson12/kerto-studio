"""Análisis de la voz: tono con pYIN (librosa), rango, afinación, estabilidad y tonalidades.

El audio va como canales x muestras (igual que el resto de Kerto) o mono.
A Claude solo le llega `resumir_informe`; los arrays nunca salen de Python.
"""

import math
from dataclasses import dataclass

import librosa
import numpy as np

from kerto.notacion import midi_a_nota, nota_a_midi

FRECUENCIA_ANALISIS = 22050
NOTA_MINIMA = "C2"  # 65 Hz: más grave que casi cualquier voz
NOTA_MAXIMA = "C6"  # 1047 Hz
PERCENTIL_EXTREMO = 2  # ignora el 2 % más grave y más agudo (ruidos, quiebres)
PERCENTIL_COMODO = 20  # la zona cómoda: del 20 % al 80 % de lo cantado
# Una nota sostenida: cuadros con voz que no se alejan más de BANDA_NOTA cents
# de su mediana, durante al menos DURACION_MINIMA_NOTA. Los deslizamientos
# entre notas quedan fuera y no cuentan como desafinación ni temblor.
BANDA_NOTA = 50
DURACION_MINIMA_NOTA = 0.15
RECORTE_BORDE = 2  # cuadros que se quitan al inicio y al final de cada nota
PAUSA_ENTRE_TOMAS = 1.0  # segundos de separación al unir tomas
VOZ_SOBRE_FONDO = 12  # dB que la voz debe superar al fondo para contar
# Cantando sin música, cada toma tiene su propia referencia (corrida del La 440).
# Si aun descontándola las notas quedan a más de UMBRAL_ESCALA cents de una
# escala fija, no caen en ninguna: notas al azar darían unos 21.
UMBRAL_ESCALA = 15
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
    toma: np.ndarray | None = None  # número de toma de cada cuadro, al unir varias


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
    notas: int
    corrimiento: float  # cents de tu referencia propia respecto del La 440
    relativa: float  # desafinación entre tus notas, descontando el corrimiento
    en_escala: bool  # si tus notas caen en una escala fija


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
    """pYIN cuadro a cuadro, entre C2 y C6, solo donde la voz supera el fondo."""
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
    return Tono(tiempos, hz, sonoro & np.isfinite(hz) & _sobre_el_fondo(senal, hz.size))


def _sobre_el_fondo(senal: np.ndarray, cuadros: int) -> np.ndarray:
    """Cuadros que superan el fondo (el 10 % más bajo) por VOZ_SOBRE_FONDO dB.

    Así el beat que se cuela desde los audífonos o un ruido tonal no se miden
    como si fueran la voz. Si todo suena parejo (no hay fondo), no se filtra.
    """
    rms = librosa.feature.rms(y=senal, frame_length=2048, hop_length=512)[0]
    niveles = 20 * np.log10(np.maximum(rms[:cuadros], 1e-10))
    niveles = np.pad(niveles, (0, cuadros - niveles.size), mode="edge")
    fondo, alto = np.percentile(niveles, [10, 90])
    if alto - fondo < VOZ_SOBRE_FONDO:
        return np.ones(cuadros, dtype=bool)
    return niveles > fondo + VOZ_SOBRE_FONDO


def analizar_voz(audio: np.ndarray, frecuencia: int) -> Informe:
    """Rango, zona cómoda, desafinación, temblor y tonalidades de una muestra."""
    segundos = _mono(audio).size / frecuencia
    return informe_desde_tono(detectar_tono(audio, frecuencia), segundos)


def informe_desde_tono(tono: Tono, segundos: float) -> Informe:
    """El informe a partir de un tono ya detectado (pYIN corre una sola vez)."""
    if not tono.sonoro.any():
        raise ErrorVoz("no se detectó voz: canta más cerca del micrófono o más fuerte")
    por_toma = [notas_sostenidas(parte) for parte in _por_toma(tono)]
    notas = [nota for notas_toma in por_toma for nota in notas_toma]
    if not notas:
        raise ErrorVoz(
            "no hubo notas sostenidas para medir la afinación:"
            " canta frases con algunas notas un poco más largas"
        )
    midi = np.concatenate(notas) / 100
    grave, aguda = np.percentile(midi, [PERCENTIL_EXTREMO, 100 - PERCENTIL_EXTREMO])
    comoda = np.percentile(midi, [PERCENTIL_COMODO, 100 - PERCENTIL_COMODO])
    centro = float(np.median(midi))
    centros = np.array([np.median(nota) for nota in notas])
    pesos = np.array([nota.size for nota in notas])
    referencias = [_referencia(notas_toma) for notas_toma in por_toma if notas_toma]
    cuadros = [peso for _, _, peso in referencias]
    relativa = float(np.average([r for _, r, _ in referencias], weights=cuadros))
    return Informe(
        segundos=segundos,
        cantado=float(tono.sonoro.mean()),
        nota_grave=midi_a_nota(round(grave)),
        nota_aguda=midi_a_nota(round(aguda)),
        comoda_grave=midi_a_nota(round(comoda[0])),
        comoda_aguda=midi_a_nota(round(comoda[1])),
        centro=midi_a_nota(round(centro)),
        desafinacion=float(np.average(np.abs(_a_la_escala(centros)), weights=pesos)),
        temblor=float(np.std(np.concatenate([n - np.median(n) for n in notas]))),
        tonalidades=tonalidades_comodas(centro),
        notas=len(notas),
        corrimiento=float(np.average([c for c, _, _ in referencias], weights=cuadros)),
        relativa=relativa,
        en_escala=relativa < UMBRAL_ESCALA,
    )


def _a_la_escala(cents: np.ndarray) -> np.ndarray:
    """Cents hasta el semitono más cercano, de -50 a +50."""
    return (cents + 50) % 100 - 50


def _referencia(notas: list[np.ndarray]) -> tuple[float, float, int]:
    """(corrimiento, desafinación relativa, cuadros) de una toma.

    Prueba correr la escala de -50 a +50 cents y se queda con el corrimiento
    que deja las notas más cerca de sus semitonos.
    """
    centros = np.array([np.median(nota) for nota in notas])
    pesos = np.array([nota.size for nota in notas], dtype=float)
    corrimientos = np.arange(-50.0, 50.0)
    errores = (
        np.abs(_a_la_escala(centros[None, :] - corrimientos[:, None])) @ pesos
    ) / pesos.sum()
    mejor = int(np.argmin(errores))
    return float(corrimientos[mejor]), float(errores[mejor]), int(pesos.sum())


def _por_toma(tono: Tono) -> list[Tono]:
    if tono.toma is None:
        return [tono]
    return [
        Tono(tono.tiempos[cual], tono.hz[cual], tono.sonoro[cual])
        for cual in (tono.toma == numero for numero in np.unique(tono.toma))
    ]


def notas_sostenidas(tono: Tono) -> list[np.ndarray]:
    """Cents de cada nota sostenida, sin los bordes ni los deslizamientos."""
    if tono.tiempos.size < 2:
        return []
    paso = float(np.median(np.diff(tono.tiempos)))
    tiempos = tono.tiempos[tono.sonoro]
    cents = hz_a_midi(tono.hz[tono.sonoro]) * 100
    tramos: list[list[float]] = []
    actual: list[float] = []
    anterior = -math.inf
    for tiempo, valor in zip(tiempos, cents, strict=True):
        corte = tiempo - anterior > 1.5 * paso
        if actual and (corte or abs(valor - np.median(actual)) > BANDA_NOTA):
            tramos.append(actual)
            actual = []
        actual.append(float(valor))
        anterior = tiempo
    tramos.append(actual)
    minimo = max(DURACION_MINIMA_NOTA / paso, 2 * RECORTE_BORDE + 1)
    return [
        np.array(tramo[RECORTE_BORDE:-RECORTE_BORDE])
        for tramo in tramos
        if len(tramo) >= minimo and _es_plano(tramo) and _lejos_del_limite(tramo)
    ]


def _lejos_del_limite(tramo: list[float]) -> bool:
    """Una nota pegada al límite del detector (C2 o C6) casi siempre es ruido."""
    centro = float(np.median(tramo))
    grave = (nota_a_midi(NOTA_MINIMA) + 1) * 100
    aguda = (nota_a_midi(NOTA_MAXIMA) - 1) * 100
    return grave < centro < aguda


def _es_plano(tramo: list[float]) -> bool:
    """Una nota no avanza: el vibrato oscila, pero un deslizamiento sube o baja."""
    pendiente = np.polyfit(np.arange(len(tramo)), tramo, 1)[0]
    return abs(pendiente) * len(tramo) <= BANDA_NOTA


def unir_tonos(tonos: list[Tono]) -> Tono:
    """Une varias tomas en un solo tono, separadas en el tiempo para no mezclar notas."""
    tiempos, inicio = [], 0.0
    for tono in tonos:
        tiempos.append(tono.tiempos + inicio)
        fin = float(tono.tiempos[-1]) if tono.tiempos.size else 0.0
        inicio += fin + PAUSA_ENTRE_TOMAS
    return Tono(
        np.concatenate(tiempos),
        np.concatenate([tono.hz for tono in tonos]),
        np.concatenate([tono.sonoro for tono in tonos]),
        np.concatenate([np.full(t.hz.size, n) for n, t in enumerate(tonos)]),
    )


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
    relativa = math.floor(informe.relativa + 0.5)
    corrimiento = math.floor(informe.corrimiento + 0.5)
    temblor = math.floor(informe.temblor + 0.5)
    afinacion = (
        f"Afinación: {desafinacion} cents del La 440 · {relativa} entre tus notas"
        f" (tu referencia: {corrimiento:+d}) · temblor {temblor} cents"
    )
    if not informe.en_escala:
        afinacion += " · tus notas no caen en una escala fija"
    tonalidades = f"Tonalidades cómodas (menor): {', '.join(informe.tonalidades)}"
    return f"{voz}\n{rango}\n{afinacion}\n{tonalidades}"
