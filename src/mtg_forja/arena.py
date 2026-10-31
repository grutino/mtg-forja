"""El mazo en el formato de importación de MTG Arena.

Cada vez que se forja un mazo, la forja deja también la lista lista para pegar en
Arena (Mazos → Importar). Si la lista original traía edición y número de colección,
se respetan; si no, se busca en Scryfall una impresión que exista en Arena.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .modelo import Mazo
from .scryfall import AGENTE, CACHE, _clave, _slug

# "4 Lightning Strike (MSH) 142", "4x Lightning Strike (msh) 142"
CODIGO = re.compile(r"^\s*(?P<n>\d+)x?\s+(?P<nombre>.+?)\s+\((?P<set>[A-Za-z0-9]{2,6})\)\s+(?P<num>\S+)")
ARENA = CACHE / "arena"


def codigos_de_lista(texto: str) -> dict[str, tuple[str, str]]:
    """Edición y número que trae la lista original, por nombre de carta."""
    fuera: dict[str, tuple[str, str]] = {}
    for linea in texto.splitlines():
        m = CODIGO.match(linea)
        if m:
            nombre = m.group("nombre").split("//")[0].strip()
            fuera.setdefault(_clave(nombre), (m.group("set").upper(), m.group("num")))
    return fuera


def impresion_arena(nombre: str) -> tuple[str, str] | None:
    """Una impresión de la carta que exista en Arena: (EDICIÓN, número).

    Prefiere expansiones y colecciones básicas, la más reciente, con número de
    colección normal. Se cachea en disco. Sin red (o con fixture), devuelve None
    y la línea sale solo con el nombre, que Arena también acepta.
    """
    if os.environ.get("MTG_FORJA_FIXTURE"):
        return None
    f = ARENA / f"{_slug(nombre)}.json"
    if f.exists():
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            return (d[0], d[1]) if d else None
        except (json.JSONDecodeError, OSError, IndexError):
            pass
    q = urllib.parse.urlencode({"q": f'!"{nombre}" game:arena', "unique": "prints",
                                "order": "released", "dir": "desc"})
    try:
        pet = urllib.request.Request("https://api.scryfall.com/cards/search?" + q,
                                     headers={"Accept": "application/json", "User-Agent": AGENTE})
        with urllib.request.urlopen(pet, timeout=20) as r:
            datos: list[dict[str, Any]] = json.loads(r.read().decode("utf-8")).get("data", [])
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    time.sleep(0.1)
    buenas = [c for c in datos if c.get("set_type") in ("expansion", "core")
              and str(c.get("collector_number", "")).isdigit() and not c.get("promo")]
    elegida = None
    if buenas:
        mismo = [c for c in buenas if c["set"] == buenas[0]["set"]]
        c = min(mismo, key=lambda c: int(c["collector_number"]))
        elegida = (c["set"].upper(), c["collector_number"])
    elif datos:
        elegida = (datos[0]["set"].upper(), str(datos[0]["collector_number"]))
    try:
        ARENA.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(list(elegida) if elegida else []), encoding="utf-8")
    except OSError:
        pass
    return elegida


def exportar(mazo: Mazo, lista_original: str = "") -> str:
    """Texto para pegar en Arena: Deck y Sideboard, con edición y número cuando se sabe."""
    propios = codigos_de_lista(lista_original)

    def linea(c) -> str:
        cod = propios.get(_clave(c.nombre)) or impresion_arena(c.nombre)
        return f"{c.copias} {c.nombre}" + (f" ({cod[0]}) {cod[1]}" if cod else "")

    principal = sorted(mazo.principal, key=lambda c: (c.es_tierra, c.mv, c.nombre))
    lineas = ["Deck"] + [linea(c) for c in principal]
    banquillo = [c for c in mazo.cartas if c.banquillo]
    if banquillo:
        lineas += ["", "Sideboard"] + [linea(c) for c in banquillo]
    return "\n".join(lineas) + "\n"
