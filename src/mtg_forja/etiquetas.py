"""Etiquetas funcionales de Scryfall: qué dice de estas cartas gente que no somos nosotros.

El motor deduce lo que hace una carta leyendo su oráculo con patrones nuestros.
Esto es una segunda opinión, y viene de fuera: Scryfall mantiene un etiquetado
funcional comunitario —`otag:ramp`, `otag:drawback`, `otag:pitch-spell`— que se
consulta con el operador `otag:` de su API pública.

Sirve para tres cosas, por orden de utilidad:

1. **Contrastar.** Si el motor dice que una carta es un lastre al entrar y la
   etiqueta `drawback` coincide, hay dos fuentes independientes de acuerdo.
2. **Ver lo que se nos escapa.** Una carta con etiquetas jugosas y sin ninguna
   línea en el mapa es una pista de que falta un concepto.
3. **Describir el mazo** sin depender de nuestras propias categorías.

No es oráculo verificado: la etiqueta la puso una persona, y puede faltar o
sobrar. Se trata como opinión informada, nunca como regla.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from .modelo import Mazo
from .scryfall import AGENTE, CACHE

RUTA = Path(__file__).with_name("etiquetas.json")
CACHE_ETIQUETAS = CACHE / "etiquetas"

# Scryfall pide espaciar las peticiones. Una por etiqueta y mazo, y se cachea.
PAUSA = 0.16
# El filtro va en la URL: con mazos muy variados hay que trocearlo.
POR_LOTE = 60

_CACHE: dict[str, int] | None = None


def cargar() -> dict[str, int]:
    """Las etiquetas conocidas y cuántas cartas tiene cada una."""
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(RUTA.read_text(encoding="utf-8"))["etiquetas"]
    return _CACHE


def por_concepto() -> dict[str, list[str]]:
    """Qué etiqueta comunitaria cabría esperar en una pareja de cada concepto.

    Solo están mapeados los conceptos con correspondencia clara. Un concepto sin
    mapear no es sospechoso: es que no hay etiqueta equivalente y por tanto no se
    puede contrastar por esta vía.
    """
    return json.loads(RUTA.read_text(encoding="utf-8")).get("conceptos", {})


def _pedir(consulta: str) -> list[str]:
    """Cartas que casan la consulta.

    Un 404 de Scryfall significa "ninguna carta casa", que es una respuesta
    legítima y devuelve lista vacía. Cualquier otro error se propaga: confundir
    "no lo sé" con "no hay" es justo lo que hace que un informe mienta.
    """
    url = ("https://api.scryfall.com/cards/search?unique=cards&q="
           + urllib.parse.quote(consulta))
    pet = urllib.request.Request(url, headers={"User-Agent": AGENTE,
                                               "Accept": "application/json"})
    for intento in range(4):
        try:
            with urllib.request.urlopen(pet, timeout=25) as r:
                datos = json.loads(r.read().decode("utf-8"))
            return [c["name"].split("//")[0].strip() for c in datos.get("data", [])]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            if e.code == 429 and intento < 3:
                time.sleep(1.5 * (intento + 1))   # Scryfall pide bajar el ritmo
                continue
            raise
    return []


def de_mazo(
    mazo: Mazo,
    etiquetas: list[str] | None = None,
    pedir: Callable[[str], list[str]] | None = None,
) -> dict[str, Any]:
    """Qué etiquetas funcionales lleva cada carta del mazo, según Scryfall.

    Nunca lanza: sin red devuelve el mazo sin etiquetas y lo dice en el aviso,
    igual que hacen los rulings y los combos.
    """
    pedir = pedir or _pedir
    nombres = [c.nombre for c in mazo.principal if not c.es_basica]

    # Una consulta por etiqueta es lento y las etiquetas cambian poco: se cachea
    # por mazo. La versión del vocabulario entra en la clave para que al refrescar
    # la lista no se sirva un informe viejo.
    firma = hashlib.sha256(
        ("|".join(sorted(nombres)) + "#" + ",".join(sorted(etiquetas or cargar()))
         ).encode("utf-8")).hexdigest()[:32]
    en_disco = CACHE_ETIQUETAS / f"{firma}.json"
    if pedir is _pedir and en_disco.exists():
        try:
            return json.loads(en_disco.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    if not nombres:
        return {"fuente": "Scryfall (etiquetas funcionales de la comunidad)",
                "por_carta": {}, "por_etiqueta": {}, "aviso": "el mazo no tiene cartas que mirar"}

    por_etiqueta: dict[str, list[str]] = {}
    sin_comprobar: list[str] = []
    for tag in (etiquetas or list(cargar())):
        aciertos: list[str] = []
        fallo = False
        for i in range(0, len(nombres), POR_LOTE):
            trozo = nombres[i:i + POR_LOTE]
            filtro = "(" + " or ".join(f'!"{n}"' for n in trozo) + ")"
            try:
                aciertos += pedir(f"otag:{tag} {filtro}")
            except (urllib.error.URLError, TimeoutError, OSError,
                    json.JSONDecodeError, ValueError):
                fallo = True
            time.sleep(PAUSA)
        # Una etiqueta que no se pudo consultar NO es una etiqueta ausente. Darla
        # por vacía convertiría un fallo de red en un dato, que es peor que no
        # tener el dato.
        if fallo:
            sin_comprobar.append(tag)
        elif aciertos:
            por_etiqueta[tag] = sorted(set(aciertos))

    por_carta: dict[str, list[str]] = {}
    for tag, cartas in por_etiqueta.items():
        for n in cartas:
            por_carta.setdefault(n, []).append(tag)
    for n in por_carta:
        por_carta[n].sort()

    aviso = ("Etiquetado comunitario, no oráculo verificado: puede faltar o sobrar. "
             "Vale como segunda opinión independiente, nunca como regla.")
    if sin_comprobar:
        aviso += (f" ATENCIÓN: {len(sin_comprobar)} etiquetas no se pudieron consultar "
                  f"({', '.join(sin_comprobar[:6])}…): no están comprobadas, no ausentes.")

    salida = {
        "fuente": "Scryfall (etiquetas funcionales de la comunidad, operador otag:)",
        "cartas_etiquetadas": len(por_carta),
        "cartas_sin_etiqueta": sorted(set(nombres) - set(por_carta)),
        "por_carta": dict(sorted(por_carta.items())),
        "por_etiqueta": dict(sorted(por_etiqueta.items())),
        "etiquetas_sin_comprobar": sin_comprobar,
        "atencion": aviso,
    }

    # Un informe incompleto no se cachea: se reintentaría nunca.
    if pedir is _pedir and not sin_comprobar:
        try:
            CACHE_ETIQUETAS.mkdir(parents=True, exist_ok=True)
            en_disco.write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    return salida
