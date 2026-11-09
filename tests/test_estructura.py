from fractions import Fraction

import mido
import pytest

from kerto.cli import main
from kerto.midi import PULSOS_POR_REDONDA, exportar_midi
from kerto.ritmos.motor import ErrorBeat, crear_cancion, tipos_de_seccion
from kerto.ritmos.pack import ErrorPack, cargar_pack, parse_estructura

R = Fraction
ESTRUCTURA_REGGAETON = (
    ("intro", 4),
    ("verso", 8),
    ("precoro", 4),
    ("coro", 8),
    ("verso", 8),
    ("coro", 8),
    ("puente", 4),
    ("outro", 4),
)


@pytest.fixture(scope="module")
def pack():
    return cargar_pack("reggaeton")


@pytest.fixture(scope="module")
def cancion(pack):
    return crear_cancion(pack, variacion="movido", acordes="teclado", humanizar=False)


def notas(beat, instrumento):
    return next(p for p in beat.pistas if p.nombre == instrumento).notas


def en_compases(lista, desde, hasta):
    return [n for n in lista if desde <= n.inicio < hasta]


# --- Pack y estructura ---


def test_el_pack_trae_secciones_y_estructura(pack):
    assert list(pack.secciones) == [
        "intro",
        "verso",
        "precoro",
        "coro",
        "puente",
        "outro",
    ]
    assert pack.secciones["intro"].sin == ("bombo", "caja", "808")
    assert pack.secciones["coro"].progresion == "i VI III VII"
    assert pack.secciones["verso"].progresion is None
    assert pack.estructura == ESTRUCTURA_REGGAETON


def test_parse_estructura(pack):
    assert parse_estructura(["intro 2", "coro  8"], pack.secciones) == (
        ("intro", 2),
        ("coro", 8),
    )


@pytest.mark.parametrize(
    ("valor", "mensaje"),
    [
        ([], "lista"),
        ("intro 4", "lista"),
        (["coro"], "coro"),
        (["coro 0"], "coro 0"),
        (["estribillo 8"], "estribillo"),
    ],
)
def test_parse_estructura_explica_los_errores(pack, valor, mensaje):
    with pytest.raises(ErrorPack, match=mensaje):
        parse_estructura(valor, pack.secciones)


PACK_MINIMO = """
nombre: prueba
compas: 4/4
bpm: {min: 80, max: 110, defecto: 95}
tonalidad: Am
instrumentos:
  bombo: {nota: C2}
variaciones:
  - nombre: uno
    progresion: i VI
    patrones: {bombo: "x...x...x...x..."}
"""


@pytest.mark.parametrize(
    ("extra", "mensaje"),
    [
        ("secciones: 5\n", "secciones"),
        ("secciones: {coro: 3}\n", "coro"),
        ("secciones: {coro: {sin: [violin]}}\n", "violin"),
        ("secciones: {coro: {progresion: i IX}}\n", "IX"),
        ("secciones: {coro: {acordes: 2}}\n", "acordes"),
        ("estructura: [coro 4]\n", "secciones"),
    ],
)
def test_secciones_invalidas(tmp_path, extra, mensaje):
    (tmp_path / "prueba").mkdir()
    (tmp_path / "prueba" / "pack.yaml").write_text(
        PACK_MINIMO + extra, encoding="utf-8"
    )
    with pytest.raises(ErrorPack, match=mensaje):
        cargar_pack("prueba", carpeta=tmp_path)


def test_pack_sin_estructura(tmp_path):
    (tmp_path / "prueba").mkdir()
    (tmp_path / "prueba" / "pack.yaml").write_text(PACK_MINIMO, encoding="utf-8")
    sin = cargar_pack("prueba", carpeta=tmp_path)
    assert (sin.secciones, sin.estructura) == ({}, ())
    with pytest.raises(ErrorBeat, match="estructura"):
        crear_cancion(sin)


# --- Compases de cada sección ---


@pytest.mark.parametrize(
    ("compases", "corte", "esperados"),
    [
        (8, True, "base base base relleno base base base corte"),
        (8, False, "base base base relleno base base base relleno"),
        (4, True, "base base base corte"),
        (2, False, "base relleno"),
    ],
)
def test_tipos_de_seccion(compases, corte, esperados):
    assert tipos_de_seccion(compases, 4, corte) == tuple(esperados.split())


# --- La canción ---


def test_la_cancion_dura_lo_que_suman_sus_partes(cancion):
    assert cancion.compases == 48
    assert cancion.duracion == 48
    assert [(m.nombre, m.compas, m.compases) for m in cancion.secciones] == [
        ("intro", 0, 4),
        ("verso", 4, 8),
        ("precoro", 12, 4),
        ("coro", 16, 8),
        ("verso 2", 24, 8),
        ("coro 2", 32, 8),
        ("puente", 40, 4),
        ("outro", 44, 4),
    ]


def test_cada_seccion_usa_su_progresion(cancion):
    assert cancion.acordes[4:8] == ("Am", "G", "F", "G")  # verso: la de movido
    assert cancion.acordes[12:14] == ("F", "G")  # precoro: VI VII
    assert cancion.acordes[16:20] == ("Am", "F", "C", "G")  # coro: i VI III VII
    assert cancion.acordes[40:42] == ("Dm", "Em")  # puente: iv v


def test_las_secciones_callan_instrumentos(cancion):
    bombo = notas(cancion, "bombo")
    assert en_compases(bombo, 0, 4) == []  # intro
    assert en_compases(bombo, 12, 16) == []  # precoro
    assert len(en_compases(bombo, 16, 17)) == 4  # coro con todo
    assert en_compases(notas(cancion, "808"), 44, 48) == []  # outro
    assert en_compases(notas(cancion, "hihat"), 0, 4)  # el hi-hat sí suena
    assert en_compases(notas(cancion, "teclado"), 0, 4)  # y los acordes también


def test_antes_de_cada_coro_hay_un_corte(cancion):
    hihat = notas(cancion, "hihat")
    for ultimo in (15, 31):  # último compás del precoro y del verso 2
        assert all(
            n.inicio < ultimo + R(3, 4) for n in en_compases(hihat, ultimo, ultimo + 1)
        )


def test_crear_cancion_con_otra_estructura(pack):
    corta = crear_cancion(pack, (("intro", 2), ("coro", 2)), "movido", humanizar=False)
    assert corta.compases == 4
    assert [m.nombre for m in corta.secciones] == ["intro", "coro"]
    assert corta.acordes == ("Am", "G", "Am", "F")


def test_la_cancion_humanizada_es_determinista(pack):
    estructura = (("verso", 2), ("coro", 2))
    assert crear_cancion(pack, estructura, semilla=4) == crear_cancion(
        pack, estructura, semilla=4
    )


# --- MIDI con marcas de sección ---


def test_el_midi_lleva_una_marca_por_seccion(cancion, tmp_path):
    archivo = exportar_midi(cancion, tmp_path / "cancion.mid")
    tick, marcas = 0, []
    for mensaje in mido.MidiFile(archivo).tracks[0]:
        tick += mensaje.time
        if mensaje.type == "marker":
            marcas.append((mensaje.text, tick // PULSOS_POR_REDONDA))
    assert marcas[:4] == [("intro", 0), ("verso", 4), ("precoro", 12), ("coro", 16)]
    assert len(marcas) == 8


# --- kerto cancion render ---


CANCION_YAML = """nombre: Prueba
genero: reggaeton
tonalidad: Am
bpm: 95
base: {variacion: movido, acordes: teclado, semilla: 0}
secciones: [intro 2, coro 2]
"""


@pytest.fixture
def carpeta_cancion(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    carpeta = tmp_path / "canciones" / "prueba"
    carpeta.mkdir(parents=True)
    (carpeta / "cancion.yaml").write_text(CANCION_YAML, encoding="utf-8")
    return carpeta


def test_cancion_render_lee_cancion_yaml(carpeta_cancion, capsys):
    assert main(["cancion", "render", "--cancion", "prueba", "--sin-wav"]) == 0
    archivo = carpeta_cancion / "cancion" / "prueba-instrumental.mid"
    assert archivo.is_file()
    lineas = capsys.readouterr().out.strip().splitlines()
    assert lineas[0] == "Canción: Prueba · reggaeton movido con teclado · Am a 95 BPM"
    assert lineas[1] == "Estructura: intro (2) · coro (2) = 4 compases, 0:10"
    assert lineas[2] == "Acordes: intro Am G · coro Am F"
    assert lineas[3].endswith("prueba-instrumental.mid")


def test_cancion_render_con_wav(carpeta_cancion, capsys):
    assert main(["cancion", "render", "--cancion", "prueba", "--sin-surge"]) == 0
    assert (carpeta_cancion / "cancion" / "prueba-instrumental.wav").is_file()
    assert "prueba-instrumental.mid y .wav" in capsys.readouterr().out


def test_cancion_render_usa_la_estructura_del_pack_si_no_hay(carpeta_cancion, capsys):
    yaml = CANCION_YAML.replace("secciones: [intro 2, coro 2]\n", "secciones: []\n")
    (carpeta_cancion / "cancion.yaml").write_text(yaml, encoding="utf-8")
    assert main(["cancion", "render", "--cancion", "prueba", "--sin-wav"]) == 0
    assert "= 48 compases, 2:01" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("viejo", "nuevo", "mensaje"),
    [
        ("secciones: [intro 2, coro 2]", "secciones: [estribillo 2]", "estribillo"),
        ("genero: reggaeton", "genero: salsa", "salsa"),
        ("genero: reggaeton\n", "", "genero"),
        ("variacion: movido", "variacion: lento", "lento"),
    ],
)
def test_cancion_render_explica_los_errores(
    carpeta_cancion, capsys, viejo, nuevo, mensaje
):
    yaml = CANCION_YAML.replace(viejo, nuevo)
    (carpeta_cancion / "cancion.yaml").write_text(yaml, encoding="utf-8")
    assert main(["cancion", "render", "--cancion", "prueba", "--sin-wav"]) == 1
    assert mensaje in capsys.readouterr().err


def test_crear_cancion_con_una_seccion_desconocida(pack):
    with pytest.raises(ErrorBeat, match="estribillo"):
        crear_cancion(pack, (("estribillo", 2),))
