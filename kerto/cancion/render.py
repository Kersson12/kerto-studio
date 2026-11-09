"""`kerto cancion render`: arma la canción entera desde su cancion.yaml.

Escribe en canciones/<nombre>/cancion/:
- <nombre>.mid: una pista por instrumento, la melodía guía con su letra y una
  marca por sección, para Waveform Free;
- <nombre>-guia.wav: todo, con la melodía guía para cantar encima;
- <nombre>-instrumental.wav: sin la melodía, para grabar tu voz;
- pistas/<pista>.mid: un MIDI por instrumento.
Esa carpeta es de Kerto: se vuelve a generar en cada render.
"""

import re
from dataclasses import dataclass, replace
from pathlib import Path

from kerto.beat import ciclo_de_acordes
from kerto.cancion.archivo import ErrorCancion, carpeta_cancion, leer_cancion
from kerto.cancion.melodia import crear_melodia
from kerto.letra.letra import leer_letra
from kerto.midi import exportar_midi, exportar_pistas
from kerto.notacion import midi_a_nota, nota_a_midi
from kerto.render.motor import renderizar
from kerto.render.sonidos import cargar_sonidos
from kerto.ritmos.motor import Beat, Pista, crear_cancion
from kerto.ritmos.pack import cargar_pack, parse_estructura

CARPETA_RENDER = "cancion"
CARPETA_PISTAS = "pistas"
ARCHIVO_LETRA = "letra.md"
RANGO_POR_DEFECTO = ("E3", "E4")
MARGEN_RANGO = 2  # semitonos que la melodía puede salir de la zona cómoda
_RE_RANGO = re.compile(r"([A-G][#b]?-?\d)\s*[-–]\s*([A-G][#b]?-?\d)")


@dataclass(frozen=True)
class Cancion:
    """La canción renderizada: su nombre, el beat completo y los archivos."""

    titulo: str
    capa: str | None
    beat: Beat
    melodia: Pista | None
    rango: tuple[int, int]
    archivos: tuple[Path, ...]
    pistas: tuple[Path, ...] = ()


def rango_de_voz(datos: dict) -> tuple[int, int]:
    """La zona cómoda de cancion.yaml (voz.comodo: F#3-A#3), con un margen."""
    voz = datos.get("voz")
    comodo = voz.get("comodo") if isinstance(voz, dict) else None
    notas = _RE_RANGO.fullmatch(str(comodo).strip()) if comodo else None
    if notas is None:
        return nota_a_midi(RANGO_POR_DEFECTO[0]), nota_a_midi(RANGO_POR_DEFECTO[1])
    grave, aguda = (nota_a_midi(nota) for nota in notas.groups())
    return grave - MARGEN_RANGO, aguda + MARGEN_RANGO


def renderizar_cancion(
    nombre: str, wav: bool = True, usar_surge: bool = True
) -> Cancion:
    """Lee cancion.yaml y letra.md, arma la canción y escribe el MIDI (y los WAV)."""
    cancion = armar_cancion(nombre)
    beat, melodia = cancion.beat, cancion.melodia
    destino = carpeta_cancion(nombre) / CARPETA_RENDER / nombre
    archivos = [exportar_midi(beat, destino.with_suffix(".mid"))]
    carpeta_pistas = destino.parent / CARPETA_PISTAS
    for viejo in carpeta_pistas.glob("*.mid"):  # pistas de un render anterior
        viejo.unlink()
    pistas = exportar_pistas(beat, carpeta_pistas)
    if wav:
        archivos += _renderizar_audio(beat, destino, beat.genero, usar_surge, melodia)
    return replace(cancion, archivos=tuple(archivos), pistas=tuple(pistas))


def armar_cancion(nombre: str) -> Cancion:
    """La canción armada en memoria (beat y melodía), sin escribir archivos."""
    datos = leer_cancion(nombre)
    genero = datos.get("genero")
    if not genero:
        raise ErrorCancion(f"el cancion.yaml de {nombre!r} no dice el genero")
    pack = cargar_pack(str(genero))
    base = datos.get("base") if isinstance(datos.get("base"), dict) else {}
    capa = base.get("acordes")
    semilla = int(base.get("semilla", 0))
    partes = datos.get("secciones") or None
    beat = crear_cancion(
        pack,
        None if partes is None else parse_estructura(partes, pack.secciones),
        base.get("variacion", 0),
        bpm=datos.get("bpm"),
        tonalidad=datos.get("tonalidad"),
        semilla=semilla,
        acordes=capa,
    )
    carpeta = carpeta_cancion(nombre)
    letra_datos = datos.get("letra") if isinstance(datos.get("letra"), dict) else {}
    letra = leer_letra(carpeta / str(letra_datos.get("archivo", ARCHIVO_LETRA)))
    rango = rango_de_voz(datos)
    melodia = crear_melodia(beat, letra, rango, semilla) if letra else None
    if melodia is not None and melodia.notas:
        beat = replace(beat, pistas=(*beat.pistas, melodia))
    else:
        melodia = None
    titulo = str(datos.get("nombre") or nombre)
    return Cancion(titulo, capa, beat, melodia, rango, ())


def _renderizar_audio(
    beat: Beat, destino: Path, genero: str, usar_surge: bool, melodia: Pista | None
) -> list[Path]:
    sonidos = cargar_sonidos(genero)
    instrumental = destino.with_name(f"{destino.name}-instrumental.wav")
    if melodia is None:
        return [renderizar(beat, instrumental, sonidos, usar_surge).ruta]
    guia = destino.with_name(f"{destino.name}-guia.wav")
    renderizar(
        beat, guia, sonidos, usar_surge, sin={instrumental: frozenset({"melodia"})}
    )
    return [guia, instrumental]


def resumir_cancion(cancion: Cancion) -> str:
    """Cinco líneas: qué es, estructura, acordes, melodía y archivos."""
    beat = cancion.beat
    capa = f" con {cancion.capa}" if cancion.capa else ""
    que = (
        f"Canción: {cancion.titulo} · {beat.genero} {beat.variacion}{capa}"
        f" · {beat.tonalidad} a {beat.bpm} BPM"
    )
    segundos = round(float(beat.duracion) * 4 * 60 / beat.bpm)
    partes = " · ".join(f"{m.nombre} ({m.compases})" for m in beat.secciones)
    estructura = (
        f"Estructura: {partes} = {beat.compases} compases,"
        f" {segundos // 60}:{segundos % 60:02d}"
    )
    vistos: dict[str, str] = {}
    for marca in beat.secciones:
        tipo = marca.nombre.split()[0]
        acordes = beat.acordes[marca.compas : marca.compas + marca.compases]
        vistos.setdefault(tipo, " ".join(ciclo_de_acordes(acordes)))
    acordes = "Acordes: " + " · ".join(f"{t} {a}" for t, a in vistos.items())
    melodia = _resumir_melodia(cancion)
    if cancion.archivos:
        carpeta = cancion.archivos[0].parent.as_posix()
        nombres = ", ".join(ruta.name for ruta in cancion.archivos)
        pistas = (
            f" · {CARPETA_PISTAS}/ ({len(cancion.pistas)} MIDI)"
            if cancion.pistas
            else ""
        )
        archivos = f"Archivos: {carpeta}/ · {nombres}{pistas}"
    else:
        archivos = "Archivos: todavía no se renderizó"
    return f"{que}\n{estructura}\n{acordes}\n{melodia}\n{archivos}"


def _resumir_melodia(cancion: Cancion) -> str:
    if cancion.melodia is None:
        return (
            "Melodía: todavía no hay letra (escribe letra.md con una línea por compás)"
        )
    beat, melodia = cancion.beat, cancion.melodia
    tonos = [nota.tono for nota in melodia.notas]
    con_letra = [
        marca.nombre
        for marca in beat.secciones
        if any(
            marca.compas <= n.inicio < marca.compas + marca.compases
            for n in melodia.notas
        )
    ]
    return (
        f"Melodía: {len(tonos)} notas de {midi_a_nota(min(tonos))} a"
        f" {midi_a_nota(max(tonos))} (tu rango: {midi_a_nota(cancion.rango[0])}–"
        f"{midi_a_nota(cancion.rango[1])}) · con letra: {', '.join(con_letra)}"
    )
