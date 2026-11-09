"""Exportación a MIDI: un archivo tipo 1 con una pista por instrumento.

Se escribe con mido, pulso a pulso, para que los tiempos sean exactos.
Se lee con pretty_midi para dar un resumen corto en vez del archivo entero.
"""

from fractions import Fraction
from pathlib import Path

import mido
import pretty_midi

from kerto.notacion import duracion_compas
from kerto.ritmos.motor import Beat, Pista

PULSOS_POR_NEGRA = 480
PULSOS_POR_REDONDA = 4 * PULSOS_POR_NEGRA
CANAL_BATERIA = 9  # el canal 10 de General MIDI, contando desde 0
_CANALES_MELODICOS = tuple(c for c in range(16) if c != CANAL_BATERIA)


def _pulsos(tiempo: Fraction) -> int:
    return round(tiempo * PULSOS_POR_REDONDA)


def exportar_midi(beat: Beat, ruta: Path) -> Path:
    """Escribe el beat en `ruta` (crea las carpetas que falten) y devuelve la ruta."""
    midi = mido.MidiFile(type=1, ticks_per_beat=PULSOS_POR_NEGRA)
    fin = _pulsos(beat.duracion)
    midi.tracks.append(_pista_de_tempo(beat, fin))
    melodicas = iter(_CANALES_MELODICOS)
    for pista in beat.pistas:
        canal = CANAL_BATERIA if pista.bateria else next(melodicas)
        midi.tracks.append(_pista_midi(pista, canal, fin))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    midi.save(ruta)
    return ruta


def _pista_de_tempo(beat: Beat, fin: int) -> mido.MidiTrack:
    """Tempo, compás y una marca por sección (Waveform las muestra en la regla)."""
    numerador, denominador = (int(parte) for parte in beat.compas.split("/"))
    mensajes = [
        mido.MetaMessage(
            "track_name", name=f"Kerto · {beat.genero} · {beat.variacion}"
        ),
        mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(beat.bpm)),
        mido.MetaMessage(
            "time_signature", numerator=numerador, denominator=denominador
        ),
    ]
    compas = _pulsos(duracion_compas(beat.compas))
    anterior = 0
    for marca in beat.secciones:
        pulso = marca.compas * compas
        mensajes.append(
            mido.MetaMessage("marker", text=marca.nombre, time=pulso - anterior)
        )
        anterior = pulso
    mensajes.append(mido.MetaMessage("end_of_track", time=fin - anterior))
    return mido.MidiTrack(mensajes)


def _pista_midi(pista: Pista, canal: int, fin: int) -> mido.MidiTrack:
    eventos: list[tuple[int, int, mido.Message | mido.MetaMessage]] = []
    for indice, nota in enumerate(pista.notas):
        inicio = _pulsos(nota.inicio)
        final = max(inicio + 1, _pulsos(nota.inicio + nota.duracion))
        if indice < len(pista.letras):
            # La sílaba justo antes de su nota: Waveform y los karaokes la muestran.
            eventos.append(
                (inicio, 1, mido.MetaMessage("lyrics", text=pista.letras[indice]))
            )
        eventos.append(
            (
                inicio,
                2,
                mido.Message(
                    "note_on", channel=canal, note=nota.tono, velocity=nota.velocidad
                ),
            )
        )
        eventos.append(
            (final, 0, mido.Message("note_off", channel=canal, note=nota.tono))
        )
    # En el mismo pulso: se apaga la nota vieja, va la sílaba y suena la nueva.
    eventos.sort(key=lambda evento: (evento[0], evento[1]))
    mensajes: list[mido.Message | mido.MetaMessage] = [
        mido.MetaMessage("track_name", name=pista.nombre)
    ]
    if pista.programa is not None and not pista.bateria:
        mensajes.append(
            mido.Message("program_change", channel=canal, program=pista.programa)
        )
    anterior = 0
    for pulso, _, mensaje in eventos:
        mensajes.append(mensaje.copy(time=pulso - anterior))
        anterior = pulso
    mensajes.append(mido.MetaMessage("end_of_track", time=max(0, fin - anterior)))
    return mido.MidiTrack(mensajes)


def resumir_midi(ruta: Path) -> str:
    """'5 pistas (bombo 31, caja 36, … 808 47 notas) · 20.2 s'."""
    instrumentos = pretty_midi.PrettyMIDI(str(ruta)).instruments
    detalle = ", ".join(f"{i.name} {len(i.notes)}" for i in instrumentos)
    segundos = mido.MidiFile(ruta).length
    return f"{len(instrumentos)} pistas ({detalle} notas) · {segundos:.1f} s"
