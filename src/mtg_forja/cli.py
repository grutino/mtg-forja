"""Línea de comandos: analiza un mazo sin necesidad de un cliente MCP."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import lexico
from . import reglas as motor
from . import scryfall
from .render import chuleta as r_chuleta
from .render import guia as r_guia
from .render import mapa as r_mapa


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="mtg-forja",
        description="Analiza un mazo de Magic y genera guía, chuleta y mapa de sinergias.",
    )
    p.add_argument("lista", help="archivo con la lista del mazo, o - para leer de la entrada estándar")
    p.add_argument("-n", "--nombre", default="Mazo", help="nombre del mazo")
    p.add_argument("-o", "--salida", default="salida", help="carpeta de destino")
    p.add_argument("--json", action="store_true", help="volcar también el documento en JSON")
    args = p.parse_args(argv)

    texto = sys.stdin.read() if args.lista == "-" else Path(args.lista).read_text(encoding="utf-8")
    mazo = scryfall.resolver(texto, args.nombre)
    if not mazo.cartas:
        print("No se ha reconocido ninguna carta en la lista.", file=sys.stderr)
        return 1

    # Sin red, Scryfall no resuelve nada y los tres documentos saldrían vacíos.
    # Salir en silencio con código 0 haría creer que ha ido bien.
    if not any(c.resuelta for c in mazo.cartas):
        print("No se ha podido resolver ninguna carta contra Scryfall. Revisa la "
              "conexión a internet, o la grafía de los nombres si la lista es rara.",
              file=sys.stderr)
        return 1

    sinergias = lexico.completo(mazo)
    doc = motor.documento(mazo, sinergias, titulo=args.nombre)

    destino = Path(args.salida)
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "guia.html").write_text(r_guia.render(doc), encoding="utf-8")
    (destino / "chuleta.html").write_text(r_chuleta.render(doc), encoding="utf-8")
    (destino / "mapa.html").write_text(r_mapa.render(doc), encoding="utf-8")
    if args.json:
        (destino / "documento.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"{mazo.total} cartas · {len(sinergias)} sinergias · {destino.resolve()}")
    if mazo.no_resueltas:
        print("Sin resolver: " + ", ".join(mazo.no_resueltas), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
