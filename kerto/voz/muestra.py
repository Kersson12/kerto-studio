"""Muestra de voz: grabarla o leerla, consejos de grabación y el JSON con todo el análisis.

sounddevice se importa solo al grabar: así el resto funciona aunque el sistema
no tenga PortAudio (por ejemplo, en la CI).
"""

import json
import re
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import librosa
import numpy as np
import soundfile

from kerto.render.wav import escribir_wav
from kerto.voz.analisis import (
    FRECUENCIA_ANALISIS,
    ErrorVoz,
    Informe,
    Tono,
    detectar_tono,
    informe_desde_tono,
)
from kerto.voz.autotune import Recomendacion

FRECUENCIA_GRABACION = 44100
SEGUNDOS_MUESTRA = 30.0
CUENTA_ATRAS = 3
UMBRAL_SATURACION = 0.999  # una muestra así de alta está recortada
MAX_SATURADAS = 1e-4  # fracción de muestras recortadas que se tolera
PICO_MINIMO_DB = -20.0
RUIDO_MAXIMO_DB = -50.0
DISTANCIA_MINIMA_DB = 25.0  # voz por encima del ruido de la sala
CANTADO_MINIMO = 0.5
_VENTANA_PYIN = 2048
_SALTO_PYIN = 512
_RE_CANCION = re.compile(r"[a-z0-9][a-z0-9_-]*")


@dataclass(frozen=True)
class Muestra:
    """El informe, los consejos de grabación y el tono cuadro a cuadro."""

    informe: Informe
    consejos: tuple[str, ...]
    tono: Tono


def leer_audio(ruta: Path) -> tuple[np.ndarray, int]:
    """WAV, FLAC, OGG o MP3 -> (canales x muestras, frecuencia)."""
    if not ruta.is_file():
        raise ErrorVoz(f"no existe el archivo {ruta.name}")
    try:
        datos, frecuencia = soundfile.read(str(ruta), dtype="float32", always_2d=True)
    except (RuntimeError, OSError) as error:
        raise ErrorVoz(f"no se pudo leer {ruta.name} como audio: {error}") from error
    return datos.T, int(frecuencia)


def analizar_muestra(audio: np.ndarray, frecuencia: int) -> Muestra:
    """Informe de la voz y consejos sobre cómo quedó grabada."""
    tono = detectar_tono(audio, frecuencia)
    senal = np.asarray(audio, dtype=np.float32)
    senal = senal.mean(axis=0) if senal.ndim == 2 else senal
    informe = informe_desde_tono(tono, senal.size / frecuencia)
    return Muestra(informe, _consejos(senal, frecuencia, tono, informe), tono)


def _db(valor: float) -> float:
    return 20 * float(np.log10(max(valor, 1e-10)))


def _niveles(
    senal: np.ndarray, frecuencia: int, tono: Tono
) -> tuple[float | None, float]:
    """(ruido de la sala, nivel de la voz) en dBFS, con cuadros alineados a pYIN."""
    escala = frecuencia / FRECUENCIA_ANALISIS
    rms = librosa.feature.rms(
        y=senal,
        frame_length=round(_VENTANA_PYIN * escala),
        hop_length=round(_SALTO_PYIN * escala),
    )[0]
    cuadros = min(rms.size, tono.sonoro.size)
    niveles = np.array([_db(v) for v in rms[:cuadros]])
    sonoro = tono.sonoro[:cuadros]
    ruido = float(np.median(niveles[~sonoro])) if (~sonoro).any() else None
    return ruido, float(np.percentile(niveles[sonoro], 90))


def _consejos(
    senal: np.ndarray, frecuencia: int, tono: Tono, informe: Informe
) -> tuple[str, ...]:
    consejos = []
    if np.mean(np.abs(senal) >= UMBRAL_SATURACION) > MAX_SATURADAS:
        consejos.append("se saturó: baja la ganancia del micrófono o aléjate un poco")
    pico = _db(float(np.abs(senal).max()))
    if pico < PICO_MINIMO_DB:
        consejos.append(
            f"el nivel está muy bajo ({pico:.0f} dBFS de pico):"
            " sube la ganancia o acércate al micrófono"
        )
    ruido, voz = _niveles(senal, frecuencia, tono)
    if ruido is not None and ruido > RUIDO_MAXIMO_DB:
        consejos.append(
            f"hay ruido de fondo ({ruido:.0f} dBFS): graba en un cuarto más"
            " silencioso, lejos de ventiladores y ventanas"
        )
    elif ruido is not None and voz - ruido < DISTANCIA_MINIMA_DB:
        consejos.append("la voz suena lejos: acércate a un palmo del micrófono")
    if informe.cantado < CANTADO_MINIMO:
        consejos.append(
            "hubo poca voz en la muestra: canta más tiempo seguido, sin pausas largas"
        )
    return tuple(consejos)


def guardar_informe(
    muestra: Muestra, ruta_audio: Path, autotune: Recomendacion | None = None
) -> Path:
    """Escribe <audio>.informe.json junto al audio, con el tono cuadro a cuadro."""
    tono = muestra.tono
    datos = {
        "archivo": ruta_audio.name,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "informe": asdict(muestra.informe),
        "autotune": asdict(autotune) if autotune else None,
        "consejos": list(muestra.consejos),
        "tono": [
            [round(float(t), 3), round(float(hz), 2)]
            for t, hz, voz in zip(tono.tiempos, tono.hz, tono.sonoro, strict=True)
            if voz
        ],
    }
    ruta = ruta_audio.with_name(f"{ruta_audio.stem}.informe.json")
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


def carpeta_de_cancion(cancion: str) -> Path:
    """canciones/<cancion>/voz, con un nombre simple como luna-negra."""
    if not _RE_CANCION.fullmatch(cancion):
        raise ErrorVoz(
            f"nombre de canción inválido {cancion!r}: usa algo como luna-negra"
        )
    return Path("canciones") / cancion / "voz"


def _grabar_con_sounddevice(
    segundos: float, frecuencia: int, dispositivo: int | None
) -> np.ndarray:
    import sounddevice

    datos = sounddevice.rec(
        round(segundos * frecuencia),
        samplerate=frecuencia,
        channels=1,
        dtype="float32",
        device=dispositivo,
    )
    sounddevice.wait()
    return datos.T


def _entradas() -> list[tuple[int, str, bool]]:
    import sounddevice

    # Windows repite cada micrófono una vez por sistema de audio (MME, WASAPI...):
    # se muestran solo los del sistema del micrófono por defecto.
    dispositivos = sounddevice.query_devices()
    defecto = sounddevice.default.device[0]
    sistema = dispositivos[defecto]["hostapi"]
    return [
        (indice, " ".join(dispositivo["name"].split()), indice == defecto)
        for indice, dispositivo in enumerate(dispositivos)
        if dispositivo["max_input_channels"] > 0 and dispositivo["hostapi"] == sistema
    ]


def listar_entradas() -> list[str]:
    """Micrófonos disponibles, uno por línea, marcando el que se usa por defecto."""
    return [
        f"{indice}: {nombre}" + (" (el que se usa por defecto)" if defecto else "")
        for indice, nombre, defecto in _entradas()
    ]


def grabar_muestra(
    carpeta: Path,
    segundos: float = SEGUNDOS_MUESTRA,
    dispositivo: int | None = None,
    avisar: Callable[[str], None] = print,
) -> Path:
    """Cuenta atrás, graba del micrófono y guarda muestra-<fecha>.wav sin pisar nada."""
    avisar(
        "Canta algo cómodo: una canción que te sepas, o de tu nota más grave"
        " a la más aguda."
    )
    for numero in range(CUENTA_ATRAS, 0, -1):
        avisar(f"{numero}…")
        time.sleep(1)
    avisar(f"Grabando {segundos:g} s…")
    try:
        audio = _grabar_con_sounddevice(segundos, FRECUENCIA_GRABACION, dispositivo)
    except Exception as error:
        raise ErrorVoz(f"no se pudo grabar del micrófono: {error}") from error
    avisar("Listo.")
    sello = datetime.now().strftime("%Y%m%d-%H%M%S")
    ruta = carpeta / f"muestra-{sello}.wav"
    numero = 2
    while ruta.exists():
        ruta = carpeta / f"muestra-{sello}-{numero}.wav"
        numero += 1
    return escribir_wav(ruta, audio, FRECUENCIA_GRABACION)
