"""La letra de la canción por secciones, desde su letra.md.

Formato: un título `## <sección>` por parte (intro, verso, precoro, coro,
verso 2, puente...) y debajo una línea por compás. Lo que va después de "(" o
":" en el título se ignora, igual que la cuenta de sílabas al final de una
línea, como "(9)". Una parte sin letra propia usa la de su tipo: coro 2 canta
lo mismo que coro.
"""

import re
from pathlib import Path

_RE_TITULO = re.compile(r"^##\s+(.+?)\s*$")
_RE_CUENTA_FINAL = re.compile(r"\(\s*\d+\s*\)\s*$")


def _etiqueta(titulo: str) -> str:
    """'Verso 1' -> 'verso'; 'Coro (otra vez)' -> 'coro'; 'Pre-coro' -> 'precoro'."""
    texto = re.split(r"[(:]", titulo)[0].strip().lower().replace("-", "")
    texto = re.sub(r"\s+", " ", texto)
    return re.sub(r"^(\S+) 1$", r"\1", texto)


def leer_letra(ruta: Path) -> dict[str, list[str]]:
    """Las líneas de cada sección; {} si todavía no hay letra."""
    if not ruta.is_file():
        return {}
    secciones: dict[str, list[str]] = {}
    actual = None
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        titulo = _RE_TITULO.match(linea)
        if titulo:
            actual = _etiqueta(titulo.group(1))
            continue
        texto = _RE_CUENTA_FINAL.sub("", linea.strip()).strip()
        if actual is None or not texto or texto.startswith(("#", ">")):
            continue
        secciones.setdefault(actual, []).append(texto)
    return secciones


def lineas_de(letra: dict[str, list[str]], parte: str) -> list[str]:
    """Las líneas de una parte, o las de su tipo (coro 2 -> coro)."""
    if parte in letra:
        return letra[parte]
    return letra.get(parte.split()[0], [])
