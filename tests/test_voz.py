import numpy as np
import pytest

from kerto.voz.analisis import (
    ErrorVoz,
    analizar_voz,
    detectar_tono,
    hz_a_nota,
    resumir_informe,
    tonalidades_comodas,
)

SR = 22050


def voz_sintetica(notas_hz, segundos=1.0, sr=SR, cents=0.0, vibrato=0.0):
    """Tono con armónicos, como una vocal cantada; `vibrato` en cents de pico."""
    tramos = []
    for hz in notas_hz:
        t = np.arange(int(segundos * sr)) / sr
        desvio = cents + vibrato * np.sin(2 * np.pi * 5.5 * t)
        frecuencia = hz * 2 ** (desvio / 1200)
        fase = 2 * np.pi * np.cumsum(frecuencia) / sr
        tramos.append(sum(0.4 / k * np.sin(k * fase) for k in (1, 2, 3)))
    return np.concatenate(tramos).astype(np.float32)


def silencio(segundos=1.0, sr=SR):
    return np.zeros(int(segundos * sr), dtype=np.float32)


# --- Notas y cents ---


@pytest.mark.parametrize(
    ("hz", "nota", "cents"),
    [
        (440.0, "A4", 0.0),
        (445.0, "A4", 19.56),
        (261.63, "C4", 0.0),
        (98.0, "G2", 0.0),
        (466.16, "A#4", 0.0),
    ],
)
def test_hz_a_nota(hz, nota, cents):
    nombre, desvio = hz_a_nota(hz)
    assert nombre == nota
    assert desvio == pytest.approx(cents, abs=0.1)


# --- Detección de tono: menos de 5 cents de error ---


@pytest.mark.parametrize("hz", [98.0, 196.0, 261.63, 440.0, 445.0, 659.25])
def test_detecta_el_tono_con_menos_de_5_cents_de_error(hz):
    tono = detectar_tono(voz_sintetica([hz], segundos=1.5), SR)
    medido = np.median(tono.hz[tono.sonoro])
    assert abs(1200 * np.log2(medido / hz)) < 5
    assert tono.sonoro.mean() > 0.9


def test_un_la_de_440_da_la4():
    tono = detectar_tono(voz_sintetica([440.0]), SR)
    nota, cents = hz_a_nota(float(np.median(tono.hz[tono.sonoro])))
    assert nota == "A4"
    assert abs(cents) < 5


def test_funciona_con_audio_a_44100():
    tono = detectar_tono(voz_sintetica([220.0], sr=44100), 44100)
    medido = np.median(tono.hz[tono.sonoro])
    assert abs(1200 * np.log2(medido / 220.0)) < 5


def test_el_silencio_no_es_voz():
    tono = detectar_tono(silencio(), SR)
    assert not tono.sonoro.any()


def test_acepta_estereo_y_rechaza_audio_vacio():
    estereo = np.stack([voz_sintetica([330.0])] * 2)
    assert detectar_tono(estereo, SR).sonoro.mean() > 0.9
    with pytest.raises(ErrorVoz):
        detectar_tono(np.zeros(0, dtype=np.float32), SR)


# --- Informe ---


@pytest.fixture(scope="module")
def escala():
    # C3 E3 G3 C4: grave C3, aguda C4.
    return analizar_voz(voz_sintetica([130.81, 164.81, 196.0, 261.63]), SR)


def test_informe_rango(escala):
    assert escala.nota_grave == "C3"
    assert escala.nota_aguda == "C4"
    assert escala.comoda_grave in ("C3", "C#3", "D3", "D#3", "E3")
    assert escala.comoda_aguda in ("G3", "G#3", "A3", "A#3", "B3", "C4")


def test_informe_duracion_y_parte_cantada():
    audio = np.concatenate([silencio(1.0), voz_sintetica([220.0], segundos=3.0)])
    informe = analizar_voz(audio, SR)
    assert informe.segundos == pytest.approx(4.0, abs=0.01)
    assert informe.cantado == pytest.approx(0.75, abs=0.05)


def test_afinacion_y_estabilidad_de_un_tono_limpio():
    informe = analizar_voz(voz_sintetica([220.0], segundos=2.0), SR)
    assert informe.desafinacion < 3
    assert informe.temblor < 3


def test_mide_la_desafinacion_en_cents():
    informe = analizar_voz(voz_sintetica([220.0], segundos=2.0, cents=30), SR)
    assert informe.desafinacion == pytest.approx(30, abs=4)


def test_el_vibrato_baja_la_estabilidad():
    limpio = analizar_voz(voz_sintetica([220.0], segundos=2.0), SR)
    con_vibrato = analizar_voz(voz_sintetica([220.0], segundos=2.0, vibrato=40), SR)
    assert con_vibrato.temblor > limpio.temblor + 10


def test_temblor_de_cuadros_sueltos_es_cero():
    from kerto.voz.analisis import _temblor

    assert _temblor(np.array([60.0])) == 0.0
    assert _temblor(np.array([60.0, 62.0, 64.0])) == 0.0


def test_informe_sin_voz_explica_el_error():
    with pytest.raises(ErrorVoz, match="voz"):
        analizar_voz(silencio(2.0), SR)


# --- Tonalidades cómodas ---


@pytest.mark.parametrize(
    ("centro", "primera"), [(57, "Am"), (52, "Em"), (64, "Em"), (61, "C#m")]
)
def test_tonalidad_mas_comoda_tiene_la_tonica_en_el_centro_de_la_voz(centro, primera):
    assert tonalidades_comodas(centro)[0] == primera


def test_tonalidades_comodas_da_tres_en_mayor_o_menor():
    assert tonalidades_comodas(57) == ("Am", "Bbm", "G#m")
    assert tonalidades_comodas(60, modo="mayor") == ("C", "Db", "B")


# --- Resumen corto ---


def test_resumen_de_cuatro_lineas(escala):
    lineas = resumir_informe(escala).splitlines()
    assert len(lineas) == 4
    assert lineas[0].startswith("Voz: 4.0 s")
    assert "C3–C4" in lineas[1]
    assert "cents" in lineas[2]
    assert lineas[3].startswith("Tonalidades cómodas")
