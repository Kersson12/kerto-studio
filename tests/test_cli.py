import pytest

from kerto import __version__
from kerto.cli import main


def test_version_muestra_nombre_y_version(capsys):
    with pytest.raises(SystemExit) as salida:
        main(["--version"])
    assert salida.value.code == 0
    assert capsys.readouterr().out.strip() == f"kerto {__version__}"


def test_sin_argumentos_muestra_la_ayuda(capsys):
    assert main([]) == 0
    salida = capsys.readouterr().out
    assert "kerto" in salida and "--version" in salida


def test_notacion_valida_y_resume(capsys):
    assert main(["notacion", "C4:1/2 E4:1/2 | G4:1"]) == 0
    assert capsys.readouterr().out.strip() == (
        "OK · 3 eventos · 2 compases de 4/4 · rango C4–G4"
    )


def test_notacion_acepta_varios_argumentos_y_otro_compas(capsys):
    assert main(["notacion", "C4:1/2", "E4:1/4", "|", "G4:3/4", "--compas", "3/4"]) == 0
    assert "2 compases de 3/4" in capsys.readouterr().out


def test_notacion_explica_el_error_y_sale_con_1(capsys):
    assert main(["notacion", "C4:1 | E4:1/2"]) == 1
    salida = capsys.readouterr()
    assert salida.out == ""
    assert "compás 2" in salida.err
