"""Sintetizador interno de Kerto, escrito en Faust: el respaldo cuando no hay Surge XT.

Cada voz es polifónica y responde a freq, gain y gate, que DawDreamer llena
con las notas MIDI. `caida(t)` es un golpe que se apaga en t segundos (-60 dB).
"""

_CABECERA = """import("stdfaust.lib");
freq = hslider("freq", 440, 20, 20000, 0.01);
gain = hslider("gain", 0.8, 0, 1, 0.001);
gate = button("gate");
golpe = gate > gate';
caida(t) = golpe : + ~ *(exp(-6.91 / (t * ma.SR)));
effect = _, _;
"""

VOCES: dict[str, str] = {
    # Bombo grave con barrido de tono y algo de saturación.
    "bombo": "process = os.osc(50 + 110 * caida(0.08)) * caida(0.45) * gain * 1.5"
    " : ma.tanh <: _, _;",
    # Caja: cuerpo afinado más ruido filtrado.
    "caja": "process = (os.osc(190 * (1 + 0.5 * caida(0.02))) * caida(0.12) * 0.6"
    " + (no.noise : fi.highpass(2, 1800) : fi.lowpass(2, 9000)) * caida(0.18))"
    " * gain <: _, _;",
    # Hi-hat cerrado: ruido agudo y corto.
    "hihat": "process = no.noise : fi.highpass(4, 7000) : fi.lowpass(2, 13000)"
    " * caida(0.05) * gain <: _, _;",
    # Conga: tono de la nota con un pequeño golpe de afinación.
    "conga": "process = os.osc(freq * (1 + 0.15 * caida(0.03))) * caida(0.22)"
    " * gain <: _, _;",
    # Sub para el 808: seno saturado que se sostiene mientras dura la nota.
    "sub": "process = os.osc(freq) * (gate : si.smooth(ba.tau2pole(0.005)))"
    " * (0.6 + 0.4 * caida(0.6)) * gain * 1.6 : ma.tanh <: _, _;",
    # Pad: dos sierras apenas desafinadas, filtradas y con entrada lenta.
    "pad": "process = (os.sawtooth(freq) + os.sawtooth(freq * 1.006)) * 0.5"
    " : fi.lowpass(2, 1600) * (gate : si.smooth(ba.tau2pole(0.25))) * gain * 0.5"
    " <: _, _;",
    # Teclado: piano eléctrico simple, con armónicos que se apagan.
    "teclado": "process = (os.osc(freq) + 0.3 * os.osc(2 * freq) + 0.1 * os.osc(3 * freq))"
    " * caida(1.2) * (gate : si.smooth(ba.tau2pole(0.02))) * gain * 0.5 <: _, _;",
    # Guía: seno con un poco de vibrato y su octava suave, para la melodía guía.
    "guia": "vib = 1 + 0.003 * os.osc(5);"
    " process = (os.osc(freq * vib) + 0.25 * os.osc(2 * freq * vib))"
    " * (gate : si.smooth(ba.tau2pole(0.03))) * gain * 0.6 <: _, _;",
    # Pluck: sierra con filtro que se cierra rápido, para arpegios.
    "pluck": "process = os.sawtooth(freq) : fi.lowpass(2, 700 + 4000 * caida(0.15))"
    " * caida(0.5) * gain * 0.5 <: _, _;",
}


def dsp(voz: str) -> str:
    """Código Faust completo de una voz."""
    return _CABECERA + VOCES[voz]
