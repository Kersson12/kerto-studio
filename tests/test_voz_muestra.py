import json

import numpy as np
import pytest

from kerto.cli import main
from kerto.render.wav import escribir_wav
from kerto.voz.analisis import ErrorVoz
from kerto.voz.muestra import analizar_muestra, guardar_informe, leer_audio

SR = 22050


def voz(hz=220.0, segundos=2.0, pico=0.5, sr=SR):
    t = np.arange(int(segundos * sr)) / sr
    senal = sum(0.4 / k * np.sin(2 * np.pi * k * hz * t) for k in (1, 2, 3))
    return (senal / np.abs(senal).max() * pico).astype(np.float32)


def con_silencio(senal, segundos=1.0, sr=SR):
    return np.concatenate([np.zeros(int(segundos * sr), np.float32), senal])


# --- Leer audio ---


def test_leer_audio_devuelve_canales_por_muestras(tmp_path):
    original = np.stack([voz(), voz(pico=0.25)])
    ruta = escribir_wav(tmp_path / "toma.wav", original, SR)
    audio, frecuencia = leer_audio(ruta)
    assert frecuencia == SR
    assert audio.shape == original.shape
    assert np.allclose(audio, original, atol=1e-5)


@pytest.mark.parametrize("contenido", [None, b"esto no es audio"])
def test_leer_audio_inexistente_o_roto(tmp_path, contenido):
    ruta = tmp_path / "toma.wav"
    if contenido is not None:
        ruta.write_bytes(contenido)
    with pytest.raises(ErrorVoz, match="toma.wav"):
        leer_audio(ruta)


# --- Consejos de grabación ---


def test_grabacion_limpia_no_tiene_consejos():
    muestra = analizar_muestra(con_silencio(voz()), SR)
    assert muestra.consejos == ()
    assert muestra.informe.nota_grave == "A3"


def test_saturacion():
    saturada = np.clip(con_silencio(voz(pico=3.0)), -1, 1)
    consejos = analizar_muestra(saturada, SR).consejos
    assert any("satur" in c for c in consejos)


def test_nivel_bajo():
    consejos = analizar_muestra(con_silencio(voz(pico=0.03)), SR).consejos
    assert any("bajo" in c for c in consejos)


def test_ruido_de_fondo():
    azar = np.random.default_rng(1)
    senal = con_silencio(voz())
    ruidosa = senal + azar.normal(0, 0.03, senal.size).astype(np.float32)
    consejos = analizar_muestra(ruidosa, SR).consejos
    assert any("ruido" in c for c in consejos)


def test_poca_voz():
    poca = con_silencio(voz(segundos=0.8), segundos=3.0)
    consejos = analizar_muestra(poca, SR).consejos
    assert any("más tiempo" in c for c in consejos)


# --- JSON con el análisis completo ---


def test_guardar_informe_json(tmp_path):
    muestra = analizar_muestra(con_silencio(voz()), SR)
    ruta = guardar_informe(muestra, tmp_path / "toma.wav")
    assert ruta.name == "toma.informe.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["archivo"] == "toma.wav"
    assert datos["informe"]["nota_grave"] == "A3"
    assert datos["consejos"] == []
    assert len(datos["tono"]) == int(muestra.tono.sonoro.sum())
    tiempo, hz = datos["tono"][0]
    assert 0.9 <= tiempo < 1.2
    assert hz == pytest.approx(220, abs=2)


# --- kerto voz ---


def test_voz_analizar_un_wav(tmp_path, capsys):
    ruta = escribir_wav(tmp_path / "toma.wav", con_silencio(voz())[None, :], SR)
    assert main(["voz", "analizar", str(ruta)]) == 0
    lineas = capsys.readouterr().out.strip().splitlines()
    assert lineas[0].startswith("Voz: 3.0 s")
    assert lineas[4].startswith("Autotune: sin autotune · ")
    assert lineas[5] == "Consejos: la grabación está limpia"
    assert lineas[6].endswith("toma.informe.json")
    datos = json.loads((tmp_path / "toma.informe.json").read_text(encoding="utf-8"))
    assert datos["autotune"]["nivel"] == "ninguno"


def test_voz_analizar_con_estilo_marcado(tmp_path, capsys):
    ruta = escribir_wav(tmp_path / "toma.wav", con_silencio(voz())[None, :], SR)
    assert main(["voz", "analizar", str(ruta), "--estilo", "marcado"]) == 0
    assert "Autotune: corrección marcada" in capsys.readouterr().out


def test_voz_analizar_explica_los_errores(tmp_path, capsys):
    assert main(["voz", "analizar", str(tmp_path / "no.wav")]) == 1
    assert "no.wav" in capsys.readouterr().err
    callado = escribir_wav(tmp_path / "callado.wav", np.zeros((1, SR)), SR)
    assert main(["voz", "analizar", str(callado)]) == 1
    assert "no se detectó voz" in capsys.readouterr().err


def test_voz_grabar_guarda_la_muestra_y_la_analiza(tmp_path, capsys, monkeypatch):
    pedidos = []

    def grabar_falso(segundos, frecuencia, dispositivo, guia=None):
        pedidos.append((segundos, frecuencia, dispositivo))
        return con_silencio(voz(sr=frecuencia), sr=frecuencia)[None, :]

    monkeypatch.setattr("kerto.voz.muestra._grabar_con_sounddevice", grabar_falso)
    monkeypatch.setattr("kerto.voz.muestra.time.sleep", lambda _: None)
    salida = tmp_path / "voz"
    codigo = main(["voz", "grabar", "--segundos", "3", "--salida", str(salida)])
    assert codigo == 0
    assert pedidos == [(3.0, 44100, None)]
    [wav] = salida.glob("muestra-*.wav")
    assert (salida / f"{wav.stem}.informe.json").is_file()
    salida_texto = capsys.readouterr().out
    assert "Grabando 3 s" in salida_texto
    assert "Voz: 3.0 s" in salida_texto


def test_voz_grabar_en_la_carpeta_de_la_cancion(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "kerto.voz.muestra._grabar_con_sounddevice",
        lambda s, f, d, g=None: con_silencio(voz(sr=f), sr=f)[None, :],
    )
    monkeypatch.setattr("kerto.voz.muestra.time.sleep", lambda _: None)
    assert main(["voz", "grabar", "--cancion", "luna-negra"]) == 0
    assert len(list((tmp_path / "canciones/luna-negra/voz").glob("*.wav"))) == 1
    assert main(["voz", "grabar", "--cancion", "../fuera"]) == 1


def test_voz_dispositivos(capsys, monkeypatch):
    monkeypatch.setattr(
        "kerto.voz.muestra._entradas",
        lambda: [(1, "Micrófono USB", True), (3, "Mezcla estéreo", False)],
    )
    assert main(["voz", "dispositivos"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "1: Micrófono USB (el que se usa por defecto)",
        "3: Mezcla estéreo",
    ]


def test_voz_lejos_del_microfono():
    azar = np.random.default_rng(2)
    senal = con_silencio(voz(pico=0.01))
    lejana = senal + azar.normal(0, 0.0005, senal.size).astype(np.float32)
    consejos = analizar_muestra(lejana, SR).consejos
    assert any("lejos" in c for c in consejos)


def test_voz_grabar_sin_microfono(tmp_path, capsys, monkeypatch):
    def sin_microfono(segundos, frecuencia, dispositivo):
        raise OSError("PortAudio library not found")

    monkeypatch.setattr("kerto.voz.muestra._grabar_con_sounddevice", sin_microfono)
    monkeypatch.setattr("kerto.voz.muestra.time.sleep", lambda _: None)
    assert main(["voz", "grabar", "--salida", str(tmp_path)]) == 1
    assert "micrófono" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_grabar_dos_veces_en_el_mismo_segundo_no_pisa(tmp_path, monkeypatch):
    from datetime import datetime

    from kerto.voz import muestra

    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 8, 20, 15, 0)

    monkeypatch.setattr(muestra, "datetime", Reloj)
    monkeypatch.setattr(muestra.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        muestra, "_grabar_con_sounddevice", lambda s, f, d, g=None: voz(sr=f)[None, :]
    )
    rutas = [
        muestra.grabar_muestra(tmp_path, 1, avisar=lambda _: None) for _ in range(3)
    ]
    assert [r.name for r in rutas] == [
        "muestra-20261108-201500.wav",
        "muestra-20261108-201500-2.wav",
        "muestra-20261108-201500-3.wav",
    ]


def test_funciones_de_sounddevice(monkeypatch):
    import sys
    import types

    from kerto.voz import muestra

    falso = types.ModuleType("sounddevice")
    falso.rec = lambda n, samplerate, channels, dtype, device: np.zeros(
        (n, channels), dtype
    )
    falso.wait = lambda: None
    falso.default = types.SimpleNamespace(device=(1, 4))
    falso.query_devices = lambda: [
        {"name": "Altavoces", "max_input_channels": 0, "hostapi": 0},
        {"name": "Micrófono\n (USB)", "max_input_channels": 1, "hostapi": 0},
        {"name": "Micrófono (USB)", "max_input_channels": 1, "hostapi": 1},
    ]
    monkeypatch.setitem(sys.modules, "sounddevice", falso)
    assert muestra._grabar_con_sounddevice(0.5, 1000, None).shape == (1, 500)
    assert muestra.listar_entradas() == [
        "1: Micrófono (USB) (el que se usa por defecto)"
    ]


# --- Varias tomas ---


def tomas_en(carpeta, *tomas):
    carpeta.mkdir(parents=True, exist_ok=True)
    return [
        escribir_wav(carpeta / f"toma-{n}.wav", np.asarray(audio)[None, :], SR)
        for n, audio in enumerate(tomas, 1)
    ]


def test_voz_analizar_varias_tomas_las_combina(tmp_path, capsys):
    rutas = tomas_en(tmp_path, con_silencio(voz(220.0)), con_silencio(voz(261.63)))
    assert main(["voz", "analizar", *map(str, rutas)]) == 0
    lineas = capsys.readouterr().out.strip().splitlines()
    assert lineas[0].startswith("Tomas: 2 · centro de A3 a C4 · nota aguda de A3 a C4")
    assert lineas[1].startswith("Voz: 6.0 s")
    assert "Rango: A3–C4" in lineas[2]
    assert lineas[5].startswith("Autotune: ")
    assert lineas[7].endswith("tomas.informe.json")
    datos = json.loads((tmp_path / "tomas.informe.json").read_text(encoding="utf-8"))
    assert datos["archivos"] == ["toma-1.wav", "toma-2.wav"]
    assert [t["informe"]["centro"] for t in datos["tomas"]] == ["A3", "C4"]
    assert (tmp_path / "toma-1.informe.json").is_file()


def test_voz_analizar_todas_las_tomas_de_la_cancion(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tomas_en(tmp_path / "canciones/luna/voz", con_silencio(voz()), con_silencio(voz()))
    assert main(["voz", "analizar", "--cancion", "luna"]) == 0
    assert capsys.readouterr().out.startswith("Tomas: 2 ")
    assert main(["voz", "analizar", "--cancion", "vacia"]) == 1
    assert "no hay tomas" in capsys.readouterr().err
    assert main(["voz", "analizar"]) == 1


def test_consejos_agrupados_y_tomas_descartadas(tmp_path, capsys):
    saturada = np.clip(con_silencio(voz(pico=3.0)), -1, 1)
    rutas = tomas_en(tmp_path, saturada, saturada, np.zeros(SR, np.float32))
    assert main(["voz", "analizar", *map(str, rutas)]) == 0
    salida = capsys.readouterr().out
    assert salida.startswith("Tomas: 2 ")
    assert (
        "se saturó: baja la ganancia del micrófono o aléjate un poco (2 de 2 tomas)"
        in salida
    )
    assert "toma-3.wav: no se detectó voz" in salida


def test_ninguna_toma_sirve(tmp_path, capsys):
    rutas = tomas_en(tmp_path, np.zeros(SR, np.float32), np.zeros(SR, np.float32))
    assert main(["voz", "analizar", *map(str, rutas)]) == 1
    assert "ninguna toma" in capsys.readouterr().err


# --- Grabar con el beat en los audífonos ---


def test_voz_grabar_con_beat(tmp_path, capsys, monkeypatch):
    beat = escribir_wav(tmp_path / "beat.wav", np.full((2, 22050), 0.1), 22050)
    guias = []

    def grabar_falso(segundos, frecuencia, dispositivo, guia=None):
        guias.append(guia)
        return con_silencio(voz(sr=frecuencia), sr=frecuencia)[None, :]

    monkeypatch.setattr("kerto.voz.muestra._grabar_con_sounddevice", grabar_falso)
    monkeypatch.setattr("kerto.voz.muestra.time.sleep", lambda _: None)
    salida = tmp_path / "voz"
    argumentos = ["voz", "grabar", "--segundos", "3", "--salida", str(salida)]
    assert main([*argumentos, "--con-beat", str(beat)]) == 0
    [guia] = guias
    assert guia.shape == (3 * 44100, 2)
    assert "audífonos" in capsys.readouterr().out
    [informe] = salida.glob("*.informe.json")
    assert json.loads(informe.read_text(encoding="utf-8"))["referencia"] == "beat.wav"
    assert main([*argumentos, "--con-beat", str(tmp_path / "no.wav")]) == 1


def test_reanalizar_conserva_la_referencia(tmp_path):
    [ruta] = tomas_en(tmp_path, con_silencio(voz()))
    muestra = analizar_muestra(*leer_audio(ruta))
    guardar_informe(muestra, ruta, referencia="beat.wav")
    json_ruta = guardar_informe(muestra, ruta)
    assert json.loads(json_ruta.read_text(encoding="utf-8"))["referencia"] == "beat.wav"


def test_playrec_con_la_guia(monkeypatch):
    import sys
    import types

    from kerto.voz import muestra

    llamadas = []
    falso = types.ModuleType("sounddevice")
    falso.playrec = lambda datos, samplerate, channels, dtype, device: (
        llamadas.append(device) or np.zeros((len(datos), channels), dtype)
    )
    falso.wait = lambda: None
    monkeypatch.setitem(sys.modules, "sounddevice", falso)
    guia = np.zeros((1000, 2), np.float32)
    assert muestra._grabar_con_sounddevice(1, 1000, 3, guia).shape == (1, 1000)
    assert muestra._grabar_con_sounddevice(1, 1000, None, guia).shape == (1, 1000)
    assert llamadas == [(3, None), None]


def test_nombre_de_la_salida_sin_portaudio(monkeypatch):
    import sys

    from kerto.voz import muestra

    monkeypatch.setitem(sys.modules, "sounddevice", None)
    assert muestra._nombre_salida() == "la salida de audio por defecto"


# --- Probar el nivel del micrófono ---


@pytest.mark.parametrize(
    ("pico", "palabra"),
    [(0.02, "sube"), (0.3, "bien"), (3.0, "baja")],
)
def test_diagnostico_de_nivel(pico, palabra):
    from kerto.voz.muestra import diagnosticar_nivel

    audio = np.clip(voz(pico=pico, segundos=3.0), -1, 1)
    nivel = diagnosticar_nivel(audio, SR)
    assert palabra in nivel.consejo.lower()
    assert nivel.bien == (palabra == "bien")


def test_diagnostico_de_nivel_sin_voz():
    from kerto.voz.muestra import diagnosticar_nivel

    nivel = diagnosticar_nivel(np.zeros(SR * 2, np.float32), SR)
    assert not nivel.bien
    assert "no llegó" in nivel.consejo


def test_voz_probar_no_guarda_nada(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "kerto.voz.muestra._grabar_con_sounddevice",
        lambda s, f, d, g=None: voz(pico=0.3, segundos=s, sr=f)[None, :],
    )
    monkeypatch.setattr("kerto.voz.muestra.time.sleep", lambda _: None)
    assert main(["voz", "probar"]) == 0
    salida = capsys.readouterr().out
    assert "Nivel: " in salida and "Bien" in salida
    assert list(tmp_path.iterdir()) == []


def test_voz_probar_sin_microfono(capsys, monkeypatch):
    def sin_microfono(segundos, frecuencia, dispositivo, guia=None):
        raise OSError("sin micrófono")

    monkeypatch.setattr("kerto.voz.muestra._grabar_con_sounddevice", sin_microfono)
    monkeypatch.setattr("kerto.voz.muestra.time.sleep", lambda _: None)
    assert main(["voz", "probar"]) == 1
    assert "micrófono" in capsys.readouterr().err
