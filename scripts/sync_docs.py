#!/usr/bin/env python3
"""Copia a docs/ los artefactos compartidos con el paquete Python.

El paquete de reglas y el código del grafo tienen una sola fuente de verdad,
dentro de src/. Este script los sincroniza con la web de GitHub Pages para que
las dos mitades del proyecto no se contradigan nunca.
"""
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
COPIAS = [
    ("src/mtg_forja/reglas.json", "docs/reglas.json"),
    ("src/mtg_forja/render/grafo.js", "docs/grafo.js"),
    ("src/mtg_forja/render/comun.js", "docs/comun.js"),
    ("src/mtg_forja/render/guia.js", "docs/guia.js"),
    ("src/mtg_forja/render/chuleta.js", "docs/chuleta.js"),
]

for origen, destino in COPIAS:
    o, d = RAIZ / origen, RAIZ / destino
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(o, d)
    print(f"{origen} -> {destino}")
