"""Mapa interactivo: grafo de fuerzas navegable con panel de detalle."""
from __future__ import annotations

import json
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
#app{display:flex}
""" + (Path(__file__).with_name("grafo.css")).read_text(encoding="utf-8")

JS = (Path(__file__).with_name("grafo.js")).read_text(encoding="utf-8")


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
<div class="leyenda"><span><i></i>sinergia</span><span><i class="r"></i>conflicto</span></div>
</div><aside id="panel"></aside></div>
<script>const DATOS={datos};</script><script>{JS}</script></body></html>"""
