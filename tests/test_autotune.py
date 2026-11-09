import pytest

from kerto.voz.analisis import ErrorVoz, Informe
from kerto.voz.autotune import EXIGENCIAS, recomendar_autotune


def informe(desafinacion, temblor=5.0, en_escala=True):
    return Informe(
        segundos=30.0,
        cantado=0.8,
        nota_grave="A2",
        nota_aguda="E4",
        comoda_grave="C3",
        comoda_aguda="C4",
        centro="G3",
        desafinacion=desafinacion,
        temblor=temblor,
        tonalidades=("Gm", "G#m", "F#m"),
        notas=12,
        corrimiento=0.0,
        relativa=5.0,
        en_escala=en_escala,
    )


@pytest.mark.parametrize(
    ("desafinacion", "nivel"),
    [
        (0, "ninguno"),
        (14.9, "ninguno"),
        (15, "suave"),
        (34.9, "suave"),
        (35, "marcado"),
        (80, "marcado"),
    ],
)
def test_regla_normal_por_desafinacion(desafinacion, nivel):
    assert recomendar_autotune(informe(desafinacion)).nivel == nivel


def test_si_la_voz_tiembla_mucho_sube_un_nivel():
    tiembla = recomendar_autotune(informe(8, temblor=35))
    assert tiembla.nivel == "suave"
    assert "tiembla" in tiembla.motivo
    assert recomendar_autotune(informe(20, temblor=35)).nivel == "marcado"
    assert recomendar_autotune(informe(50, temblor=35)).nivel == "marcado"


@pytest.mark.parametrize(
    ("exigencia", "desafinacion", "nivel"),
    [
        ("exigente", 12, "suave"),
        ("exigente", 26, "marcado"),
        ("relajado", 18, "ninguno"),
        ("relajado", 40, "suave"),
    ],
)
def test_otras_exigencias(exigencia, desafinacion, nivel):
    assert recomendar_autotune(informe(desafinacion), exigencia).nivel == nivel


def test_estilo_natural_nunca_pasa_de_suave():
    assert recomendar_autotune(informe(60), estilo="natural").nivel == "suave"
    assert recomendar_autotune(informe(5), estilo="natural").nivel == "ninguno"


def test_estilo_marcado_siempre_marcado_por_estetica():
    recomendacion = recomendar_autotune(informe(5), estilo="marcado")
    assert recomendacion.nivel == "marcado"
    assert "estilo" in recomendacion.motivo


def test_la_recomendacion_se_explica():
    ninguno = recomendar_autotune(informe(8))
    assert "8 cents" in ninguno.motivo and "15" in ninguno.motivo
    suave = recomendar_autotune(informe(22))
    assert "Graillon" in suave.consejo and "MAutoPitch" in suave.consejo
    assert "lento" in suave.consejo
    marcado = recomendar_autotune(informe(40))
    assert "rápido" in marcado.consejo


def test_resumen_de_una_linea():
    linea = recomendar_autotune(informe(22)).resumen()
    assert linea.startswith("Autotune: corrección suave · ")
    assert "\n" not in linea


def test_exigencias_disponibles():
    assert set(EXIGENCIAS) == {"normal", "exigente", "relajado"}


@pytest.mark.parametrize("argumentos", [{"exigencia": "extrema"}, {"estilo": "robot"}])
def test_rechaza_opciones_desconocidas(argumentos):
    with pytest.raises(ErrorVoz):
        recomendar_autotune(informe(10), **argumentos)


def test_sin_escala_fija_todavia_no_se_puede_medir():
    recomendacion = recomendar_autotune(informe(40, en_escala=False))
    assert recomendacion.nivel == "sin_medir"
    assert "--con-beat" in recomendacion.consejo
    assert recomendacion.resumen().startswith("Autotune: todavía no se puede medir")
    marcado = recomendar_autotune(informe(40, en_escala=False), estilo="marcado")
    assert marcado.nivel == "marcado"


def test_con_el_beat_de_referencia_la_regla_se_aplica_igual():
    recomendacion = recomendar_autotune(
        informe(25, en_escala=False), con_referencia=True
    )
    assert recomendacion.nivel == "suave"
    assert "beat" in recomendacion.motivo
    assert "melodía guía" in recomendacion.motivo
    limpio = recomendar_autotune(informe(8), con_referencia=True)
    assert limpio.nivel == "ninguno" and "melodía guía" not in limpio.motivo
