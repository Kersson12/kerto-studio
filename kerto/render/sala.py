"""Sala y volumen: lo que hace que el beat pegue como en una disco.

- La sala es una reverb por convolución con una respuesta sintética: ruido que
  se apaga, distinto en cada lado (da ancho estéreo) y sin graves (el bombo y el
  808 quedan secos y apretados).
- El master empuja el volumen hasta un nivel de canción terminada y un
  limitador con anticipación evita que pase del techo.
Es una mezcla de escucha: la mezcla y el master de verdad llegan en la Fase 5.
"""

import numpy as np
from scipy import signal

SALA_SEGUNDOS = 1.6  # lo que tarda la sala en apagarse (-60 dB)
PRE_RETARDO = 0.02  # segundos antes de que llegue el eco
CORTE_GRAVES_HZ = 250.0  # la sala no lleva graves
CORTE_AGUDOS_HZ = 7000.0  # ni agudos chillones
BLOQUE_LIMITADOR = 64  # muestras por bloque del limitador
SUELTA_LIMITADOR = 0.08  # segundos que tarda en soltar
EMPUJE_MAXIMO_DB = 12.0


def respuesta_de_sala(
    frecuencia: int, segundos: float = SALA_SEGUNDOS, semilla: int = 0
) -> np.ndarray:
    """Respuesta de la sala (2 x muestras), con la misma energía en cada lado."""
    muestras = int(segundos * frecuencia)
    tiempo = np.arange(muestras) / frecuencia
    ruido = np.random.default_rng(semilla).standard_normal((2, muestras))
    respuesta = ruido * np.exp(-6.91 * tiempo / segundos)
    filtro = signal.butter(
        2, [CORTE_GRAVES_HZ, CORTE_AGUDOS_HZ], "bandpass", fs=frecuencia, output="sos"
    )
    respuesta = signal.sosfilt(filtro, respuesta, axis=1)
    respuesta = np.pad(respuesta, ((0, 0), (int(PRE_RETARDO * frecuencia), 0)))
    return respuesta / np.sqrt((respuesta**2).sum(axis=1, keepdims=True))


def aplicar_sala(
    envio: np.ndarray, respuesta: np.ndarray, frecuencia: int
) -> np.ndarray:
    """El eco estéreo (2 x muestras) de una señal mono, del mismo largo."""
    filtro = signal.butter(2, CORTE_GRAVES_HZ, "highpass", fs=frecuencia, output="sos")
    limpio = signal.sosfilt(filtro, envio)
    return np.stack(
        [signal.fftconvolve(limpio, lado)[: envio.size] for lado in respuesta]
    )


def limitar(audio: np.ndarray, frecuencia: int, techo_db: float = -1.0) -> np.ndarray:
    """Baja el volumen justo antes de cada pico para que nunca pase del techo."""
    techo = 10 ** (techo_db / 20)
    muestras = audio.shape[1]
    bloques = -(-muestras // BLOQUE_LIMITADOR)
    relleno = np.pad(
        np.abs(audio).max(axis=0), (0, bloques * BLOQUE_LIMITADOR - muestras)
    )
    picos = relleno.reshape(bloques, BLOQUE_LIMITADOR).max(axis=1)
    necesaria = np.minimum(1.0, techo / np.maximum(picos, 1e-12))
    # Anticipación: cada bloque ya baja lo que pide el siguiente.
    necesaria = np.minimum(necesaria, np.append(necesaria[1:], 1.0))
    soltar = 1 - np.exp(-BLOQUE_LIMITADOR / (SUELTA_LIMITADOR * frecuencia))
    ganancia = np.empty(bloques)
    actual = 1.0
    for indice, valor in enumerate(necesaria):
        actual = min(valor, actual + (1.0 - actual) * soltar)
        ganancia[indice] = actual
    centros = (np.arange(bloques) + 0.5) * BLOQUE_LIMITADOR
    curva = np.interp(np.arange(muestras), centros, ganancia)
    curva = np.minimum(curva, np.repeat(ganancia, BLOQUE_LIMITADOR)[:muestras])
    return np.clip(audio * curva, -techo, techo)


def masterizar(
    mezcla: np.ndarray,
    frecuencia: int,
    rms_objetivo_db: float = -12.0,
    techo_db: float = -1.0,
) -> np.ndarray:
    """Empuja la mezcla hasta el volumen objetivo (hasta 12 dB) y la limita."""
    rms = float(np.sqrt((mezcla**2).mean()))
    if rms == 0:
        return mezcla
    empuje = min(rms_objetivo_db - 20 * np.log10(rms), EMPUJE_MAXIMO_DB)
    limitada = limitar(mezcla * 10 ** (empuje / 20), frecuencia, techo_db)
    # Al final, el pico justo en el techo: igual de fuerte en cada render.
    return limitada * (10 ** (techo_db / 20) / float(np.abs(limitada).max()))
