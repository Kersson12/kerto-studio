"""Los agentes de .claude/agents usan el motor a través del MCP de Kerto."""

from pathlib import Path

import pytest
import yaml
from mcp import Client

from mcp_server.servidor import mcp

pytestmark = pytest.mark.anyio
AGENTES = Path(".claude/agents")
PREFIJO = "mcp__kerto__"
NOMBRES = {"productor", "coach-vocal", "ingeniero-mezcla", "letrista", "critico-ar"}
# Lo mínimo que necesita cada uno para su trabajo.
NECESITA = {
    "productor": {"crear_beat", "renderizar_cancion", "transponer", "estado_cancion"},
    "coach-vocal": {"analizar_voz", "estado_cancion"},
    "ingeniero-mezcla": {"estado_cancion"},
    "letrista": {"estado_cancion"},
    "critico-ar": {"estado_cancion"},
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def agentes() -> dict[str, tuple[dict, str]]:
    """nombre -> (frontmatter, cuerpo) de cada agente."""
    leidos = {}
    for ruta in sorted(AGENTES.glob("*.md")):
        _, cabecera, cuerpo = ruta.read_text(encoding="utf-8").split("---", 2)
        datos = yaml.safe_load(cabecera)
        leidos[datos["name"]] = (datos, cuerpo)
    return leidos


def herramientas_de(datos: dict) -> set[str]:
    return {h.strip() for h in str(datos.get("tools", "")).split(",") if h.strip()}


def test_estan_los_cinco_agentes():
    assert set(agentes()) == NOMBRES


async def test_cada_agente_usa_solo_herramientas_que_existen():
    async with Client(mcp) as cliente:
        existen = {h.name for h in (await cliente.list_tools()).tools}
    for nombre, (datos, _) in agentes().items():
        propias = {
            h.removeprefix(PREFIJO)
            for h in herramientas_de(datos)
            if h.startswith(PREFIJO)
        }
        assert propias <= existen, (nombre, propias - existen)
        assert NECESITA[nombre] <= propias, (nombre, NECESITA[nombre] - propias)


def test_ningun_agente_necesita_la_terminal():
    for nombre, (datos, _) in agentes().items():
        tiene = herramientas_de(datos)
        assert tiene, f"{nombre} debe listar sus herramientas"
        assert "Bash" not in tiene, nombre


def test_ningun_agente_sigue_esperando_el_mcp():
    for nombre, (_, cuerpo) in agentes().items():
        assert "Hasta la Fase 4" not in cuerpo, nombre
        assert "hasta que exista el MCP" not in cuerpo.lower(), nombre
        assert "uv run kerto mezcla" not in cuerpo, nombre
