"""Comando `kerto`: la puerta de entrada al motor.

Cada subcomando responde con un resumen corto, pensado para que Claude lo lea
sin gastar tokens.
"""

import argparse
import sys

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
    return parser


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
    parser.print_help()
    return 0
