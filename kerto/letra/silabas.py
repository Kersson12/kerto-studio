"""Sílabas del español para cantar: división, acento y sinalefa.

silabas("instrumento") -> ins-tru-men-to; tonica("canción") -> 1;
cantar("y hasta que salga el sol") une las vocales entre palabras como al
cantar: yhas-ta-que-sal-gael-sol.
"""

import re
from dataclasses import dataclass

_VOCALES = "aeiouáéíóúü"
_FUERTES = "aeoáéó"
_DEBILES_ACENTUADAS = "íú"
_ACENTUADAS = "áéíóú"
_DIGRAFOS = ("ch", "ll", "rr")
# Grupos que nunca se separan: van juntos al principio de la sílaba.
_GRUPOS = {
    "pl",
    "pr",
    "bl",
    "br",
    "fl",
    "fr",
    "cl",
    "cr",
    "gl",
    "gr",
    "tr",
    "dr",
    "kl",
    "kr",
}
# Monosílabos que se dicen sin acento (artículos, preposiciones, pronombres...).
_ATONAS = {
    "el", "la", "los", "las", "lo", "le", "les", "me", "te", "se", "nos", "os",
    "mi", "mis", "tu", "tus", "su", "sus", "de", "del", "a", "al", "en", "con",
    "por", "sin", "y", "e", "o", "u", "ni", "que", "si", "un",
}  # fmt: skip
_RE_PALABRA = re.compile(r"[a-záéíóúüñ]+", re.IGNORECASE)
_RE_CUENTA = re.compile(r"\(\s*\d+\s*\)")


@dataclass(frozen=True)
class Silaba:
    """Una sílaba cantada y si lleva el acento de su palabra."""

    texto: str
    tonica: bool


def _unidades(palabra: str) -> list[tuple[str, bool]]:
    """Letras agrupadas: (texto, es_vocal). ch, ll, rr, qu y gu (ante e/i) son una."""
    minusculas = palabra.lower()
    unidades: list[tuple[str, bool]] = []
    i = 0
    while i < len(palabra):
        par = minusculas[i : i + 2]
        siguiente = minusculas[i + 2 : i + 3]
        if par in _DIGRAFOS or (par in ("qu", "gu") and siguiente in tuple("eéií")):
            unidades.append((palabra[i : i + 2], False))
            i += 2
            continue
        letra = minusculas[i]
        y_vocal = (
            letra == "y"
            and i == len(palabra) - 1
            and (len(palabra) == 1 or minusculas[i - 1] in _VOCALES)
        )
        unidades.append((palabra[i], letra in _VOCALES or y_vocal))
        i += 1
    return unidades


def _corta(anterior: str, vocal: str) -> bool:
    """Hiato: dos vocales fuertes, o una débil acentuada (pa-ís, mí-a)."""
    a, b = anterior.lower(), vocal.lower()
    fuertes = a in _FUERTES and b in _FUERTES
    return fuertes or a in _DEBILES_ACENTUADAS or b in _DEBILES_ACENTUADAS


def _a_la_anterior(consonantes: list[str]) -> int:
    """Cuántas consonantes entre dos vocales se quedan con la sílaba anterior."""
    juntas = [c.lower() for c in consonantes]
    if len(juntas) <= 1:
        return 0
    if len(juntas) == 2:
        return 0 if "".join(juntas) in _GRUPOS else 1
    if len(juntas) == 3:
        return 1 if "".join(juntas[1:]) in _GRUPOS else 2
    return 2


def silabas(palabra: str) -> list[str]:
    """La palabra dividida en sílabas: 'transporte' -> ['trans', 'por', 'te']."""
    # Trozos alternados: consonantes antes de cada núcleo vocálico, y al final.
    nucleos: list[str] = []
    entre: list[list[str]] = [[]]
    for texto, es_vocal in _unidades(palabra):
        if not es_vocal:
            entre[-1].append(texto)
        elif nucleos and not entre[-1] and not _corta(nucleos[-1][-1], texto):
            nucleos[-1] += texto
        else:
            nucleos.append(texto)
            entre.append([])
    if not nucleos:
        return [palabra] if palabra else []
    partes = ["".join(entre[0]) + nucleos[0]]
    for indice in range(1, len(nucleos)):
        consonantes = entre[indice]
        quedan = _a_la_anterior(consonantes)
        partes[-1] += "".join(consonantes[:quedan])
        partes.append("".join(consonantes[quedan:]) + nucleos[indice])
    partes[-1] += "".join(entre[-1])
    return partes


def tonica(palabra: str) -> int:
    """Qué sílaba lleva el acento (desde 0): la de tilde, o la regla de llana o aguda."""
    partes = silabas(palabra)
    for indice, parte in enumerate(partes):
        if any(letra in _ACENTUADAS for letra in parte.lower()):
            return indice
    final = palabra.lower()[-1:]
    llana = final in _VOCALES or final in ("n", "s")
    return len(partes) - 2 if llana and len(partes) >= 2 else len(partes) - 1


def _termina_en_vocal(palabra: str) -> bool:
    final = palabra.lower()[-1]
    return final in _VOCALES or final == "y"


def _empieza_en_vocal(palabra: str) -> bool:
    inicio = palabra.lower()
    inicio = inicio.removeprefix("h")
    return bool(inicio) and inicio[0] in _VOCALES


def cantar(linea: str) -> list[Silaba]:
    """Las sílabas tal como se cantan, con las vocales entre palabras unidas."""
    palabras = _RE_PALABRA.findall(_RE_CUENTA.sub(" ", linea))
    cantadas: list[Silaba] = []
    anterior = ""
    for palabra in palabras:
        partes = silabas(palabra)
        acento = None if palabra.lower() in _ATONAS else tonica(palabra)
        nuevas = [Silaba(parte, i == acento) for i, parte in enumerate(partes)]
        if cantadas and _termina_en_vocal(anterior) and _empieza_en_vocal(palabra):
            unida = cantadas.pop()
            primera = nuevas.pop(0)
            nuevas.insert(
                0, Silaba(unida.texto + primera.texto, unida.tonica or primera.tonica)
            )
        cantadas.extend(nuevas)
        anterior = palabra
    return cantadas
