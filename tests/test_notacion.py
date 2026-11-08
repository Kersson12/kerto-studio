from fractions import Fraction as F

import pytest

from kerto.notacion import (
    ErrorNotacion,
    Evento,
    Golpe,
    duracion_compas,
    formatear_evento,
    formatear_secuencia,
    midi_a_nota,
    nota_a_midi,
    parse_evento,
    parse_patron,
    parse_secuencia,
    resumir_secuencia,
)

# --- Notas y números MIDI ---


@pytest.mark.parametrize(
    ("nombre", "numero"),
    [
        ("C4", 60),
        ("A4", 69),
        ("C#4", 61),
        ("Db4", 61),
        ("Bb3", 58),
        ("B#3", 60),
        ("Cb4", 59),
        ("C-1", 0),
        ("G9", 127),
    ],
)
def test_nota_a_midi(nombre, numero):
    assert nota_a_midi(nombre) == numero


@pytest.mark.parametrize(
    "nombre", ["", "C", "4", "H4", "c4", "C10", "C##4", "G#9", "Cb-1", "C4 "]
)
def test_nota_a_midi_rechaza_notas_invalidas(nombre):
    with pytest.raises(ErrorNotacion):
        nota_a_midi(nombre)


def test_midi_a_nota_usa_sostenidos_o_bemoles():
    assert midi_a_nota(61) == "C#4"
    assert midi_a_nota(61, bemoles=True) == "Db4"
    assert midi_a_nota(0) == "C-1"
    assert midi_a_nota(127) == "G9"


@pytest.mark.parametrize("numero", [-1, 128])
def test_midi_a_nota_rechaza_numeros_fuera_de_rango(numero):
    with pytest.raises(ErrorNotacion):
        midi_a_nota(numero)


def test_todas_las_notas_midi_van_y_vuelven():
    for numero in range(128):
        assert nota_a_midi(midi_a_nota(numero)) == numero
        assert nota_a_midi(midi_a_nota(numero, bemoles=True)) == numero


# --- Eventos: notas, acordes y silencios ---


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("C4:1/4:v90", Evento((60,), F(1, 4), 90)),
        ("C4", Evento((60,), F(1, 4), 100)),
        ("F#3:1/8", Evento((54,), F(1, 8), 100)),
        ("C4:v90", Evento((60,), F(1, 4), 90)),
        ("C4:v90:1/8", Evento((60,), F(1, 8), 90)),
        ("C4:3/8", Evento((60,), F(3, 8), 100)),
        ("C4:1/12", Evento((60,), F(1, 12), 100)),
        ("C4:2", Evento((60,), F(2), 100)),
        ("C4+E4+G4:1/2:v80", Evento((60, 64, 67), F(1, 2), 80)),
        ("G4+C4+E4", Evento((60, 64, 67), F(1, 4), 100)),
        ("R:1/8", Evento((), F(1, 8))),
        (" C4:1/4 ", Evento((60,), F(1, 4), 100)),
    ],
)
def test_parse_evento(texto, esperado):
    assert parse_evento(texto) == esperado


@pytest.mark.parametrize(
    "texto",
    [
        "",
        "C4:0",
        "C4:1/0",
        "C4:-1/4",
        "C4:0.25",
        "C4:v0",
        "C4:v128",
        "C4:v",
        "C4:1/4:1/8",
        "C4:v90:v80",
        "C4::v90",
        "C4:xyz",
        "R:1/4:v90",
        "R+C4",
        "C4+C4",
        "C4+",
        "H4:1/4",
    ],
)
def test_parse_evento_rechaza_texto_invalido(texto):
    with pytest.raises(ErrorNotacion):
        parse_evento(texto)


def test_evento_ordena_los_tonos_del_acorde():
    assert Evento((67, 60, 64)).tonos == (60, 64, 67)


@pytest.mark.parametrize(
    "argumentos",
    [
        ((60, 60),),
        ((128,),),
        ((-1,),),
        ((60,), F(0)),
        ((60,), F(-1, 4)),
        ((60,), F(1, 4), 0),
        ((60,), F(1, 4), 128),
        ((), F(1, 4), 90),
    ],
)
def test_evento_valida_sus_valores(argumentos):
    with pytest.raises(ErrorNotacion):
        Evento(*argumentos)


def test_evento_es_inmutable():
    evento = Evento((60,))
    with pytest.raises(AttributeError):
        evento.velocidad = 90


@pytest.mark.parametrize(
    ("evento", "texto"),
    [
        (Evento((60,), F(1, 4), 90), "C4:1/4:v90"),
        (Evento((60,), F(1, 4)), "C4:1/4"),
        (Evento((61,), F(1, 8)), "C#4:1/8"),
        (Evento((60, 64, 67), F(1, 2), 80), "C4+E4+G4:1/2:v80"),
        (Evento((), F(1, 2)), "R:1/2"),
        (Evento((60,), F(1)), "C4:1"),
    ],
)
def test_formatear_evento(evento, texto):
    assert formatear_evento(evento) == texto


@pytest.mark.parametrize(
    "texto", ["C4:1/4:v90", "Bb2:3/8", "R:1/16", "A3+C4+E4:1:v70", "G9:1/12:v1"]
)
def test_parse_y_formatear_evento_van_y_vuelven(texto):
    evento = parse_evento(texto)
    assert parse_evento(formatear_evento(evento)) == evento


# --- Compases y secuencias ---


@pytest.mark.parametrize(
    ("compas", "duracion"),
    [("4/4", F(1)), ("3/4", F(3, 4)), ("6/8", F(3, 4)), ("2/2", F(1))],
)
def test_duracion_compas(compas, duracion):
    assert duracion_compas(compas) == duracion


@pytest.mark.parametrize("compas", ["", "4", "4/0", "0/4", "a/b"])
def test_duracion_compas_rechaza_compases_invalidos(compas):
    with pytest.raises(ErrorNotacion):
        duracion_compas(compas)


def test_parse_secuencia_sin_compases():
    assert parse_secuencia("C4:1/4  E4 R:1/2") == [
        Evento((60,), F(1, 4)),
        Evento((64,), F(1, 4)),
        Evento((), F(1, 2)),
    ]


def test_parse_secuencia_vacia():
    assert parse_secuencia("") == []
    assert parse_secuencia("   ") == []


def test_parse_secuencia_valida_cada_compas():
    eventos = parse_secuencia("| C4:1/2 E4:1/2 |G4:1|")
    assert [e.duracion for e in eventos] == [F(1, 2), F(1, 2), F(1)]


@pytest.mark.parametrize(
    ("texto", "compas", "cantidad"),
    [
        ("C4:1/2 E4:1/4 | G4:1/2 R:1/4", "3/4", 4),
        ("C4:3/8 E4:3/8 | G4:3/4", "6/8", 3),
    ],
)
def test_parse_secuencia_con_otros_compases(texto, compas, cantidad):
    assert len(parse_secuencia(texto, compas=compas)) == cantidad


def test_parse_secuencia_avisa_que_compas_no_cuadra():
    with pytest.raises(ErrorNotacion, match="compás 2"):
        parse_secuencia("C4:1 | E4:1/2")


def test_parse_secuencia_rechaza_compas_vacio():
    with pytest.raises(ErrorNotacion):
        parse_secuencia("C4:1 || E4:1")


def test_parse_secuencia_sin_compas_no_valida_barras():
    assert len(parse_secuencia("C4:1 | E4:1/2", compas=None)) == 2


def test_parse_secuencia_rechaza_compas_mal_escrito():
    with pytest.raises(ErrorNotacion):
        parse_secuencia("C4:1 | E4:1", compas="cuatro")


def test_formatear_secuencia_sin_compas():
    eventos = [Evento((60,)), Evento((64,), F(1, 8), 90)]
    assert formatear_secuencia(eventos) == "C4:1/4 E4:1/8:v90"


def test_formatear_secuencia_marca_los_compases():
    eventos = parse_secuencia("C4:1/2 E4:1/2 G4:1")
    assert formatear_secuencia(eventos, compas="4/4") == "C4:1/2 E4:1/2 | G4:1"


def test_formatear_secuencia_rechaza_notas_que_cruzan_la_barra():
    eventos = parse_secuencia("C4:3/4 E4:1/2 R:3/4")
    with pytest.raises(ErrorNotacion, match="cruza"):
        formatear_secuencia(eventos, compas="4/4")


def test_formatear_secuencia_rechaza_compas_incompleto():
    with pytest.raises(ErrorNotacion):
        formatear_secuencia(parse_secuencia("C4:1 E4:1/2"), compas="4/4")


def test_secuencia_va_y_vuelve_con_compases():
    texto = (
        "A3+C4+E4:1/2:v80 R:1/4 E4:1/8 G4:1/8 | F3+A3+C4:1 "
        "| C4:1/12 D4:1/12 E4:1/12 G4:3/4"
    )
    eventos = parse_secuencia(texto)
    assert parse_secuencia(formatear_secuencia(eventos, compas="4/4")) == eventos


# --- Patrones de batería ---


def test_parse_patron_en_semicorcheas():
    patron = parse_patron("x...x...x...x...")
    assert patron.pasos == 16
    assert patron.duracion == 1
    assert [g.inicio for g in patron.golpes] == [0, F(1, 4), F(1, 2), F(3, 4)]
    assert {g.velocidad for g in patron.golpes} == {100}


def test_parse_patron_con_acentos_y_golpes_suaves():
    patron = parse_patron("X.o.x")
    assert patron.golpes == (
        Golpe(F(0), 120),
        Golpe(F(1, 8), 60),
        Golpe(F(1, 4), 100),
    )


def test_parse_patron_ignora_espacios_y_barras():
    assert parse_patron("x... x... | x... x...") == parse_patron("x...x...x...x...")


def test_parse_patron_con_otro_paso():
    patron = parse_patron("x.x.", paso="1/8")
    assert [g.inicio for g in patron.golpes] == [0, F(1, 4)]
    assert patron.duracion == F(1, 2)


@pytest.mark.parametrize(
    ("texto", "paso"),
    [
        ("", "1/16"),
        (" | ", "1/16"),
        ("x-x-", "1/16"),
        ("x...", "0"),
        ("x...", "1/0"),
        ("x...", "rápido"),
    ],
)
def test_parse_patron_rechaza_texto_invalido(texto, paso):
    with pytest.raises(ErrorNotacion):
        parse_patron(texto, paso=paso)


# --- Resumen corto para Claude ---


def test_resumir_secuencia():
    eventos = parse_secuencia("C4:1/2 E4:1/2 | G4+B4:1")
    assert resumir_secuencia(eventos) == "3 eventos · 2 compases de 4/4 · rango C4–B4"


def test_resumir_secuencia_en_singular_y_sin_compases_completos():
    assert resumir_secuencia([Evento((60,), F(1, 2))]) == (
        "1 evento · duración 1/2 · rango C4"
    )


def test_resumir_secuencia_solo_silencios():
    assert resumir_secuencia([Evento((), F(1))]) == "1 evento · 1 compás de 4/4"
