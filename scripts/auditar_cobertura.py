#!/usr/bin/env python3
"""¿Se le está escapando algo al léxico?

Cada colección nueva trae mecánicas nuevas, y el motor solo sabe lo que alguien le
ha escrito. Este guion no lo arregla: lo hace visible. Pregunta a Scryfall qué
mecánicas existen hoy en Magic, mira cuántas cartas usa cada una, y avisa de las
que ningún concepto del léxico menciona.

El orden es por número de cartas a propósito. De las 371 mecánicas del juego, la
inmensa mayoría son residuales de colecciones antiguas con menos de veinte cartas;
las que merecen un concepto son las pocas que se usan de verdad.

    python scripts/auditar_cobertura.py            # informe
    python scripts/auditar_cobertura.py --minimo 25  # solo lo que pasa de 25 cartas

Sale con código 1 si encuentra alguna por encima del mínimo, para que un cron o
una acción de CI pueda avisar sola.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from mtg_forja.lexico import EVERGREEN  # noqa: E402

AGENTE = "mtg-forja/0.1 (+https://github.com/grutino/mtg-forja)"
CATALOGOS = ("keyword-abilities", "keyword-actions", "ability-words")
CACHE = Path("/tmp/mtg-forja-auditoria.json")


def _pedir(url: str) -> dict:
    pet = urllib.request.Request(url, headers={"User-Agent": AGENTE,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(pet, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def mecanicas() -> list[str]:
    fuera: set[str] = set()
    for cat in CATALOGOS:
        fuera |= set(_pedir(f"https://api.scryfall.com/catalog/{cat}").get("data", []))
        time.sleep(0.12)
    return sorted(fuera)


def cuantas_cartas(nombres: list[str], cache: dict[str, int]) -> dict[str, int]:
    """Cartas por mecánica. Se cachea: es lento y cambia poco."""
    for i, k in enumerate(nombres, 1):
        if k in cache:
            continue
        q = urllib.parse.quote(f'keyword:"{k}"')
        try:
            d = _pedir(f"https://api.scryfall.com/cards/search?q={q}&unique=cards")
            cache[k] = int(d.get("total_cards", 0))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            cache[k] = 0  # 404 = ninguna carta la usa
        time.sleep(0.11)
        if i % 50 == 0:
            print(f"   consultadas {i}/{len(nombres)}…", file=sys.stderr, flush=True)
    return cache


def main() -> int:
    p = argparse.ArgumentParser(description="Audita qué mecánicas del juego no cubre el léxico.")
    p.add_argument("--minimo", type=int, default=20,
                   help="cartas mínimas para considerar que una mecánica merece concepto")
    args = p.parse_args()

    texto = ((RAIZ / "src/mtg_forja/lexico.json").read_text(encoding="utf-8")
             + (RAIZ / "src/mtg_forja/reglas.json").read_text(encoding="utf-8")).lower()

    todas = mecanicas()
    sin_cubrir = [k for k in todas if k.lower() not in texto and k not in EVERGREEN]

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    cache = cuantas_cartas(sin_cubrir, cache)
    try:
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass

    relevantes = sorted(((k, cache.get(k, 0)) for k in sin_cubrir if cache.get(k, 0) >= args.minimo),
                        key=lambda kv: -kv[1])

    print(f"mecánicas en Magic: {len(todas)}")
    print(f"  cubiertas o de puro combate: {len(todas) - len(sin_cubrir)}")
    print(f"  sin cubrir: {len(sin_cubrir)}, de las que "
          f"{len(relevantes)} pasan de {args.minimo} cartas\n")

    if not relevantes:
        print(f"Nada que hacer: ninguna mecánica sin cubrir llega a {args.minimo} cartas.")
        return 0

    print("Merecen un concepto en lexico.json, de más a menos usada:")
    for k, n in relevantes:
        print(f"   {n:>5} cartas   {k}")
    print("\nCada concepto nuevo cubre de golpe todas las parejas que lo compartan.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
