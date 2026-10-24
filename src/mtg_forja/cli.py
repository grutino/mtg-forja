"""Línea de comandos.

La forja ya no analiza mazos por su cuenta: deducir sinergias con patrones de
texto inventaba jugadas («ganar vida» donde no había vida) y no entendía las
mecánicas nuevas. Ahora el trabajo va en dos pasos:

    mtg-forja datos  lista.txt -o carpeta
        Resuelve el mazo en Scryfall y guarda datos.json: oráculo, tipos,
        costes y rulings oficiales. Solo hechos, ninguna interpretación.

    mtg-forja forjar lista.txt --analisis analisis.json -o carpeta
        Comprueba el análisis que ha escrito el experto —citas literales,
        fuentes con URL y firma de la revisión— y, si todo cuadra, genera
        guía, chuleta y mapa. Si algo falla, no genera nada y dice qué.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import analisis as an
from . import scryfall
from .render import chuleta as r_chuleta
from .render import guia as r_guia
from .render import incrustar as r_incrustar
from .render import mapa as r_mapa

ORDENES = ("datos", "forjar")


def _leer_lista(ruta: str) -> str:
    return sys.stdin.read() if ruta == "-" else Path(ruta).read_text(encoding="utf-8")


def _resolver(ruta: str, nombre: str):
    mazo = scryfall.resolver(_leer_lista(ruta), nombre)
    if not mazo.cartas:
        print("No se ha reconocido ninguna carta en la lista.", file=sys.stderr)
        return None
    # Sin red, Scryfall no resuelve nada: salir con 0 haría creer que ha ido bien.
    if not any(c.resuelta for c in mazo.cartas):
        print("No se ha podido resolver ninguna carta contra Scryfall. Revisa la "
              "conexión a internet, o la grafía de los nombres si la lista es rara.",
              file=sys.stderr)
        return None
    return mazo


def _datos(args) -> int:
    mazo = _resolver(args.lista, args.nombre)
    if mazo is None:
        return 1
    destino = Path(args.salida)
    destino.mkdir(parents=True, exist_ok=True)
    datos = an.datos_para_experto(mazo, scryfall.rulings)
    (destino / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
    print(f"{mazo.total} cartas · hechos para el experto en {(destino / 'datos.json').resolve()}")
    if mazo.no_resueltas:
        print("Sin resolver: " + ", ".join(mazo.no_resueltas), file=sys.stderr)
    return 0


def _forjar(args) -> int:
    mazo = _resolver(args.lista, args.nombre)
    if mazo is None:
        return 1
    analisis = json.loads(Path(args.analisis).read_text(encoding="utf-8"))
    errores = an.validar(mazo, analisis, scryfall.rulings, scryfall.consultar)
    if errores:
        print(f"El análisis no se puede forjar ({len(errores)} problemas):", file=sys.stderr)
        for e in errores:
            print("  · " + e, file=sys.stderr)
        return 2
    doc = an.documento(mazo, analisis)
    htmls = {
        "guia.html": r_guia.render(doc),
        "chuleta.html": r_chuleta.render(doc),
        "mapa.html": r_mapa.render(doc),
    }
    if args.incrustar_imagenes:
        htmls = r_incrustar.incrustar_documentos(htmls, doc)
    destino = Path(args.salida)
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, html in htmls.items():
        (destino / nombre).write_text(html, encoding="utf-8")
    (destino / "documento.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
    rev = doc["revision_experta"]
    print(f"{mazo.total} cartas · {len(doc['sinergias'])} jugadas · "
          f"{doc['forjado']['citas_verificadas']} citas verificadas · "
          f"revisado por {rev.get('revisor')} · {destino.resolve()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ORDENES and not argv[0].startswith("-"):
        print("La forja ya no deduce sinergias por su cuenta: el análisis lo hace un "
              "experto.\n  1) mtg-forja datos LISTA -o carpeta      (hechos para el experto)\n"
              "  2) mtg-forja forjar LISTA --analisis analisis.json -o carpeta",
              file=sys.stderr)
        return 1

    p = argparse.ArgumentParser(
        prog="mtg-forja",
        description="Hechos de Scryfall para el experto y documentos de su análisis verificado.",
    )
    sub = p.add_subparsers(dest="orden", required=True)

    d = sub.add_parser("datos", help="resolver el mazo y guardar los hechos (oráculo y rulings)")
    f = sub.add_parser("forjar", help="validar el análisis del experto y generar los documentos")
    for q in (d, f):
        q.add_argument("lista", help="archivo con la lista del mazo, o - para la entrada estándar")
        q.add_argument("-n", "--nombre", default="Mazo", help="nombre del mazo")
        q.add_argument("-o", "--salida", default="salida", help="carpeta de destino")
    f.add_argument("-a", "--analisis", required=True, help="análisis del experto en JSON")
    f.add_argument("--incrustar-imagenes", action="store_true",
                   help="meter las imágenes dentro del HTML (para visores que bloquean la red)")

    args = p.parse_args(argv)
    return _datos(args) if args.orden == "datos" else _forjar(args)


if __name__ == "__main__":
    raise SystemExit(main())
