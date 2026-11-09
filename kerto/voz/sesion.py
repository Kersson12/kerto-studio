"""Analizar varias tomas de voz de una vez: lo usan `kerto voz analizar` y el MCP."""

from pathlib import Path

from kerto.voz import muestra as voz
from kerto.voz.analisis import resumir_informe
from kerto.voz.autotune import recomendar_autotune


def analizar_y_guardar(
    rutas: list[Path], exigencia: str = "normal", estilo: str = "segun_voz"
) -> list[str]:
    """Analiza y combina las tomas, guarda los JSON y devuelve el resumen (8 líneas).

    Si todas las tomas se grabaron con el beat sonando, el autotune se mide
    contra el beat.
    """
    tomas = voz.analizar_tomas(rutas)
    con_beat = []
    for ruta, muestra in zip(tomas.archivos, tomas.muestras, strict=True):
        referencia = voz.referencia_de(ruta)
        con_beat.append(referencia is not None)
        propia = recomendar_autotune(
            muestra.informe, exigencia, estilo, con_referencia=referencia is not None
        )
        voz.guardar_informe(muestra, ruta, propia)
    autotune = recomendar_autotune(
        tomas.informe, exigencia, estilo, con_referencia=all(con_beat)
    )
    informe = voz.guardar_tomas(tomas, autotune)
    consejos = (
        " · ".join(voz.consejos_de_tomas(tomas)) or "las grabaciones están limpias"
    )
    return [
        voz.resumir_consistencia(tomas),
        resumir_informe(tomas.informe),
        autotune.resumen(),
        f"Consejos: {consejos}",
        f"Informe completo: {informe.as_posix()}",
    ]
