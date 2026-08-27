"""Contrasta las sinergias detectadas contra los rulings oficiales de Wizards.

El motor deduce interacciones leyendo el oráculo. Esto es otra cosa: busca si
Wizards ya ha escrito algo sobre esa misma interacción. Cuando existe, es la
mejor prueba posible — no es la opinión de nadie, es la regla.

El caso que lo justificó: Phyrexian Dreadnought + Stifle es un combo conocido y
documentado desde hace veinte años, y sus propios rulings lo dicen con todas las
letras («this now has an "enters" triggered ability», «phasing in does not
trigger "enters" abilities»). No tiene sentido deducir a ciegas lo que la fuente
oficial ya explica.

Ojo con lo que esto es y lo que no: empareja por vocabulario, así que señala
rulings **relacionados**, no demuestra la jugada. Sirve para que quien lea —o el
modelo, por MCP— tenga delante el texto oficial y juzgue. Una pareja sin ruling
no es una pareja falsa: la mayoría de las cartas apenas tienen rulings.
"""
from __future__ import annotations

import re
from typing import Any, Callable

from .modelo import Mazo
from .reglas import Sinergia

# Palabras que salen en casi cualquier carta o ruling y no dicen nada sobre por
# qué dos cartas interactúan. Sin esta lista, todo casa con todo.
RELLENO = set("""the a an of to in on for and or with that this it its you your they their
them if is are be as at by from can may not do does when whenever while than then there
target each all any other another such into onto up down out off over under card cards
player players game turn one two three more less least most only same both either
control controls controlled battlefield graveyard library hand exile spell spells
creature creatures permanent permanents mana cost costs pay pays paid choose chooses
chosen choice during before after option options resolution resolves resolve instead
return returns put puts still would have has had been will just even also because about
which what where were was sacrifice sacrifices sacrificed number total value time times
way ways part""".split())

# Un término largo compartido basta; dos cortos también. Uno corto y solo, no:
# "token" o "damage" sueltos aparecen en media colección.
LARGO = 6


def _terminos(texto: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{5,}", texto.lower()) if w not in RELLENO}


def _apoya(ruling: str, oraculo_otro: str) -> list[str]:
    """Términos que comparten el ruling y la otra carta, si son significativos.

    La comparación es por palabra exacta, sin reducir a la raíz: "countered" es
    contrarrestar y "counters" son contadores +1/+1, y juntarlas emparejaba un
    ruling sobre contrahechizos con cualquier carta que pusiera contadores.
    """
    comunes = _terminos(ruling) & _terminos(oraculo_otro)
    if any(len(w) >= LARGO for w in comunes) or len(comunes) >= 2:
        return sorted(comunes)
    return []


def contrastar(
    mazo: Mazo,
    sinergias: list[Sinergia],
    por_pareja: int = 2,
    buscar_rulings: Callable[[Any], list[str]] | None = None,
) -> dict[str, Any]:
    """Para cada pareja detectada, los rulings oficiales que hablan de lo mismo."""
    if buscar_rulings is None:
        from .scryfall import rulings as buscar_rulings

    cache: dict[str, list[str]] = {}

    def rulings_de(nombre: str) -> list[str]:
        if nombre not in cache:
            carta = mazo.buscar(nombre)
            # Sin red, `rulings` devuelve lista vacía: el contraste se queda sin
            # apoyos, pero el análisis no se rompe por ello.
            cache[nombre] = buscar_rulings(carta) if carta else []
        return cache[nombre]

    salida: list[dict[str, Any]] = []
    parejas = 0
    for s in sinergias:
        if len(s.piezas) < 2:
            continue
        parejas += 1
        apoyos: list[dict[str, Any]] = []
        for i, nombre in enumerate(s.piezas[:2]):
            otra = mazo.buscar(s.piezas[1 - i])
            if not otra:
                continue
            for r in rulings_de(nombre):
                comunes = _apoya(r, otra.oraculo)
                if comunes:
                    apoyos.append({"carta": nombre, "terminos": comunes, "ruling": r})
                if len(apoyos) >= por_pareja:
                    break
            if len(apoyos) >= por_pareja:
                break
        if apoyos:
            salida.append({
                "piezas": s.piezas,
                "concepto": s.id.split("::")[0],
                "apoyos": apoyos,
            })

    return {
        "fuente": "Rulings oficiales de Wizards of the Coast, vía Scryfall",
        "parejas_analizadas": parejas,
        "parejas_con_apoyo": len(salida),
        "contrastes": salida,
        "atencion": (
            "Empareja por vocabulario: señala rulings relacionados, no demuestra la "
            "jugada. Y que una pareja no tenga apoyo no la vuelve falsa — la mayoría "
            "de las cartas apenas tienen rulings."
        ),
    }
