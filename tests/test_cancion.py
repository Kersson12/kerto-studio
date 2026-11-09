import json

import numpy as np
import pytest

from kerto.cancion.archivo import ErrorCancion, beat_base, leer_cancion
from kerto.cli import main
from kerto.render.wav import escribir_wav


@pytest.fixture
def cancion(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    carpeta = tmp_path / "canciones" / "luna"
    (carpeta / "beats").mkdir(parents=True)
    escribir_wav(carpeta / "beats" / "base.wav", np.full((2, 4410), 0.1), 44100)
    (carpeta / "cancion.yaml").write_text(
        "nombre: Luna\nbase:\n  variacion: movido\n  wav: beats/base.wav\n",
        encoding="utf-8",
    )
    return carpeta


def test_leer_cancion_y_su_beat_base(cancion):
    assert leer_cancion("luna")["nombre"] == "Luna"
    assert beat_base("luna").resolve() == (cancion / "beats" / "base.wav").resolve()


@pytest.mark.parametrize(
    ("yaml", "mensaje"),
    [
        ("nombre: Luna\n", "base"),
        ("base: {variacion: movido}\n", "base"),
        ("base: {wav: beats/no.wav}\n", "no.wav"),
        ("- una lista\n", "mapa"),
    ],
)
def test_beat_base_explica_lo_que_falta(cancion, yaml, mensaje):
    (cancion / "cancion.yaml").write_text(yaml, encoding="utf-8")
    with pytest.raises(ErrorCancion, match=mensaje):
        beat_base("luna")


def test_cancion_inexistente_o_nombre_invalido(cancion):
    with pytest.raises(ErrorCancion, match="no existe"):
        leer_cancion("sol")
    with pytest.raises(ErrorCancion, match="inválido"):
        leer_cancion("../luna")


def test_grabar_con_el_beat_base_de_la_cancion(cancion, capsys, monkeypatch):
    t = np.arange(44100 * 3) / 44100
    voz = (0.4 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    guias = []

    def grabar_falso(segundos, frecuencia, dispositivo, guia=None):
        guias.append(guia)
        return np.concatenate([np.zeros(44100, np.float32), voz])[None, :]

    monkeypatch.setattr("kerto.voz.muestra._grabar_con_sounddevice", grabar_falso)
    monkeypatch.setattr("kerto.voz.muestra.time.sleep", lambda _: None)
    argumentos = ["voz", "grabar", "--cancion", "luna", "--segundos", "4"]
    assert main([*argumentos, "--con-beat"]) == 0
    assert guias[0].shape == (4 * 44100, 2)
    [informe] = (cancion / "voz").glob("*.informe.json")
    assert json.loads(informe.read_text(encoding="utf-8"))["referencia"] == "base.wav"
    assert "El beat suena por:" in capsys.readouterr().out


def test_con_beat_sin_cancion_explica_el_error(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["voz", "grabar", "--con-beat"]) == 1
    assert "--cancion" in capsys.readouterr().err
