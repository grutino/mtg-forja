"""Paleta, tipografía y utilidades compartidas por los tres renderizadores."""
from __future__ import annotations

import html
import re
from typing import Any

IMG = ("https://api.scryfall.com/cards/named?fuzzy={q}"
       "&format=image&version={v}&face=front")

PALETA = """
:root{
  --ceniza:#1B1714;--fondo:#1E1A16;--pergamino:#E5DFD1;--papel:#EFEADF;
  --brasa:#A8321A;--laton:#9C7A22;--tinta:#2A241F;--humo:#7C7266;--lin:#C8BFAC;
  --serif:"Charter","Bitstream Charter",Georgia,"Times New Roman",serif;
  --cond:"Avenir Next Condensed","DejaVu Sans Condensed","Arial Narrow",sans-serif;
}
"""

# El pip incoloro se llama `inc`, no `c`: la guía usa `.c` para la ficha de
# carta (118px de ancho) y, al definirse después con la misma especificidad,
# ganaba y convertía el círculo del maná genérico en un óvalo.
PIPS = """
.pip{display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;
 border-radius:50%;font-family:var(--cond);font-size:9.5px;font-weight:700;line-height:1;
 border:1px solid rgba(0,0,0,.3);flex:0 0 auto}
.pip.w{background:#F5F1E4;color:#57503f}.pip.u{background:#8FBEDC;color:#22333d}
.pip.b{background:#3B3238;color:#e7dfe2}.pip.r{background:#C4472A;color:#fff8f0}
.pip.g{background:#7E9B6A;color:#1f2a19}.pip.inc{background:#C3BAA8;color:#3d382f}
"""

COLOR_ROL = {
    "motor": "#D8B15E",
    "amenaza": "#C1462A",
    "respuesta": "#D9D0C0",
    "tierra": "#7E8C5C",
}
NOMBRE_ROL = {
    "motor": "Motor", "amenaza": "Amenaza", "respuesta": "Respuesta", "tierra": "Tierra",
}


def e(t: Any) -> str:
    return html.escape(str(t if t is not None else ""))


def consulta(nombre: str) -> str:
    """Nombre de carta -> parámetro fuzzy de la API de Scryfall."""
    limpio = re.sub(r"[^\w\s'-]", " ", nombre.split("//")[0])
    return "+".join(limpio.split())


def imagen(nombre: str, version: str = "normal") -> str:
    return IMG.format(q=consulta(nombre), v=version)


def pips(coste: str) -> str:
    """Convierte {2}{W}{W} en círculos de color."""
    if not coste:
        return ""
    fuera = []
    for simbolo in re.findall(r"\{([^}]+)\}", coste):
        s = simbolo.upper()
        if s in "WUBRG":
            fuera.append(f'<i class="pip {s.lower()}">{s}</i>')
        elif s.isdigit() or s == "X":
            fuera.append(f'<i class="pip inc">{s}</i>')
        elif "/" in s:
            fuera.append(f'<i class="pip inc">{s[0]}</i>')
        else:
            fuera.append(f'<i class="pip inc">{s[0]}</i>')
    return "".join(fuera)


def indice(documento: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["nombre"]: c for c in documento.get("cartas", [])}


def bloques(documento: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    """Agrupa las sinergias por bloque conservando el orden de aparición."""
    orden: list[str] = []
    grupos: dict[str, list[dict[str, Any]]] = {}
    for s in documento.get("sinergias", []):
        b = s.get("bloque", "Otros")
        if b not in grupos:
            grupos[b] = []
            orden.append(b)
        grupos[b].append(s)
    return [(b, grupos[b]) for b in orden]


def curva_svg(curva: dict[str, int], ancho: int = 200, alto: int = 42) -> str:
    """Barras de la curva de maná, en HTML puro para que imprima bien."""
    if not curva:
        return ""
    tope = max(curva.values()) or 1
    cols = "".join(
        f'<span class="cb"><u>{v}</u><b style="height:{100 * v / tope:.0f}%"></b>'
        f"<i>{e(k)}</i></span>"
        for k, v in curva.items()
    )
    return f'<div class="curva" style="height:{alto}px">{cols}</div>'


CSS_CURVA = """
.curva{display:flex;gap:5px;align-items:flex-end}
.cb{width:16px;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;
 height:100%;position:relative}
.cb b{width:100%;background:linear-gradient(180deg,#C9A144,#A8321A);border-radius:2px 2px 0 0}
.cb i{font-style:normal;font-family:var(--cond);font-size:9px;color:var(--humo);
 position:absolute;bottom:-13px}
.cb u{text-decoration:none;font-family:var(--cond);font-size:10px;font-weight:700;margin-bottom:2px}
"""


def pie(documento: dict[str, Any]) -> str:
    aviso = ""
    if documento.get("no_resueltas"):
        aviso = (" · sin resolver: " +
                 e(", ".join(documento["no_resueltas"][:5])))
    return (
        '<footer><span>' + e(documento.get("titulo", "")) + aviso + "</span>"
        "<span>Generado con MTG Forja · imágenes de Scryfall · "
        "Magic: The Gathering © Wizards of the Coast</span></footer>"
    )
