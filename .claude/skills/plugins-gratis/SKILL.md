---
name: plugins-gratis
description: "Los programas y plugins gratis de Kerto (Waveform Free, Surge XT, Vital, Graillon, MAutoPitch, TDR Nova, Valhalla Supermassive): para qué sirve cada uno, de qué sitio oficial bajarlo, cómo instalarlo y dónde busca el motor los VST3. Úsala siempre que el usuario pregunte qué DAW, sintetizador, autotune, ecualizador o reverb usar, cómo instalar un plugin o VST, por qué un plugin no aparece o no suena, o pida alternativas gratis a un programa de pago."
---

# Plugins gratis

Todo es gratis y legal. Kerto nunca redistribuye binarios ajenos: cada programa se baja de su sitio oficial. Nada de software pirata ni de copias no oficiales: pueden traer malware.

## La lista

| Programa | Para qué | Sitio oficial | Fase |
| --- | --- | --- | --- |
| Waveform Free | DAW: grabar la voz, escuchar y armar la canción | tracktion.com (pide una cuenta gratis) | 5 |
| Surge XT | Sintetizador de bajos, pads y leads; el motor lo usa para renderizar | surge-synthesizer.github.io | 1 |
| Vital | Sintetizador para leads y 808 (versión gratis) | vital.audio | opcional |
| Graillon | Autotune en vivo mientras grabas (edición gratis) | auburnsounds.com | 5 |
| MAutoPitch | Autotune alternativo, en el paquete gratis de MeldaProduction | meldaproduction.com | 5 |
| TDR Nova | Ecualizador dinámico para la voz | tokyodawn.net | 5 |
| Valhalla Supermassive | Reverb y delay | valhalladsp.com | 5 |

Si el usuario pide uno que no está en la lista, propón primero el de la lista que hace lo mismo y explica por qué.

## Instalar en Windows

- Surge XT se puede instalar con `winget install --id SurgeSynth.SurgeXT` (es la versión oficial de GitHub). Waveform Free no está en winget: se baja de tracktion.com.
- Los plugins VST3 van en `C:\Program Files\Common Files\VST3`. Ahí los encuentran el motor y Waveform.
- El motor busca Surge XT en `...\VST3\Surge Synth Team\Surge XT.vst3` y sus sonidos en `C:\ProgramData\Surge XT\patches_factory`. Si no lo encuentra, usa sus voces internas (Faust) y lo dice en el resumen como "sonido: Faust".

## Cuando algo no suena

1. El resumen de `crear_beat` dice qué motor usó cada instrumento: si dice Faust donde esperabas Surge XT, Surge no está instalado o el sonido (patch) no existe.
2. Los sonidos se eligen en `generos/<genero>/sonidos.yaml` con su nombre de fábrica, como `Basses/Sub Square`.
3. En Waveform, si un plugin no aparece, hay que buscar plugins otra vez en su configuración.

## Reglas

- Recomienda solo programas gratis de esta lista o equivalentes oficiales; nunca cracks.
- Explica cada programa en una frase, sin jerga.
