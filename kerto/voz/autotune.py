"""Recomendación de autotune con reglas simples y explicadas.

Umbrales elegidos por el usuario (Fase 2): exigencia "normal" y estilo
"según mi voz". Se mide la desafinación media en cents (100 cents = medio tono);
si la voz tiembla mucho dentro de las notas, la recomendación sube un nivel.
"""

from dataclasses import dataclass

from kerto.voz.analisis import ErrorVoz, Informe

NIVELES = ("ninguno", "suave", "marcado")
SIN_MEDIR = "sin_medir"
TEMBLOR_ALTO = 30.0  # cents de desvío dentro de cada nota


@dataclass(frozen=True)
class Umbrales:
    """Desde cuántos cents de desafinación se pasa a corrección suave y a marcada."""

    suave: float
    marcado: float


EXIGENCIAS: dict[str, Umbrales] = {
    "normal": Umbrales(suave=15, marcado=35),
    "exigente": Umbrales(suave=10, marcado=25),
    "relajado": Umbrales(suave=20, marcado=45),
}
ESTILOS = ("segun_voz", "marcado", "natural")

_NOMBRES = {
    "ninguno": "sin autotune",
    "suave": "corrección suave",
    "marcado": "corrección marcada",
    SIN_MEDIR: "todavía no se puede medir",
}
_CONSEJOS = {
    "ninguno": (
        "graba sin autotune; si alguna nota se escapa, se corrige a mano en la mezcla"
    ),
    "suave": (
        "Graillon o MAutoPitch (gratis) con retune lento,"
        " para que corrija sin que se note"
    ),
    "marcado": (
        "Graillon o MAutoPitch con retune rápido:"
        " suena al efecto robótico del reggaetón y el trap"
    ),
    SIN_MEDIR: (
        "deja el micrófono en la zona buena (uv run kerto voz probar) y graba"
        " sobre el beat con audífonos (uv run kerto voz grabar --cancion"
        " <cancion> --con-beat), alargando las vocales del coro"
    ),
}


@dataclass(frozen=True)
class Recomendacion:
    """Nivel de autotune, por qué y con qué plugin."""

    nivel: str
    motivo: str
    consejo: str

    def resumen(self) -> str:
        return f"Autotune: {_NOMBRES[self.nivel]} · {self.motivo} · {self.consejo}"


def recomendar_autotune(
    informe: Informe,
    exigencia: str = "normal",
    estilo: str = "segun_voz",
    con_referencia: bool = False,
) -> Recomendacion:
    """Aplica la regla del usuario a un informe de voz.

    `con_referencia` dice que la toma se grabó con el beat sonando: entonces la
    desafinación se mide contra el beat (La 440), aunque las notas no caigan en
    una escala fija. Sin referencia, eso no se puede medir.
    """
    if exigencia not in EXIGENCIAS:
        raise ErrorVoz(
            f"exigencia desconocida {exigencia!r}: usa {', '.join(EXIGENCIAS)}"
        )
    if estilo not in ESTILOS:
        raise ErrorVoz(f"estilo desconocido {estilo!r}: usa {', '.join(ESTILOS)}")
    if estilo == "marcado":
        return _recomendacion("marcado", "elegiste el efecto marcado como estilo")
    if not informe.en_escala and not con_referencia:
        return _recomendacion(
            SIN_MEDIR,
            "tus notas no caen en una escala fija, así que no hay contra qué medir",
        )
    umbrales = EXIGENCIAS[exigencia]
    cents = round(informe.desafinacion)
    contra = " contra el beat" if con_referencia else ""
    if informe.desafinacion < umbrales.suave:
        nivel = 0
        motivo = (
            f"te desvías {cents} cents en promedio{contra}, menos de {umbrales.suave:g}"
        )
    elif informe.desafinacion < umbrales.marcado:
        nivel = 1
        motivo = (
            f"te desvías {cents} cents en promedio{contra}, entre {umbrales.suave:g}"
            f" y {umbrales.marcado:g}"
        )
    else:
        nivel = 2
        motivo = (
            f"te desvías {cents} cents en promedio{contra}, desde {umbrales.marcado:g}"
        )
    if not informe.en_escala:
        motivo += (
            "; tus notas todavía no siguen la escala del beat: la melodía guía"
            " (Fase 3) te dirá qué notas cantar"
        )
    if informe.temblor > TEMBLOR_ALTO and nivel < 2:
        nivel += 1
        motivo += (
            f"; sube un nivel porque tu voz tiembla {round(informe.temblor)} cents"
            " dentro de las notas"
        )
    if estilo == "natural":
        nivel = min(nivel, 1)
    return _recomendacion(NIVELES[nivel], motivo)


def _recomendacion(nivel: str, motivo: str) -> Recomendacion:
    return Recomendacion(nivel, motivo, _CONSEJOS[nivel])
