#!/usr/bin/env python3
"""¿Qué etiquetas funcionales existen hoy en Scryfall, y cuáles nos sirven?

Scryfall mantiene un etiquetado comunitario que se consulta con `otag:`. No hay
catálogo público para listarlas, así que este guion prueba nombres candidatos
contra la API y se queda con los que existen, ordenados por cuántas cartas usan.

    python scripts/etiquetas_descubrir.py                 # informe
    python scripts/etiquetas_descubrir.py --guardar       # actualiza etiquetas.json

Es el equivalente de auditar_cobertura.py para la fuente externa: dice qué hay
disponible ahí fuera que todavía no estamos aprovechando.
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

AGENTE = "mtg-forja/0.1 (+https://github.com/grutino/mtg-forja)"
RUTA = RAIZ / "src" / "mtg_forja" / "etiquetas.json"
MINIMO = 10

# Candidatos: los que ya usamos más los que se le ocurren a cualquiera que juegue.
# Probarlos cuesta una petición; el que no exista, se descarta solo.
CANDIDATOS = """drawback downside cantrip tutor flicker phasing ramp removal counterspell
sacrifice-outlet lifegain mill discard graveyard-hate recursion reanimate protection
untapper tapper mana-sink bounce wheel extra-turn extra-combat damage-doubler lord
anthem landfall blink copy-spell copy-permanent unblockable evasion fog pitch-spell
attack-trigger death-trigger free-spell storm cost-reduction land-destruction stax
tribal-support equipment-matters aura-matters spellslinger pump fight""".split()


def cuantas(tag: str) -> int | None:
    """Cartas con esa etiqueta. None si la consulta no se pudo hacer."""
    url = ("https://api.scryfall.com/cards/search?unique=cards&q="
           + urllib.parse.quote(f"otag:{tag}"))
    pet = urllib.request.Request(url, headers={"User-Agent": AGENTE,
                                               "Accept": "application/json"})
    for intento in range(4):
        try:
            with urllib.request.urlopen(pet, timeout=25) as r:
                return int(json.loads(r.read().decode("utf-8")).get("total_cards", 0))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 0          # la etiqueta no existe
            if e.code == 429 and intento < 3:
                time.sleep(1.5 * (intento + 1))
                continue
            return None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return None
    return None


def main() -> int:
    p = argparse.ArgumentParser(description="Descubre etiquetas funcionales de Scryfall.")
    p.add_argument("--guardar", action="store_true", help="reescribe etiquetas.json")
    args = p.parse_args()

    actuales = json.loads(RUTA.read_text(encoding="utf-8"))["etiquetas"]
    vivas, fallidas = {}, []
    for i, tag in enumerate(sorted(set(CANDIDATOS) | set(actuales)), 1):
        n = cuantas(tag)
        if n is None:
            fallidas.append(tag)
        elif n >= MINIMO:
            vivas[tag] = n
        time.sleep(0.16)
        if i % 20 == 0:
            print(f"   probadas {i}…", file=sys.stderr, flush=True)

    nuevas = sorted(set(vivas) - set(actuales))
    perdidas = sorted(set(actuales) - set(vivas) - set(fallidas))

    print(f"etiquetas vivas: {len(vivas)}   (mínimo {MINIMO} cartas)")
    if nuevas:
        print("\nNUEVAS, aún sin aprovechar:")
        for t in nuevas:
            print(f"   {vivas[t]:>6}  otag:{t}")
    if perdidas:
        print("\nYa no existen o han caído bajo el mínimo:", ", ".join(perdidas))
    if fallidas:
        print(f"\nSin comprobar ({len(fallidas)}): no son ausencias, son fallos de red.")

    if args.guardar and not fallidas:
        doc = json.loads(RUTA.read_text(encoding="utf-8"))
        doc["etiquetas"] = dict(sorted(vivas.items(), key=lambda kv: -kv[1]))
        RUTA.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\netiquetas.json actualizado: {len(vivas)} etiquetas.")
    elif args.guardar:
        print("\nNO se guarda: hubo consultas sin respuesta y el informe está incompleto.")
    return 1 if nuevas else 0


if __name__ == "__main__":
    raise SystemExit(main())
