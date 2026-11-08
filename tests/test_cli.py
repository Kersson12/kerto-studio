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
