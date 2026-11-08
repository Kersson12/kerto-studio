"""Escritura de WAV PCM de 24 bits, sin librerías extra."""

import wave
from pathlib import Path

import numpy as np

MAXIMO_24 = 2**23 - 1


def escribir_wav(ruta: Path, audio: np.ndarray, frecuencia: int) -> Path:
    """Escribe audio (canales x muestras, de -1 a 1) y devuelve la ruta."""
    if audio.ndim != 2:
        raise ValueError("el audio debe tener forma (canales, muestras)")
    enteros = np.round(np.clip(audio, -1.0, 1.0) * MAXIMO_24).astype("<i4")
    intercalado = np.ascontiguousarray(enteros.T).reshape(-1)
    # Cada muestra de 32 bits en little endian: sus 3 primeros bytes son los 24 bits.
    datos = intercalado.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(ruta), "wb") as archivo:
        archivo.setnchannels(audio.shape[0])
        archivo.setsampwidth(3)
        archivo.setframerate(frecuencia)
        archivo.writeframes(datos)
    return ruta
