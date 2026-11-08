"""Packs de género: leen generos/<genero>/pack.yaml y validan instrumentos y patrones."""

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from kerto.notacion import (
    ErrorNotacion,
    Patron,
    duracion_compas,
    nota_a_midi,
    parse_patron,
)
from kerto.teoria.acordes import parse_tonalidad, progresion
from kerto.teoria.escalas import ErrorTeoria

GENEROS = Path(__file__).resolve().parents[2] / "generos"
ARCHIVO_PACK = "pack.yaml"
TRANSICIONES = ("relleno", "corte")
PASO_POR_DEFECTO = Fraction(1, 16)
FRASE_POR_DEFECTO = 4
LARGO_POR_DEFECTO = Fraction(1, 4)
HUMANIZAR_TIEMPO = Fraction(1, 384)
HUMANIZAR_FUERZA = 6
_CLAVES_OBLIGATORIAS = (
    "nombre",
    "compas",
    "bpm",
    "tonalidad",
    "instrumentos",
    "variaciones",
)


class ErrorPack(ValueError):
    """Pack de género que no existe o que está mal escrito."""


@dataclass(frozen=True)
class Instrumento:
    """Batería con nota fija (bombo en C2) o melódico con su nota más grave (808)."""

    nombre: str
    nota: int | None = None
    grave: int | None = None
    largo: Fraction = LARGO_POR_DEFECTO
    programa: int | None = None

    @property
    def bateria(self) -> bool:
        return self.nota is not None


@dataclass(frozen=True)
class Variacion:
    """Una versión del beat: sus patrones por instrumento y su progresión."""

    nombre: str
    descripcion: str
    progresion: str
    patrones: dict[str, Patron]


@dataclass(frozen=True)
class Pack:
    """Todo lo que el motor necesita saber de un género."""

    nombre: str
    descripcion: str
    compas: str
    paso: Fraction
    bpm_min: int
    bpm_max: int
    bpm_defecto: int
    tonalidad: str
    frase: int
    humanizar_tiempo: Fraction
    humanizar_fuerza: int
    instrumentos: dict[str, Instrumento]
    variaciones: tuple[Variacion, ...]
    transiciones: dict[str, dict[str, Patron]]

    @property
    def largo_compas(self) -> Fraction:
        return duracion_compas(self.compas)


def generos_disponibles(carpeta: Path = GENEROS) -> tuple[str, ...]:
    """Carpetas de `generos/` que tienen pack.yaml, en orden alfabético."""
    if not carpeta.is_dir():
        return ()
    return tuple(
        sorted(d.name for d in carpeta.iterdir() if (d / ARCHIVO_PACK).is_file())
    )


def cargar_pack(genero: str, carpeta: Path = GENEROS) -> Pack:
    """Lee y valida generos/<genero>/pack.yaml."""
    disponibles = generos_disponibles(carpeta)
    if genero not in disponibles:
        lista = ", ".join(disponibles) or "ninguno"
        raise ErrorPack(f"no hay pack para el género {genero!r}; disponibles: {lista}")
    ruta = carpeta / genero / ARCHIVO_PACK
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ErrorPack(f"{ruta} no es YAML válido: {error}") from error
    if not isinstance(datos, dict):
        raise ErrorPack(f"{ruta} debe ser un mapa de claves, como nombre: y compas:")
    faltan = [clave for clave in _CLAVES_OBLIGATORIAS if clave not in datos]
    if faltan:
        raise ErrorPack(f"a {ruta} le faltan las claves: {', '.join(faltan)}")
    try:
        return _armar_pack(datos)
    except ErrorPack as error:
        raise ErrorPack(f"pack {genero!r}: {error}") from error


def _armar_pack(datos: dict[str, Any]) -> Pack:
    compas = str(datos["compas"])
    try:
        duracion_compas(compas)
    except ErrorNotacion as error:
        raise ErrorPack(f"compas: {error}") from error
    paso = _fraccion(datos.get("paso", PASO_POR_DEFECTO), "paso")
    bpm_min, bpm_max, bpm_defecto = _bpm(datos["bpm"])
    tonalidad = _tonalidad(datos["tonalidad"])
    frase = datos.get("frase", FRASE_POR_DEFECTO)
    if not _entero_positivo(frase):
        raise ErrorPack(
            f"frase debe ser un número entero de compases mayor que 0, no {frase!r}"
        )
    tiempo, fuerza = _humanizacion(datos.get("humanizar") or {})
    instrumentos = _instrumentos(datos["instrumentos"])
    patrones = _LectorDePatrones(instrumentos, paso, compas)
    return Pack(
        nombre=str(datos["nombre"]),
        descripcion=str(datos.get("descripcion", "")),
        compas=compas,
        paso=paso,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
        bpm_defecto=bpm_defecto,
        tonalidad=tonalidad,
        frase=frase,
        humanizar_tiempo=tiempo,
        humanizar_fuerza=fuerza,
        instrumentos=instrumentos,
        variaciones=_variaciones(datos["variaciones"], patrones, tonalidad),
        transiciones=_transiciones(datos.get("transiciones") or {}, patrones),
    )


def _entero_positivo(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool) and valor > 0


def _fraccion(valor: object, campo: str, permitir_cero: bool = False) -> Fraction:
    try:
        fraccion = Fraction(str(valor))
    except (ValueError, ZeroDivisionError):
        raise ErrorPack(f"{campo}: {valor!r} no es una fracción como 1/16") from None
    if fraccion < 0 or (fraccion == 0 and not permitir_cero):
        raise ErrorPack(f"{campo} debe ser mayor que 0, no {valor!r}")
    return fraccion


def _bpm(datos: object) -> tuple[int, int, int]:
    claves = ("min", "max", "defecto")
    if not isinstance(datos, dict) or not all(
        _entero_positivo(datos.get(clave)) for clave in claves
    ):
        raise ErrorPack("bpm debe tener min, max y defecto como números enteros")
    minimo, maximo, defecto = (datos[clave] for clave in claves)
    if not minimo <= defecto <= maximo:
        raise ErrorPack(
            f"bpm: el defecto {defecto} está fuera del rango {minimo}–{maximo}"
        )
    return minimo, maximo, defecto


def _tonalidad(valor: object) -> str:
    try:
        return str(parse_tonalidad(str(valor)))
    except ErrorTeoria as error:
        raise ErrorPack(f"tonalidad: {error}") from error


def _humanizacion(datos: object) -> tuple[Fraction, int]:
    if not isinstance(datos, dict):
        raise ErrorPack("humanizar debe ser un mapa con tiempo y fuerza")
    tiempo = _fraccion(
        datos.get("tiempo", HUMANIZAR_TIEMPO), "humanizar.tiempo", permitir_cero=True
    )
    fuerza = datos.get("fuerza", HUMANIZAR_FUERZA)
    if not isinstance(fuerza, int) or isinstance(fuerza, bool) or fuerza < 0:
        raise ErrorPack(f"humanizar.fuerza debe ser un entero desde 0, no {fuerza!r}")
    return tiempo, fuerza


def _instrumentos(datos: object) -> dict[str, Instrumento]:
    if not isinstance(datos, dict) or not datos:
        raise ErrorPack("instrumentos debe ser un mapa con al menos un instrumento")
    return {
        str(nombre): _instrumento(str(nombre), valor) for nombre, valor in datos.items()
    }


def _instrumento(nombre: str, datos: object) -> Instrumento:
    datos = datos or {}
    if not isinstance(datos, dict):
        raise ErrorPack(
            f"el instrumento {nombre!r} debe ser un mapa, como {{nota: C2}}"
        )
    if ("nota" in datos) == ("grave" in datos):
        raise ErrorPack(
            f"el instrumento {nombre!r} necesita una sola clave: nota (batería, como C2)"
            " o grave (melódico, como E1)"
        )
    try:
        nota = nota_a_midi(str(datos["nota"])) if "nota" in datos else None
        grave = nota_a_midi(str(datos["grave"])) if "grave" in datos else None
    except ErrorNotacion as error:
        raise ErrorPack(f"instrumento {nombre!r}: {error}") from error
    largo = _fraccion(datos.get("largo", LARGO_POR_DEFECTO), f"largo de {nombre!r}")
    programa = datos.get("programa")
    if programa is not None and (
        not isinstance(programa, int) or not 0 <= programa <= 127
    ):
        raise ErrorPack(f"programa de {nombre!r} debe ir de 0 a 127, no {programa!r}")
    return Instrumento(nombre, nota, grave, largo, programa)


class _LectorDePatrones:
    """Lee los patrones de una variación o transición y comprueba que encajan."""

    def __init__(
        self, instrumentos: dict[str, Instrumento], paso: Fraction, compas: str
    ) -> None:
        self.instrumentos = instrumentos
        self.paso = paso
        self.compas = compas
        self.por_compas = duracion_compas(compas) / paso

    def leer(self, textos: object, donde: str, un_compas: bool) -> dict[str, Patron]:
        if not isinstance(textos, dict):
            raise ErrorPack(
                f"los patrones de {donde} deben ser un mapa instrumento: patrón"
            )
        patrones = {}
        for clave, texto in textos.items():
            nombre = str(clave)
            if nombre not in self.instrumentos:
                raise ErrorPack(
                    f"{donde} usa el instrumento {nombre!r}, que no está en instrumentos"
                )
            patrones[nombre] = self._patron(nombre, str(texto), donde, un_compas)
        return patrones

    def _patron(self, nombre: str, texto: str, donde: str, un_compas: bool) -> Patron:
        try:
            patron = parse_patron(texto, self.paso)
        except ErrorNotacion as error:
            raise ErrorPack(f"patrón de {nombre!r} en {donde}: {error}") from error
        compases = patron.pasos / self.por_compas
        if un_compas and compases != 1:
            raise ErrorPack(
                f"el patrón de {nombre!r} en {donde} tiene {patron.pasos} pasos y debe"
                f" tener {self.por_compas} (1 compás de {self.compas})"
            )
        if compases.denominator != 1:
            raise ErrorPack(
                f"el patrón de {nombre!r} en {donde} tiene {patron.pasos} pasos; debe"
                f" ser múltiplo de {self.por_compas} (compases completos de {self.compas})"
            )
        return patron


def _variaciones(
    lista: object, patrones: _LectorDePatrones, tonalidad: str
) -> tuple[Variacion, ...]:
    if not isinstance(lista, list) or not lista:
        raise ErrorPack("variaciones debe ser una lista con al menos una variación")
    variaciones: list[Variacion] = []
    for posicion, datos in enumerate(lista, start=1):
        if not isinstance(datos, dict) or "nombre" not in datos:
            raise ErrorPack(f"la variación {posicion} necesita nombre")
        nombre = str(datos["nombre"])
        donde = f"la variación {nombre!r}"
        leidos = patrones.leer(datos.get("patrones") or {}, donde, un_compas=False)
        faltan = [i for i in patrones.instrumentos if i not in leidos]
        if faltan:
            raise ErrorPack(f"a {donde} le falta el patrón de: {', '.join(faltan)}")
        grados = str(datos.get("progresion", ""))
        _validar_progresion(tonalidad, grados, donde)
        descripcion = str(datos.get("descripcion", ""))
        variaciones.append(Variacion(nombre, descripcion, grados, leidos))
    nombres = [v.nombre for v in variaciones]
    if len(set(nombres)) != len(nombres):
        raise ErrorPack(f"hay variaciones con el mismo nombre: {', '.join(nombres)}")
    return tuple(variaciones)


def _validar_progresion(tonalidad: str, grados: str, donde: str) -> None:
    try:
        acordes = progresion(tonalidad, grados)
    except ErrorTeoria as error:
        raise ErrorPack(f"progresión de {donde}: {error}") from error
    if not acordes:
        raise ErrorPack(f"{donde} necesita una progresión, como i VI III VII")


def _transiciones(
    datos: object, patrones: _LectorDePatrones
) -> dict[str, dict[str, Patron]]:
    if not isinstance(datos, dict):
        raise ErrorPack("transiciones debe ser un mapa, como relleno: y corte:")
    transiciones = {}
    for clave, textos in datos.items():
        nombre = str(clave)
        if nombre not in TRANSICIONES:
            raise ErrorPack(
                f"transición desconocida {nombre!r}: usa {' o '.join(TRANSICIONES)}"
            )
        donde = f"la transición {nombre!r}"
        transiciones[nombre] = patrones.leer(textos or {}, donde, un_compas=True)
    return transiciones
