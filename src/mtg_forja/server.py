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
from . import combos
from . import hechos
from . import lexico
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

    Acepta las exportaciones de MTG Arena, Moxfield, Archidekt, MTGO, el CSV de
    ManaBox o una lista suelta ("4 Lightning Helix" por línea). Úsalo SIEMPRE antes de afirmar nada
    sobre lo que hace una carta: no cites de memoria.
    """
    mazo = scryfall.resolver(lista, nombre)
    return _json(mazo.dict())


@mcp.tool()
def radiografia_del_mazo(lista: str, nombre: str = "Mazo") -> str:
    """Los hechos objetivos del mazo, para razonar sobre datos y no de memoria.

    Úsala ANTES de escribir el análisis, junto con `detectar_sinergias`. Devuelve,
    para cada carta, el oráculo real y unas señales comprobables:

    * `alcance` — si el efecto es simétrico, asimétrico, solo tuyo o solo del rival.
      Es lo que distingue «barre la mesa» de «apaga lo suyo pero no lo tuyo».
    * `tipos_que_menciona` — para ver qué NO alcanza un efecto: un barrido de
      criaturas deja vivos los planeswalkers.
    * `zonas_que_toca` y `velocidad` — para razonar sobre secuencias y respuestas.

    Y a nivel de mazo: curva, reparto por tipo, copias únicas, y si hay fuentes
    de color suficientes para lo que el propio mazo exige.

    Estas son las piezas con las que se hace un análisis bueno de un mazo que
    nadie ha visto antes. El motor de patrones solo encuentra lo que ya estaba
    escrito; aquí tienes los hechos para ver el resto tú.
    """
    return _json(hechos.radiografia(scryfall.resolver(lista, nombre)))


@mcp.tool()
def detectar_sinergias(lista: str, nombre: str = "Mazo") -> str:
    """Resuelve el mazo y busca patrones de interacción entre sus cartas.

    Devuelve un documento con las cartas, la curva y las sinergias candidatas.
    Cada candidata incluye `evidencia`: la frase del oráculo que ha disparado la
    regla. Trátalas como borrador — reescribe títulos, resúmenes y pasos con tu
    propio criterio, descarta las que no apliquen y añade las que el motor no vea.
    """
    mazo = scryfall.resolver(lista, nombre)
    sinergias = lexico.completo(mazo)
    return _json(motor.documento(mazo, sinergias, titulo=nombre))


@mcp.tool()
def combos_conocidos(lista: str, nombre: str = "Mazo") -> str:
    """Combos ya catalogados que hay en el mazo, según Commander Spellbook.

    Devuelve los combos **completos** (todas las piezas están en el mazo) y los
    **casi completos** (falta una carta, que se indica), cada uno con las cartas
    implicadas, qué produce y los pasos redactados.

    ⚠️ **Esto no es texto de oráculo verificado.** Es una base curada por una
    comunidad, y es la única herramienta de este servidor cuyos datos no salen de
    Scryfall. Antes de meter cualquiera de estos combos en un documento:

    1. Comprueba con `resolver_mazo` o `radiografia_del_mazo` que las cartas hacen
       de verdad lo que el combo dice.
    2. Si el oráculo real no sostiene los pasos, descarta el combo.
    3. Cuando lo uses, cita Commander Spellbook como fuente.

    Complementa al motor de patrones: aquí salen combos con nombre propio que
    nadie ha escrito en `reglas.json`, y que el léxico de recursos no puede
    deducir porque requieren razonar sobre reglas del juego.
    """
    return _json(combos.buscar(scryfall.resolver(lista, nombre)))


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
    doc = motor.documento(mazo, lexico.completo(mazo), titulo=nombre)
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
