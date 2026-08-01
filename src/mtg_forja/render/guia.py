"""Guía extensa: una página larga con cada sinergia desarrollada.

El diseño vive en `guia.js`, no aquí. Este módulo solo arma el archivo autónomo:
incrusta el renderizador y el documento, igual que `mapa.py` hace con `grafo.js`.
Así la web y la línea de comandos pintan exactamente lo mismo, y no hay dos
implementaciones que puedan separarse.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .comun import e

COMUN = (Path(__file__).with_name("comun.js")).read_text(encoding="utf-8")
JS = (Path(__file__).with_name("guia.js")).read_text(encoding="utf-8")


def render(documento: dict[str, Any]) -> str:
    # El escape de "<" evita que un nombre de carta con "</script>" corte el bloque.
    datos = json.dumps(documento, ensure_ascii=False).replace("<", "\\u003c")
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(documento.get('titulo',''))} — guía de sinergias</title></head><body>
<script>const DOC={datos};</script>
<script>{COMUN}</script>
<script>{JS}</script>
<script>ForjaGuia.montar(DOC);</script>
</body></html>"""
