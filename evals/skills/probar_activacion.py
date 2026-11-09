"""¿Se activan las skills propias cuando toca? Prueba con `claude -p` de verdad.

Basado en la prueba de activación de skill-creator, con tres cambios:
- funciona en Windows (lee la salida con un hilo, no con select);
- prueba las skills reales de .claude/skills, compitiendo con todas las demás;
- una sesión por pregunta anota todas las skills que se activan, así cada
  pregunta prueba varias skills a la vez (unas deben activarse y otras no).

La sesión se corta en cuanto Claude va a usar una herramienta que hace algo
(escribir, Bash, el MCP...): solo se deja leer, buscar y cargar skills.

    uv run python evals/skills/probar_activacion.py --veces 3

Gasta una sesión de Claude por pregunta y vez: no corre en los tests normales.
"""

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CASOS = Path(__file__).with_name("casos.json")
# Herramientas que no cambian nada: con ellas la prueba sigue.
SEGURAS = {"Skill", "Read", "Glob", "Grep", "ToolSearch"} | {
    "mcp__kerto__listar_generos",
    "mcp__kerto__estado_cancion",
}


@dataclass(frozen=True)
class Sesion:
    """Lo que hizo Claude: las skills que cargó y su primera acción."""

    skills: frozenset[str]
    accion: str | None


def buscar_claude() -> str:
    """El CLI de Claude Code: del PATH o, si no, el de la extensión de VS Code."""
    encontrado = shutil.which("claude")
    if encontrado:
        return encontrado
    extensiones = Path.home() / ".vscode" / "extensions"
    binarios = sorted(
        extensiones.glob("anthropic.claude-code-*/resources/native-binary/claude*"),
        key=lambda ruta: ruta.stat().st_mtime,
    )
    if not binarios:
        raise SystemExit("no encuentro el comando claude: pásalo con --claude")
    return str(binarios[-1])


def probar(pregunta: str, claude: str, modelo: str | None, limite: float) -> Sesion:
    """Las skills que Claude carga antes de su primera acción o de responder."""
    comando = [
        claude,
        "-p",
        pregunta,
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-partial-messages",
    ]
    if modelo:
        comando += ["--model", modelo]
    entorno = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    proceso = subprocess.Popen(
        comando,
        cwd=RAIZ,
        env=entorno,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    lineas: queue.Queue[bytes | None] = queue.Queue()

    def leer() -> None:
        for linea in proceso.stdout:
            lineas.put(linea)
        lineas.put(None)

    threading.Thread(target=leer, daemon=True).start()
    try:
        return _seguir(lineas, time.monotonic() + limite)
    finally:
        if proceso.poll() is None:
            proceso.kill()
        proceso.wait()


def _seguir(lineas: queue.Queue, hasta: float) -> Sesion:
    activadas: set[str] = set()
    accion = None
    abiertas: dict[int, list[str]] = {}  # índice del bloque -> [herramienta, json]
    while time.monotonic() < hasta:
        try:
            linea = lineas.get(timeout=1.0)
        except queue.Empty:
            continue
        if linea is None:
            break
        try:
            evento = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if evento.get("type") == "result":
            break
        if evento.get("type") != "stream_event":
            continue
        dato = evento.get("event", {})
        tipo, indice = dato.get("type"), dato.get("index", 0)
        if tipo == "content_block_start":
            bloque = dato.get("content_block", {})
            if bloque.get("type") == "tool_use":
                if bloque.get("name") not in SEGURAS:
                    accion = bloque.get("name")
                    break  # va a hacer algo: aquí termina la prueba
                abiertas[indice] = [bloque["name"], ""]
        elif tipo == "content_block_delta" and indice in abiertas:
            abiertas[indice][1] += dato.get("delta", {}).get("partial_json", "")
        elif tipo == "content_block_stop" and indice in abiertas:
            nombre, texto = abiertas.pop(indice)
            activadas |= _skill_de(nombre, texto)
    return Sesion(frozenset(activadas), accion)


def _skill_de(herramienta: str, texto: str) -> set[str]:
    try:
        entrada = json.loads(texto or "{}")
    except json.JSONDecodeError:
        return set()
    if herramienta == "Skill":
        return {str(entrada.get("skill", "")).split(":")[-1]}
    ruta = str(entrada.get("file_path", "")).replace("\\", "/")
    if herramienta == "Read" and "/skills/" in ruta and ruta.endswith("/SKILL.md"):
        return {ruta.split("/")[-2]}
    return set()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--casos", type=Path, default=CASOS)
    parser.add_argument("--veces", type=int, default=3, help="sesiones por pregunta")
    parser.add_argument("--modelo", help="modelo de claude -p (el tuyo por defecto)")
    parser.add_argument("--trabajadores", type=int, default=6)
    parser.add_argument("--limite", type=float, default=120, help="segundos por sesión")
    parser.add_argument("--salida", type=Path, help="JSON con cada resultado")
    parser.add_argument("--claude", help="ruta del CLI de Claude Code")
    args = parser.parse_args()
    claude = args.claude or buscar_claude()
    casos = json.loads(args.casos.read_text(encoding="utf-8"))
    trabajos = [(caso, vez) for caso in casos for vez in range(args.veces)]
    with ThreadPoolExecutor(args.trabajadores) as grupo:
        resultados = list(
            grupo.map(
                lambda t: probar(t[0]["pregunta"], claude, args.modelo, args.limite),
                trabajos,
            )
        )
    por_caso: dict[int, list[Sesion]] = {}
    for (caso, _), sesion in zip(trabajos, resultados, strict=True):
        por_caso.setdefault(id(caso), []).append(sesion)
    return _informar(casos, por_caso, args.salida)


def _comprobaciones(caso: dict) -> list[tuple[str, bool]]:
    """(qué, debe pasar): skills que deben o no activarse y la primera acción."""
    lista = [(s, True) for s in caso.get("debe", [])]
    lista += [(s, False) for s in caso.get("no_debe", [])]
    if "accion" in caso:
        lista.append((f"accion:{caso['accion']}", True))
    return lista


def _ocurrio(que: str, sesion: Sesion) -> bool:
    if que.startswith("accion:"):
        return sesion.accion == que.removeprefix("accion:")
    return que in sesion.skills


def _informar(casos: list, por_caso: dict, salida: Path | None) -> int:
    fallos, total, filas = 0, 0, []
    for caso in casos:
        sesiones = por_caso[id(caso)]
        for que, debe in _comprobaciones(caso):
            veces = sum(_ocurrio(que, sesion) for sesion in sesiones)
            parte = veces / len(sesiones)
            bien = parte >= 0.5 if debe else parte < 0.5
            total += 1
            fallos += not bien
            marca = "OK   " if bien else "FALLA"
            esperado = "debe" if debe else "no debe"
            print(
                f"{marca} {que} ({esperado}) {veces}/{len(sesiones)}:"
                f" {caso['pregunta'][:70]}"
            )
        filas.append(
            {
                **caso,
                "sesiones": [
                    {"skills": sorted(s.skills), "accion": s.accion} for s in sesiones
                ],
            }
        )
    print(f"\n{total - fallos}/{total} comprobaciones bien")
    if salida:
        salida.write_text(json.dumps(filas, ensure_ascii=False, indent=2), "utf-8")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
