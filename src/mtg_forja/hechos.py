"""Hechos objetivos del mazo, para que el modelo razone sobre datos y no sobre memoria.

El análisis bueno de un mazo —el que ve que un barrido no alcanza a tus
planeswalkers, o que una carta apaga los artefactos del rival pero no los tuyos—
no sale de casar patrones: sale de razonar sobre las reglas del juego. Eso lo hace
el modelo, no un motor de expresiones regulares.

Lo que sí puede hacer un programa es dejarle los hechos masticados y comprobables:
a quién alcanza cada efecto, qué zonas toca, qué tipos menciona, y si el mazo es
siquiera capaz de lanzar sus propias cartas. Todo lo de aquí se deduce del oráculo
real y de la línea de tipo, nunca de conocimiento memorizado.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .lexico import texto_reglas
from .modelo import Carta, Mazo

COLORES = ("W", "U", "B", "R", "G")
NOMBRE_COLOR = {"W": "blanco", "U": "azul", "B": "negro", "R": "rojo", "G": "verde"}

TIPOS = ("Creature", "Artifact", "Enchantment", "Land", "Planeswalker",
         "Instant", "Sorcery", "Battle")

ZONAS = {
    "cementerio": r"graveyard",
    "biblioteca": r"library",
    "exilio": r"\bexile",
    "mano": r"\bhand\b",
    "campo de batalla": r"battlefield",
}


def _pips(coste: str) -> Counter:
    """Símbolos de color que exige un coste. {U/B} cuenta para los dos."""
    fuera: Counter = Counter()
    for simbolo in re.findall(r"\{([^}]+)\}", coste or ""):
        for color in COLORES:
            if color in simbolo.upper():
                fuera[color] += 1
    return fuera


def _exigencia(coste: str) -> tuple[Counter, list[list[str]]]:
    """Separa lo que un coste EXIGE de lo que solo prefiere.

    Un híbrido `{G/U}` no exige ni verde ni azul: se paga con cualquiera de los
    dos. Contarlo como exigencia de ambos hacía avisar de falta de azul en un mazo
    verde-negro que no lleva una sola carta azul. Los fireos (`{U/P}`) tampoco
    exigen: se pagan con vida.
    """
    duros: Counter = Counter()
    hibridos: list[list[str]] = []
    for simbolo in re.findall(r"\{([^}]+)\}", coste or ""):
        s = simbolo.upper()
        colores = [c for c in COLORES if c in s]
        if not colores:
            continue
        if "/" in s:
            hibridos.append(colores)
        else:
            duros[colores[0]] += 1
    return duros, hibridos


def _alcance(oraculo: str) -> str:
    """A quién alcanza el efecto. Es lo que distingue una asimetría de un barrido."""
    tuyo = re.search(r"you control|your (creatures|permanents|library|graveyard|hand)", oraculo, re.I)
    rival = re.search(r"opponent|each other player|target player|they control", oraculo, re.I)
    ambos = re.search(r"each player|all creatures|all permanents|all artifacts|"
                      r"every|each creature\b", oraculo, re.I)
    if ambos:
        return "simétrico"
    if tuyo and rival:
        return "asimétrico"
    if rival:
        return "solo al rival"
    if tuyo:
        return "solo a lo tuyo"
    return "sin determinar"


def _velocidad(carta: Carta, oraculo: str) -> str:
    if "Instant" in carta.tipo or re.search(r"\bFlash\b", oraculo):
        return "a velocidad de instantáneo"
    if "Sorcery" in carta.tipo:
        return "solo en tu turno"
    if re.search(r"\{T\}[,:]|^\{|:\s", oraculo):
        return "permanente con habilidad activada"
    return "permanente"


def senales(carta: Carta) -> dict[str, Any]:
    """Los hechos comprobables de una carta, sin interpretar nada."""
    o = texto_reglas(carta.oraculo, carta.nombre)
    return {
        "alcance": _alcance(o),
        "velocidad": _velocidad(carta, o),
        "zonas_que_toca": [n for n, p in ZONAS.items() if re.search(p, o, re.I)],
        "tipos_que_menciona": [t for t in TIPOS if re.search(rf"\b{t}s?\b", o, re.I)],
        "condicional": bool(re.search(r"\bas long as\b|\bonly if\b|\bif you\b", o, re.I)),
        "simbolos_de_color": dict(_pips(carta.coste)),
    }


def mana(mazo: Mazo) -> dict[str, Any]:
    """¿Es el mazo capaz de lanzar sus propias cartas?

    Comprueba fuentes de cada color contra los símbolos que el mazo exige. Es
    objetivo, no depende de conocer ninguna carta, y vale para cualquier mazo.
    """
    fuentes: Counter = Counter()
    flexibles = 0
    for c in mazo.principal:
        if not c.es_tierra and "Land" not in c.tipo:
            continue
        if c.produce_mana:
            for color in c.produce_mana:
                if color in COLORES:
                    fuentes[color] += c.copias
        elif re.search(r"Search your library for", c.oraculo, re.I):
            flexibles += c.copias  # tierras de búsqueda: valen para lo que puedan traer

    exigencia: Counter = Counter()
    exigentes: list[dict[str, Any]] = []
    flexibles_hibridos: list[dict[str, Any]] = []
    for c in mazo.principal:
        duros, hibridos = _exigencia(c.coste)
        for color, n in duros.items():
            exigencia[color] = max(exigencia[color], n)
        if duros and max(duros.values()) >= 2:
            exigentes.append({"carta": c.nombre, "copias": c.copias,
                              "exige": {k: v for k, v in duros.items() if v >= 2}})
        for colores in hibridos:
            # solo es un problema si NINGUNO de sus colores tiene fuentes
            if not any(fuentes.get(x) for x in colores):
                flexibles_hibridos.append(
                    {"carta": c.nombre,
                     "paga_con": [NOMBRE_COLOR[x] for x in colores]})

    aviso = []
    for color in sorted(set(list(fuentes) + list(exigencia))):
        tiene, pide = fuentes.get(color, 0), exigencia.get(color, 0)
        if pide and tiene + flexibles < 12 * pide:
            aviso.append(f"{NOMBRE_COLOR[color]}: {tiene} fuentes directas"
                         f"{f' + {flexibles} de búsqueda' if flexibles else ''}"
                         f" para cartas que piden {pide} símbolo(s)")

    return {
        "fuentes_por_color": {NOMBRE_COLOR[k]: v for k, v in sorted(fuentes.items())},
        "tierras_de_busqueda": flexibles,
        "cartas_de_doble_simbolo": exigentes,
        "posible_problema_de_color": aviso,
        "hibridos_sin_ninguna_fuente": flexibles_hibridos,
    }


def radiografia(mazo: Mazo) -> dict[str, Any]:
    """Todo lo objetivo que se puede decir del mazo sin interpretar nada."""
    principal = mazo.principal
    unicas = [c.nombre for c in principal if c.copias == 1 and not c.es_basica]
    tipos = Counter()
    for c in principal:
        for t in TIPOS:
            if re.search(rf"\b{t}\b", c.tipo):
                tipos[t] += c.copias
    return {
        "resumen": {
            "cartas": mazo.total,
            "tierras": mazo.tierras,
            "basicas": mazo.basicas,
            "curva": mazo.curva(),
            "reparto_por_tipo": dict(tipos.most_common()),
        },
        "mana": mana(mazo),
        "copias_unicas": unicas,
        "cartas": [
            {"nombre": c.nombre, "copias": c.copias, "coste": c.coste, "mv": c.mv,
             "tipo": c.tipo, "oraculo": c.oraculo, "senales": senales(c)}
            for c in principal
        ],
        "banquillo": [
            {"nombre": c.nombre, "copias": c.copias, "tipo": c.tipo, "oraculo": c.oraculo}
            for c in mazo.cartas if c.banquillo
        ],
        "sin_resolver": mazo.no_resueltas,
    }
