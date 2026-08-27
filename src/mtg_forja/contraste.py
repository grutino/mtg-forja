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
    etiquetas_mazo: dict[str, list[str]] | None = None,
    combos_comunidad: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Para cada pareja detectada, qué dicen las fuentes externas sobre ella.

    Dos vías independientes. Los **rulings oficiales** son la regla escrita por
    Wizards. Las **etiquetas comunitarias** de Scryfall dicen qué hace cada carta
    según quien la etiquetó; si el concepto que disparó la pareja espera cierta
    etiqueta y alguna de las dos cartas la lleva, hay acuerdo entre dos fuentes
    que no se hablan entre sí.

    `etiquetas_mazo` es el `por_carta` de `etiquetas.de_mazo`. Si no se pasa, no
    se consulta nada y el contraste se queda solo con los rulings.

    Una pareja sin apoyo **no es una pareja falsa**: la mayoría de las cartas
    apenas tienen rulings, y solo veinte de los conceptos tienen etiqueta
    equivalente. Es "no comprobado", no "desmentido".
    """
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

    from .etiquetas import por_concepto
    esperadas = por_concepto()

    salida: list[dict[str, Any]] = []
    sin_contraste: list[dict[str, Any]] = []
    parejas = 0
    for s in sinergias:
        if len(s.piezas) < 2:
            continue
        parejas += 1
        concepto = s.id.split("::")[0]

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

        # La comunidad refuerza si el concepto espera cierta etiqueta y alguna de
        # las dos cartas la lleva de verdad.
        quiere = esperadas.get(concepto, [])
        coinciden: dict[str, list[str]] = {}
        if etiquetas_mazo and quiere:
            for nombre in s.piezas[:2]:
                comunes = sorted(set(etiquetas_mazo.get(nombre, [])) & set(quiere))
                if comunes:
                    coinciden[nombre] = comunes

        fila = {
            "piezas": s.piezas,
            "concepto": concepto,
            "apoyos": apoyos,
            "etiquetas_que_coinciden": coinciden,
        }
        if apoyos or coinciden:
            fuentes = (["ruling oficial"] if apoyos else []) + (["etiquetas"] if coinciden else [])
            fila["veredicto"] = "reforzada por " + " y ".join(fuentes)
            salida.append(fila)
        else:
            # Distinguir "nadie lo ha comprobado" de "nadie lo respalda" importa:
            # sin etiqueta equivalente no hay nada que comprobar por esa vía.
            fila["veredicto"] = ("sin contraste posible: el concepto no tiene etiqueta "
                                 "equivalente y las cartas no traen rulings del caso"
                                 if not quiere else
                                 "sin apoyo externo: mírala con lupa")
            sin_contraste.append(fila)

    # La comunidad manda. Si un catálogo de combos dice que dos cartas del mazo
    # se combinan y nuestro motor no las une, el que se equivoca es el motor: son
    # jugadas que alguien ha visto funcionar en una mesa. Se listan aparte para
    # que se vean, no se inventan sinergias con ellas.
    detectadas = {tuple(sorted(s.piezas)) for s in sinergias if len(s.piezas) >= 2}
    en_el_mazo = {c.nombre for c in mazo.principal}
    nos_falta: list[dict[str, Any]] = []
    for grupo in ((combos_comunidad or {}).get("completos") or []):
        cartas = [c for c in grupo.get("cartas", []) if c in en_el_mazo]
        if len(cartas) < 2:
            continue
        parejas_combo = {tuple(sorted((a, b)))
                         for i, a in enumerate(cartas) for b in cartas[i + 1:]}
        if not (parejas_combo & detectadas):
            nos_falta.append({"cartas": cartas,
                              "produce": grupo.get("produce"),
                              "pasos": grupo.get("pasos"),
                              "por_que_importa": "la comunidad lo cataloga y el motor no lo une"})

    comprobables = [f for f in sin_contraste if esperadas.get(f["concepto"])]
    return {
        "fuentes": ["Rulings oficiales de Wizards of the Coast, vía Scryfall",
                    "Etiquetas funcionales de la comunidad (Scryfall)"
                    if etiquetas_mazo else "Etiquetas: no consultadas"],
        "parejas_analizadas": parejas,
        "parejas_reforzadas": len(salida),
        "contrastes": salida,
        "sin_apoyo_pero_comprobables": comprobables,
        "la_comunidad_ve_lo_que_nosotros_no": nos_falta,
        "sin_contraste_posible": len(sin_contraste) - len(comprobables),
        "atencion": (
            "Los rulings se emparejan por vocabulario: señalan textos relacionados, no "
            "demuestran la jugada. Y una pareja sin apoyo NO es una pareja falsa — la "
            "mayoría de las cartas apenas tienen rulings y solo veinte conceptos tienen "
            "etiqueta equivalente. Mira `sin_apoyo_pero_comprobables`: ahí sí había algo "
            "que comprobar y no salió, que es donde conviene desconfiar. Y si "
            "`la_comunidad_ve_lo_que_nosotros_no` trae algo, eso pesa MÁS que el motor: "
            "son jugadas catalogadas por gente que las ha visto funcionar, así que ante "
            "una discrepancia gana la comunidad y el hueco es nuestro."
        ),
    }
