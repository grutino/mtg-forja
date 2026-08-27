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
from . import contraste
from . import etiquetas as etq
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
def etiquetas_funcionales(lista: str, nombre: str = "Mazo") -> str:
    """Qué hace cada carta según el etiquetado comunitario de Scryfall.

    Es una **segunda opinión que no es nuestra**: el motor deduce leyendo el
    oráculo con sus propios patrones, y esto viene de gente que etiquetó las
    cartas por función — `drawback`, `pitch-spell`, `sacrifice-outlet`, `tutor`.

    Tres usos, por orden de utilidad:

    1. **Contrastar.** Si el motor llama lastre a una carta y la etiqueta
       `drawback` coincide, tienes dos fuentes independientes de acuerdo.
    2. **Ver lo que se escapa.** Una carta con etiquetas jugosas que no aparece en
       ninguna sinergia es la mejor pista de que falta un concepto: lee su oráculo
       y razona tú la interacción.
    3. **Describir el mazo** sin depender de nuestras categorías.

    Dos avisos: el etiquetado lo hacen personas y puede faltar o sobrar, así que
    no es oráculo verificado; y si `etiquetas_sin_comprobar` viene con algo, esas
    **no están comprobadas, no ausentes** — no concluyas nada de ellas.
    """
    return _json(etq.de_mazo(scryfall.resolver(lista, nombre)))


@mcp.tool()
def contrastar_con_rulings(lista: str, nombre: str = "Mazo") -> str:
    """Contrasta las sinergias detectadas contra los rulings oficiales de Wizards.

    Úsala **antes de afirmar que una interacción funciona**, y sobre todo con
    combos conocidos: muchos están explicados en el ruling oficial de la propia
    carta, que es la mejor prueba que existe — no es la opinión de nadie, es la
    regla.

    El caso que la motivó: Phyrexian Dreadnought + Stifle lleva veinte años
    documentado, y sus rulings lo dicen con todas las letras («this now has an
    "enters" triggered ability», «phasing in does not trigger "enters"
    abilities»). Deducirlo a ciegas cuando la fuente oficial ya lo explica es
    trabajar de más y peor.

    Dos avisos al leer el resultado:

    * Empareja por vocabulario, así que devuelve rulings **relacionados**. Léelos
      y decide tú si respaldan la jugada o hablan de otra cosa.
    * Que una pareja no traiga apoyo **no la vuelve falsa**: la mayoría de las
      cartas apenas tienen rulings. La ausencia no dice nada.

    Si un ruling contradice una sinergia detectada, gana el ruling: dilo y
    descarta la sinergia.
    """
    mazo = scryfall.resolver(lista, nombre)
    return _json(contraste.contrastar(mazo, lexico.completo(mazo)))


@mcp.tool()
def cobertura_del_analisis(lista: str, nombre: str = "Mazo") -> str:
    """Cuánto de este mazo entiende el motor, y qué se le escapa.

    Úsala **siempre que el mazo traiga cartas de una colección reciente**, y en
    general cuando el análisis salga escaso: distingue las dos causas posibles,
    que se confunden con facilidad.

    * Si `sin resolver` viene vacío, las cartas se leyeron bien contra Scryfall.
      Eso funciona incluso con colecciones que aún no han salido.
    * Si hay `mecanicas_sin_concepto` o `cartas_invisibles`, el motor **lee pero
      no entiende**: nadie ha escrito todavía un concepto para esa mecánica, así
      que sus sinergias no se van a deducir por muchas vueltas que le des.

    Cuando eso pase, no te fíes del recuento de sinergias: coge `radiografia_del_mazo`,
    lee el oráculo de las cartas invisibles y razona tú la interacción. Es
    exactamente el caso para el que existe el camino MCP.
    """
    return _json(lexico.cobertura(scryfall.resolver(lista, nombre)))


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
