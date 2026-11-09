"""Las skills propias de .claude/skills están bien formadas y no chocan con nada."""

from pathlib import Path

import yaml

from kerto.ritmos.pack import generos_disponibles

SKILLS = Path(".claude/skills")
COMANDOS = Path(".claude/commands")
PROPIAS = {
    "notacion-compacta",
    "teoria-musical",
    "coach-vocal",
    "mezcla-y-master",
    "plugins-gratis",
}
LARGO_DESCRIPCION = 1024  # límite de Claude Code
LINEAS_MAXIMAS = 500  # lo que recomienda skill-creator


def skills() -> dict[str, tuple[dict, str]]:
    leidas = {}
    for ruta in sorted(SKILLS.glob("*/SKILL.md")):
        _, cabecera, cuerpo = ruta.read_text(encoding="utf-8").split("---", 2)
        leidas[ruta.parent.name] = (yaml.safe_load(cabecera), cuerpo)
    return leidas


def test_estan_las_skills_propias_y_una_por_genero():
    esperadas = PROPIAS | {f"genero-{g}" for g in generos_disponibles()}
    assert set(skills()) == esperadas


def test_cada_skill_se_llama_como_su_carpeta_y_dice_cuando_usarla():
    for carpeta, (datos, cuerpo) in skills().items():
        assert datos["name"] == carpeta
        assert "Úsala" in datos["description"], carpeta
        assert len(datos["description"]) <= LARGO_DESCRIPCION, carpeta
        assert len(cuerpo.splitlines()) < LINEAS_MAXIMAS, carpeta


def test_ninguna_skill_tapa_un_comando():
    """Una skill con el nombre de un comando le gana y el comando deja de andar."""
    comandos = {ruta.stem for ruta in COMANDOS.glob("*.md")}
    assert not set(skills()) & comandos
