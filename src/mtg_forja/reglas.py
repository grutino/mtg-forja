"""Motor de reglas: casa patrones de oráculo contra las cartas del mazo.

El motor no sabe nada de cartas concretas. Solo aplica los patrones de
`reglas.json` sobre el texto que Scryfall ha devuelto, y por cada acierto
guarda qué frase exacta lo ha disparado (la evidencia). Así cualquier
afirmación del análisis puede comprobarse contra la carta.
"""
from __future__ import annotations

import itertools
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .modelo import Carta, Mazo

# Tope de parejas por regla. Sin él, una regla laxa en un mazo grande llenaría
# el mapa de líneas iguales y taparía todo lo demás.
TOPE_POR_REGLA = 12

RUTA_REGLAS = Path(__file__).with_name("reglas.json")


@dataclass
class Sinergia:
    id: str
    nombre: str
    bloque: str
    tipo: str
    fuerza: int
    turno: str
    piezas: list[str] = field(default_factory=list)
    resumen: str = ""
    pasos: list[str] = field(default_factory=list)
    evidencia: dict[str, str] = field(default_factory=dict)

    def dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "bloque": self.bloque,
            "tipo": self.tipo,
            "fuerza": self.fuerza,
            "turno": self.turno,
            "piezas": self.piezas,
            "resumen": self.resumen,
            "pasos": self.pasos,
            "evidencia": self.evidencia,
        }


def cargar_reglas(ruta: str | Path | None = None) -> list[dict[str, Any]]:
    p = Path(ruta) if ruta else RUTA_REGLAS
    return json.loads(p.read_text(encoding="utf-8"))["reglas"]


def _frase(texto: str, patron: str) -> str:
    """Devuelve la frase completa donde ha casado el patrón, como evidencia."""
    m = re.search(patron, texto, re.I | re.S)
    if not m:
        return ""
    ini = texto.rfind(".", 0, m.start()) + 1
    fin = texto.find(".", m.end())
    fin = len(texto) if fin == -1 else fin + 1
    return " ".join(texto[ini:fin].split())[:240]


def _casa(carta: Carta, pieza: dict[str, Any]) -> tuple[bool, str]:
    if not carta.resuelta:
        return False, ""
    if "tipo" in pieza and not re.search(pieza["tipo"], carta.tipo, re.I):
        return False, ""
    if "no_tipo" in pieza and re.search(pieza["no_tipo"], carta.tipo, re.I):
        return False, ""
    if "coste" in pieza and not re.search(pieza["coste"], carta.coste or "", re.I):
        return False, ""
    if "mv_min" in pieza and carta.mv < pieza["mv_min"]:
        return False, ""
    if "mv_max" in pieza and carta.mv > pieza["mv_max"]:
        return False, ""
    if "copias_min" in pieza and carta.copias < pieza["copias_min"]:
        return False, ""
    if "copias_max" in pieza and carta.copias > pieza["copias_max"]:
        return False, ""

    evidencia = ""
    for clave in ("oracle", "oracle2", "oracle3"):
        patron = pieza.get(clave)
        if not patron:
            continue
        if not re.search(patron, carta.oraculo, re.I | re.S):
            return False, ""
        if not evidencia:
            evidencia = _frase(carta.oraculo, patron)
    if "no_oracle" in pieza and re.search(pieza["no_oracle"], carta.oraculo, re.I | re.S):
        return False, ""
    if not evidencia:
        evidencia = " ".join(carta.oraculo.split())[:200] or carta.tipo
    return True, evidencia


def _conteo_ok(mazo: Mazo, condiciones: list[dict[str, Any]]) -> bool:
    valores = {
        "basicas": mazo.basicas,
        "tierras": mazo.tierras,
        "total": mazo.total,
    }
    for c in condiciones:
        v = valores.get(c.get("que", ""), 0)
        if "max" in c and v > c["max"]:
            return False
        if "min" in c and v < c["min"]:
            return False
    return True


def detectar(mazo: Mazo, reglas: list[dict[str, Any]] | None = None) -> list[Sinergia]:
    reglas = reglas if reglas is not None else cargar_reglas()
    cartas = mazo.principal
    salida: list[Sinergia] = []

    for regla in reglas:
        if regla.get("conteo") and not _conteo_ok(mazo, regla["conteo"]):
            continue

        por_rol: dict[str, list[tuple[Carta, str]]] = {}
        completa = True
        for pieza in regla["piezas"]:
            aciertos = []
            for carta in cartas:
                ok, ev = _casa(carta, pieza)
                if ok:
                    aciertos.append((carta, ev))
            if not aciertos:
                completa = False
                break
            por_rol[pieza["rol"]] = aciertos
        if not completa:
            continue

        # Una regla puede aplicarse a varias cartas a la vez. Emitir solo la pareja
        # "mejor" escondía el resto: con Cleansing Wildfire, Cascading Cataracts se
        # llevaba la única línea y Rustvale Bridge —cuatro copias, igual de
        # indestructible— se quedaba suelto en el mapa. Se emiten todas.
        roles = [p["rol"] for p in regla["piezas"]]
        opciones = [sorted(por_rol[r], key=lambda c: (-c[0].copias, c[0].mv, c[0].nombre))
                    for r in roles]

        vistas: set[tuple[str, ...]] = set()
        for combo in itertools.product(*opciones):
            nombres = [c.nombre for c, _ in combo]
            if len(set(nombres)) < len(nombres):
                continue            # una carta no puede hacer dos papeles a la vez
            clave = tuple(sorted(nombres))
            if clave in vistas:
                continue
            vistas.add(clave)

            sust = dict(zip(roles, nombres))
            salida.append(
                Sinergia(
                    id="::".join([regla["id"], *nombres]),
                    nombre=regla["nombre"],
                    bloque=regla.get("bloque", "Otros"),
                    tipo=regla.get("tipo", "sinergia"),
                    fuerza=int(regla.get("fuerza", 2)),
                    turno=regla.get("turno", ""),
                    piezas=nombres,
                    resumen=regla.get("resumen", "").format(**sust),
                    pasos=[p.format(**sust) for p in regla.get("pasos", [])],
                    evidencia={c.nombre: ev for c, ev in combo},
                )
            )
            if len(vistas) >= TOPE_POR_REGLA:
                break

    orden = {"sinergia": 0, "aviso": 1, "conflicto": 2}
    salida.sort(key=lambda s: (orden.get(s.tipo, 3), -s.fuerza, s.bloque))
    return salida


def documento(mazo: Mazo, sinergias: list[Sinergia], titulo: str = "", subtitulo: str = "") -> dict[str, Any]:
    """Construye el documento intermedio que consumen los renderizadores."""
    principal = sorted(mazo.principal, key=lambda c: (c.es_tierra, c.mv, c.nombre))
    return {
        "titulo": titulo or mazo.nombre,
        "subtitulo": subtitulo or f"{mazo.total} cartas · {mazo.tierras} tierras",
        "curva": mazo.curva(),
        "cartas": [
            {
                "nombre": c.nombre,
                "copias": c.copias,
                "coste": c.coste,
                "mv": c.mv,
                "tipo": c.tipo,
                "rol": c.rol,
                "produce_mana": c.produce_mana,
                "estrategia": "",
            }
            for c in principal
        ],
        "sinergias": [s.dict() for s in sinergias],
        "orden": [],
        "reglas_oro": [],
        "no_resueltas": mazo.no_resueltas,
    }
