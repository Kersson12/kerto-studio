"""Herramientas sobre una canción para el MCP: una sección sola, el estado y transponer.

Cada una devuelve un resumen corto (menos de 10 líneas) para que Claude lo lea.
"""

import re
from dataclasses import replace

from kerto.cancion.archivo import (
    ARCHIVO_CANCION,
    ErrorCancion,
    carpeta_cancion,
    leer_cancion,
)
from kerto.cancion.render import (
    CARPETA_RENDER,
    Cancion,
    armar_cancion,
    renderizar_cancion,
    resumir_cancion,
)
from kerto.midi import exportar_midi
from kerto.notacion import duracion_compas
from kerto.render.motor import renderizar
from kerto.render.sonidos import cargar_sonidos
from kerto.ritmos.motor import Beat, Marca
from kerto.teoria.acordes import parse_tonalidad
from kerto.teoria.escalas import ErrorTeoria

_RE_TONALIDAD = re.compile(r"^(tonalidad:\s*)([^#\n]*?)(\s*#.*)?$", re.MULTILINE)


def _recortar(beat: Beat, marca: Marca) -> Beat:
    """Solo los compases de una sección, empezando en 0."""
    largo = duracion_compas(beat.compas)
    desde, hasta = marca.compas * largo, (marca.compas + marca.compases) * largo
    pistas = []
    for pista in beat.pistas:
        dentro = [i for i, n in enumerate(pista.notas) if desde <= n.inicio < hasta]
        notas = tuple(
            replace(pista.notas[i], inicio=pista.notas[i].inicio - desde)
            for i in dentro
        )
        letras = tuple(pista.letras[i] for i in dentro if i < len(pista.letras))
        pistas.append(replace(pista, notas=notas, letras=letras))
    return replace(
        beat,
        compases=marca.compases,
        acordes=beat.acordes[marca.compas : marca.compas + marca.compases],
        pistas=tuple(pistas),
        secciones=(Marca(marca.nombre, 0, marca.compases),),
    )


def generar_seccion(nombre: str, seccion: str, wav: bool = True) -> str:
    """Escribe solo una parte de la canción (coro, verso 2...) para escucharla rápido."""
    cancion = armar_cancion(nombre)
    marcas = {marca.nombre: marca for marca in cancion.beat.secciones}
    if seccion not in marcas:
        raise ErrorCancion(
            f"la canción no tiene la sección {seccion!r}: usa {', '.join(marcas)}"
        )
    parte = _recortar(cancion.beat, marcas[seccion])
    destino = (
        carpeta_cancion(nombre)
        / CARPETA_RENDER
        / f"{nombre}-{seccion.replace(' ', '-')}"
    )
    archivos = [exportar_midi(parte, destino.with_suffix(".mid"))]
    if wav:
        sonidos = cargar_sonidos(parte.genero)
        archivos.append(renderizar(parte, destino.with_suffix(".wav"), sonidos).ruta)
    segundos = round(float(parte.duracion) * 4 * 60 / parte.bpm)
    con_letra = cancion.melodia is not None and any(
        p.nombre == "melodia" and p.notas for p in parte.pistas
    )
    return "\n".join(
        (
            f"Sección: {seccion} · {parte.compases} compases, {segundos} s"
            f" · acordes {' '.join(parte.acordes[:4])}"
            + (" · con melodía guía" if con_letra else ""),
            "Archivos: " + ", ".join(ruta.as_posix() for ruta in archivos),
        )
    )


def estado_cancion(nombre: str) -> str:
    """Resumen de la canción: qué es, estructura, voz, letra y lo ya renderizado."""
    cancion: Cancion = armar_cancion(nombre)
    lineas = resumir_cancion(replace(cancion, archivos=())).splitlines()[:4]
    datos = leer_cancion(nombre)
    voz = datos.get("voz") if isinstance(datos.get("voz"), dict) else {}
    letra = datos.get("letra") if isinstance(datos.get("letra"), dict) else {}
    lineas.append(
        f"Voz: cómodo {voz.get('comodo', 'sin medir')}"
        f" · autotune: {voz.get('autotune', 'sin recomendar')}"
    )
    lineas.append(f"Letra: {letra.get('estado', 'sin letra')}")
    carpeta = carpeta_cancion(nombre) / CARPETA_RENDER
    hechos = sorted(p.name for p in carpeta.glob("*.*")) if carpeta.is_dir() else []
    lineas.append(f"Renderizado: {', '.join(hechos) if hechos else 'nada todavía'}")
    return "\n".join(lineas)


def transponer(nombre: str, tonalidad: str, wav: bool = True) -> str:
    """Cambia la tonalidad en cancion.yaml (sin tocar comentarios) y vuelve a renderizar."""
    try:
        clave = str(parse_tonalidad(tonalidad))
    except ErrorTeoria as error:
        raise ErrorCancion(str(error)) from error
    ruta = carpeta_cancion(nombre) / ARCHIVO_CANCION
    if not ruta.is_file():
        raise ErrorCancion(f"no existe {ruta.as_posix()}")
    texto = ruta.read_text(encoding="utf-8")
    if _RE_TONALIDAD.search(texto):
        texto = _RE_TONALIDAD.sub(
            lambda m: f"{m.group(1)}{clave}{m.group(3) or ''}", texto, count=1
        )
    else:
        texto += f"tonalidad: {clave}\n"
    ruta.write_bytes(texto.encode("utf-8"))
    return resumir_cancion(renderizar_cancion(nombre, wav=wav))
