"""Motor deductivo: encuentra sinergias que nadie ha escrito.

`reglas.json` describe parejas concretas de cartas, así que solo encuentra lo que
alguien se molestó en escribir — no escala a los treinta mil naipes de Magic.
Este módulo trabaja al revés: `lexico.json` describe **recursos**, y de cada carta
se deduce qué produce, qué premia y qué rompe. Una sinergia es entonces
«A produce R y B premia R», y un conflicto «A rompe R y B depende de R».

Añadir un concepto cubre de golpe todas las parejas que lo compartan, así que el
esfuerzo crece con el número de mecánicas del juego, no con el de mazos.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .modelo import Carta, Mazo
from .reglas import Sinergia

RUTA = Path(__file__).with_name("lexico.json")
_CACHE: list[dict[str, Any]] | None = None

# Sin topes, un mazo de sesenta cartas produce ruido: lo interesante son las
# conexiones fuertes, no todas. Los conflictos llevan cupo propio porque son
# menos numerosos y se los comerían las sinergias, y son lo más valioso.
TOPE_SINERGIAS = 10
TOPE_CONFLICTOS = 6
POR_CONCEPTO = 3
POR_CARTA = 4


def cargar(ruta: str | Path | None = None) -> list[dict[str, Any]]:
    global _CACHE
    if ruta is None and _CACHE is not None:
        return _CACHE
    datos = json.loads(Path(ruta or RUTA).read_text(encoding="utf-8"))["conceptos"]
    if ruta is None:
        _CACHE = datos
    return datos


_RECORDATORIO = re.compile(r"\([^)]*\)")


def texto_reglas(oraculo: str, nombre: str = "") -> str:
    """El oráculo listo para analizar: sin recordatorios ni el nombre propio.

    Dos fuentes de falsos positivos, ambas comprobadas sobre cartas reales:

    - El **texto recordatorio** entre paréntesis explica mecánicas que la carta no
      tiene. El de retrospectiva de Snapcaster Mage dice «exile it», y sin quitarlo
      la carta pasaba por odio al cementerio.
    - El **nombre propio**, porque las cartas antiguas se citan a sí mismas. Lightning
      Storm lleva «Storm» en el nombre y colaba como si tuviera la mecánica Tormenta.
    """
    t = _RECORDATORIO.sub(" ", oraculo)
    for forma in sorted({nombre, nombre.split(",")[0].strip()} - {""}, key=len, reverse=True):
        t = re.sub(r"\b" + re.escape(forma) + r"\b", " esta carta ", t)
    return " ".join(t.split())


def _encaja(carta: Carta, bloque: dict[str, Any] | None, oraculo: str | None = None) -> str:
    """Devuelve la evidencia si la carta cumple el bloque, o '' si no."""
    if not bloque or not carta.resuelta:
        return ""
    oraculo = texto_reglas(carta.oraculo, carta.nombre) if oraculo is None else oraculo
    if "tipo" in bloque and not re.search(bloque["tipo"], carta.tipo, re.I):
        return ""
    if "no_tipo" in bloque and re.search(bloque["no_tipo"], carta.tipo, re.I):
        return ""
    if "mv_min" in bloque and carta.mv < bloque["mv_min"]:
        return ""
    if "mv_max" in bloque and carta.mv > bloque["mv_max"]:
        return ""
    patrones = bloque.get("oracle") or []
    if not patrones:
        # Bloque puramente estructural (tipo o coste): la evidencia es la línea de tipo.
        return carta.tipo if ("tipo" in bloque or "mv_min" in bloque or "mv_max" in bloque) else ""
    for patron in patrones:
        m = re.search(patron, oraculo, re.I | re.S)
        if m:
            return _frase(oraculo, m)
    return ""


def _frase(texto: str, m: re.Match[str]) -> str:
    """La oración del oráculo que ha disparado el patrón, para poder citarla."""
    ini = texto.rfind(".", 0, m.start()) + 1
    fin = texto.find(".", m.end())
    fin = len(texto) if fin == -1 else fin + 1
    return " ".join(texto[ini:fin].split())[:240]


def _papeles(mazo: Mazo, conceptos: list[dict[str, Any]]) -> dict[str, dict[str, list]]:
    """Para cada concepto, qué cartas lo producen, lo premian y lo rompen."""
    limpio = {c.nombre: texto_reglas(c.oraculo, c.nombre) for c in mazo.principal}
    fuera: dict[str, dict[str, list]] = {}
    for c in conceptos:
        reparto = {"produce": [], "premia": [], "rompe": []}
        for papel in reparto:
            for carta in mazo.principal:
                ev = _encaja(carta, c.get(papel), limpio[carta.nombre])
                if ev:
                    reparto[papel].append((carta, ev))
        fuera[c["id"]] = reparto
    return fuera


def _texto(bloque: dict[str, Any] | None, por_defecto: str) -> str:
    return (bloque or {}).get("texto", por_defecto)


def detectar(mazo: Mazo, conceptos: list[dict[str, Any]] | None = None) -> list[Sinergia]:
    """Deduce sinergias y conflictos cruzando los papeles de cada concepto."""
    conceptos = conceptos if conceptos is not None else cargar()
    reparto = _papeles(mazo, conceptos)
    salida: list[Sinergia] = []

    for c in conceptos:
        r = reparto[c["id"]]
        # Sinergia: alguien produce el recurso y alguien lo aprovecha.
        for (a, eva), (b, evb), tipo, bl_a, bl_b in _parejas(c, r):
            if a.nombre == b.nombre:
                continue
            fuerza = min(4, c.get("fuerza", 2) + (1 if min(a.copias, b.copias) >= 3 else 0))
            salida.append(Sinergia(
                id=f"{c['id']}::{tipo}::{a.nombre}::{b.nombre}",
                nombre=f"{a.nombre} y {b.nombre}",
                bloque=_BLOQUE.get(tipo, "Motor"),
                tipo=tipo,
                fuerza=fuerza,
                turno="",
                piezas=[a.nombre, b.nombre],
                resumen=(f"{{a}} {_texto(c.get(bl_a), 'aporta')} y "
                         f"{{b}} {_texto(c.get(bl_b), 'lo aprovecha')}."),
                pasos=[],
                evidencia={a.nombre: eva, b.nombre: evb},
            ))

    salida.sort(key=lambda s: (0 if s.tipo == "sinergia" else 1, -s.fuerza, s.id))
    return _podar(salida)


_BLOQUE = {"sinergia": "Motor", "conflicto": "Conflictos"}


def _parejas(c: dict[str, Any], r: dict[str, list]):
    for a, eva in r["produce"]:
        for b, evb in r["premia"]:
            yield (a, eva), (b, evb), "sinergia", "produce", "premia"
    for a, eva in r["rompe"]:
        for b, evb in r["premia"]:
            yield (a, eva), (b, evb), "conflicto", "rompe", "premia"


def completo(mazo: Mazo, reglas_: list[dict[str, Any]] | None = None,
             conceptos: list[dict[str, Any]] | None = None) -> list[Sinergia]:
    """El análisis entero: primero lo escrito, después lo deducido.

    Las reglas con nombre van delante porque llevan título, pasos y avisos
    redactados. El léxico rellena lo que ninguna regla cubre, que es casi todo
    en cuanto te sales de los arquetipos que alguien se sentó a escribir.
    """
    from . import reglas as motor

    nombradas = motor.detectar(mazo, reglas_)
    cubiertas = {tuple(sorted(s.piezas)) for s in nombradas}
    deducidas = [s for s in detectar(mazo, conceptos)
                 if tuple(sorted(s.piezas)) not in cubiertas]
    return nombradas + deducidas


def _podar(sinergias: list[Sinergia]) -> list[Sinergia]:
    """Quita repeticiones y limita el ruido.

    Una misma pareja de cartas puede compartir varios conceptos; se queda la
    conexión más fuerte. Y una carta no puede acaparar la página entera.
    """
    vistas: set[tuple[str, ...]] = set()
    veces: dict[str, int] = {}
    por_concepto: dict[tuple[str, str], int] = {}
    cupo = {"sinergia": TOPE_SINERGIAS, "conflicto": TOPE_CONFLICTOS}
    fuera: list[Sinergia] = []
    for s in sinergias:
        par = tuple(sorted(s.piezas))
        clave = (s.id.split("::")[0], s.tipo)
        if par in vistas or cupo.get(s.tipo, 0) <= 0:
            continue
        if por_concepto.get(clave, 0) >= POR_CONCEPTO:
            continue
        if any(veces.get(n, 0) >= POR_CARTA for n in s.piezas):
            continue
        vistas.add(par)
        cupo[s.tipo] -= 1
        por_concepto[clave] = por_concepto.get(clave, 0) + 1
        for n in s.piezas:
            veces[n] = veces.get(n, 0) + 1
        fuera.append(s)
    return fuera
