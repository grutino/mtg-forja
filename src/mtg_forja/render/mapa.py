"""Mapa interactivo: grafo de fuerzas navegable con panel de detalle."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .comun import COLOR_ROL, NOMBRE_ROL, e, indice

CSS = """
:root{--ceniza:#15120F;--fondo:#1E1A16;--pap:#EFEADF;--brasa:#C1462A;--laton:#D8B15E;
 --humo:#8B8175;--lin:#3A332B;
 --s:"Charter","Bitstream Charter",Georgia,serif;
 --c:"Avenir Next Condensed","DejaVu Sans Condensed","Arial Narrow",sans-serif}
*{box-sizing:border-box}html,body{height:100%;margin:0}
body{background:var(--ceniza);color:var(--pap);font-family:var(--s);overflow:hidden}
#app{display:flex;height:100vh}
#lienzo{flex:1;position:relative;min-width:0}
svg{width:100%;height:100%;display:block;cursor:grab}svg.arrastrando{cursor:grabbing}
.enlace{stroke:#5C5245;stroke-width:1.4;transition:stroke .2s,stroke-width .2s,opacity .2s}
.enlace.riesgo{stroke:#7C3320;stroke-dasharray:5 4}
.enlace.mana{stroke:#3F4A38;stroke-width:1;stroke-dasharray:2 3;opacity:.55}
.enlace.mana.on{stroke:#7E8C5C;stroke-width:2;opacity:1}
.enlace.fuerte{stroke-width:2.6}
.enlace.on{stroke:var(--laton);stroke-width:3}.enlace.riesgo.on{stroke:var(--brasa)}
.enlace.off{opacity:.10}
.etq{font-family:var(--c);font-size:10px;fill:var(--laton);letter-spacing:.06em;
 text-transform:uppercase;pointer-events:none}
.etq.riesgo{fill:var(--brasa)}
.nodo{cursor:pointer}
.nodo .aro{fill:var(--fondo);stroke-width:2.5;transition:stroke-width .15s}
.nodo:hover .aro{stroke-width:4}.nodo.sel .aro{stroke-width:5}.nodo.off{opacity:.16}
.nodo .nom{font-family:var(--c);font-size:11px;font-weight:700;fill:#D9CFBE;text-anchor:middle;
 letter-spacing:.03em;pointer-events:none}
.nodo .cnt{font-family:var(--c);font-size:11px;font-weight:700;fill:#fff;text-anchor:middle;
 pointer-events:none}
.cntbg{fill:var(--brasa)}
.barra{position:absolute;top:0;left:0;right:0;padding:16px 20px;display:flex;gap:16px;
 align-items:flex-start;justify-content:space-between;pointer-events:none;flex-wrap:wrap}
.barra h1{font-size:19px;margin:0;line-height:1.05;letter-spacing:-.01em}
.barra h1 em{font-style:normal;color:var(--laton)}
.barra p{margin:3px 0 0;font-family:var(--c);font-size:10.5px;text-transform:uppercase;
 letter-spacing:.14em;color:var(--humo)}
.chips{display:flex;gap:6px;flex-wrap:wrap;pointer-events:auto}
.chip{font-family:var(--c);font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
 background:transparent;color:var(--humo);border:1px solid var(--lin);border-radius:999px;
 padding:5px 11px;cursor:pointer}
.chip:hover{color:var(--pap);border-color:#5C5245}
.chip.act{color:var(--ceniza);background:var(--laton);border-color:var(--laton)}
.pie{position:absolute;left:20px;bottom:14px;font-family:var(--c);font-size:10px;letter-spacing:.1em;
 text-transform:uppercase;color:#544B41;pointer-events:none}
.leyenda{position:absolute;right:20px;bottom:14px;display:flex;gap:14px;font-family:var(--c);
 font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--humo);pointer-events:none}
.leyenda i{display:inline-block;width:16px;height:0;border-top:2px solid var(--laton);
 vertical-align:3px;margin-right:5px}
.leyenda i.r{border-top:2px dashed var(--brasa)}
.leyenda i.m{border-top:2px dotted #7E8C5C}
#panel{width:340px;flex:0 0 340px;background:var(--fondo);border-left:1px solid var(--lin);
 overflow-y:auto;padding:20px}
.carta-img{width:100%;aspect-ratio:488/680;border-radius:10px;object-fit:cover;background:#2A241D;
 display:block}
.rolcap{font-family:var(--c);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;
 margin:14px 0 2px}
#panel h2{font-size:20px;margin:0 0 2px;line-height:1.1;letter-spacing:-.01em}
.meta{font-family:var(--c);font-size:11px;letter-spacing:.08em;text-transform:uppercase;
 color:var(--humo);margin:0 0 12px}
.bloq{font-size:13.5px;line-height:1.45;color:#CFC5B4;margin:0 0 12px}
.bloq b{color:var(--pap)}
h3{font-family:var(--c);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;
 color:var(--laton);margin:18px 0 8px;padding-bottom:5px;border-bottom:1px solid var(--lin)}
h3.r{color:var(--brasa)}
.conn{display:flex;gap:10px;align-items:flex-start;padding:8px;margin:0 -8px;border-radius:6px;
 cursor:pointer;background:none;border:0;width:calc(100% + 16px);text-align:left;color:inherit;font:inherit}
.conn:hover{background:rgba(216,177,94,.09)}
.conn img{width:34px;aspect-ratio:488/680;object-fit:cover;border-radius:3px;background:#2A241D;
 flex:0 0 auto}
.conn .qn{font-size:13px;font-weight:700;line-height:1.2}
.conn .qd{font-size:12px;line-height:1.35;color:#A79C8C;margin-top:2px}
.pill{font-family:var(--c);font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;
 color:var(--laton);display:block;margin-bottom:1px}
.pill.r{color:var(--brasa)}
.ev{font-size:11px;color:#8B8175;font-style:italic;margin-top:6px;padding-left:8px;
 border-left:1px solid var(--lin)}
@media (max-width:860px){html,body{overflow:auto;height:auto}#app{flex-direction:column;height:auto}
 #lienzo{height:70vh}#panel{width:100%;flex:1 1 auto;border-left:0;border-top:1px solid var(--lin)}}
"""

JS = (Path(__file__).with_name("grafo.js")).read_text(encoding="utf-8")


COLORES = ("W", "U", "B", "R", "G")
NOMBRE_COLOR = {"W": "blanco", "U": "azul", "B": "negro", "R": "rojo", "G": "verde"}
# Cuántos enlaces de maná deja pasar cada fuente. Sin tope, cada Isla se ataría a
# todos los hechizos azules y el grafo dejaría de leerse.
POR_FUENTE = 2
CARO = 5  # a partir de este valor de maná, una fuente incolora ya ayuda de verdad


def _simbolos(coste: str) -> dict[str, int]:
    """Cuántos símbolos de cada color exige un coste. {U/B} cuenta para los dos."""
    fuera: dict[str, int] = {}
    for simbolo in re.findall(r"\{([^}]+)\}", coste or ""):
        for color in COLORES:
            if color in simbolo.upper():
                fuera[color] = fuera.get(color, 0) + 1
    return fuera


def _enlaces_de_mana(cartas: dict[str, Any]) -> list[dict[str, Any]]:
    """Ata cada fuente de maná con los hechizos que más la necesitan.

    No es una sinergia: es la fontanería del mazo. Sin esto, las tierras salían
    sueltas aunque sean justo lo que permite lanzar el resto.
    """
    def fuentes_de(color: str) -> list[str]:
        """Las tierras primero: son la base de maná de verdad.

        Una carta que produce los cinco colores por su cara trasera es cierta según
        Scryfall, pero como fuente dice mucho menos que una dual.
        """
        return [n for n, _ in sorted(
            ((n, c) for n, c in cartas.items() if color in (c.get("produce_mana") or [])),
            key=lambda kv: ("Land" not in (kv[1].get("tipo") or ""),
                            -kv[1].get("copias", 1), kv[0]))]

    fuera: list[dict[str, Any]] = []
    for nombre, c in cartas.items():
        if "Land" in (c.get("tipo") or ""):
            continue
        pide = _simbolos(c.get("coste", ""))
        if pide:
            # el color que más exige es el que de verdad condiciona el lanzamiento
            color = max(sorted(pide), key=lambda x: pide[x])
            n = pide[color]
            for f in fuentes_de(color)[:POR_FUENTE]:
                fuera.append({
                    "a": f, "b": nombre, "f": 1, "m": 1, "r": 0,
                    "t": f"Maná {NOMBRE_COLOR[color]}",
                    "d": f"{nombre} pide {n} símbolo{'s' if n > 1 else ''} de maná "
                         f"{NOMBRE_COLOR[color]}, y {f} lo produce.",
                })
        elif float(c.get("mv", 0) or 0) >= CARO:
            for f in fuentes_de("C")[:POR_FUENTE]:
                fuera.append({
                    "a": f, "b": nombre, "f": 1, "m": 1, "r": 0,
                    "t": "Maná incoloro",
                    "d": f"{nombre} cuesta {int(float(c.get('mv', 0) or 0))} de maná, y "
                         f"{f} aporta el genérico que hace falta para levantarlo.",
                })
    return fuera


def _datos(documento: dict[str, Any]) -> dict[str, Any]:
    idx = indice(documento)
    sinergias = documento.get("sinergias", [])
    usadas: set[str] = set()
    for s in sinergias:
        usadas.update(s.get("piezas", []))
    # Todas las cartas entran en el mapa, tengan sinergia o no: una carta suelta
    # también dice algo del mazo, y antes desaparecía sin más.
    usadas.update(c["nombre"] for c in documento.get("cartas", []))

    cartas: dict[str, Any] = {}
    for nombre in sorted(usadas):
        c = idx.get(nombre, {})
        evidencia = ""
        for s in sinergias:
            ev = (s.get("evidencia") or {}).get(nombre)
            if ev:
                evidencia = ev
                break
        corto = nombre.split(",")[0]
        if len(corto) > 20:
            corto = corto[:19] + "…"
        cartas[nombre] = {
            "copias": c.get("copias", 1),
            "coste": c.get("coste", ""),
            "tipo": c.get("tipo", ""),
            "rol": c.get("rol", "motor"),
            "corto": corto,
            "estrategia": c.get("estrategia", ""),
            "evidencia": evidencia,
            "produce_mana": c.get("produce_mana", []),
        }

    enlaces = []
    for s in sinergias:
        piezas = s.get("piezas", [])
        for a, b in zip(piezas, piezas[1:]):
            enlaces.append({
                "a": a, "b": b,
                "f": int(s.get("fuerza", 2)),
                "t": s.get("nombre", ""),
                "d": s.get("resumen", ""),
                "r": 1 if s.get("tipo") in ("conflicto", "aviso") else 0,
            })

    enlaces.extend(_enlaces_de_mana(cartas))

    roles = {k: {"n": NOMBRE_ROL[k], "c": COLOR_ROL[k]} for k in COLOR_ROL}
    return {"cartas": cartas, "enlaces": enlaces, "roles": roles}


def render(documento: dict[str, Any]) -> str:
    # El escape de "<" evita que un nombre de carta con "</script>" corte el bloque.
    datos = json.dumps(_datos(documento), ensure_ascii=False).replace("<", "\\u003c")
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(documento.get('titulo',''))} — mapa de sinergias</title>
<style>{CSS}</style></head><body>
<div id="app"><div id="lienzo"><svg id="svg"></svg>
<div class="barra"><div><h1>{e(documento.get('titulo',''))} <em>· mapa de sinergias</em></h1>
<p>{e(documento.get('subtitulo',''))}</p></div><div class="chips" id="chips"></div></div>
<div class="pie">Arrastra las cartas · rueda para acercar</div>
<div class="leyenda"><span><i></i>sinergia</span><span><i class="r"></i>conflicto</span><span><i class="m"></i>maná</span></div>
</div><aside id="panel"></aside></div>
<script>const DATOS={datos};</script><script>{JS}</script></body></html>"""
