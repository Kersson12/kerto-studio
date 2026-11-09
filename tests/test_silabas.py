import pytest

from kerto.letra.silabas import cantar, silabas, tonica


@pytest.mark.parametrize(
    ("palabra", "separada"),
    [
        ("luna", "lu-na"),
        ("negra", "ne-gra"),
        ("canción", "can-ción"),
        ("ciudad", "ciu-dad"),
        ("país", "pa-ís"),
        ("poeta", "po-e-ta"),
        ("instrumento", "ins-tru-men-to"),
        ("transporte", "trans-por-te"),
        ("hoy", "hoy"),
        ("llegó", "lle-gó"),
        ("querer", "que-rer"),
        ("guitarra", "gui-ta-rra"),
        ("pingüino", "pin-güi-no"),
        ("Uruguay", "U-ru-guay"),
        ("oscura", "os-cu-ra"),
        ("ahora", "a-ho-ra"),
        ("mía", "mí-a"),
        ("perreo", "pe-rre-o"),
        ("noche", "no-che"),
        ("y", "y"),
    ],
)
def test_silabas(palabra, separada):
    assert "-".join(silabas(palabra)) == separada


@pytest.mark.parametrize(
    ("palabra", "posicion"),
    [
        ("luna", 0),
        ("canción", 1),
        ("sol", 0),
        ("lugar", 1),
        ("música", 0),
        ("pared", 1),
        ("negra", 0),
        ("avisar", 2),
        ("bailando", 1),
    ],
)
def test_tonica(palabra, posicion):
    assert tonica(palabra) == posicion


@pytest.mark.parametrize(
    ("linea", "cantadas"),
    [
        ("Luna negra, luna negra", "Lu-na-ne-gra-lu-na-ne-gra"),
        ("cuando sale, nadie la frena", "cuan-do-sa-le-na-die-la-fre-na"),
        ("la pista entera se le entrega", "la-pis-taen-te-ra-se-leen-tre-ga"),
        (
            "y hasta que salga el sol, ella juega",
            "yhas-ta-que-sal-gael-sol-e-lla-jue-ga",
        ),
    ],
)
def test_cantar_une_las_vocales_entre_palabras(linea, cantadas):
    assert "-".join(s.texto for s in cantar(linea)) == cantadas


def test_cantar_marca_las_silabas_acentuadas():
    acentos = [s.texto for s in cantar("Luna negra, luna negra") if s.tonica]
    assert acentos == ["Lu", "ne", "lu", "ne"]
    assert [s.tonica for s in cantar("el sol")] == [False, True]


def test_cantar_ignora_signos_y_numeros_entre_parentesis():
    assert len(cantar("¡Luna negra! (8)")) == 4
    assert cantar("") == []


def test_palabra_sin_vocales():
    assert silabas("pst") == ["pst"]
    assert silabas("") == []
