from fractions import Fraction

import mido
import pretty_midi
import pytest

from kerto.midi import CANAL_BATERIA, PULSOS_POR_NEGRA, exportar_midi, resumir_midi
from kerto.ritmos.motor import Beat, Nota, Pista, crear_beat
from kerto.ritmos.pack import cargar_pack

R = Fraction


@pytest.fixture
def beat():
    bombo = Pista(
        "bombo",
        True,
        None,
        (Nota(R(0), R(1, 16), 36, 100), Nota(R(1, 4), R(1, 16), 36, 120)),
    )
    bajo = Pista(
        "808",
        False,
        38,
        (Nota(R(0), R(3, 16), 33, 120), Nota(R(3, 16), R(1, 4), 33, 90)),
    )
    return Beat("prueba", "uno", 95, "Am", "4/4", 1, ("Am",), (bombo, bajo))


@pytest.fixture
def archivo(beat, tmp_path):
    return exportar_midi(beat, tmp_path / "beats" / "prueba.mid")


def mensajes(pista, tipo):
    tick, resultado = 0, []
    for mensaje in pista:
        tick += mensaje.time
        if mensaje.type == tipo:
            resultado.append((tick, mensaje))
    return resultado


def test_crea_el_archivo_y_sus_carpetas(archivo):
    assert archivo.is_file()
    assert archivo.name == "prueba.mid"


def test_una_pista_por_instrumento_mas_la_del_tempo(archivo):
    midi = mido.MidiFile(archivo)
    assert midi.type == 1
    assert midi.ticks_per_beat == PULSOS_POR_NEGRA
    nombres = [p.name for p in midi.tracks]
    assert nombres == ["Kerto · prueba · uno", "bombo", "808"]


def test_tempo_y_compas_en_la_primera_pista(archivo):
    conductor = mido.MidiFile(archivo).tracks[0]
    [(_, tempo)] = mensajes(conductor, "set_tempo")
    [(_, compas)] = mensajes(conductor, "time_signature")
    assert tempo.tempo == mido.bpm2tempo(95)
    assert (compas.numerator, compas.denominator) == (4, 4)


def test_bateria_en_el_canal_10_y_808_con_su_programa(archivo):
    _, bombo, bajo = mido.MidiFile(archivo).tracks
    assert {m.channel for _, m in mensajes(bombo, "note_on")} == {CANAL_BATERIA}
    [(_, programa)] = mensajes(bajo, "program_change")
    assert (programa.program, programa.channel) == (38, 0)
    assert mensajes(bombo, "program_change") == []


def test_notas_en_pulsos_exactos(archivo):
    _, bombo, bajo = mido.MidiFile(archivo).tracks
    assert [(t, m.note, m.velocity) for t, m in mensajes(bombo, "note_on")] == [
        (0, 36, 100),
        (480, 36, 120),
    ]
    assert [t for t, _ in mensajes(bajo, "note_off")] == [360, 840]


def test_note_off_antes_que_note_on_en_el_mismo_pulso(archivo):
    tick, en_360 = 0, []
    for mensaje in mido.MidiFile(archivo).tracks[2]:
        tick += mensaje.time
        if tick == 360 and mensaje.type in ("note_on", "note_off"):
            en_360.append(mensaje.type)
    assert en_360 == ["note_off", "note_on"]


def test_cada_pista_dura_lo_mismo_que_el_beat(archivo):
    for pista in mido.MidiFile(archivo).tracks:
        [(fin, _)] = mensajes(pista, "end_of_track")
        assert fin == 4 * PULSOS_POR_NEGRA


def test_pretty_midi_lee_instrumentos_y_segundos(archivo):
    midi = pretty_midi.PrettyMIDI(str(archivo))
    bombo, bajo = midi.instruments
    assert (bombo.name, bombo.is_drum) == ("bombo", True)
    assert (bajo.name, bajo.is_drum, bajo.program) == ("808", False, 38)
    assert bajo.notes[0].end == pytest.approx(0.75 * 60 / 95)


def test_resumen_corto(archivo):
    assert resumir_midi(archivo) == "2 pistas (bombo 2, 808 2 notas) · 2.5 s"


def test_beat_del_pack_de_reggaeton(tmp_path):
    beat = crear_beat(cargar_pack("reggaeton"), compases=8, semilla=1)
    archivo = exportar_midi(beat, tmp_path / "reggaeton.mid")
    midi = mido.MidiFile(archivo)
    assert [p.name for p in midi.tracks[1:]] == [
        "bombo",
        "caja",
        "hihat",
        "percusion",
        "808",
    ]
    assert midi.length == pytest.approx(8 * 4 * 60 / 95)
