# Kerto Studio

Kerto convierte a [Claude Code](https://claude.com/claude-code) en un equipo de producción musical gratis y open source: compone el beat, analiza tu voz, recomienda autotune, mezcla y masteriza. Cada género llega como un pack; el primero es reggaetón.

*Kerto turns Claude Code into a free, open source music production team: beats, vocal coaching, autotune advice, mixing and mastering. English docs arrive with v0.1.*

**Estado:** en construcción, Fase 0 de [PLAN.md](PLAN.md).

## Desarrollo

Solo necesitas [uv](https://github.com/astral-sh/uv); instala Python por su cuenta.

```bash
uv sync
uv run pytest
uv run kerto --help
```

## Licencia

[GPL-3.0](LICENSE). Los plugins de audio se descargan de sus sitios oficiales: este repo no redistribuye binarios ajenos.
