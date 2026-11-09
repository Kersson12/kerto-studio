import numpy as np
import pytest

from kerto.render.sala import aplicar_sala, limitar, masterizar, respuesta_de_sala
from kerto.render.sonidos import ErrorSonidos, cargar_sonidos

SR = 22050


def db(x):
    return 20 * np.log10(max(float(x), 1e-12))


def test_la_sala_es_estereo_y_se_apaga():
    ir = respuesta_de_sala(SR, segundos=1.0)
    assert ir.shape[0] == 2
    izquierda, derecha = ir
    assert (
        abs(np.corrcoef(izquierda, derecha)[0, 1]) < 0.2
    )  # suena distinto en cada lado
    decimo = ir.shape[1] // 10
    inicio = np.sqrt((ir[:, :decimo] ** 2).mean())
    final = np.sqrt((ir[:, -decimo:] ** 2).mean())
    assert db(inicio) - db(final) > 30


def test_aplicar_sala_quita_los_graves_y_guarda_el_largo():
    t = np.arange(SR) / SR
    grave = np.sin(2 * np.pi * 60 * t)
    agudo = np.sin(2 * np.pi * 2000 * t)
    ir = respuesta_de_sala(SR, segundos=0.5)
    humedo_grave = aplicar_sala(grave, ir, SR)
    humedo_agudo = aplicar_sala(agudo, ir, SR)
    assert humedo_grave.shape == (2, SR)
    assert db(np.abs(humedo_grave).max()) < db(np.abs(humedo_agudo).max()) - 12


def test_limitar_no_pasa_del_techo_y_no_toca_lo_bajo():
    azar = np.random.default_rng(0)
    fuerte = azar.normal(0, 0.6, (2, SR))
    assert np.abs(limitar(fuerte, SR, techo_db=-1.0)).max() <= 10 ** (-1 / 20) + 1e-9
    bajo = 0.1 * np.ones((2, 1000))
    assert np.allclose(limitar(bajo, SR, techo_db=-1.0), bajo)


def test_masterizar_sube_el_volumen_sin_pasar_el_techo():
    t = np.arange(SR * 2) / SR
    golpes = (np.sin(2 * np.pi * 80 * t) * (np.sin(2 * np.pi * 2 * t) > 0.9)) * 0.09
    mezcla = np.stack([golpes + 0.02 * np.sin(2 * np.pi * 500 * t)] * 2)
    salida = masterizar(mezcla, SR, rms_objetivo_db=-12.0, techo_db=-1.0)
    rms = db(np.sqrt((salida**2).mean()))
    assert rms > db(np.sqrt((mezcla**2).mean())) + 3
    assert np.abs(salida).max() <= 10 ** (-1 / 20) + 1e-9
    assert np.all(masterizar(np.zeros((2, 100)), SR) == 0)


def test_sonidos_con_sala():
    sonidos = cargar_sonidos("reggaeton")
    assert sonidos["bombo"].sala == 0 and sonidos["808"].sala == 0
    assert sonidos["caja"].sala > 0 and sonidos["pad"].sala > sonidos["hihat"].sala


@pytest.mark.parametrize("sala", ["1.5", "-0.1", "mucha"])
def test_sala_invalida(tmp_path, sala):
    (tmp_path / "prueba").mkdir()
    (tmp_path / "prueba" / "sonidos.yaml").write_text(
        f"caja: {{faust: caja, sala: {sala}}}\n", encoding="utf-8"
    )
    with pytest.raises(ErrorSonidos, match="sala"):
        cargar_sonidos("prueba", carpeta=tmp_path)
