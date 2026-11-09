import json

import numpy as np
import pytest
from mcp import Client

from kerto.render.wav import escribir_wav
from mcp_server.servidor import mcp

pytestmark = pytest.mark.anyio
HERRAMIENTAS = {
    "listar_generos",
    "crear_beat",
    "analizar_voz",
    "renderizar_cancion",
    "generar_seccion",
    "transponer",
    "estado_cancion",
}
CANCION = """nombre: Prueba
genero: reggaeton
tonalidad: Am # la del beat
bpm: 95
base: {variacion: movido, acordes: teclado, semilla: 0}
voz: {comodo: F#3-A#3, autotune: corrección suave}
letra: {archivo: letra.md, estado: aprobada}
secciones: [intro 2, coro 2]
"""


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def cancion(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    carpeta = tmp_path / "canciones" / "prueba"
    carpeta.mkdir(parents=True)
    (carpeta / "cancion.yaml").write_text(CANCION, encoding="utf-8")
    (carpeta / "letra.md").write_text(
        "## Coro\nLuna negra, luna negra\ncuando sale, nadie la frena\n",
        encoding="utf-8",
    )
    return carpeta


async def llamar(nombre, **argumentos):
    async with Client(mcp) as cliente:
        resultado = await cliente.call_tool(nombre, argumentos)
    texto = resultado.content[0].text
    if not resultado.is_error:
        assert len(texto.splitlines()) < 10, texto
    return texto, resultado.is_error


async def test_el_servidor_ofrece_las_herramientas():
    async with Client(mcp) as cliente:
        nombres = {h.name for h in (await cliente.list_tools()).tools}
    assert nombres == HERRAMIENTAS


async def test_listar_generos():
    texto, error = await llamar("listar_generos")
    assert not error
    assert texto.startswith("reggaeton: 88–100 BPM, Am")
    assert "trap: 130–160 BPM" in texto


async def test_crear_beat_en_la_carpeta_de_la_cancion(cancion):
    texto, error = await llamar(
        "crear_beat", variacion="movido", acordes="pad", cancion="prueba", wav=False
    )
    assert not error
    assert "beat-2-movido-Am-pad" in texto
    assert (cancion / "beats" / "beat-2-movido-Am-pad.mid").is_file()
    texto, error = await llamar("crear_beat", genero="salsa", wav=False)
    assert error and "salsa" in texto


async def test_renderizar_y_estado_de_la_cancion(cancion):
    texto, error = await llamar("renderizar_cancion", cancion="prueba", wav=False)
    assert not error and "Melodía: 17 notas" in texto
    texto, error = await llamar("estado_cancion", cancion="prueba")
    assert not error
    assert texto.splitlines()[0].startswith("Canción: Prueba")
    assert "Voz: cómodo F#3-A#3 · autotune: corrección suave" in texto
    assert "Letra: aprobada" in texto
    assert "prueba.mid" in texto


async def test_generar_una_seccion(cancion):
    texto, error = await llamar(
        "generar_seccion", cancion="prueba", seccion="coro", wav=False
    )
    assert not error
    assert texto.startswith("Sección: coro · 2 compases")
    assert "con melodía guía" in texto
    assert (cancion / "cancion" / "prueba-coro.mid").is_file()
    texto, error = await llamar("generar_seccion", cancion="prueba", seccion="puente")
    assert error and "intro, coro" in texto


async def test_transponer_cambia_cancion_yaml_sin_tocar_comentarios(cancion):
    texto, error = await llamar(
        "transponer", cancion="prueba", tonalidad="Gm", wav=False
    )
    assert not error and "Gm a 95 BPM" in texto
    assert "tonalidad: Gm # la del beat" in (cancion / "cancion.yaml").read_text(
        encoding="utf-8"
    )
    texto, error = await llamar("transponer", cancion="prueba", tonalidad="H")
    assert error and "tonalidad" in texto


async def test_analizar_voz_de_la_cancion(cancion):
    texto, error = await llamar("analizar_voz", cancion="prueba")
    assert error and "kerto voz grabar" in texto
    sr = 22050
    t = np.arange(sr * 2) / sr
    voz = np.concatenate([np.zeros(sr), 0.4 * np.sin(2 * np.pi * 220 * t)])
    escribir_wav(cancion / "voz" / "toma.wav", voz[None, :], sr)
    texto, error = await llamar("analizar_voz", cancion="prueba")
    assert not error and texto.startswith("Tomas: 1 ")
    datos = json.loads(
        (cancion / "voz" / "tomas.informe.json").read_text(encoding="utf-8")
    )
    assert datos["archivos"] == ["toma.wav"]


async def test_cancion_inexistente(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    texto, error = await llamar("estado_cancion", cancion="nada")
    assert error and "no existe" in texto


async def test_generar_seccion_con_wav(cancion):
    _texto, error = await llamar("generar_seccion", cancion="prueba", seccion="intro")
    assert not error
    assert (cancion / "cancion" / "prueba-intro.wav").is_file()


async def test_transponer_sin_linea_de_tonalidad_o_sin_cancion(cancion):
    yaml = CANCION.replace("tonalidad: Am # la del beat\n", "")
    (cancion / "cancion.yaml").write_text(yaml, encoding="utf-8")
    texto, error = await llamar(
        "transponer", cancion="prueba", tonalidad="Em", wav=False
    )
    assert not error and "Em a 95 BPM" in texto
    texto, error = await llamar("transponer", cancion="otra", tonalidad="Em")
    assert error and "no existe" in texto
