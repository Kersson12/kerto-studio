"""Servidor MCP de Kerto: el equipo de producción usa el motor sin comandos.

Cada herramienta devuelve un resumen de menos de 10 líneas y las rutas de los
archivos; nunca audio ni datos crudos. Arranca con:
    uv run python -m mcp_server.servidor
y Claude Code lo encuentra solo gracias a .mcp.json.
"""

from collections.abc import Callable
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from kerto.beat import generar_beats, resumir
from kerto.cancion import herramientas
from kerto.cancion.archivo import carpeta_cancion
from kerto.cancion.nueva import iniciar_cancion
from kerto.cancion.render import renderizar_cancion as _renderizar_cancion
from kerto.cancion.render import resumir_cancion
from kerto.ritmos.pack import cargar_pack, generos_disponibles
from kerto.voz.sesion import analizar_y_guardar

mcp = MCPServer("kerto")


def _responder(trabajo: Callable[[], str]) -> str:
    """Los errores del motor llegan a Claude como un mensaje claro, no como un fallo.

    Las herramientas son async a propósito: así el SDK no las manda a otro hilo.
    Surge XT (JUCE) se traba si se usa desde hilos distintos en el mismo proceso.
    """
    try:
        return trabajo()
    except (ValueError, FileExistsError) as error:
        raise ToolError(str(error)) from error


@mcp.tool()
async def listar_generos() -> str:
    """Géneros disponibles con su tempo, tonalidad, variaciones y capas de acordes."""

    def trabajo() -> str:
        lineas = []
        for genero in generos_disponibles():
            pack = cargar_pack(genero)
            variaciones = ", ".join(v.nombre for v in pack.variaciones)
            capas = ", ".join(pack.acordes) or "ninguna"
            lineas.append(
                f"{genero}: {pack.bpm_min}–{pack.bpm_max} BPM, {pack.tonalidad}"
                f" · variaciones {variaciones} · capas {capas}"
            )
        return "\n".join(lineas)

    return _responder(trabajo)


@mcp.tool()
async def crear_beat(
    genero: str = "reggaeton",
    bpm: int | None = None,
    tonalidad: str | None = None,
    compases: int = 8,
    variaciones: int = 3,
    variacion: str | None = None,
    acordes: str | None = None,
    cancion: str | None = None,
    vibe: str | None = None,
    sobrescribir: bool = False,
    wav: bool = True,
) -> str:
    """Crea variaciones de un beat en MIDI y WAV.

    Con `variacion`, solo esa (sirve para transponer la base). `acordes` suma una
    capa del pack (pad, teclado, piano...). Con `cancion` (un nombre como
    luna-negra), guarda en canciones/<cancion>/beats y, si la canción es nueva,
    escribe su cancion.yaml con la `vibe` pedida.
    """

    def trabajo() -> str:
        salida = (
            carpeta_cancion(cancion) / "beats"
            if cancion
            else Path("canciones/borrador/beats")
        )
        beats = generar_beats(
            genero,
            bpm=bpm,
            tonalidad=tonalidad,
            compases=compases,
            variaciones=variaciones,
            variacion=variacion,
            acordes=acordes,
            salida=salida,
            wav=wav,
            sobrescribir=sobrescribir,
        )
        resumen = resumir(beats)
        nueva = iniciar_cancion(cancion, beats, vibe, acordes) if cancion else None
        if nueva is not None:
            resumen += f"\nCanción nueva: {nueva.as_posix()} · elige la base de oído"
        return resumen

    return _responder(trabajo)


@mcp.tool()
async def analizar_voz(
    cancion: str, exigencia: str = "normal", estilo: str = "segun_voz"
) -> str:
    """Analiza todas las tomas de canciones/<cancion>/voz juntas: rango, afinación,
    tonalidades cómodas, autotune recomendado y consejos de grabación."""

    def trabajo() -> str:
        rutas = sorted(carpeta_cancion(cancion).joinpath("voz").glob("*.wav"))
        if not rutas:
            raise ValueError(
                f"no hay tomas en canciones/{cancion}/voz: grábalas con"
                f" uv run kerto voz grabar --cancion {cancion} --con-beat"
            )
        return "\n".join(analizar_y_guardar(rutas, exigencia, estilo))

    return _responder(trabajo)


@mcp.tool()
async def renderizar_cancion(cancion: str, wav: bool = True) -> str:
    """Arma la canción entera desde cancion.yaml y letra.md: MIDI, MIDI por pista,
    WAV guía con la melodía y WAV instrumental."""
    return _responder(lambda: resumir_cancion(_renderizar_cancion(cancion, wav=wav)))


@mcp.tool()
async def generar_seccion(cancion: str, seccion: str, wav: bool = True) -> str:
    """Escribe solo una parte de la canción (intro, verso, coro, verso 2...) para
    escucharla rápido después de un cambio."""
    return _responder(lambda: herramientas.generar_seccion(cancion, seccion, wav))


@mcp.tool()
async def transponer(cancion: str, tonalidad: str, wav: bool = True) -> str:
    """Cambia la tonalidad de la canción (por ejemplo a G#m) y la vuelve a renderizar."""
    return _responder(lambda: herramientas.transponer(cancion, tonalidad, wav))


@mcp.tool()
async def estado_cancion(cancion: str) -> str:
    """Cómo va la canción: género, estructura, acordes, melodía, voz, letra y archivos."""
    return _responder(lambda: herramientas.estado_cancion(cancion))


if __name__ == "__main__":
    mcp.run()
