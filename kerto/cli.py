"""Comando `kerto`: la puerta de entrada al motor."""

import argparse

from kerto import __version__


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kerto",
        description="Motor de producción musical de Kerto Studio.",
    )
    parser.add_argument("--version", action="version", version=f"kerto {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = crear_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0
