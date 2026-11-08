from fractions import Fraction

import pytest

from kerto.ritmos.motor import crear_beat
from kerto.ritmos.pack import cargar_pack, generos_disponibles

# El dembow, en semicorcheas desde 0: bombo en cada tiempo y caja en 3, 6, 11 y 14.
BOMBO_DEMBOW = {0, 4, 8, 12}
CAJA_DEMBOW = {3, 6, 11, 14}


@pytest.fixture(scope="module")
def pack():
    return cargar_pack("reggaeton")


def pasos(patron):
    return {int(golpe.inicio / patron.paso) for golpe in patron.golpes}


def test_reggaeton_esta_entre_los_generos():
    assert "reggaeton" in generos_disponibles()


def test_datos_del_genero(pack):
    assert pack.compas == "4/4"
    assert pack.paso == Fraction(1, 16)
    assert pack.bpm_min <= 95 <= pack.bpm_max
    assert pack.tonalidad == "Am"


def test_instrumentos_del_reggaeton(pack):
    assert list(pack.instrumentos) == ["bombo", "caja", "hihat", "percusion", "808"]
    assert pack.instrumentos["bombo"].nota == 36
    assert pack.instrumentos["caja"].nota == 38
    assert pack.instrumentos["hihat"].nota == 42
    assert not pack.instrumentos["808"].bateria


def test_tres_variaciones_con_nombre_y_descripcion(pack):
    assert [v.nombre for v in pack.variaciones] == ["clasico", "movido", "oscuro"]
    assert all(v.descripcion for v in pack.variaciones)


@pytest.mark.parametrize("indice", [0, 1, 2])
def test_cada_variacion_lleva_el_dembow(pack, indice):
    patrones = pack.variaciones[indice].patrones
    assert pasos(patrones["bombo"]) >= BOMBO_DEMBOW
    assert pasos(patrones["caja"]) >= CAJA_DEMBOW


def test_relleno_y_corte(pack):
    assert set(pack.transiciones) == {"relleno", "corte"}
    corte = pack.transiciones["corte"]
    # En el corte, el último tiempo queda en silencio antes del coro.
    for patron in corte.values():
        assert all(paso < 12 for paso in pasos(patron))


@pytest.mark.parametrize("indice", [0, 1, 2])
def test_cada_variacion_arma_un_beat_de_8_compases(pack, indice):
    beat = crear_beat(pack, indice, bpm=95, tonalidad="Am", compases=8)
    assert len(beat.pistas) == 5
    assert all(pista.notas for pista in beat.pistas)
    assert beat.duracion == 8
