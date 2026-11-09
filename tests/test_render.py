import random
import struct
import wave

import numpy as np
import pytest

from kerto.render.faust import VOCES
from kerto.render.motor import renderizar
from kerto.render.sonidos import ErrorSonidos, Sonido, cargar_sonidos
from kerto.render.surge import (
    ErrorSurge,
    base64_juce,
    buscar_surge,
    cargar_patch,
    estado_desde_fxp,
)
from kerto.render.wav import MAXIMO_24, escribir_wav
from kerto.ritmos.motor import crear_beat
from kerto.ritmos.pack import cargar_pack

# --- Estado de Surge XT en formato JUCE ---


def base64_juce_lento(datos):
    """La definición de JUCE: grupos de 6 bits leídos desde el bit más bajo."""
    tabla = ".ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+"
    numero = int.from_bytes(datos, "little")
    caracteres = (len(datos) * 8 + 5) // 6
    return f"{len(datos)}." + "".join(
        tabla[(numero >> (6 * i)) & 63] for i in range(caracteres)
    )


@pytest.mark.parametrize(
    ("datos", "texto"), [(b"", "0."), (b"\x00", "1..."), (b"\xff", "1.+C")]
)
def test_base64_juce_casos_conocidos(datos, texto):
    assert base64_juce(datos) == texto


@pytest.mark.parametrize("largo", [1, 2, 3, 4, 5, 100, 1001])
def test_base64_juce_coincide_con_la_definicion(largo):
    azar = random.Random(largo)
    datos = bytes(azar.randrange(256) for _ in range(largo))
    assert base64_juce(datos) == base64_juce_lento(datos)


def fxp_falso(chunk):
    cabecera = b"CcnK" + struct.pack(">I", 52 + len(chunk)) + b"FPCh"
    cabecera += struct.pack(">IIII", 1, 0x636A7333, 1, 1) + b"\0" * 28
    return cabecera + struct.pack(">I", len(chunk)) + chunk


def test_estado_desde_fxp_envuelve_el_patch_para_juce():
    chunk = b"sub3" + bytes(range(50))
    estado = estado_desde_fxp(fxp_falso(chunk))
    assert estado[:4] == b"VC2!"
    (largo,) = struct.unpack("<I", estado[4:8])
    assert largo == len(estado) - 9
    assert estado.endswith(b"\0")
    xml = estado[8:-1].decode("utf-8")
    assert xml == (
        f"<VST3PluginState><IComponent>{base64_juce(chunk)}</IComponent>"
        "</VST3PluginState>"
    )


@pytest.mark.parametrize(
    "crudo", [b"", b"RIFF" + b"\0" * 60, fxp_falso(b"x" * 10)[:-4]]
)
def test_estado_desde_fxp_rechaza_archivos_que_no_son_patches(crudo):
    with pytest.raises(ErrorSurge):
        estado_desde_fxp(crudo)


def test_cargar_patch_solo_dentro_de_la_carpeta_de_fabrica(tmp_path):
    fabrica = tmp_path / "patches_factory"
    (fabrica / "Basses").mkdir(parents=True)
    (fabrica / "Basses" / "Sub.fxp").write_bytes(fxp_falso(b"sub3"))
    (tmp_path / "Fuera.fxp").write_bytes(fxp_falso(b"sub3"))
    assert cargar_patch(fabrica, "Basses/Sub")[:4] == b"VC2!"
    for nombre in ("Basses/No existe", "../Fuera"):
        with pytest.raises(ErrorSurge):
            cargar_patch(fabrica, nombre)


def test_buscar_surge_devuelve_el_primer_candidato_que_existe(tmp_path):
    vst3, patches = tmp_path / "Surge XT.vst3", tmp_path / "patches_factory"
    vst3.mkdir()
    patches.mkdir()
    falta = tmp_path / "no"
    assert buscar_surge([falta, vst3], [falta, patches]) == (vst3, patches)
    assert buscar_surge([falta], [patches]) is None
    assert buscar_surge([vst3], [falta]) is None


# --- WAV ---


def test_escribir_wav_estereo_de_24_bits(tmp_path):
    audio = np.array([[0.0, 0.25, -0.25, 1.5], [0.0, 0.0, 0.1, -2.0]])
    ruta = escribir_wav(tmp_path / "sub" / "prueba.wav", audio, 44100)
    with wave.open(str(ruta), "rb") as archivo:
        assert archivo.getnchannels() == 2
        assert archivo.getsampwidth() == 3
        assert archivo.getframerate() == 44100
        crudo = archivo.readframes(archivo.getnframes())
    muestras = [
        int.from_bytes(crudo[i : i + 3], "little", signed=True)
        for i in range(0, len(crudo), 3)
    ]
    izquierda, derecha = muestras[0::2], muestras[1::2]
    assert [m / MAXIMO_24 for m in izquierda] == pytest.approx([0, 0.25, -0.25, 1])
    assert [m / MAXIMO_24 for m in derecha] == pytest.approx([0, 0, 0.1, -1])


def test_escribir_wav_rechaza_audio_que_no_es_canales_por_muestras(tmp_path):
    with pytest.raises(ValueError):
        escribir_wav(tmp_path / "x.wav", np.zeros(10), 44100)


# --- Sonidos del género ---


def test_sonidos_del_reggaeton_cubren_todos_los_instrumentos():
    sonidos = cargar_sonidos("reggaeton")
    pack = cargar_pack("reggaeton")
    assert list(sonidos) == [*pack.instrumentos, *pack.acordes]
    assert all(s.faust in VOCES for s in sonidos.values())
    assert all(s.nivel <= 0 for s in sonidos.values())
    assert sonidos["808"].surge == "Basses/Sub Square"


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [
        ("bombo: {faust: tambor, nivel: -6}", "tambor"),
        ("bombo: {faust: bombo, nivel: 3}", "nivel"),
        ("bombo: {nivel: -6}", "faust"),
        ("bombo: 5", "bombo"),
        ("- bombo", "mapa"),
        ("bombo: {faust: bombo, surge: 7}", "surge"),
    ],
)
def test_sonidos_invalidos(tmp_path, texto, mensaje):
    (tmp_path / "prueba").mkdir()
    (tmp_path / "prueba" / "sonidos.yaml").write_text(texto, encoding="utf-8")
    with pytest.raises(ErrorSonidos, match=mensaje):
        cargar_sonidos("prueba", carpeta=tmp_path)


def test_sonidos_de_un_genero_sin_archivo(tmp_path):
    with pytest.raises(ErrorSonidos, match="sonidos.yaml"):
        cargar_sonidos("prueba", carpeta=tmp_path)
    with pytest.raises(ErrorSonidos, match="sonidos.yaml"):
        cargar_sonidos("../reggaeton", carpeta=tmp_path)


def test_sonidos_con_yaml_roto(tmp_path):
    (tmp_path / "prueba").mkdir()
    (tmp_path / "prueba" / "sonidos.yaml").write_text("bombo: [", encoding="utf-8")
    with pytest.raises(ErrorSonidos, match="YAML"):
        cargar_sonidos("prueba", carpeta=tmp_path)


# --- Render ---


@pytest.fixture(scope="module")
def beat_corto():
    return crear_beat(cargar_pack("reggaeton"), compases=1, humanizar=False)


def test_render_con_el_sintetizador_interno(beat_corto, tmp_path):
    sonidos = cargar_sonidos("reggaeton")
    render = renderizar(beat_corto, tmp_path / "beat.wav", sonidos, usar_surge=False)
    assert set(render.motores.values()) == {"faust"}
    assert render.segundos == pytest.approx(4 * 60 / 95)
    assert render.pico_db == pytest.approx(-1.0, abs=0.01)
    with wave.open(str(render.ruta), "rb") as archivo:
        assert archivo.getnchannels() == 2
        assert archivo.getnframes() == round(render.segundos * 44100)


def test_render_falla_si_falta_el_sonido_de_un_instrumento(beat_corto, tmp_path):
    sonidos = {"bombo": Sonido(None, "bombo", -6.0)}
    with pytest.raises(ErrorSonidos, match="caja"):
        renderizar(beat_corto, tmp_path / "beat.wav", sonidos, usar_surge=False)


def test_si_surge_falla_suena_el_respaldo(beat_corto, tmp_path, monkeypatch):
    falso = (tmp_path / "Surge XT.vst3", tmp_path / "patches_factory")
    monkeypatch.setattr("kerto.render.motor.buscar_surge", lambda: falso)
    render = renderizar(beat_corto, tmp_path / "beat.wav", cargar_sonidos("reggaeton"))
    assert set(render.motores.values()) == {"faust"}


@pytest.mark.skipif(buscar_surge() is None, reason="Surge XT no está instalado")
def test_render_con_surge_xt(beat_corto, tmp_path):
    render = renderizar(beat_corto, tmp_path / "beat.wav", cargar_sonidos("reggaeton"))
    assert render.motores["808"] == "surge"
    assert render.motores["hihat"] == "faust"
    assert render.pico_db == pytest.approx(-1.0, abs=0.01)


@pytest.mark.parametrize("capa", ["pad", "teclado", "arpegio"])
def test_render_de_cada_capa_de_acordes(capa, tmp_path):
    beat = crear_beat(
        cargar_pack("reggaeton"), "movido", compases=1, humanizar=False, acordes=capa
    )
    sonidos = cargar_sonidos("reggaeton")
    render = renderizar(beat, tmp_path / "beat.wav", sonidos, usar_surge=False)
    assert render.motores[capa] == "faust"
    assert render.pico_db == pytest.approx(-1.0, abs=0.01)
