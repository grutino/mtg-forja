"""Servidor MCP de MTG Forja.

Reparto de trabajo deliberado:

* el servidor aporta **hechos** — texto de oráculo traído de Scryfall y patrones
  de interacción comprobados contra ese texto;
* el modelo aporta **criterio** — qué sinergias importan, cómo se explican y en
  qué orden se juegan.

Por eso `detectar_sinergias` devuelve la evidencia textual de cada acierto: todo
lo que acabe en el documento final se puede contrastar con la carta.
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
from . import reglas as motor
from . import scryfall
from .render import chuleta as r_chuleta
from .render import guia as r_guia
from .render import mapa as r_mapa

try:  # los SDK que la aceptan la anuncian en el handshake como serverInfo.version
    mcp = _Servidor("mtg-forja", version=__version__)
except TypeError:  # SDK antiguo sin ese parámetro
    mcp = _Servidor("mtg-forja")

SALIDA = Path(os.environ.get("MTG_FORJA_SALIDA", Path.cwd() / "mtg-forja-salida"))


def _json(dato: Any) -> str:
    return json.dumps(dato, ensure_ascii=False, indent=2)


def _cargar(documento: str) -> dict[str, Any]:
    if isinstance(documento, dict):
        return documento
    texto = documento.strip()
    if texto.startswith("{"):
        return json.loads(texto)
    return json.loads(Path(texto).read_text(encoding="utf-8"))


def _escribir(nombre: str, html: str, ruta: str | None) -> str:
    destino = Path(ruta) if ruta else SALIDA / nombre
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    return str(destino.resolve())


@mcp.tool()
def resolver_mazo(lista: str, nombre: str = "Mazo") -> str:
    """Resuelve una lista de mazo contra Scryfall y devuelve el texto de oráculo real.

    Acepta el formato de exportación de MTG Arena, el de Moxfield o una lista
    suelta ("4 Lightning Helix" por línea). Úsalo SIEMPRE antes de afirmar nada
    sobre lo que hace una carta: no cites de memoria.
    """
    mazo = scryfall.resolver(lista, nombre)
    return _json(mazo.dict())


@mcp.tool()
def detectar_sinergias(lista: str, nombre: str = "Mazo") -> str:
    """Resuelve el mazo y busca patrones de interacción entre sus cartas.

    Devuelve un documento con las cartas, la curva y las sinergias candidatas.
    Cada candidata incluye `evidencia`: la frase del oráculo que ha disparado la
    regla. Trátalas como borrador — reescribe títulos, resúmenes y pasos con tu
    propio criterio, descarta las que no apliquen y añade las que el motor no vea.
    """
    mazo = scryfall.resolver(lista, nombre)
    sinergias = motor.detectar(mazo)
    return _json(motor.documento(mazo, sinergias, titulo=nombre))


@mcp.tool()
def listar_reglas() -> str:
    """Lista los patrones de interacción que conoce el motor, con su id y qué buscan."""
    return _json([
        {
            "id": r["id"],
            "nombre": r["nombre"],
            "bloque": r.get("bloque"),
            "tipo": r.get("tipo"),
            "busca": [
                {k: v for k, v in p.items() if k != "rol"} for p in r["piezas"]
            ],
        }
        for r in motor.cargar_reglas()
    ])


@mcp.tool()
def render_guia(documento: str, ruta: str = "") -> str:
    """Genera la guía extensa en HTML a partir de un documento de análisis.

    `documento` es el JSON de `detectar_sinergias`, idealmente ya reescrito por ti.
    Devuelve la ruta del archivo creado.
    """
    return _escribir("guia.html", r_guia.render(_cargar(documento)), ruta or None)


@mcp.tool()
def render_chuleta(documento: str, ruta: str = "") -> str:
    """Genera la chuleta imprimible de dos caras A4. Devuelve la ruta del archivo."""
    return _escribir("chuleta.html", r_chuleta.render(_cargar(documento)), ruta or None)


@mcp.tool()
def render_mapa(documento: str, ruta: str = "") -> str:
    """Genera el mapa interactivo de sinergias. Devuelve la ruta del archivo."""
    return _escribir("mapa.html", r_mapa.render(_cargar(documento)), ruta or None)


@mcp.tool()
def analizar(lista: str, nombre: str = "Mazo", ruta: str = "") -> str:
    """Atajo: resuelve, detecta y genera los tres HTML con los textos automáticos.

    Útil para una primera pasada rápida. Para un resultado bueno de verdad,
    encadena `detectar_sinergias` → reescribes el documento → los tres `render_*`.
    """
    mazo = scryfall.resolver(lista, nombre)
    doc = motor.documento(mazo, motor.detectar(mazo), titulo=nombre)
    base = Path(ruta) if ruta else SALIDA
    return _json({
        "sinergias_encontradas": len(doc["sinergias"]),
        "cartas_sin_resolver": doc["no_resueltas"],
        "guia": _escribir("guia.html", r_guia.render(doc), str(base / "guia.html")),
        "chuleta": _escribir("chuleta.html", r_chuleta.render(doc), str(base / "chuleta.html")),
        "mapa": _escribir("mapa.html", r_mapa.render(doc), str(base / "mapa.html")),
    })


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
