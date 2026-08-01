"""Modelo de datos de MTG Forja: cartas, mazo y sinergias."""
from __future__ import annotations

import re
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


def parsear_lista(texto: str) -> list[tuple[int, str, bool]]:
    """Convierte una lista de mazo en tuplas (copias, nombre, es_banquillo).

    Acepta el formato de exportación de MTG Arena, el de Moxfield y listas
    sueltas de texto. Las cabeceras "Deck" y "Sideboard" cambian de sección.
    """
    salida: list[tuple[int, str, bool]] = []
    banquillo = False
    for cruda in texto.splitlines():
        linea = cruda.strip()
        if not linea or linea.startswith(("#", "//")):
            continue
        clave = linea.lower().rstrip(":")
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
        salida.append((int(m.group("n") or 1), nombre, banquillo))
    return salida
