"""Resolución de cartas contra la API pública de Scryfall.

Regla de oro del proyecto: el texto de oráculo nunca se escribe de memoria.
Todo lo que afirme el análisis tiene que venir de aquí.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .modelo import Carta, Mazo, parsear_lista

API = "https://api.scryfall.com/cards/collection"
AGENTE = "mtg-forja/0.1 (https://github.com/)"
LOTE = 75
CACHE = Path(os.environ.get("MTG_FORJA_CACHE", Path.home() / ".cache" / "mtg-forja"))


def _cache_leer(nombre: str) -> dict[str, Any] | None:
    f = CACHE / f"{_slug(nombre)}.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _cache_escribir(nombre: str, dato: dict[str, Any]) -> None:
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        (CACHE / f"{_slug(nombre)}.json").write_text(
            json.dumps(dato, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def _slug(nombre: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in nombre.lower())[:80]


def _fixture() -> dict[str, dict[str, Any]] | None:
    """Permite trabajar sin red: MTG_FORJA_FIXTURE=ruta/a/cartas.json"""
    ruta = os.environ.get("MTG_FORJA_FIXTURE")
    if not ruta:
        return None
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if isinstance(datos, dict) and "data" in datos:
        datos = datos["data"]
    return {c["name"].split("//")[0].strip().lower(): c for c in datos}


def _pedir(nombres: list[str]) -> list[dict[str, Any]]:
    cuerpo = json.dumps({"identifiers": [{"name": n} for n in nombres]}).encode()
    pet = urllib.request.Request(
        API,
        data=cuerpo,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": AGENTE,
        },
    )
    with urllib.request.urlopen(pet, timeout=30) as r:
        return json.loads(r.read().decode("utf-8")).get("data", [])


def _aplanar(bruto: dict[str, Any]) -> dict[str, Any]:
    """Une las dos caras de una carta modal en un solo texto de oráculo."""
    caras = bruto.get("card_faces") or []
    if caras and not bruto.get("oracle_text"):
        oraculo = "\n//\n".join(f.get("oracle_text", "") for f in caras)
        coste = caras[0].get("mana_cost", "") or bruto.get("mana_cost", "")
        tipo = " // ".join(f.get("type_line", "") for f in caras)
    else:
        oraculo = bruto.get("oracle_text", "")
        coste = bruto.get("mana_cost", "")
        tipo = bruto.get("type_line", "")
    return {"oraculo": oraculo, "coste": coste, "tipo": tipo}


def resolver(lista: str, nombre_mazo: str = "Mazo") -> Mazo:
    """Convierte una lista de texto en un Mazo con oráculo real."""
    entradas = parsear_lista(lista)
    if not entradas:
        return Mazo(nombre=nombre_mazo)

    unicos = list(dict.fromkeys(n for _, n, _ in entradas))
    fix = _fixture()
    encontrados: dict[str, dict[str, Any]] = {}
    pendientes: list[str] = []

    for n in unicos:
        clave = n.lower()
        if fix is not None:
            if clave in fix:
                encontrados[clave] = fix[clave]
            continue
        guardada = _cache_leer(n)
        if guardada:
            encontrados[clave] = guardada
        else:
            pendientes.append(n)

    for i in range(0, len(pendientes), LOTE):
        trozo = pendientes[i : i + LOTE]
        try:
            for bruto in _pedir(trozo):
                clave = bruto["name"].split("//")[0].strip().lower()
                encontrados[clave] = bruto
                _cache_escribir(clave, bruto)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            pass
        if i + LOTE < len(pendientes):
            time.sleep(0.1)  # Scryfall pide 50-100 ms entre peticiones

    mazo = Mazo(nombre=nombre_mazo)
    vistos: dict[tuple[str, bool], Carta] = {}
    for copias, nombre, banq in entradas:
        bruto = encontrados.get(nombre.lower())
        if bruto is None:
            if nombre not in mazo.no_resueltas:
                mazo.no_resueltas.append(nombre)
            carta = Carta(nombre=nombre, copias=copias, banquillo=banq, resuelta=False)
        else:
            plano = _aplanar(bruto)
            carta = Carta(
                nombre=bruto["name"].split("//")[0].strip(),
                copias=copias,
                banquillo=banq,
                coste=plano["coste"],
                mv=float(bruto.get("cmc", 0)),
                tipo=plano["tipo"],
                oraculo=plano["oraculo"],
                colores=bruto.get("colors", []),
                identidad=bruto.get("color_identity", []),
                rarezas=bruto.get("rarity", ""),
                scryfall_uri=bruto.get("scryfall_uri", ""),
            )
        clave = (carta.nombre.lower(), banq)
        if clave in vistos:
            vistos[clave].copias += copias
        else:
            vistos[clave] = carta
            mazo.cartas.append(carta)
    return mazo
