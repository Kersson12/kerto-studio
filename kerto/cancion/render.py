"""`kerto cancion render`: arma la canción entera desde su cancion.yaml.

Escribe canciones/<nombre>/cancion/<nombre>-instrumental.mid (una pista por
instrumento y una marca por sección) y, si se pide, el .wav. Esa carpeta es de
Kerto: se vuelve a generar en cada render.
"""

from dataclasses import dataclass
from pathlib import Path

from kerto.beat import ciclo_de_acordes
from kerto.cancion.archivo import ErrorCancion, carpeta_cancion, leer_cancion
from kerto.midi import exportar_midi
from kerto.render.motor import renderizar
from kerto.render.sonidos import cargar_sonidos
from kerto.ritmos.motor import Beat, crear_cancion
from kerto.ritmos.pack import cargar_pack, parse_estructura

CARPETA_RENDER = "cancion"


@dataclass(frozen=True)
class Cancion:
    """La canción renderizada: su nombre, el beat completo y los archivos."""

    titulo: str
    capa: str | None
    beat: Beat
    archivos: tuple[Path, ...]


def renderizar_cancion(
    nombre: str, wav: bool = True, usar_surge: bool = True
) -> Cancion:
    """Lee cancion.yaml, arma todas sus secciones y escribe el MIDI (y el WAV)."""
    datos = leer_cancion(nombre)
    genero = datos.get("genero")
    if not genero:
        raise ErrorCancion(f"el cancion.yaml de {nombre!r} no dice el genero")
    pack = cargar_pack(str(genero))
    base = datos.get("base") if isinstance(datos.get("base"), dict) else {}
    capa = base.get("acordes")
    partes = datos.get("secciones") or None
    beat = crear_cancion(
        pack,
        None if partes is None else parse_estructura(partes, pack.secciones),
        base.get("variacion", 0),
        bpm=datos.get("bpm"),
        tonalidad=datos.get("tonalidad"),
        semilla=int(base.get("semilla", 0)),
        acordes=capa,
    )
    destino = carpeta_cancion(nombre) / CARPETA_RENDER / f"{nombre}-instrumental"
    archivos = [exportar_midi(beat, destino.with_suffix(".mid"))]
    if wav:
        sonidos = cargar_sonidos(str(genero))
        archivos.append(
            renderizar(beat, destino.with_suffix(".wav"), sonidos, usar_surge).ruta
        )
    titulo = str(datos.get("nombre") or nombre)
    return Cancion(titulo, capa, beat, tuple(archivos))


def resumir_cancion(cancion: Cancion) -> str:
    """Cuatro líneas: qué es, su estructura, sus acordes por sección y los archivos."""
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
    primero, *resto = cancion.archivos
    extra = "".join(f" y {ruta.suffix}" for ruta in resto)
    return f"{que}\n{estructura}\n{acordes}\nArchivos: {primero.as_posix()}{extra}"
