from fractions import Fraction

import pytest

from kerto.cli import main
from kerto.ritmos.motor import crear_beat, crear_cancion
from kerto.ritmos.pack import cargar_pack, generos_disponibles


@pytest.fixture(scope="module")
def pack():
    return cargar_pack("trap")


def pasos(patron):
    return [int(golpe.inicio / patron.paso) for golpe in patron.golpes]


def test_el_trap_es_un_pack_mas(pack):
    assert generos_disponibles() == ("reggaeton", "trap")
    assert pack.paso == Fraction(1, 32)
    assert pack.bpm_min <= pack.bpm_defecto == 140 <= pack.bpm_max
    assert list(pack.instrumentos) == ["bombo", "caja", "hihat", "percusion", "808"]


@pytest.mark.parametrize("indice", [0, 1, 2])
def test_la_caja_en_el_tercer_tiempo_y_redobles_de_hihat(pack, indice):
    patrones = pack.variaciones[indice].patrones
    assert 16 in pasos(patrones["caja"])  # medio tiempo: la caja en el 3
    golpes = set(pasos(patrones["hihat"]))
    assert any({p, p + 1, p + 2, p + 3} <= golpes for p in golpes)  # redoble de fusas


def test_el_trap_arma_una_cancion_sin_tocar_el_motor(pack):
    cancion = crear_cancion(pack, variacion="melodico", acordes="piano")
    assert cancion.compases == sum(compases for _, compases in pack.estructura)
    assert {m.nombre.split()[0] for m in cancion.secciones} >= {
        "intro",
        "verso",
        "coro",
    }
    assert "campana" in [p.nombre for p in cancion.pistas]


def test_kerto_beat_de_trap(tmp_path, capsys):
    argumentos = [
        "beat",
        "--genero",
        "trap",
        "--salida",
        str(tmp_path),
        "--compases",
        "2",
    ]
    assert main([*argumentos, "--sin-surge"]) == 0
    salida = capsys.readouterr().out
    assert "Género: trap · 3 variaciones" in salida
    assert "BPM: 140" in salida
    assert len(list(tmp_path.glob("*.wav"))) == 3


def test_las_capas_del_trap_suenan(pack, tmp_path):
    from kerto.render.motor import renderizar
    from kerto.render.sonidos import cargar_sonidos

    sonidos = cargar_sonidos("trap")
    for capa in pack.acordes:
        beat = crear_beat(pack, compases=1, humanizar=False, acordes=capa)
        render = renderizar(beat, tmp_path / f"{capa}.wav", sonidos, usar_surge=False)
        assert render.pico_db == pytest.approx(-1.0, abs=0.01)
