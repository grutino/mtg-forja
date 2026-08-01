"""Guía extensa: una página larga con cada sinergia desarrollada."""
from __future__ import annotations

from typing import Any

from .comun import (CSS_CURVA, NOMBRE_ROL, PALETA, PIPS, bloques, curva_svg, e,
                    imagen, indice, pie, pips)

CSS = PALETA + PIPS + CSS_CURVA + """
*{box-sizing:border-box}
body{margin:0;background:var(--pergamino);color:var(--tinta);font-family:var(--serif);
 font-size:15px;line-height:1.5}
.wrap{max-width:1000px;margin:0 auto;padding:0 28px 64px}
header{background:var(--ceniza);color:var(--papel);position:relative;overflow:hidden;margin-bottom:44px}
header .wrap{padding:46px 28px 44px;position:relative;z-index:2}
.sol{position:absolute;left:50%;bottom:-260px;transform:translateX(-50%);width:620px;height:620px;
 border-radius:50%;background:radial-gradient(circle,rgba(230,196,120,.30) 0%,
 rgba(168,50,26,.20) 42%,rgba(27,23,20,0) 68%);z-index:1}
.eyebrow{font-family:var(--cond);text-transform:uppercase;letter-spacing:.20em;font-size:11px;
 font-weight:700;color:var(--laton)}
header .eyebrow{color:#D8B15E}
h1{font-size:clamp(38px,7vw,60px);line-height:.96;margin:10px 0 6px;font-weight:700;letter-spacing:-.01em}
h1 em{font-style:normal;color:#D8B15E}
.dek{color:#B9AE9C;max-width:56ch;margin:0}
.c{margin:0;width:118px;position:relative;flex:0 0 auto}
.c .marco{display:block;position:relative;aspect-ratio:488/680;border-radius:6px;overflow:hidden;
 background:linear-gradient(160deg,#3a332c,#191512);box-shadow:0 2px 6px rgba(30,22,14,.28)}
.c img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;z-index:2}
.c .ph{position:absolute;inset:0;z-index:1;display:flex;align-items:center;justify-content:center;
 text-align:center;padding:8px;font-family:var(--cond);font-size:11px;font-weight:700;
 letter-spacing:.04em;color:#C9BFA8;text-transform:uppercase}
.c figcaption{font-size:11.5px;line-height:1.25;margin-top:5px;font-weight:700;display:flex;
 flex-wrap:wrap;gap:4px;align-items:center}
.c .n{position:absolute;top:-7px;left:-7px;z-index:3;background:var(--brasa);color:#fff;
 font-family:var(--cond);font-weight:700;font-size:13px;line-height:1;width:27px;height:27px;
 border-radius:50%;display:flex;align-items:center;justify-content:center;
 box-shadow:0 1px 3px rgba(0,0,0,.35)}
.c .n small{font-size:9px;margin-left:1px}
.piezas{display:flex;flex-wrap:wrap;align-items:flex-start;gap:14px;margin:16px 0 18px}
.mas{font-family:var(--cond);color:var(--humo);font-size:18px;font-weight:700;align-self:center;
 margin-top:-14px}
.seccion{margin-top:48px}
.seccion h2{font-size:26px;margin:2px 0 4px;font-weight:700;letter-spacing:-.015em;
 border-bottom:2px solid var(--tinta);padding-bottom:10px}
.seccion .intro{color:var(--humo);margin:12px 0 0;font-size:14px;max-width:70ch}
.combo{margin-top:28px;padding-left:74px;position:relative;break-inside:avoid}
.turno{position:absolute;left:0;top:2px;width:60px;text-align:center;font-family:var(--cond);
 font-weight:700;font-size:11px;letter-spacing:.05em;color:var(--brasa);border:1px solid var(--brasa);
 border-radius:3px;padding:3px 2px;text-transform:uppercase}
.combo.conflicto .turno,.combo.aviso .turno{color:var(--humo);border-color:var(--lin)}
.combo h3{margin:0;font-size:19px;font-weight:700;letter-spacing:-.01em}
.combo h3 .que{color:var(--humo);font-weight:400;font-size:15px;display:block;margin-top:2px}
ol.sec{margin:0;padding:0;list-style:none;counter-reset:paso}
ol.sec li{counter-increment:paso;position:relative;padding-left:26px;margin-bottom:7px;font-size:14.5px}
ol.sec li::before{content:counter(paso);position:absolute;left:0;top:1px;font-family:var(--cond);
 font-size:11px;font-weight:700;width:17px;height:17px;border-radius:50%;background:var(--tinta);
 color:var(--papel);display:flex;align-items:center;justify-content:center}
.ojo{margin-top:12px;padding:9px 13px;background:rgba(168,50,26,.07);border-left:3px solid var(--brasa);
 font-size:13.5px;line-height:1.45}
.ojo b{font-family:var(--cond);text-transform:uppercase;letter-spacing:.08em;font-size:11px;
 color:var(--brasa);display:block;margin-bottom:2px}
.grupo{margin-top:26px;break-inside:avoid}
.grupo .eyebrow span{color:var(--tinta);margin-left:6px}
.rejilla{display:flex;flex-wrap:wrap;gap:14px;margin-top:12px}
footer{margin-top:52px;padding-top:18px;border-top:2px solid var(--tinta);font-size:12.5px;
 color:var(--humo);display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}
footer span{font-family:var(--cond);letter-spacing:.06em;text-transform:uppercase;font-size:11px}
@media (max-width:680px){.wrap{padding:0 16px 48px}.combo{padding-left:0}
 .turno{position:static;display:inline-block;margin-bottom:8px;width:auto;padding:3px 10px}
 .c{width:96px}}
@media print{@page{size:A4;margin:12mm}body{background:#fff;font-size:10.5pt}
 *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
 .sol{display:none}.wrap{max-width:none;padding:0}header .wrap{padding:24px 18px}
 .c{width:92px}.seccion{margin-top:24px}.combo{margin-top:18px}}
"""


def _ficha(carta: dict[str, Any] | None, nombre: str, contar: bool = True) -> str:
    copias = carta.get("copias") if carta else None
    coste = carta.get("coste", "") if carta else ""
    tipo = carta.get("tipo", "") if carta else ""
    badge = f'<span class="n">{copias}<small>×</small></span>' if (contar and copias) else ""
    sub = pips(coste) or (
        '<span style="font-family:var(--cond);font-size:10px;letter-spacing:.08em;'
        'text-transform:uppercase;color:var(--humo)">tierra</span>'
        if "Land" in tipo else ""
    )
    return (
        f'<figure class="c">{badge}<span class="marco"><span class="ph">{e(nombre)}</span>'
        f'<img loading="lazy" alt="{e(nombre)}" src="{imagen(nombre)}"></span>'
        f'<figcaption>{e(nombre)}<span class="coste">{sub}</span></figcaption></figure>'
    )


def render(documento: dict[str, Any]) -> str:
    idx = indice(documento)
    partes: list[str] = []

    if documento.get("curva"):
        partes.append(
            '<section class="seccion"><p class="eyebrow">Punto de partida</p>'
            "<h2>La curva del mazo</h2>"
            f'<p class="intro">{e(documento.get("subtitulo", ""))}</p>'
            f'<div style="margin-top:26px">{curva_svg(documento["curva"], alto=140)}</div>'
            '<p style="margin-top:26px;font-size:13px;color:var(--humo)">Valor de maná de los '
            "hechizos. Las tierras no cuentan.</p></section>"
        )

    for bloque, lista in bloques(documento):
        combos = []
        for s in lista:
            piezas = "".join(
                ('<span class="mas">+</span>' if i else "") + _ficha(idx.get(n), n)
                for i, n in enumerate(s.get("piezas", []))
            )
            pasos = "".join(f"<li>{p}</li>" for p in s.get("pasos", []))
            aviso = ""
            if s.get("aviso"):
                aviso = f'<div class="ojo"><b>Ojo</b>{s["aviso"]}</div>'
            elif s.get("tipo") == "conflicto":
                aviso = ('<div class="ojo"><b>Conflicto</b>Estas cartas se estorban entre sí: '
                         "revisa el orden en que las juegas.</div>")
            combos.append(
                f'<div class="combo {e(s.get("tipo", ""))}">'
                f'<div class="turno">{e(s.get("turno") or "—")}</div>'
                f'<h3>{e(s.get("nombre", ""))}<span class="que">{s.get("resumen", "")}</span></h3>'
                f'<div class="piezas">{piezas}</div><ol class="sec">{pasos}</ol>{aviso}</div>'
            )
        partes.append(
            f'<section class="seccion"><p class="eyebrow">{e(bloque)}</p>'
            f"<h2>{e(bloque)}</h2>" + "".join(combos) + "</section>"
        )

    if documento.get("orden"):
        filas = "".join(
            '<div class="combo"><div class="turno">%s</div><h3>%s<span class="que">%s</span></h3></div>'
            % (e(o.get("turno", "")), e(o.get("carta", "")), o.get("que", ""))
            for o in documento["orden"]
        )
        partes.append('<section class="seccion"><p class="eyebrow">Secuencia</p>'
                      "<h2>Orden de aparición</h2>" + filas + "</section>")

    grupos: dict[str, list[dict[str, Any]]] = {}
    for c in documento.get("cartas", []):
        grupos.setdefault(c.get("rol", "otros"), []).append(c)
    rejillas = "".join(
        '<div class="grupo"><p class="eyebrow">%s <span>%d</span></p><div class="rejilla">%s</div></div>'
        % (
            e(NOMBRE_ROL.get(rol, rol)),
            sum(c.get("copias", 0) for c in cartas),
            "".join(_ficha(c, c["nombre"]) for c in cartas),
        )
        for rol, cartas in grupos.items()
    )
    partes.append('<section class="seccion"><p class="eyebrow">Referencia</p>'
                  "<h2>El mazo completo</h2>" + rejillas + "</section>")

    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(documento.get('titulo',''))} — guía de sinergias</title><style>{CSS}</style></head><body>
<header><div class="sol"></div><div class="wrap">
<p class="eyebrow">{e(documento.get('subtitulo',''))}</p>
<h1>{e(documento.get('titulo',''))}<br><em>guía de sinergias</em></h1>
<p class="dek">Cada jugada del mazo con sus cartas a la vista y el orden en que se ejecuta.
Pasa el ratón por encima de cualquier carta para verla grande.</p>
</div></header><div class="wrap">{''.join(partes)}{pie(documento)}</div></body></html>"""
