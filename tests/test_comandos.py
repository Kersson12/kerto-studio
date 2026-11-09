"""Los comandos de .claude/commands: /nueva-cancion, /analiza-mi-voz y /mezcla."""

import re
from pathlib import Path

import yaml

COMANDOS = Path(".claude/commands")
AGENTES = Path(".claude/agents")
HERRAMIENTAS = {
    "listar_generos",
    "crear_beat",
    "analizar_voz",
    "renderizar_cancion",
    "generar_seccion",
    "transponer",
    "estado_cancion",
}
FUTURAS = {"mezclar"}  # llega en la Fase 5


def comandos() -> dict[str, tuple[dict, str]]:
    leidos = {}
    for ruta in sorted(COMANDOS.glob("*.md")):
        _, cabecera, cuerpo = ruta.read_text(encoding="utf-8").split("---", 2)
        leidos[ruta.stem] = (yaml.safe_load(cabecera), cuerpo)
    return leidos


def test_estan_los_tres_comandos():
    assert set(comandos()) == {"nueva-cancion", "analiza-mi-voz", "mezcla"}


def test_cada_comando_se_explica_y_recibe_lo_que_escribes():
    for nombre, (datos, cuerpo) in comandos().items():
        assert datos["description"], nombre
        assert datos["argument-hint"], nombre
        assert "$ARGUMENTS" in cuerpo, nombre


def test_los_comandos_nombran_herramientas_y_agentes_que_existen():
    agentes = {ruta.stem for ruta in AGENTES.glob("*.md")}
    for nombre, (_, cuerpo) in comandos().items():
        citados = set(re.findall(r"`([a-z_-]+)`", cuerpo))
        herramientas = {c for c in citados if "_" in c}
        assert herramientas <= HERRAMIENTAS | FUTURAS, (nombre, herramientas)
        for agente in re.findall(r"agente `([a-z-]+)`", cuerpo):
            assert agente in agentes, (nombre, agente)
