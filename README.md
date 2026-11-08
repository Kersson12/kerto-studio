# Kerto Studio

Kerto convierte a [Claude Code](https://claude.com/claude-code) en un equipo de producción musical gratis y open source: compone el beat, analiza tu voz, recomienda autotune, mezcla y masteriza. Cada género llega como un pack; el primero es reggaetón.

*Kerto turns Claude Code into a free, open source music production team: beats, vocal coaching, autotune advice, mixing and mastering. English docs arrive with v0.1.*

**Estado:** en construcción, Fase 1 de [PLAN.md](PLAN.md) (primer beat).

## Primer beat

```bash
uv sync
uv run kerto beat --genero reggaeton --bpm 95 --tonalidad Am --compases 8 --variaciones 3
```

Crea tres variaciones (clásico, movido y oscuro) en MIDI y WAV dentro de `canciones/borrador/beats/`. Con [Surge XT](https://surge-synthesizer.github.io) instalado, el bombo, la caja y el 808 suenan con sus patches de fábrica; sin él, suena el sintetizador interno. Los sonidos de cada género están en `generos/<genero>/sonidos.yaml`.

## Desarrollo

Solo necesitas [uv](https://github.com/astral-sh/uv); instala Python por su cuenta.

```bash
uv sync
uv run pytest
uv run kerto --help
```

## Licencia

[GPL-3.0](LICENSE). Los plugins de audio se descargan de sus sitios oficiales: este repo no redistribuye binarios ajenos.
