"""Una canción nueva arranca con su cancion.yaml, sin pisar nunca uno que exista."""

import pytest

from kerto.beat import generar_beats
from kerto.cancion.archivo import ARCHIVO_CANCION, carpeta_cancion, leer_cancion
from kerto.cancion.nueva import iniciar_cancion
from kerto.cancion.render import armar_cancion
from kerto.ritmos.pack import cargar_pack


@pytest.fixture
def en_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _beats(nombre, **opciones):
    salida = carpeta_cancion(nombre) / "beats"
    return generar_beats(salida=salida, wav=False, **opciones)


def test_escribe_el_cancion_yaml_de_una_cancion_nueva(en_tmp):
    beats = _beats("perreo-nuevo", bpm=95, tonalidad="Am")
    ruta = iniciar_cancion("perreo-nuevo", beats, vibe="perreo oscuro")
    assert ruta == carpeta_cancion("perreo-nuevo") / ARCHIVO_CANCION
    datos = leer_cancion("perreo-nuevo")
    assert datos["nombre"] == "Perreo Nuevo"
    assert datos["vibe"] == "perreo oscuro"
    assert (datos["genero"], datos["tonalidad"], datos["bpm"]) == (
        "reggaeton",
        "Am",
        95,
    )
    assert [b["variacion"] for b in datos["beats"]] == ["clasico", "movido", "oscuro"]
    primero = datos["beats"][0]
    assert primero["acordes"] == "Am F C G"
    assert primero["archivos"] == "beats/beat-1-clasico-Am.mid"
    assert datos["autotune"] == {"exigencia": "normal", "estilo": "segun_voz"}
    assert datos["letra"]["archivo"] == "letra.md"
    estructura = cargar_pack("reggaeton").estructura
    assert datos["secciones"] == [f"{parte} {n}" for parte, n in estructura]


def test_la_cancion_nueva_ya_se_puede_armar(en_tmp):
    beats = _beats("nueva", variacion="movido", acordes="teclado")
    iniciar_cancion("nueva", beats, capa="teclado")
    datos = leer_cancion("nueva")
    assert datos["base"] == {"variacion": "movido", "acordes": "teclado"}
    cancion = armar_cancion("nueva")
    assert cancion.melodia is None  # todavía no hay letra
    assert cancion.beat.variacion == "movido"


def test_con_varias_variaciones_la_base_queda_por_elegir(en_tmp):
    iniciar_cancion("nueva", _beats("nueva"))
    assert leer_cancion("nueva")["base"] is None


def test_no_pisa_un_cancion_yaml_que_ya_existe(en_tmp):
    carpeta = carpeta_cancion("luna")
    carpeta.mkdir(parents=True)
    (carpeta / ARCHIVO_CANCION).write_text("nombre: Mía\n", encoding="utf-8")
    assert iniciar_cancion("luna", _beats("luna", variacion="clasico")) is None
    assert (carpeta / ARCHIVO_CANCION).read_text(encoding="utf-8") == "nombre: Mía\n"


def test_una_vibe_con_dos_puntos_no_rompe_el_archivo(en_tmp):
    iniciar_cancion("nueva", _beats("nueva"), vibe="oscura: como de noche")
    assert leer_cancion("nueva")["vibe"] == "oscura: como de noche"


def test_los_beats_con_wav_guardan_las_dos_rutas(en_tmp):
    beats = _beats("nueva", variacion="clasico")
    wav = beats.archivos[0].with_suffix(".wav")
    falsos = type(beats)(beats.salida, (*beats.archivos, wav), beats.beats, {})
    iniciar_cancion("nueva", falsos)
    base = leer_cancion("nueva")["base"]
    assert base["wav"] == "beats/beat-1-clasico-Am.wav"
    archivos = leer_cancion("nueva")["beats"][0]["archivos"]
    assert archivos == "beats/beat-1-clasico-Am.mid, beats/beat-1-clasico-Am.wav"
