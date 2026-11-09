from fractions import Fraction

import mido
import pytest

from kerto.cancion.melodia import ErrorMelodia, crear_melodia, ritmo_de_linea
from kerto.letra.letra import leer_letra, lineas_de
from kerto.letra.silabas import cantar
from kerto.midi import exportar_midi
from kerto.ritmos.motor import crear_cancion
from kerto.ritmos.pack import cargar_pack

R = Fraction
LETRA = """# Prueba: letra (borrador)

Texto suelto antes de las secciones: se ignora.

## Intro (4 compases): escucha

## Coro
Luna negra, luna negra (8)
cuando sale, nadie la frena (9)

## Verso 1
Llegó vestida de negro, sin avisar
las luces bajan y empieza a brillar

## Coro (otra vez)
"""


@pytest.fixture
def letra(tmp_path):
    ruta = tmp_path / "letra.md"
    ruta.write_text(LETRA, encoding="utf-8")
    return leer_letra(ruta)


@pytest.fixture(scope="module")
def cancion():
    pack = cargar_pack("reggaeton")
    partes = (("intro", 2), ("verso", 2), ("coro", 4), ("verso", 2), ("coro", 2))
    return crear_cancion(pack, partes, "movido", humanizar=False)


# --- Letra por secciones ---


def test_leer_letra_por_secciones(letra):
    assert letra == {
        "coro": ["Luna negra, luna negra", "cuando sale, nadie la frena"],
        "verso": [
            "Llegó vestida de negro, sin avisar",
            "las luces bajan y empieza a brillar",
        ],
    }


def test_cada_parte_toma_su_letra_o_la_de_su_tipo(letra):
    assert lineas_de(letra, "coro 2") == letra["coro"]
    assert lineas_de(letra, "verso 2") == letra["verso"]
    assert lineas_de(letra, "intro") == []


def test_leer_letra_inexistente(tmp_path):
    assert leer_letra(tmp_path / "no.md") == {}


# --- Ritmo de cada línea ---


@pytest.mark.parametrize(
    ("silabas", "posiciones"),
    [
        (1, [12]),
        (4, [6, 8, 10, 12]),
        (7, [0, 2, 4, 6, 8, 10, 12]),
        (8, [5, 6, 7, 8, 9, 10, 11, 12]),
        (13, list(range(13))),
        (16, list(range(16))),
    ],
)
def test_ritmo_de_linea_termina_en_el_cuarto_tiempo(silabas, posiciones):
    assert ritmo_de_linea(silabas, 16) == posiciones


def test_linea_demasiado_larga_para_un_compas():
    with pytest.raises(ErrorMelodia, match="17 sílabas"):
        ritmo_de_linea(17, 16)


# --- Melodía guía ---


RANGO = (52, 60)  # E3 a C4


def test_una_nota_por_silaba_y_cada_una_con_su_silaba(cancion, letra):
    melodia = crear_melodia(cancion, letra, RANGO)
    assert melodia.nombre == "melodia" and not melodia.bateria
    esperadas = []
    for marca in cancion.secciones:
        lineas = lineas_de(letra, marca.nombre)
        for k in range(marca.compases if lineas else 0):
            esperadas += [s.texto for s in cantar(lineas[k % len(lineas)])]
    assert list(melodia.letras) == esperadas
    assert len(melodia.notas) == len(melodia.letras)


def test_la_melodia_nunca_sale_del_rango(cancion, letra):
    for semilla in range(10):
        melodia = crear_melodia(cancion, letra, RANGO, semilla=semilla)
        assert all(RANGO[0] <= n.tono <= RANGO[1] for n in melodia.notas)


def test_la_melodia_usa_notas_de_la_escala(cancion, letra):
    la_menor = {9, 11, 0, 2, 4, 5, 7}
    melodia = crear_melodia(cancion, letra, RANGO)
    assert {n.tono % 12 for n in melodia.notas} <= la_menor


def test_cada_linea_cabe_en_su_compas_y_termina_larga(cancion, letra):
    melodia = crear_melodia(cancion, letra, RANGO)
    por_compas = {}
    for nota in melodia.notas:
        por_compas.setdefault(int(nota.inicio), []).append(nota)
    for compas, notas in por_compas.items():
        assert all(
            compas <= n.inicio and n.inicio + n.duracion <= compas + 1 for n in notas
        )
        assert notas[-1].duracion >= R(1, 4)


def test_la_ultima_silaba_de_cada_linea_cae_en_una_nota_del_acorde(cancion, letra):
    from kerto.teoria.acordes import parse_acorde
    from kerto.teoria.escalas import clase_de_altura

    melodia = crear_melodia(cancion, letra, RANGO)
    ultimas = {}
    for nota in melodia.notas:
        ultimas[int(nota.inicio)] = nota
    for compas, nota in ultimas.items():
        acorde = parse_acorde(cancion.acordes[compas])
        assert nota.tono % 12 in {clase_de_altura(n) for n in acorde.notas}


def test_el_coro_va_mas_agudo_que_el_verso(cancion, letra):
    melodia = crear_melodia(cancion, letra, RANGO)
    marcas = {m.nombre: m for m in cancion.secciones}

    def promedio(nombre):
        m = marcas[nombre]
        tonos = [
            n.tono
            for n in melodia.notas
            if m.compas <= n.inicio < m.compas + m.compases
        ]
        return sum(tonos) / len(tonos)

    assert promedio("coro") > promedio("verso")


def test_la_melodia_es_determinista(cancion, letra):
    assert crear_melodia(cancion, letra, RANGO, 3) == crear_melodia(
        cancion, letra, RANGO, 3
    )


def test_rango_demasiado_chico(cancion, letra):
    with pytest.raises(ErrorMelodia, match="rango"):
        crear_melodia(cancion, letra, (60, 61))


def test_el_midi_lleva_la_letra_de_cada_nota(cancion, letra, tmp_path):
    from dataclasses import replace

    melodia = crear_melodia(cancion, letra, RANGO)
    beat = replace(cancion, pistas=(*cancion.pistas, melodia))
    archivo = exportar_midi(beat, tmp_path / "guia.mid")
    pista = next(p for p in mido.MidiFile(archivo).tracks if p.name == "melodia")
    letras = [m.text for m in pista if m.type == "lyrics"]
    assert letras == list(melodia.letras)


def test_lineas_de_una_silaba_o_sin_palabras(cancion):
    letra = {"coro": ["¡Ay!", "..."]}
    melodia = crear_melodia(cancion, letra, RANGO)
    assert set(melodia.letras) == {"Ay"}
    assert all(n.inicio % 1 == R(12, 16) for n in melodia.notas)
