import pytest

from kerto import __version__
from kerto.cli import main


def test_version_muestra_nombre_y_version(capsys):
    with pytest.raises(SystemExit) as salida:
        main(["--version"])
    assert salida.value.code == 0
    assert capsys.readouterr().out.strip() == f"kerto {__version__}"


def test_sin_argumentos_muestra_la_ayuda(capsys):
    assert main([]) == 0
    salida = capsys.readouterr().out
    assert "kerto" in salida and "--version" in salida


def test_notacion_valida_y_resume(capsys):
    assert main(["notacion", "C4:1/2 E4:1/2 | G4:1"]) == 0
    assert capsys.readouterr().out.strip() == (
        "OK · 3 eventos · 2 compases de 4/4 · rango C4–G4"
    )


def test_notacion_acepta_varios_argumentos_y_otro_compas(capsys):
    assert main(["notacion", "C4:1/2", "E4:1/4", "|", "G4:3/4", "--compas", "3/4"]) == 0
    assert "2 compases de 3/4" in capsys.readouterr().out


def test_notacion_explica_el_error_y_sale_con_1(capsys):
    assert main(["notacion", "C4:1 | E4:1/2"]) == 1
    salida = capsys.readouterr()
    assert salida.out == ""
    assert "compás 2" in salida.err


# --- kerto beat ---


def beat(tmp_path, *extra):
    base = ["beat", "--genero", "reggaeton", "--bpm", "95", "--tonalidad", "Am"]
    return main([*base, "--salida", str(tmp_path / "beats"), *extra])


def test_beat_crea_midi_y_wav_de_cada_variacion(tmp_path, capsys):
    assert beat(tmp_path, "--compases", "8", "--variaciones", "3", "--sin-surge") == 0
    nombres = sorted(p.name for p in (tmp_path / "beats").iterdir())
    assert nombres == [
        "beat-1-clasico.mid",
        "beat-1-clasico.wav",
        "beat-2-movido.mid",
        "beat-2-movido.wav",
        "beat-3-oscuro.mid",
        "beat-3-oscuro.wav",
    ]
    lineas = capsys.readouterr().out.strip().splitlines()
    assert len(lineas) == 3
    archivos, genero, tempo = lineas
    assert archivos.startswith("Archivos: 6 en ")
    assert "beat-1-clasico, beat-2-movido, beat-3-oscuro (.mid y .wav)" in archivos
    assert genero.startswith("Género: reggaeton · 3 variaciones · 8 compases de 4/4")
    assert "Faust (bombo, caja, hihat, percusion, 808)" in genero
    assert tempo == (
        "BPM: 95 · Tonalidad: Am · acordes: Am F C G / Am G F G / Am F Dm E"
    )


def test_beat_solo_midi_y_valores_del_pack(tmp_path, capsys):
    assert (
        main(["beat", "--salida", str(tmp_path), "--sin-wav", "--variaciones", "1"])
        == 0
    )
    assert [p.name for p in tmp_path.iterdir()] == ["beat-1-clasico.mid"]
    archivos, genero, tempo = capsys.readouterr().out.strip().splitlines()
    assert archivos.endswith("(.mid)")
    assert genero.endswith("sonido: solo MIDI")
    assert tempo.startswith("BPM: 95 · Tonalidad: Am")


def test_beat_no_pisa_archivos_sin_permiso(tmp_path, capsys):
    destino = tmp_path / "beats" / "beat-1-clasico.mid"
    destino.parent.mkdir()
    destino.write_bytes(b"mio")
    assert beat(tmp_path, "--variaciones", "1", "--sin-wav") == 1
    assert "--sobrescribir" in capsys.readouterr().err
    assert destino.read_bytes() == b"mio"
    assert beat(tmp_path, "--variaciones", "1", "--sin-wav", "--sobrescribir") == 0
    assert destino.read_bytes() != b"mio"


@pytest.mark.parametrize(
    ("extra", "mensaje"),
    [
        (["--variaciones", "5"], "3 variaciones"),
        (["--variaciones", "0"], "3 variaciones"),
        (["--genero", "cumbia"], "reggaeton"),
        (["--bpm", "400"], "bpm"),
        (["--tonalidad", "H"], "tonalidad"),
        (["--compases", "0"], "compases"),
    ],
)
def test_beat_explica_los_errores(tmp_path, capsys, extra, mensaje):
    assert beat(tmp_path, "--sin-wav", *extra) == 1
    assert mensaje in capsys.readouterr().err
    assert not (tmp_path / "beats").exists()
