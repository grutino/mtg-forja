"""Modelo de datos de MTG Forja: cartas, mazo y sinergias."""
from __future__ import annotations

import re
from csv import reader as csv_lector
from dataclasses import dataclass, field, asdict
from typing import Any


LINEA = re.compile(
    r"""^\s*
        (?:(?P<n>\d+)\s*[xX]?\s+)?      # cantidad opcional: "4", "4x"
        (?P<nombre>[^(\[\n]+?)          # nombre, hasta set o corchete
        (?:\s*\((?P<set>[A-Za-z0-9_]{2,6})\)\s*(?P<num>[\w-]+)?)?   # (ZNR) 137
        \s*$""",
    re.VERBOSE,
)

# La sección "About" de MTG Arena trae "Name <nombre del mazo>" en una sola línea.
# Sin esto se colaba como si fuera una carta. Pide que NO haya cantidad delante,
# para no tragarse un "1 Nameless Inversion".
META_ARENA = re.compile(r"^(name|layout)\s+\S", re.I)

CABECERAS = {
    "deck", "mazo", "sideboard", "banquillo", "reserva", "commander",
    "companion", "maybeboard", "about", "name",
}


@dataclass
class Carta:
    """Una carta resuelta contra Scryfall."""

    nombre: str
    copias: int = 1
    banquillo: bool = False
    coste: str = ""
    mv: float = 0.0
    tipo: str = ""
    oraculo: str = ""
    colores: list[str] = field(default_factory=list)
    identidad: list[str] = field(default_factory=list)
    rarezas: str = ""
    scryfall_uri: str = ""
    # Colores que la carta sabe producir. Sin esto no se puede comprobar si el
    # mazo es capaz de lanzar sus propias cartas.
    produce_mana: list[str] = field(default_factory=list)
    # Mecánicas con nombre según Scryfall. Es la señal objetiva de si una
    # colección trae algo que el léxico todavía no sabe leer.
    keywords: list[str] = field(default_factory=list)
    # De dónde bajar los rulings oficiales de Wizards. Son el contenido de
    # Gatherer y explican interacciones que ningún patrón puede deducir.
    rulings_uri: str = ""
    resuelta: bool = True

    @property
    def es_tierra(self) -> bool:
        return "Land" in self.tipo

    @property
    def es_basica(self) -> bool:
        return "Basic" in self.tipo and self.es_tierra

    @property
    def rol(self) -> str:
        """Clasificación gruesa para colorear y agrupar."""
        t, o = self.tipo, self.oraculo
        if self.es_tierra:
            if re.search(r"becomes? a .*creature|animated", o, re.I):
                return "amenaza"
            return "tierra"
        if "Planeswalker" in t:
            return "amenaza"
        if re.search(r"you win the game", o, re.I):
            return "amenaza"
        if re.search(r"\bdraw\b|scry|surveil|look at the top", o, re.I) and (
            "Artifact" in t or "Enchantment" in t or "Instant" in t or "Sorcery" in t
        ):
            return "motor"
        if re.search(r"destroy|exile|damage to|counter target|-\d+/-\d+", o, re.I):
            return "respuesta"
        if "Creature" in t:
            return "amenaza"
        return "motor"

    def dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["rol"] = self.rol
        d["es_tierra"] = self.es_tierra
        d["es_basica"] = self.es_basica
        return d


@dataclass
class Mazo:
    cartas: list[Carta] = field(default_factory=list)
    nombre: str = "Mazo"
    no_resueltas: list[str] = field(default_factory=list)

    @property
    def principal(self) -> list[Carta]:
        return [c for c in self.cartas if not c.banquillo]

    @property
    def total(self) -> int:
        return sum(c.copias for c in self.principal)

    @property
    def tierras(self) -> int:
        return sum(c.copias for c in self.principal if c.es_tierra)

    @property
    def basicas(self) -> int:
        return sum(c.copias for c in self.principal if c.es_basica)

    def curva(self) -> dict[str, int]:
        """Reparto de hechizos por valor de maná. Las tierras no cuentan."""
        out: dict[str, int] = {}
        for c in self.principal:
            if c.es_tierra:
                continue
            k = str(int(c.mv)) if c.mv < 7 else "7+"
            out[k] = out.get(k, 0) + c.copias
        return dict(sorted(out.items(), key=lambda kv: (kv[0] == "7+", kv[0])))

    def buscar(self, nombre: str) -> Carta | None:
        n = nombre.strip().lower()
        for c in self.cartas:
            if c.nombre.lower() == n or c.nombre.lower().startswith(n):
                return c
        return None

    def dict(self) -> dict[str, Any]:
        return {
            "nombre": self.nombre,
            "total": self.total,
            "tierras": self.tierras,
            "basicas": self.basicas,
            "curva": self.curva(),
            "cartas": [c.dict() for c in self.cartas],
            "no_resueltas": self.no_resueltas,
        }


MARCAS = re.compile(r"\*[A-Za-z]{1,2}\*")        # *F* / *E*, foil y grabada de Moxfield
CATEGORIA = re.compile(r"\[([^\]]*)\]")           # [Burn], [Maybeboard{noPrice}] de Archidekt
FUERA_DEL_MAZO = ("maybeboard", "sideboard", "considering")


def _csv(texto: str) -> list[tuple[int, str, bool]] | None:
    """Exportación de ManaBox y similares: cabecera con Name y Quantity."""
    lineas = [l for l in texto.splitlines() if l.strip()]
    if not lineas or "," not in lineas[0]:
        return None
    cabecera = [c.strip().strip('"').lower() for c in lineas[0].split(",")]
    if "name" not in cabecera:
        return None
    i_nombre = cabecera.index("name")
    i_cant = next((cabecera.index(c) for c in ("quantity", "count", "qty") if c in cabecera), None)
    i_seccion = next((cabecera.index(c) for c in ("section", "board") if c in cabecera), None)

    salida: list[tuple[int, str, bool]] = []
    for linea in lineas[1:]:
        campos = next(csv_lector([linea]), None)
        if not campos or len(campos) <= i_nombre:
            continue
        nombre = campos[i_nombre].strip().split("//")[0].strip()
        if not nombre:
            continue
        try:
            copias = int(campos[i_cant]) if i_cant is not None and campos[i_cant] else 1
        except ValueError:
            copias = 1
        banq = bool(i_seccion is not None and len(campos) > i_seccion
                    and campos[i_seccion].strip().lower() in FUERA_DEL_MAZO)
        salida.append((copias, nombre, banq))
    return salida or None


def parsear_lista(texto: str) -> list[tuple[int, str, bool]]:
    """Convierte una lista de mazo en tuplas (copias, nombre, es_banquillo).

    Acepta las exportaciones de MTG Arena, Moxfield (con marcas *F*), Archidekt
    (con categorías entre corchetes), MTGO, el CSV de ManaBox y listas sueltas. Las cabeceras "Deck" y "Sideboard" cambian de sección.
    """
    en_csv = _csv(texto)
    if en_csv is not None:
        return en_csv

    salida: list[tuple[int, str, bool]] = []
    banquillo = False
    for cruda in texto.splitlines():
        linea = cruda.strip()
        if not linea or linea.startswith(("#", "//")):
            continue
        # Archidekt cuelga la categoría de cada carta entre corchetes; Moxfield
        # marca la edición foil con *F*. Ni una cosa ni la otra son el nombre.
        etiquetas = " ".join(CATEGORIA.findall(linea)).lower()
        fuera = any(p in etiquetas for p in FUERA_DEL_MAZO)
        linea = MARCAS.sub(" ", CATEGORIA.sub(" ", linea)).strip()
        if not linea:
            continue
        clave = linea.lower().rstrip(":")
        if META_ARENA.match(linea):
            continue
        if clave in CABECERAS:
            banquillo = clave in {"sideboard", "banquillo", "reserva"}
            continue
        m = LINEA.match(linea)
        if not m:
            continue
        nombre = m.group("nombre").strip()
        if not nombre:
            continue
        # Cartas de doble cara: Scryfall resuelve por la cara frontal.
        nombre = nombre.split("//")[0].strip()
        salida.append((int(m.group("n") or 1), nombre, banquillo or fuera))
    return salida
