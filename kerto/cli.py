"""Comando `kerto`: la puerta de entrada al motor.

Cada subcomando responde con un resumen corto, pensado para que Claude lo lea
sin gastar tokens.
"""

import argparse
import sys
from pathlib import Path

from kerto import __version__
from kerto.notacion import ErrorNotacion, parse_secuencia, resumir_secuencia


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
    return parser


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
    parser.print_help()
    return 0
