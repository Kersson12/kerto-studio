import itertools
from fractions import Fraction

import pytest

from kerto.ritmos.motor import ErrorBeat, crear_beat, estructura
from kerto.ritmos.pack import ErrorPack, cargar_pack, generos_disponibles

PACK_PRUEBA = """
nombre: prueba
descripcion: pack mínimo para los tests
compas: 4/4
paso: 1/16
bpm: {min: 80, max: 110, defecto: 95}
tonalidad: Am
frase: 4
humanizar: {tiempo: 1/384, fuerza: 6}
instrumentos:
  bombo: {nota: C2}
  caja: {nota: D2}
  808: {grave: E1, largo: 1/4, programa: 38}
variaciones:
  - nombre: uno
    descripcion: la base
    progresion: i VI III VII
    patrones:
      bombo: "x...x...x...x..."
      caja: "...x..x....x..x."
      808: "X..x..x.X..x..x."
  - nombre: dos
    progresion: i VII
    patrones:
      bombo: "X...x...X...x..."
      caja: "...x..x....x..x. | ...x..x....x.xxx"
      808: "X..............."
transiciones:
  relleno:
    caja: "...x..x....xxxxx"
  corte:
    bombo: "x...x...x......."
    808: "X..x..x........."
"""

R = Fraction


def escribir_pack(carpeta, texto=PACK_PRUEBA, nombre="prueba"):
    destino = carpeta / nombre
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "pack.yaml").write_text(texto, encoding="utf-8")
    return carpeta


@pytest.fixture
def generos(tmp_path):
    return escribir_pack(tmp_path)


@pytest.fixture
def pack(generos):
    return cargar_pack("prueba", carpeta=generos)


def notas_de(beat, instrumento):
    return next(p for p in beat.pistas if p.nombre == instrumento).notas


# --- Packs ---


def test_cargar_pack_lee_datos_generales(pack):
    assert pack.nombre == "prueba"
    assert pack.compas == "4/4"
    assert (pack.bpm_min, pack.bpm_defecto, pack.bpm_max) == (80, 95, 110)
    assert pack.tonalidad == "Am"
    assert pack.frase == 4
    assert (pack.humanizar_tiempo, pack.humanizar_fuerza) == (R(1, 384), 6)


def test_cargar_pack_lee_instrumentos_de_bateria_y_melodicos(pack):
    assert list(pack.instrumentos) == ["bombo", "caja", "808"]
    assert pack.instrumentos["bombo"].nota == 36
    assert pack.instrumentos["bombo"].bateria
    bajo = pack.instrumentos["808"]
    assert not bajo.bateria
    assert (bajo.grave, bajo.largo, bajo.programa) == (28, R(1, 4), 38)


def test_cargar_pack_lee_variaciones_y_patrones(pack):
    assert [v.nombre for v in pack.variaciones] == ["uno", "dos"]
    uno = pack.variaciones[0]
    assert uno.progresion == "i VI III VII"
    assert [g.inicio for g in uno.patrones["bombo"].golpes] == [
        R(0),
        R(1, 4),
        R(1, 2),
        R(3, 4),
    ]
    assert pack.variaciones[1].patrones["caja"].duracion == 2


def test_generos_disponibles(generos):
    escribir_pack(generos, PACK_PRUEBA.replace("prueba", "otro"), "otro")
    (generos / "sin_pack").mkdir()
    assert generos_disponibles(generos) == ("otro", "prueba")


def test_genero_inexistente_dice_cuales_hay(generos):
    with pytest.raises(ErrorPack, match="prueba"):
        cargar_pack("cumbia", carpeta=generos)


@pytest.mark.parametrize(
    ("viejo", "nuevo", "mensaje"),
    [
        ('bombo: "x...x...x...x..."', 'bombo: "x...x...x...x.."', "bombo"),
        ('808: "X..x..x.X..x..x."', 'hihat: "x.x.x.x.x.x.x.x."', "hihat"),
        ('808: "X..x..x.X..x..x."', "", "808"),
        (
            'caja: "...x..x....xxxxx"',
            'caja: "...x..x....xxxxx...x..x....xxxxx"',
            "1 compás",
        ),
        ("relleno:", "salto:", "salto"),
        ("progresion: i VII", "progresion: i VIII", "VIII"),
        ("defecto: 95", "defecto: 120", "bpm"),
        ("caja: {nota: D2}", "caja: {}", "caja"),
        ("compas: 4/4", "compas: cuatro", "cuatro"),
        ("frase: 4", "frase: 0", "frase"),
        ('bombo: "x...x...x...x..."', 'bombo: "x...k...x...x..."', "bombo"),
    ],
)
def test_pack_invalido_explica_el_error(generos, viejo, nuevo, mensaje):
    escribir_pack(generos, PACK_PRUEBA.replace(viejo, nuevo, 1))
    with pytest.raises(ErrorPack, match=mensaje):
        cargar_pack("prueba", carpeta=generos)


def test_pack_que_no_es_un_mapa(generos):
    escribir_pack(generos, "- solo\n- una lista\n")
    with pytest.raises(ErrorPack, match="pack.yaml"):
        cargar_pack("prueba", carpeta=generos)


def test_pack_con_yaml_roto(generos):
    escribir_pack(generos, "nombre: [sin cerrar\n")
    with pytest.raises(ErrorPack, match="YAML"):
        cargar_pack("prueba", carpeta=generos)


def test_carpeta_de_generos_inexistente(tmp_path):
    assert generos_disponibles(tmp_path / "no_existe") == ()
    with pytest.raises(ErrorPack, match="ninguno"):
        cargar_pack("prueba", carpeta=tmp_path / "no_existe")


@pytest.mark.parametrize(
    ("viejo", "nuevo", "mensaje"),
    [
        ("tonalidad: Am\n", "", "tonalidad"),
        ("tonalidad: Am", "tonalidad: H", "tonalidad"),
        ("bpm: {min: 80, max: 110, defecto: 95}", "bpm: 95", "bpm"),
        ("humanizar: {tiempo: 1/384, fuerza: 6}", "humanizar: 3", "humanizar"),
        ("fuerza: 6", "fuerza: -1", "fuerza"),
        ("tiempo: 1/384", "tiempo: rápido", "tiempo"),
        ("largo: 1/4", "largo: 0", "largo"),
        ("programa: 38", "programa: 200", "programa"),
        ("caja: {nota: D2}", "caja: D2", "caja"),
        ("caja: {nota: D2}", "caja: {nota: H2}", "caja"),
        ("instrumentos:", "instrumentos: {}\notros:", "instrumentos"),
        ("variaciones:", "variaciones: {}\notras:", "variaciones"),
        ("  - nombre: dos\n", "  - descripcion: sin nombre\n", "nombre"),
        ("nombre: dos", "nombre: uno", "mismo nombre"),
        ("progresion: i VII", "progresion: ''", "progresión"),
        ("transiciones:", "transiciones: 5\nviejas:", "transiciones"),
        ('relleno:\n    caja: "...x..x....xxxxx"', "relleno: [x]", "mapa"),
    ],
)
def test_pack_con_claves_mal_escritas(generos, viejo, nuevo, mensaje):
    assert viejo in PACK_PRUEBA
    escribir_pack(generos, PACK_PRUEBA.replace(viejo, nuevo, 1))
    with pytest.raises(ErrorPack, match=mensaje):
        cargar_pack("prueba", carpeta=generos)


# --- Estructura de compases ---


@pytest.mark.parametrize(
    ("compases", "esperada"),
    [
        (8, "base base base relleno base base base corte"),
        (4, "base base base corte"),
        (2, "base base"),
        (6, "base base base relleno base corte"),
        (12, "base base base relleno base base base relleno base base base corte"),
    ],
)
def test_estructura_pone_relleno_al_final_de_frase_y_corte_al_final(compases, esperada):
    assert estructura(compases, frase=4) == tuple(esperada.split())


@pytest.mark.parametrize(("compases", "frase"), [(0, 4), (4, 0)])
def test_estructura_rechaza_valores_no_positivos(compases, frase):
    with pytest.raises(ErrorBeat):
        estructura(compases, frase)


# --- Beat sin humanizar ---


def test_beat_lleva_datos_y_una_pista_por_instrumento(pack):
    beat = crear_beat(pack, compases=8, humanizar=False)
    assert (beat.genero, beat.variacion, beat.bpm, beat.tonalidad) == (
        "prueba",
        "uno",
        95,
        "Am",
    )
    assert (beat.compas, beat.compases, beat.duracion) == ("4/4", 8, 8)
    assert [p.nombre for p in beat.pistas] == ["bombo", "caja", "808"]
    assert beat.acordes == ("Am", "F", "C", "G", "Am", "F", "C", "G")


def test_bombo_sigue_el_patron_y_el_corte_del_ultimo_compas(pack):
    bombo = notas_de(crear_beat(pack, compases=8, humanizar=False), "bombo")
    assert len(bombo) == 7 * 4 + 3
    assert [n.inicio for n in bombo[:5]] == [R(0), R(1, 4), R(1, 2), R(3, 4), R(1)]
    assert {n.tono for n in bombo} == {36}
    assert {n.velocidad for n in bombo} == {100}
    assert {n.duracion for n in bombo} == {R(1, 16)}


def test_caja_usa_el_relleno_al_final_de_la_frase(pack):
    caja = notas_de(crear_beat(pack, compases=8, humanizar=False), "caja")
    compas_4 = [n.inicio - 3 for n in caja if 3 <= n.inicio < 4]
    assert compas_4 == [R(k, 16) for k in (3, 6, 11, 12, 13, 14, 15)]


def test_808_sigue_las_raices_de_la_progresion_en_la_octava_grave(pack):
    bajo = notas_de(crear_beat(pack, compases=4, humanizar=False), "808")
    primeras = {n.inicio: n.tono for n in bajo if n.inicio in (0, 1, 2, 3)}
    assert primeras == {R(0): 33, R(1): 29, R(2): 36, R(3): 31}
    assert bajo[0].velocidad == 120


def test_808_dura_hasta_el_siguiente_golpe_con_tope(pack):
    bajo = notas_de(crear_beat(pack, compases=1, humanizar=False), "808")
    assert [n.duracion for n in bajo] == [R(3, 16), R(3, 16), R(2, 16)] * 2
    largo = notas_de(crear_beat(pack, "dos", compases=1, humanizar=False), "808")
    assert [n.duracion for n in largo] == [R(1, 4)]


def test_patron_de_dos_compases_se_repite(pack):
    caja = notas_de(crear_beat(pack, "dos", compases=3, humanizar=False), "caja")
    compas_2 = [n.inicio - 1 for n in caja if 1 <= n.inicio < 2]
    compas_3 = [n.inicio - 2 for n in caja if 2 <= n.inicio < 3]
    assert compas_2 == [R(k, 16) for k in (3, 6, 11, 13, 14, 15)]
    assert compas_3 == [R(k, 16) for k in (3, 6, 11, 14)]


def test_variacion_por_indice_o_nombre(pack):
    assert crear_beat(pack, 1, humanizar=False).variacion == "dos"
    assert crear_beat(pack, "dos", humanizar=False).acordes[:2] == ("Am", "G")


def test_tonalidad_y_progresion_se_pueden_cambiar(pack):
    beat = crear_beat(
        pack, tonalidad="Em", progresion="i iv", compases=2, humanizar=False
    )
    assert beat.tonalidad == "Em"
    assert beat.acordes == ("Em", "Am")
    assert notas_de(beat, "808")[0].tono == 28


@pytest.mark.parametrize(
    "argumentos",
    [
        {"variacion": "tres"},
        {"variacion": 5},
        {"bpm": 20},
        {"bpm": 400},
        {"compases": 0},
        {"tonalidad": "H"},
        {"progresion": "i IX"},
        {"progresion": "   "},
    ],
)
def test_crear_beat_rechaza_argumentos_invalidos(pack, argumentos):
    with pytest.raises(ErrorBeat):
        crear_beat(pack, **argumentos)


# --- Humanización ---


def test_humanizar_es_determinista_con_la_misma_semilla(pack):
    assert crear_beat(pack, semilla=7) == crear_beat(pack, semilla=7)
    assert crear_beat(pack, semilla=7) != crear_beat(pack, semilla=8)


def test_humanizar_es_suave(pack):
    recto = crear_beat(pack, compases=8, humanizar=False)
    humano = crear_beat(pack, compases=8, semilla=3)
    for pista_recta, pista_humana in zip(recto.pistas, humano.pistas, strict=True):
        assert len(pista_recta.notas) == len(pista_humana.notas)
        for a, b in zip(pista_recta.notas, pista_humana.notas, strict=True):
            assert abs(b.inicio - a.inicio) <= R(1, 384)
            assert b.inicio >= 0
            assert abs(b.velocidad - a.velocidad) <= 6
            assert 1 <= b.velocidad <= 127
    assert any(
        a.inicio != b.inicio
        for p, q in zip(recto.pistas, humano.pistas, strict=True)
        for a, b in zip(p.notas, q.notas, strict=True)
    )


def test_humanizar_no_solapa_notas_del_mismo_tono(pack):
    for semilla in range(20):
        for pista in crear_beat(pack, compases=8, semilla=semilla).pistas:
            notas = sorted(pista.notas, key=lambda n: n.inicio)
            for actual, siguiente in itertools.pairwise(notas):
                if actual.tono == siguiente.tono:
                    assert actual.inicio + actual.duracion <= siguiente.inicio
                assert actual.duracion > 0


# --- Capa de acordes ---

CAPAS = """
acordes:
  pad: {patron: "X... .... .... ....", octava: 3, largo: 1, programa: 89}
  teclado: {patron: "x..x ..x. x..x ..x.", octava: 4, largo: 1/8}
  arpegio: {patron: "x.x. x.x. x.x. x.x.", octava: 4, largo: 1/8, arpegio: true}
"""


@pytest.fixture
def pack_con_acordes(tmp_path):
    return cargar_pack("prueba", carpeta=escribir_pack(tmp_path, PACK_PRUEBA + CAPAS))


def test_cargar_capas_de_acordes(pack_con_acordes):
    capas = pack_con_acordes.acordes
    assert list(capas) == ["pad", "teclado", "arpegio"]
    assert (capas["pad"].octava, capas["pad"].largo, capas["pad"].programa) == (
        3,
        1,
        89,
    )
    assert capas["arpegio"].arpegio and not capas["pad"].arpegio
    assert capas["teclado"].patron.pasos == 16


def test_el_pack_sin_acordes_no_tiene_capas(pack):
    assert pack.acordes == {}


@pytest.mark.parametrize(
    ("viejo", "nuevo", "mensaje"),
    [
        (
            'patron: "X... .... .... ....", octava: 3',
            'patron: "X...", octava: 3',
            "pad",
        ),
        ("octava: 3, largo: 1", "octava: 9, largo: 1", "octava"),
        ("arpegio: true", "arpegio: 3", "arpegio"),
        ("  teclado: {", "  teclado: 5\n  otro: {", "teclado"),
        ("acordes:\n", "acordes: 5\nviejo:\n", "mapa"),
        ("  pad: {", "  bombo: {", "instrumento"),
    ],
)
def test_capas_invalidas(tmp_path, viejo, nuevo, mensaje):
    escribir_pack(tmp_path, PACK_PRUEBA + CAPAS.replace(viejo, nuevo, 1))
    with pytest.raises(ErrorPack, match=mensaje):
        cargar_pack("prueba", carpeta=tmp_path)


def test_pad_toca_los_acordes_de_la_progresion(pack_con_acordes):
    beat = crear_beat(pack_con_acordes, acordes="pad", compases=2, humanizar=False)
    pad = next(p for p in beat.pistas if p.nombre == "pad")
    assert (pad.bateria, pad.programa) == (False, 89)
    por_inicio = {}
    for nota in pad.notas:
        por_inicio.setdefault(nota.inicio, []).append(nota.tono)
    assert por_inicio == {R(0): [57, 60, 64], R(1): [53, 57, 60]}  # Am y F
    assert {n.duracion for n in pad.notas} == {R(1)}


def test_en_el_corte_los_acordes_se_callan_en_el_ultimo_tiempo(pack_con_acordes):
    beat = crear_beat(pack_con_acordes, acordes="pad", compases=4, humanizar=False)
    pad = next(p for p in beat.pistas if p.nombre == "pad")
    ultimo = [n for n in pad.notas if n.inicio >= 3]
    assert ultimo and all(n.inicio + n.duracion <= R(3) + R(3, 4) for n in ultimo)
    teclado = crear_beat(
        pack_con_acordes, acordes="teclado", compases=4, humanizar=False
    )
    golpes = next(p for p in teclado.pistas if p.nombre == "teclado").notas
    assert all(n.inicio < R(3) + R(3, 4) for n in golpes)


def test_teclado_marca_el_acorde_en_cada_golpe(pack_con_acordes):
    beat = crear_beat(pack_con_acordes, acordes="teclado", compases=1, humanizar=False)
    teclado = next(p for p in beat.pistas if p.nombre == "teclado").notas
    assert len(teclado) == 6 * 3
    assert {n.tono for n in teclado} == {69, 72, 76}  # A4 C5 E5
    assert {n.duracion for n in teclado} == {R(1, 8)}


def test_arpegio_recorre_el_acorde_nota_por_nota(pack_con_acordes):
    beat = crear_beat(pack_con_acordes, acordes="arpegio", compases=1, humanizar=False)
    arpegio = next(p for p in beat.pistas if p.nombre == "arpegio").notas
    assert [n.tono for n in arpegio] == [69, 72, 76, 81] * 2


def test_sin_acordes_no_hay_capa_y_capa_desconocida_falla(pack_con_acordes):
    nombres = [p.nombre for p in crear_beat(pack_con_acordes, humanizar=False).pistas]
    assert nombres == ["bombo", "caja", "808"]
    with pytest.raises(ErrorBeat, match="pad, teclado, arpegio"):
        crear_beat(pack_con_acordes, acordes="violin")
