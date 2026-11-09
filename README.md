# Kerto Studio

Kerto convierte a [Claude Code](https://claude.com/claude-code) en un equipo de producción musical gratis y open source: compone el beat, analiza tu voz, recomienda autotune, mezcla y masteriza. Cada género llega como un pack; el primero es reggaetón.

*Kerto turns Claude Code into a free, open source music production team: beats, vocal coaching, autotune advice, mixing and mastering. English docs arrive with v0.1.*

**Estado:** en construcción, Fase 4 de [PLAN.md](PLAN.md) (Claude Code conectado).

## Hablarle a tu equipo

Abre la carpeta en Claude Code y la primera vez aprueba el servidor MCP `kerto` (está en `.mcp.json`). Después pídelo en lenguaje normal:

- "hazme un perreo en La menor a 95" crea el beat sin escribir comandos.
- `/nueva-cancion perreo oscuro de discoteca` arma una canción nueva con su `cancion.yaml`.
- `/analiza-mi-voz luna-negra` revisa tus tomas y te dice qué autotune usar.
- `/mezcla luna-negra` mezcla y masteriza (llega en la Fase 5).

El equipo está en `.claude/agents/`: productor, coach-vocal, letrista, ingeniero-mezcla y critico-ar. Las skills de `.claude/skills/` les enseñan teoría, voz, mezcla, plugins gratis y cada género. Para comprobar que las skills se activan cuando toca: `uv run python evals/skills/probar_activacion.py` (usa sesiones reales de Claude).

## Primer beat

```bash
uv sync
uv run kerto beat --genero reggaeton --bpm 95 --tonalidad Am --compases 8 --variaciones 3
```

Crea tres variaciones (clásico, movido y oscuro) en MIDI y WAV dentro de `canciones/borrador/beats/`. Con [Surge XT](https://surge-synthesizer.github.io) instalado, el bombo, la caja y el 808 suenan con sus patches de fábrica; sin él, suena el sintetizador interno. Los sonidos de cada género están en `generos/<genero>/sonidos.yaml`.

## Canción completa

```bash
uv run kerto cancion render --cancion <nombre>
```

Lee `canciones/<nombre>/cancion.yaml` (género, variación, tonalidad, BPM y secciones) y `letra.md` (una línea por compás) y escribe en `canciones/<nombre>/cancion/` un MIDI con todas las pistas, un MIDI por pista, el WAV guía con una melodía hecha a tu rango y el WAV instrumental. Géneros: reggaetón y trap.

## Desarrollo

Solo necesitas [uv](https://github.com/astral-sh/uv); instala Python por su cuenta.

```bash
uv sync
uv run pytest
uv run kerto --help
```

## Licencia

[GPL-3.0](LICENSE). Los plugins de audio se descargan de sus sitios oficiales: este repo no redistribuye binarios ajenos.
