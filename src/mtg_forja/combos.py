"""Combos conocidos, consultados a Commander Spellbook.

Qué aporta que no aporte el resto del proyecto: `reglas.json` solo encuentra lo
que alguien escribió aquí, y `lexico.json` deduce flujos de recursos pero no
razona sobre reglas del juego. Commander Spellbook es una base curada por su
comunidad con los **pasos redactados** de cada combo — conocimiento que ningún
motor de patrones deduce.

Con una salvedad que gobierna todo el módulo: **esto es dato de terceros, no
oráculo verificado.** Lo que salga de aquí es una pista que hay que contrastar
contra el texto real de la carta antes de afirmarlo en un documento. El resto
del proyecto se sostiene sobre Scryfall; esto no.

Uso responsable: una sola petición por análisis (el endpoint acepta el mazo
entero), User-Agent identificativo, caché en disco y degradación limpia — si la
API no responde, el análisis continúa sin combos en vez de romperse.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .modelo import Mazo
from .scryfall import CACHE

API = "https://backend.commanderspellbook.com/find-my-combos/"
AGENTE = "mtg-forja/0.1 (+https://github.com/grutino/mtg-forja)"
ESPERA = 25
CACHE_COMBOS = CACHE / "combos"
FUENTE = "Commander Spellbook (https://commanderspellbook.com)"


def _clave(nombres: list[tuple[int, str]]) -> str:
    crudo = json.dumps(sorted(nombres), ensure_ascii=False)
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()[:32]


def _cache_leer(clave: str) -> dict[str, Any] | None:
    f = CACHE_COMBOS / f"{clave}.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _cache_escribir(clave: str, dato: dict[str, Any]) -> None:
    try:
        CACHE_COMBOS.mkdir(parents=True, exist_ok=True)
        (CACHE_COMBOS / f"{clave}.json").write_text(
            json.dumps(dato, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _pedir(cuerpo: dict[str, Any]) -> dict[str, Any]:
    pet = urllib.request.Request(
        API,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": AGENTE},
    )
    with urllib.request.urlopen(pet, timeout=ESPERA) as r:
        return json.loads(r.read().decode("utf-8"))


def _resumir(v: dict[str, Any]) -> dict[str, Any]:
    """Deja de cada combo solo lo que sirve para razonar y explicarlo."""
    return {
        "cartas": [u["card"]["name"] for u in v.get("uses", []) if u.get("card")],
        "ademas_necesita": [r["template"]["name"] for r in v.get("requires", [])
                            if r.get("template")],
        "produce": [p["feature"]["name"] for p in v.get("produces", []) if p.get("feature")],
        "pasos": (v.get("description") or "").strip()[:1200],
        "requisitos": (v.get("notablePrerequisites") or "").strip()[:400] or None,
        "legal_en": sorted(k for k, ok in (v.get("legalities") or {}).items() if ok),
        "url": f"https://commanderspellbook.com/combo/{v['id']}/" if v.get("id") else None,
    }


def buscar(mazo: Mazo, limite: int = 12) -> dict[str, Any]:
    """Combos conocidos presentes en el mazo, y los que se quedan a una carta.

    Nunca lanza: si la API falla, devuelve el motivo y listas vacías para que el
    análisis siga adelante.
    """
    cartas = [(c.copias, c.nombre) for c in mazo.principal if c.resuelta]
    if not cartas:
        return {"fuente": FUENTE, "completos": [], "casi_completos": [],
                "aviso": "El mazo no tiene cartas resueltas que consultar."}

    fixture = os.environ.get("MTG_FORJA_COMBOS_FIXTURE")
    clave = _clave(cartas)
    if fixture:
        crudo: dict[str, Any] | None = json.loads(Path(fixture).read_text(encoding="utf-8"))
    else:
        crudo = _cache_leer(clave)
        if crudo is None:
            try:
                crudo = _pedir({"commanders": [],
                                "main": [{"card": n, "quantity": q} for q, n in cartas]})
                _cache_escribir(clave, crudo)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
                return {"fuente": FUENTE, "completos": [], "casi_completos": [],
                        "aviso": f"No se ha podido consultar Commander Spellbook ({e}). "
                                 "El análisis sigue sin combos conocidos."}

    r = (crudo or {}).get("results") or {}
    return {
        "fuente": FUENTE,
        "atencion": ("Datos curados por la comunidad de Commander Spellbook, NO texto de "
                     "oráculo verificado. Contrasta cada combo contra la carta real antes "
                     "de afirmarlo en un documento."),
        "completos": [_resumir(v) for v in (r.get("included") or [])[:limite]],
        "casi_completos": [_resumir(v) for v in (r.get("almostIncluded") or [])[:limite]],
        "cuenta": {
            "completos": len(r.get("included") or []),
            "casi_completos": len(r.get("almostIncluded") or []),
            "casi_anadiendo_colores": len(r.get("almostIncludedByAddingColors") or []),
        },
    }
