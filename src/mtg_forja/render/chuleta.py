"""Chuleta: dos caras A4 densas, pensadas para imprimir y tener al lado."""
from __future__ import annotations

from typing import Any

from .comun import (CSS_CURVA, PALETA, bloques, curva_svg, e, imagen, indice)

CSS = PALETA + CSS_CURVA + """
*{box-sizing:border-box}
body{margin:0;background:#D9D2C4;font-family:var(--serif);color:var(--tinta)}
.hoja{width:210mm;min-height:297mm;margin:14px auto;background:var(--papel);padding:9mm 9mm 7mm;
 box-shadow:0 3px 14px rgba(0,0,0,.2);display:flex;flex-direction:column}
h1{font-size:20pt;margin:0;line-height:1;letter-spacing:-.01em}
h1 em{font-style:normal;color:var(--brasa)}
.sub{font-family:var(--cond);text-transform:uppercase;letter-spacing:.14em;font-size:6.6pt;
 color:var(--humo);margin:3px 0 0}
.cab{display:flex;justify-content:space-between;align-items:flex-end;
 border-bottom:1.6pt solid var(--tinta);padding-bottom:5px;margin-bottom:7px}
.cab .curva{height:34px}
.cab .cb{width:13px}
.cab .cb i{font-size:5.6pt;bottom:-9px}
.cab .cb u{font-size:6pt}
.curva-w{text-align:right}
.curva-w p{font-family:var(--cond);font-size:5.8pt;text-transform:uppercase;letter-spacing:.1em;
 color:var(--humo);margin:11px 0 0}
.cols{column-count:2;column-gap:6mm;flex:1}
.bl{break-inside:avoid-column;margin-bottom:5px}
h2{font-family:var(--cond);font-size:7.4pt;text-transform:uppercase;letter-spacing:.16em;
 color:var(--brasa);margin:6px 0 4px;padding-bottom:2px;border-bottom:.8pt solid var(--lin)}
.r{display:flex;gap:5px;break-inside:avoid;margin-bottom:6px;align-items:flex-start}
.ts{display:flex;gap:2px;flex:0 0 auto;padding-top:1px}
.t{position:relative;width:29px;display:block}
.t img{width:100%;aspect-ratio:488/680;object-fit:cover;display:block;border-radius:2px;
 background:#2b241d;position:relative;z-index:2}
.t em{position:absolute;inset:0;z-index:1;display:flex;align-items:center;justify-content:center;
 text-align:center;font-family:var(--cond);font-size:4.4pt;font-style:normal;color:#CBBFA6;
 padding:2px;line-height:1.05;text-transform:uppercase}
.t .n{position:absolute;top:-3px;left:-3px;z-index:3;background:var(--brasa);color:#fff;
 font-family:var(--cond);font-style:normal;font-weight:700;font-size:6.2pt;width:12px;height:12px;
 border-radius:50%;display:flex;align-items:center;justify-content:center}
.d{flex:1;min-width:0}
p{margin:0}
.h{font-size:8.4pt;font-weight:700;line-height:1.15}
.tn{font-family:var(--cond);font-size:6pt;font-weight:700;letter-spacing:.06em;color:#fff;
 background:var(--tinta);padding:1px 4px;border-radius:2px;margin-right:5px;vertical-align:1px;
 text-transform:uppercase}
.r.conflicto .tn,.r.aviso .tn{background:var(--brasa)}
.x{font-size:7.8pt;line-height:1.3;margin-top:1px}
.o{font-size:7pt;line-height:1.25;color:var(--brasa);margin-top:1px;padding-left:7px;
 border-left:1.4pt solid var(--brasa)}
.orden{display:flex;gap:4px;justify-content:space-between;margin-top:4px}
.ob{flex:1;text-align:center;font-size:7pt;line-height:1.2}
.ob .t{width:100%;margin:0 auto 3px}
.ob i{display:block;font-style:normal;font-family:var(--cond);font-weight:700;font-size:6.4pt;
 color:var(--brasa);letter-spacing:.06em}
.ob em{font-style:normal;display:block;font-size:6.8pt}
.pie{margin-top:auto;padding-top:5px;border-top:1pt solid var(--tinta);display:flex;
 justify-content:space-between;font-family:var(--cond);font-size:5.8pt;text-transform:uppercase;
 letter-spacing:.1em;color:var(--humo)}
@media print{@page{size:A4;margin:0}body{background:#fff}
 .hoja{margin:0;box-shadow:none;page-break-after:always;min-height:0;height:297mm}
 .hoja:last-child{page-break-after:auto}
 *{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def _mini(nombre: str, copias: int | None = None) -> str:
    n = f'<i class="n">{copias}</i>' if copias else ""
    return (f'<span class="t">{n}<img loading="lazy" alt="{e(nombre)}" '
            f'src="{imagen(nombre, "small")}"><em>{e(nombre)}</em></span>')


def render(documento: dict[str, Any]) -> str:
    idx = indice(documento)
    columnas: list[str] = []

    for bloque, lista in bloques(documento):
        filas = []
        for s in lista:
            minis = "".join(
                _mini(n, (idx.get(n) or {}).get("copias")) for n in s.get("piezas", [])
            )
            aviso = f'<p class="o">{s["aviso"]}</p>' if s.get("aviso") else ""
            filas.append(
                f'<div class="r {e(s.get("tipo",""))}"><div class="ts">{minis}</div><div class="d">'
                f'<p class="h"><span class="tn">{e(s.get("turno") or "—")}</span>'
                f'{e(s.get("nombre",""))}</p>'
                f'<p class="x">{s.get("resumen","")}</p>{aviso}</div></div>'
            )
        columnas.append(f'<section class="bl"><h2>{e(bloque)}</h2>{"".join(filas)}</section>')

    orden = "".join(
        f'<span class="ob">{_mini(o.get("carta",""))}<i>{e(o.get("turno",""))}</i>'
        f'<em>{e(o.get("resumen") or o.get("que",""))}</em></span>'
        for o in documento.get("orden", [])
    )
    reglas = "".join(
        f'<p class="x" style="margin-bottom:4px"><b>{i + 1}.</b> {r}</p>'
        for i, r in enumerate(documento.get("reglas_oro", []))
    )

    cara2 = ""
    if orden or reglas:
        cara2 = f"""<div class="hoja">
<div class="cab"><div><h1>Orden <em>· y reglas</em></h1>
<p class="sub">La secuencia por defecto y los principios que no cambian</p></div></div>
{'<h2>Orden de aparición</h2><div class="orden">' + orden + '</div>' if orden else ''}
{'<h2 style="margin-top:12px">Reglas de oro</h2><div class="cols">' + reglas + '</div>' if reglas else ''}
<div class="pie"><span>Cara 2 · secuencia</span><span>Generado con MTG Forja</span></div></div>"""

    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>{e(documento.get('titulo',''))} — chuleta</title><style>{CSS}</style></head><body>
<div class="hoja">
<div class="cab">
 <div><h1>{e(documento.get('titulo',''))} <em>· chuleta de combos</em></h1>
 <p class="sub">{e(documento.get('subtitulo',''))}</p></div>
 <div class="curva-w">{curva_svg(documento.get('curva', {}))}<p>Curva por valor de maná</p></div>
</div>
<div class="cols">{''.join(columnas)}</div>
<div class="pie"><span>Cara 1 · sinergias</span>
<span>Los números rojos son copias en el mazo</span></div>
</div>{cara2}</body></html>"""
