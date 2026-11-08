import pytest

from kerto.teoria.acordes import (
    Acorde,
    Tonalidad,
    parse_acorde,
    parse_tonalidad,
    progresion,
)
from kerto.teoria.escalas import ErrorTeoria, clase_de_altura, escala

# --- Alturas ---


@pytest.mark.parametrize(
    ("nombre", "clase"),
    [
        ("C", 0),
        ("C#", 1),
        ("Db", 1),
        ("Bb", 10),
        ("B#", 0),
        ("Cb", 11),
        ("F##", 7),
        ("Ebb", 2),
    ],
)
def test_clase_de_altura(nombre, clase):
    assert clase_de_altura(nombre) == clase


@pytest.mark.parametrize("nombre", ["", "H", "c", "C###", "Cb#", "C4"])
def test_clase_de_altura_rechaza_nombres_invalidos(nombre):
    with pytest.raises(ErrorTeoria):
        clase_de_altura(nombre)


# --- Escalas ---


@pytest.mark.parametrize(
    ("tonica", "modo", "notas"),
    [
        ("A", "menor", "A B C D E F G"),
        ("C", "mayor", "C D E F G A B"),
        ("F", "mayor", "F G A Bb C D E"),
        ("E", "menor", "E F# G A B C D"),
        ("Bb", "menor", "Bb C Db Eb F Gb Ab"),
        ("A", "menor_armonica", "A B C D E F G#"),
        ("E", "frigia", "E F G A B C D"),
        ("D", "dorica", "D E F G A B C"),
        ("A", "pentatonica_menor", "A C D E G"),
        ("C", "pentatonica_mayor", "C D E G A"),
    ],
)
def test_escala_bien_escrita(tonica, modo, notas):
    assert escala(tonica, modo) == tuple(notas.split())


def test_la_menor_contiene_la_si_do_re_mi_fa_sol():
    assert set(escala("A", "menor")) == {"A", "B", "C", "D", "E", "F", "G"}


@pytest.mark.parametrize(
    ("tonica", "modo"), [("A", "lidia_dorada"), ("H", "menor"), ("G##", "mayor")]
)
def test_escala_rechaza_modo_o_tonica_invalidos(tonica, modo):
    with pytest.raises(ErrorTeoria):
        escala(tonica, modo)


# --- Acordes por cifrado ---


@pytest.mark.parametrize(
    ("cifrado", "notas"),
    [
        ("Am", "A C E"),
        ("F", "F A C"),
        ("G7", "G B D F"),
        ("Bdim", "B D F"),
        ("Cmaj7", "C E G B"),
        ("Ebm", "Eb Gb Bb"),
        ("F#m7", "F# A C# E"),
        ("Caug", "C E G#"),
    ],
)
def test_parse_acorde_y_sus_notas(cifrado, notas):
    acorde = parse_acorde(cifrado)
    assert acorde.notas == tuple(notas.split())
    assert str(acorde) == cifrado


@pytest.mark.parametrize("cifrado", ["", "H", "Amaj9", "am", "A m"])
def test_parse_acorde_rechaza_cifrados_invalidos(cifrado):
    with pytest.raises(ErrorTeoria):
        parse_acorde(cifrado)


def test_acorde_en_midi_desde_su_octava():
    assert Acorde("A", "m").midi(octava=3) == (57, 60, 64)
    assert Acorde("C").midi(octava=4) == (60, 64, 67)
    assert Acorde("Cb").midi(octava=4) == (59, 63, 66)


def test_acorde_valida_raiz_y_calidad():
    with pytest.raises(ErrorTeoria):
        Acorde("H")
    with pytest.raises(ErrorTeoria):
        Acorde("A", "sus9")


# --- Tonalidades y grados ---


@pytest.mark.parametrize(
    ("texto", "tonica", "modo"),
    [
        ("Am", "A", "menor"),
        ("C", "C", "mayor"),
        ("F#m", "F#", "menor"),
        ("Bb", "Bb", "mayor"),
    ],
)
def test_parse_tonalidad(texto, tonica, modo):
    tonalidad = parse_tonalidad(texto)
    assert tonalidad == Tonalidad(tonica, modo)
    assert str(tonalidad) == texto


@pytest.mark.parametrize("texto", ["", "H", "Amm", "am", "A menor"])
def test_parse_tonalidad_rechaza_texto_invalido(texto):
    with pytest.raises(ErrorTeoria):
        parse_tonalidad(texto)


def test_tonalidad_solo_acepta_mayor_o_menor():
    with pytest.raises(ErrorTeoria):
        Tonalidad("A", "lidia")


def test_acordes_diatonicos_de_la_menor():
    acordes = parse_tonalidad("Am").acordes_diatonicos
    assert [str(a) for a in acordes] == ["Am", "Bdim", "C", "Dm", "Em", "F", "G"]


@pytest.mark.parametrize(
    ("tonalidad", "grados", "cifrados"),
    [
        ("Am", "i VI III VII", "Am F C G"),
        ("Am", "i iv V", "Am Dm E"),
        ("Am", "ii° v7", "Bdim Em7"),
        ("C", "I V vi IV", "C G Am F"),
        ("Em", "i VI VII", "Em C D"),
    ],
)
def test_progresion_por_grados(tonalidad, grados, cifrados):
    assert [str(a) for a in progresion(tonalidad, grados)] == cifrados.split()


@pytest.mark.parametrize("grados", ["VIII", "x", "Iv", "i II°"])
def test_progresion_rechaza_grados_invalidos(grados):
    with pytest.raises(ErrorTeoria):
        progresion("Am", grados)
