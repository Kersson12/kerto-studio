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
        "beat-1-clasico-Am.mid",
        "beat-1-clasico-Am.wav",
        "beat-2-movido-Am.mid",
        "beat-2-movido-Am.wav",
        "beat-3-oscuro-Am.mid",
        "beat-3-oscuro-Am.wav",
    ]
    lineas = capsys.readouterr().out.strip().splitlines()
    assert len(lineas) == 3
    archivos, genero, tempo = lineas
    assert archivos.startswith("Archivos: 6 en ")
    assert (
        "beat-1-clasico-Am, beat-2-movido-Am, beat-3-oscuro-Am (.mid y .wav)"
        in archivos
    )
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
    assert [p.name for p in tmp_path.iterdir()] == ["beat-1-clasico-Am.mid"]
    archivos, genero, tempo = capsys.readouterr().out.strip().splitlines()
    assert archivos.endswith("(.mid)")
    assert genero.endswith("sonido: solo MIDI")
    assert tempo.startswith("BPM: 95 · Tonalidad: Am")


def test_beat_no_pisa_archivos_sin_permiso(tmp_path, capsys):
    destino = tmp_path / "beats" / "beat-1-clasico-Am.mid"
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
        (["--variacion", "salsa"], "clasico, movido, oscuro"),
    ],
)
def test_beat_explica_los_errores(tmp_path, capsys, extra, mensaje):
    assert beat(tmp_path, "--sin-wav", *extra) == 1
    assert mensaje in capsys.readouterr().err
    assert not (tmp_path / "beats").exists()


def test_beat_transpone_una_sola_variacion(tmp_path, capsys):
    import mido

    def notas(archivo):
        midi = mido.MidiFile(archivo)
        return {
            pista.name: [m.note for m in pista if m.type == "note_on"]
            for pista in midi.tracks[1:]
        }

    assert beat(tmp_path, "--variacion", "movido", "--sin-wav") == 0
    capsys.readouterr()
    assert (
        beat(tmp_path, "--variacion", "movido", "--tonalidad", "Cm", "--sin-wav") == 0
    )
    _, genero, tempo = capsys.readouterr().out.strip().splitlines()
    assert "· 1 variación ·" in genero
    assert tempo == "BPM: 95 · Tonalidad: Cm · acordes: Cm Bb Ab Bb"
    en_am = notas(tmp_path / "beats" / "beat-2-movido-Am.mid")
    en_cm = notas(tmp_path / "beats" / "beat-2-movido-Cm.mid")
    assert [n + 3 for n in en_am["808"]] == en_cm["808"]
    for instrumento in ("bombo", "caja", "hihat", "percusion"):
        assert en_am[instrumento] == en_cm[instrumento]
