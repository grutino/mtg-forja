"""Mete las imágenes de las cartas dentro del HTML, como data URI.

Los documentos enlazan las imágenes a Scryfall y el navegador las pide al
abrirlos. Hay visores —el de archivos del chat de Claude, por ejemplo— que
bloquean cualquier petición externa, y entonces salen los huecos sin cartas.
Con esto el archivo pesa más (unos 3 MB para 13 cartas) pero no pide nada fuera.
"""
from __future__ import annotations

import base64
import json
import re
import time
import urllib.parse
import urllib.request
from typing import Any

from ..scryfall import AGENTE

VERSIONES = ("small", "normal", "art_crop")


def clave(nombre: str) -> str:
    """Igual que hace el parche en el navegador: sin signos, minúsculas."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", nombre.lower())).strip()


def _bajar(url: str) -> bytes:
    pet = urllib.request.Request(url, headers={"User-Agent": AGENTE, "Accept": "*/*"})
    with urllib.request.urlopen(pet, timeout=30) as r:
        return r.read()


def imagenes(nombres: list[str]) -> dict[str, str]:
    """{clave|version: data URI}. Una carta que falle se queda con su enlace."""
    salida: dict[str, str] = {}
    for n in nombres:
        try:
            q = urllib.parse.urlencode({"exact": n})
            datos = json.loads(_bajar(f"https://api.scryfall.com/cards/named?{q}"))
            uris = datos.get("image_uris") or datos["card_faces"][0]["image_uris"]
            for v in VERSIONES:
                b = _bajar(uris[v])
                mime = "image/png" if uris[v].split("?")[0].endswith(".png") else "image/jpeg"
                salida[f"{clave(n)}|{v}"] = f"data:{mime};base64,{base64.b64encode(b).decode()}"
                time.sleep(0.08)  # Scryfall pide 50-100 ms entre peticiones
        except Exception:      # sin imagen no se rompe el documento
            continue
    return salida


PARCHE = """<script>(function(){const M=%s;
function sust(u){if(!u||u.indexOf('api.scryfall.com/cards/named')<0)return null;try{const p=new URL(u);
const q=(p.searchParams.get('fuzzy')||p.searchParams.get('exact')||'').replace(/\\+/g,' ').toLowerCase()
.replace(/[^a-z0-9 ]/g,'').replace(/\\s+/g,' ').trim();const v=p.searchParams.get('version')||'normal';
return M[q+'|'+v]||M[q+'|normal']||null}catch(e){return null}}
function fija(el){for(const a of ['src','href','xlink:href']){const u=el.getAttribute&&el.getAttribute(a);
const d=sust(u);if(d)el.setAttribute(a,d)}}
function barre(r){if(r.nodeType!==1)return;fija(r);r.querySelectorAll&&r.querySelectorAll('img,image').forEach(fija)}
new MutationObserver(ms=>ms.forEach(m=>{if(m.type==='attributes')fija(m.target);else m.addedNodes.forEach(barre)}))
.observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['src','href','xlink:href']});
document.addEventListener('DOMContentLoaded',()=>barre(document.documentElement));})();</script>"""


def incrustar(html: str, mapa: dict[str, str]) -> str:
    """Inserta el parche al principio de <head>, antes de que se pinte nada."""
    if not mapa:
        return html
    parche = PARCHE % json.dumps(mapa).replace("<", "\\u003c")
    if re.search(r"<head[^>]*>", html):
        return re.sub(r"<head[^>]*>", lambda m: m.group(0) + parche, html, count=1)
    return parche + html


def incrustar_documentos(htmls: dict[str, str], documento: dict[str, Any]) -> dict[str, str]:
    mapa = imagenes([c["nombre"] for c in documento.get("cartas", [])])
    return {k: incrustar(v, mapa) for k, v in htmls.items()}
