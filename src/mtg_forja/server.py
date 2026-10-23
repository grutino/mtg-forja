"""Servidor MCP de MTG Forja.

Reparto de trabajo:

* el servidor aporta **hechos** — texto de oráculo y rulings oficiales traídos
  de Scryfall — y **comprueba** el análisis antes de dibujarlo;
* el **experto** (Claude u otro modelo que se indique) aporta todo el criterio:
  qué hace cada carta en este mazo, qué sinergias existen, cómo se juegan y
  cómo de bueno es el mazo, apoyándose en los recursos de la comunidad.

El servidor ya no deduce sinergias con patrones de texto: inventaban jugadas y
no entendían las mecánicas nuevas. Ningún documento sale sin un análisis con
citas literales verificadas y la firma de la revisión experta.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:  # SDK de MCP 2.x
    from mcp.server import MCPServer as _Servidor
except ImportError:  # SDK de MCP 1.x
    from mcp.server.fastmcp import FastMCP as _Servidor

from . import __version__
from . import analisis as an
from . import combos
from . import scryfall
from .render import chuleta as r_chuleta
from .render import guia as r_guia
from .render import incrustar as r_incrustar
from .render import mapa as r_mapa

try:  # los SDK que la aceptan la anuncian en el handshake como serverInfo.version
    mcp = _Servidor("mtg-forja", version=__version__)
except TypeError:  # SDK antiguo sin ese parámetro
    mcp = _Servidor("mtg-forja")

SALIDA = Path(os.environ.get("MTG_FORJA_SALIDA", Path.cwd() / "mtg-forja-salida"))


def _json(dato: Any) -> str:
    return json.dumps(dato, ensure_ascii=False, indent=2)


def _cargar(texto: str | dict) -> dict[str, Any]:
    if isinstance(texto, dict):
        return texto
    t = texto.strip()
    if t.startswith("{"):
        return json.loads(t)
    return json.loads(Path(t).read_text(encoding="utf-8"))


@mcp.tool()
def resolver_mazo(lista: str, nombre: str = "Mazo") -> str:
    """Resuelve una lista de mazo contra Scryfall y devuelve el texto de oráculo real.

    Acepta las exportaciones de MTG Arena, Moxfield, Archidekt, MTGO, el CSV de
    ManaBox o una lista suelta ("4 Lightning Helix" por línea). Úsalo SIEMPRE antes
    de afirmar nada sobre lo que hace una carta: no cites de memoria.
    """
    return _json(scryfall.resolver(lista, nombre).dict())


@mcp.tool()
def datos_para_analisis(lista: str, nombre: str = "Mazo") -> str:
    """Los hechos del mazo para que tú, como experto, escribas el análisis.

    Por carta: oráculo, tipo, coste, palabras clave y **rulings oficiales**. Por
    mazo: total, tierras y curva. No trae ninguna sinergia ni clasificación: eso
    lo decides tú, leyendo las cartas y consultando listas y artículos reales.
    """
    mazo = scryfall.resolver(lista, nombre)
    return _json(an.datos_para_experto(mazo, scryfall.rulings))


@mcp.tool()
def rulings_oficiales(lista: str, cartas: str = "") -> str:
    """Las aclaraciones oficiales de Wizards sobre las cartas del mazo.

    Es el contenido de Gatherer, servido por Scryfall, y **sí es fuente
    verificada** — a diferencia de Commander Spellbook, esto lo escribe el propio
    fabricante del juego.

    Vale exactamente para lo que ningún motor de patrones alcanza, porque explica
    los límites de un efecto en lenguaje de reglas:

    * «Karn's first ability affects only artifacts on the battlefield» — la asimetría.
    * «The second Approach of the Second Sun must be cast from your hand» — la
      condición que hace que barajar te arruine el plan.

    Pásale `cartas` con nombres separados por comas para pedir solo las que te
    interesen; si lo dejas vacío trae las del mazo entero que tengan aclaraciones.
    Úsala cuando vayas a afirmar algo sobre **cuándo, dónde o a quién** alcanza un
    efecto: es la diferencia entre describir la carta y entenderla.
    """
    mazo = scryfall.resolver(lista, "Mazo")
    pedidas = {n.strip().lower() for n in cartas.split(",") if n.strip()}
    fuera = {}
    for c in mazo.principal:
        if pedidas and c.nombre.lower() not in pedidas:
            continue
        r = scryfall.rulings(c)
        if r:
            fuera[c.nombre] = r
    return _json({
        "fuente": "Rulings oficiales de Wizards of the Coast, vía Scryfall",
        "cartas_con_aclaraciones": len(fuera),
        "rulings": fuera,
    })


@mcp.tool()
def combos_conocidos(lista: str, nombre: str = "Mazo") -> str:
    """Combos ya catalogados que hay en el mazo, según Commander Spellbook.

    Devuelve los combos **completos** (todas las piezas están en el mazo) y los
    **casi completos** (falta una carta, que se indica), cada uno con las cartas
    implicadas, qué produce y los pasos redactados.

    ⚠️ **Esto no es texto de oráculo verificado.** Es una base curada por una
    comunidad, y es la única herramienta de este servidor cuyos datos no salen de
    Scryfall. Antes de meter cualquiera de estos combos en un documento:

    1. Comprueba con `datos_para_analisis` que las cartas hacen
       de verdad lo que el combo dice.
    2. Si el oráculo real no sostiene los pasos, descarta el combo.
    3. Cuando lo uses, cita Commander Spellbook como fuente.

    Es una fuente de la comunidad más, como las listas y artículos que consultes:
    si usas un combo, añade Commander Spellbook a `fuentes` y cítala.
    """
    return _json(combos.buscar(scryfall.resolver(lista, nombre)))


@mcp.tool()
def validar_analisis(lista: str, analisis: str, nombre: str = "Mazo") -> str:
    """Comprueba un análisis sin generar nada. Devuelve la lista de problemas.

    `analisis` es el JSON (o la ruta a él). Se exige: firma de la revisión
    experta, rol de cada carta que no sea tierra, una cita literal del oráculo o
    de un ruling para cada pieza de cada jugada, y fuentes con URL para lo que
    no sale de la carta. El formato está en la skill.
    """
    mazo = scryfall.resolver(lista, nombre)
    errores = an.validar(mazo, _cargar(analisis), scryfall.rulings)
    return _json({"valido": not errores, "problemas": errores})


@mcp.tool()
def forjar(lista: str, analisis: str, nombre: str = "Mazo", ruta: str = "",
           incrustar_imagenes: bool = False) -> str:
    """Valida el análisis del experto y, si cuadra, genera guía, chuleta y mapa.

    Si hay problemas no se escribe ningún archivo y se devuelven. Con
    `incrustar_imagenes` las cartas van dentro del HTML (para visores que
    bloquean la red, como el de archivos del chat).
    """
    mazo = scryfall.resolver(lista, nombre)
    datos = _cargar(analisis)
    errores = an.validar(mazo, datos, scryfall.rulings)
    if errores:
        return _json({"forjado": False, "problemas": errores})
    doc = an.documento(mazo, datos)
    htmls = {"guia.html": r_guia.render(doc), "chuleta.html": r_chuleta.render(doc),
             "mapa.html": r_mapa.render(doc)}
    if incrustar_imagenes:
        htmls = r_incrustar.incrustar_documentos(htmls, doc)
    base = Path(ruta) if ruta else SALIDA
    base.mkdir(parents=True, exist_ok=True)
    rutas = {}
    for n, h in htmls.items():
        (base / n).write_text(h, encoding="utf-8")
        rutas[n] = str((base / n).resolve())
    (base / "documento.json").write_text(_json(doc), encoding="utf-8")
    return _json({"forjado": True, "jugadas": len(doc["sinergias"]),
                  "citas_verificadas": doc["forjado"]["citas_verificadas"],
                  "revisor": doc["revision_experta"].get("revisor"), "archivos": rutas})


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
