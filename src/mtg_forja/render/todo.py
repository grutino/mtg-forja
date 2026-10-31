"""Un solo HTML con todo: guía, chuleta, mapa y la lista para Arena, en pestañas.

Cada documento se monta en su propio marco, así sus estilos no chocan entre sí y el
mapa, la chuleta y la guía funcionan igual que sueltos. Con imágenes incrustadas, las
imágenes van una sola vez en la página y los tres documentos las leen de ahí.
"""
from __future__ import annotations

import json
from typing import Any

from . import chuleta as r_chuleta
from . import guia as r_guia
from . import mapa as r_mapa
from .comun import e
from .incrustar import imagenes, incrustar_hijo

PESTANAS = (("guia", "Guía"), ("chuleta", "Chuleta"), ("mapa", "Mapa"), ("arena", "Arena"))

CSS = """
:root{--ceniza:#15120F;--pap:#EFEADF;--brasa:#C1462A;--laton:#D8B15E;--humo:#8B8175;
 --s:"Charter","Bitstream Charter",Georgia,serif;
 --c:"Avenir Next Condensed","DejaVu Sans Condensed","Arial Narrow",sans-serif}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{background:var(--ceniza);color:var(--pap);font-family:var(--s);display:flex;flex-direction:column}
.barra{display:flex;align-items:center;gap:18px;padding:8px 16px;flex-wrap:wrap;
 border-bottom:1px solid #3A332B}
.barra h1{margin:0;font-size:18px;font-weight:700;white-space:nowrap}
.barra h1 em{font-style:normal;color:var(--laton);font-weight:400}
nav{display:flex;gap:4px;flex-wrap:wrap}
nav button{font-family:var(--c);text-transform:uppercase;letter-spacing:.12em;font-size:12px;
 background:transparent;color:var(--humo);border:1px solid #3A332B;padding:7px 14px;cursor:pointer}
nav button[aria-selected=true]{color:var(--ceniza);background:var(--laton);border-color:var(--laton)}
.acciones{margin-left:auto}
.acciones button{font-family:var(--c);text-transform:uppercase;letter-spacing:.1em;font-size:11px;
 background:var(--brasa);color:#fff;border:0;padding:7px 12px;cursor:pointer}
main{flex:1;position:relative;min-height:0}
.panel{position:absolute;inset:0;display:none}
.panel.activo{display:block}
iframe{width:100%;height:100%;border:0;display:block;background:#fff}
#p-arena{overflow:auto;padding:24px 16px;background:#E6DFD2;color:#1E1A16}
#p-arena .caja{max-width:640px;margin:0 auto}
#p-arena h2{margin:0 0 6px}
#p-arena p{margin:0 0 14px;color:#5E554B}
#p-arena pre{background:#F4EFE6;border:1px solid #CFC5B4;padding:14px 18px;font-size:13px;
 line-height:1.45;white-space:pre-wrap}
#p-arena button{font-family:var(--c);text-transform:uppercase;letter-spacing:.1em;font-size:12px;
 padding:8px 14px;border:0;background:#1E1A16;color:#EFEADF;cursor:pointer}
@media print{.barra{display:none}}
"""

JS = """
const ids=%s;
function abrir(id){
  for(const x of ids){
    document.getElementById('p-'+x).classList.toggle('activo',x===id);
    document.getElementById('b-'+x).setAttribute('aria-selected',x===id);
  }
  const f=document.querySelector('#p-'+id+' iframe');
  if(f&&!f.srcdoc){f.srcdoc=JSON.parse(document.getElementById('d-'+id).textContent);}
  document.getElementById('imprimir').style.display=id==='chuleta'?'':'none';
  try{history.replaceState(null,'','#'+id)}catch(e){}
}
for(const x of ids){document.getElementById('b-'+x).onclick=()=>abrir(x);}
document.getElementById('imprimir').onclick=()=>{
  const f=document.querySelector('#p-chuleta iframe');f&&f.contentWindow&&f.contentWindow.print();};
const c=document.getElementById('copiar');
if(c)c.onclick=()=>{navigator.clipboard&&navigator.clipboard.writeText(
  document.getElementById('arena-txt').textContent).then(()=>{c.textContent='Copiado'})};
const h=(location.hash||'').slice(1);abrir(ids.includes(h)?h:'guia');
"""


def _json_seguro(x: Any) -> str:
    # Escapar "<" evita que un "</script>" dentro de un documento corte el bloque.
    return json.dumps(x, ensure_ascii=False).replace("<", "\\u003c")


def render(documento: dict[str, Any], incrustar_imagenes: bool = False) -> str:
    docs = {"guia": r_guia.render(documento), "chuleta": r_chuleta.render(documento),
            "mapa": r_mapa.render(documento)}
    imgs = ""
    if incrustar_imagenes:
        mapa = imagenes([c["nombre"] for c in documento.get("cartas", [])])
        if mapa:
            imgs = f"<script>window.FORJA_IMG={_json_seguro(mapa)};</script>"
            docs = {k: incrustar_hijo(v) for k, v in docs.items()}

    pestanas = [p for p in PESTANAS if p[0] != "arena" or documento.get("arena")]
    botones = "".join(f'<button id="b-{k}" role="tab" aria-selected="false">{n}</button>'
                      for k, n in pestanas)
    paneles = "".join(
        f'<section class="panel" id="p-{k}"><iframe title="{n}"></iframe></section>'
        f'<script type="application/json" id="d-{k}">{_json_seguro(docs[k])}</script>'
        for k, n in pestanas if k in docs)
    if documento.get("arena"):
        paneles += ('<section class="panel" id="p-arena"><div class="caja"><h2>El mazo para Arena</h2>'
                    '<p>Copia la lista y pégala en MTG Arena: Mazos → Importar.</p>'
                    '<button id="copiar" type="button">Copiar lista</button>'
                    f'<pre id="arena-txt">{e(documento["arena"])}</pre></div></section>')
    ids = [k for k, _ in pestanas]
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(documento.get('titulo', ''))} — MTG Forja</title><style>{CSS}</style>{imgs}</head><body>
<header class="barra"><h1>{e(documento.get('titulo', ''))} <em>· MTG Forja</em></h1>
<nav role="tablist">{botones}</nav>
<div class="acciones"><button id="imprimir" type="button">Imprimir chuleta</button></div></header>
<main>{paneles}</main>
<script>{JS % _json_seguro(ids)}</script></body></html>"""
