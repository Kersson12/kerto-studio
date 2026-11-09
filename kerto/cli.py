"""Comando `kerto`: la puerta de entrada al motor.

Cada subcomando responde con un resumen corto, pensado para que Claude lo lea
sin gastar tokens.
"""

import argparse
import sys
from pathlib import Path

from kerto import __version__
from kerto.cancion.archivo import ErrorCancion, beat_base
from kerto.notacion import ErrorNotacion, parse_secuencia, resumir_secuencia

_BEAT_BASE = Path("<beat base de la canción>")  # --con-beat sin archivo


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kerto",
        description="Motor de producción musical de Kerto Studio.",
    )
    parser.add_argument("--version", action="version", version=f"kerto {__version__}")
    comandos = parser.add_subparsers(dest="comando", metavar="comando")

    notacion = comandos.add_parser(
        "notacion", help="valida una secuencia en notación compacta y la resume"
    )
    notacion.add_argument(
        "texto", nargs="+", help='eventos, por ejemplo "C4:1/2 E4:1/2 | G4:1"'
    )
    notacion.add_argument(
        "--compas", default="4/4", help="compás con el que se validan las barras (4/4)"
    )
    _agregar_beat(comandos)
    _agregar_voz(comandos)
    return parser


def _agregar_voz(comandos: argparse._SubParsersAction) -> None:
    voz = comandos.add_parser("voz", help="graba o analiza una muestra de tu voz")
    acciones = voz.add_subparsers(dest="accion", metavar="accion", required=True)
    grabar = acciones.add_parser("grabar", help="graba del micrófono y analiza")
    grabar.add_argument("--segundos", type=float, default=30.0, help="largo (30)")
    grabar.add_argument("--cancion", help="guarda en canciones/<cancion>/voz")
    grabar.add_argument(
        "--salida",
        type=Path,
        help="carpeta donde guardar (por defecto canciones/borrador/voz)",
    )
    grabar.add_argument(
        "--dispositivo", type=int, help="número del micrófono (kerto voz dispositivos)"
    )
    grabar.add_argument(
        "--con-beat",
        type=Path,
        nargs="?",
        const=_BEAT_BASE,
        help="WAV que suena en los audífonos mientras cantas; sin archivo,"
        " el beat base de la canción",
    )
    analizar = acciones.add_parser(
        "analizar", help="analiza una o varias tomas; varias se combinan"
    )
    analizar.add_argument("archivos", type=Path, nargs="*", help="WAV, FLAC, OGG o MP3")
    analizar.add_argument(
        "--cancion", help="analiza todas las tomas de canciones/<cancion>/voz"
    )
    for accion in (grabar, analizar):
        accion.add_argument(
            "--exigencia",
            default="normal",
            choices=("normal", "exigente", "relajado"),
            help="regla del autotune (normal)",
        )
        accion.add_argument(
            "--estilo",
            default="segun_voz",
            choices=("segun_voz", "marcado", "natural"),
            help="autotune según tu voz, siempre marcado o siempre natural",
        )
    acciones.add_parser("dispositivos", help="lista los micrófonos")
    probar = acciones.add_parser(
        "probar", help="prueba el nivel del micrófono (6 s, no guarda nada)"
    )
    probar.add_argument("--dispositivo", type=int, help="número del micrófono")


def _comando_voz(args: argparse.Namespace) -> int:
    from kerto.voz import muestra as voz
    from kerto.voz.analisis import ErrorVoz, resumir_informe
    from kerto.voz.autotune import recomendar_autotune

    if args.accion == "dispositivos":
        print("\n".join(voz.listar_entradas()))
        return 0
    if args.accion == "probar":
        try:
            nivel = voz.probar_nivel(dispositivo=args.dispositivo)
        except ErrorVoz as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        print(
            f"Nivel: tu voz llega a {nivel.voz_db:.0f} dBFS (pico {nivel.pico_db:.0f});"
            f" la zona buena va de -20 a -8 · {nivel.consejo}"
        )
        return 0
    try:
        referencia = None
        if args.accion == "grabar":
            carpeta = args.salida or voz.carpeta_de_cancion(args.cancion or "borrador")
            guia = args.con_beat
            if guia is _BEAT_BASE:
                if not args.cancion:
                    raise ErrorVoz("--con-beat sin archivo necesita --cancion <nombre>")
                guia = beat_base(args.cancion)
            archivo = voz.grabar_muestra(
                carpeta, args.segundos, args.dispositivo, beat=guia
            )
            referencia = guia.name if guia else None
            rutas = [archivo]
        else:
            rutas = list(args.archivos)
            if args.cancion:
                rutas += sorted(voz.carpeta_de_cancion(args.cancion).glob("*.wav"))
            if not rutas:
                raise ErrorVoz("no hay tomas: pasa archivos o --cancion <nombre>")
        if len(rutas) > 1 or args.accion == "analizar" and args.cancion:
            return _varias_tomas(voz, rutas, args)
        resultado = voz.analizar_muestra(*voz.leer_audio(rutas[0]))
        autotune = recomendar_autotune(resultado.informe, args.exigencia, args.estilo)
        informe = voz.guardar_informe(resultado, rutas[0], autotune, referencia)
    except (ErrorVoz, ErrorCancion) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    consejos = " · ".join(resultado.consejos) or "la grabación está limpia"
    print(resumir_informe(resultado.informe))
    print(autotune.resumen())
    print(f"Consejos: {consejos}")
    print(f"Informe completo: {informe.as_posix()}")
    return 0


def _varias_tomas(voz, rutas: list[Path], args: argparse.Namespace) -> int:
    from kerto.voz.analisis import resumir_informe
    from kerto.voz.autotune import recomendar_autotune

    tomas = voz.analizar_tomas(rutas)
    for ruta, muestra in zip(tomas.archivos, tomas.muestras, strict=True):
        propia = recomendar_autotune(muestra.informe, args.exigencia, args.estilo)
        voz.guardar_informe(muestra, ruta, propia)
    autotune = recomendar_autotune(tomas.informe, args.exigencia, args.estilo)
    informe = voz.guardar_tomas(tomas, autotune)
    consejos = (
        " · ".join(voz.consejos_de_tomas(tomas)) or "las grabaciones están limpias"
    )
    print(voz.resumir_consistencia(tomas))
    print(resumir_informe(tomas.informe))
    print(autotune.resumen())
    print(f"Consejos: {consejos}")
    print(f"Informe completo: {informe.as_posix()}")
    return 0


def _agregar_beat(comandos: argparse._SubParsersAction) -> None:
    beat = comandos.add_parser(
        "beat", help="crea las variaciones de un beat en MIDI y WAV"
    )
    beat.add_argument("--genero", default="reggaeton", help="pack de generos/")
    beat.add_argument("--bpm", type=int, help="tempo; por defecto, el del pack")
    beat.add_argument("--tonalidad", help="Am, C, F#m...; por defecto, la del pack")
    beat.add_argument("--compases", type=int, default=8, help="largo del beat (8)")
    beat.add_argument(
        "--variaciones", type=int, default=3, help="cuántas versiones crear (3)"
    )
    beat.add_argument(
        "--variacion", help="solo esta versión, por ejemplo movido (para transponer)"
    )
    beat.add_argument(
        "--acordes", help="suma una capa de acordes del pack: pad, teclado o arpegio"
    )
    beat.add_argument("--semilla", type=int, default=0, help="azar de la humanización")
    beat.add_argument(
        "--salida",
        type=Path,
        default=Path("canciones/borrador/beats"),
        help="carpeta de salida (canciones/borrador/beats)",
    )
    beat.add_argument("--sin-wav", action="store_true", help="solo MIDI, sin render")
    beat.add_argument(
        "--sin-surge", action="store_true", help="usa solo el sintetizador interno"
    )
    beat.add_argument(
        "--sobrescribir", action="store_true", help="reemplaza archivos que ya existen"
    )


def _comando_beat(args: argparse.Namespace) -> int:
    from kerto.beat import generar_beats, resumir

    try:
        beats = generar_beats(
            args.genero,
            bpm=args.bpm,
            tonalidad=args.tonalidad,
            compases=args.compases,
            variaciones=args.variaciones,
            variacion=args.variacion,
            acordes=args.acordes,
            semilla=args.semilla,
            salida=args.salida,
            wav=not args.sin_wav,
            usar_surge=not args.sin_surge,
            sobrescribir=args.sobrescribir,
        )
    except (ValueError, FileExistsError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(resumir(beats))
    return 0


def _comando_notacion(args: argparse.Namespace) -> int:
    try:
        eventos = parse_secuencia(" ".join(args.texto), compas=args.compas)
        resumen = resumir_secuencia(eventos, compas=args.compas)
    except ErrorNotacion as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"OK · {resumen}")
    return 0


def _salida_utf8() -> None:
    """Acentos bien escritos también en Windows cuando la salida va a un pipe."""
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    _salida_utf8()
    parser = crear_parser()
    args = parser.parse_args(argv)
    if args.comando == "notacion":
        return _comando_notacion(args)
    if args.comando == "beat":
        return _comando_beat(args)
    if args.comando == "voz":
        return _comando_voz(args)
    parser.print_help()
    return 0
