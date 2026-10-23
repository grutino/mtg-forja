"""El análisis lo hace un experto; la forja solo aporta hechos y comprueba citas.

Reparto de trabajo:

* **La forja** resuelve el mazo contra Scryfall y entrega los hechos que no se
  discuten: texto de oráculo, tipos, costes, palabras clave y rulings oficiales
  de Wizards. No deduce sinergias, no clasifica cartas y no interpreta textos.
* **El experto** (Claude u otro modelo que se indique, o una persona) lee esos
  hechos, consulta los recursos de la comunidad —listas reales, artículos,
  estadísticas— y escribe el análisis.
* **La forja** comprueba ese análisis antes de dibujar nada:

  - cada carta nombrada existe en el mazo;
  - cada pieza de cada sinergia viene respaldada por una cita **literal** de su
    oráculo o de uno de sus rulings oficiales;
  - cada afirmación que no sale de la carta (metajuego, porcentajes, listas de
    otros jugadores) cita una fuente con URL;
  - el análisis lleva la firma de la revisión experta.

Si algo no cuadra, no se genera ningún documento: se devuelven los errores.
"""
from __future__ import annotations

import datetime as _dt
import re
import unicodedata
from typing import Any, Callable

from . import __version__
from .modelo import Mazo

TIPOS = ("sinergia", "conflicto", "aviso")
ROLES = ("motor", "amenaza", "respuesta", "tierra")


# ---------------------------------------------------------------- hechos

def _tipo_base(tipo: str) -> str:
    """El tipo principal tal cual lo imprime la carta. No es una interpretación."""
    return tipo.split("—")[0].strip()


def datos_para_experto(mazo: Mazo, rulings: Callable[[Any], list[str]] | None = None
                       ) -> dict[str, Any]:
    """Los hechos del mazo, sin una sola deducción, para que el experto trabaje.

    `rulings` es la función que trae los rulings oficiales de una carta; se
    inyecta para poder probar sin red.
    """
    cartas = []
    for c in mazo.cartas:
        cartas.append({
            "nombre": c.nombre,
            "copias": c.copias,
            "banquillo": c.banquillo,
            "coste": c.coste,
            "valor_de_mana": c.mv,
            "tipo": c.tipo,
            "oraculo": c.oraculo,
            "palabras_clave": c.keywords,
            "produce_mana": c.produce_mana,
            "fuerza": c.fuerza,
            "lealtad": c.lealtad,
            "scryfall": c.scryfall_uri,
            "rulings": rulings(c) if (rulings and c.resuelta) else [],
            "resuelta": c.resuelta,
        })
    return {
        "nombre": mazo.nombre,
        "total": mazo.total,
        "tierras": mazo.tierras,
        "curva": mazo.curva(),
        "cartas": cartas,
        "no_resueltas": mazo.no_resueltas,
        "instrucciones": (
            "Estos son solo hechos. Escribe el análisis como experto: lee cada "
            "oráculo y sus rulings, consulta listas y artículos reales, y respalda "
            "cada sinergia con citas literales y cada dato externo con una fuente."
        ),
    }


# ---------------------------------------------------------------- citas

_EQUIV = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "−": "-", "–": "-", "—": "-", " ": " ",
}


def normalizar(texto: str) -> str:
    """Para comparar citas: misma forma Unicode, comillas y guiones rectos,
    espacios colapsados. No cambia palabras: una cita sigue teniendo que ser literal."""
    t = unicodedata.normalize("NFC", texto or "")
    for a, b in _EQUIV.items():
        t = t.replace(a, b)
    return " ".join(t.split()).lower()


def _cita_valida(texto: str, oraculo: str, rulings: list[str]) -> str | None:
    """Devuelve el origen de la cita ('oráculo' o 'ruling') o None si no es literal."""
    n = normalizar(texto)
    if len(n) < 8:
        return None
    if n in normalizar(oraculo):
        return "oráculo"
    if any(n in normalizar(r) for r in rulings):
        return "ruling"
    return None


# ---------------------------------------------------------------- validación

def validar(mazo: Mazo, analisis: dict[str, Any],
            rulings: Callable[[Any], list[str]] | None = None) -> list[str]:
    """Lista de errores. Vacía significa que el análisis se puede forjar."""
    errores: list[str] = []
    por_nombre = {c.nombre.lower(): c for c in mazo.cartas}
    cache_rulings: dict[str, list[str]] = {}

    def carta(nombre: str):
        return por_nombre.get(str(nombre).strip().lower())

    def rul(c) -> list[str]:
        if c.nombre not in cache_rulings:
            cache_rulings[c.nombre] = rulings(c) if rulings else []
        return cache_rulings[c.nombre]

    # --- la firma de la revisión experta
    rev = analisis.get("revision_experta")
    if not isinstance(rev, dict):
        errores.append("Falta 'revision_experta': ningún resultado sale sin revisión experta.")
    else:
        if not str(rev.get("revisor", "")).strip():
            errores.append("'revision_experta.revisor' vacío: hay que decir quién revisa "
                           "(p. ej. «Claude Opus 5.5»).")
        if not str(rev.get("fecha", "")).strip():
            errores.append("'revision_experta.fecha' vacía.")
        if not str(rev.get("veredicto", "")).strip():
            errores.append("'revision_experta.veredicto' vacío: el experto tiene que "
                           "valorar el mazo, no solo describirlo.")

    # --- fuentes externas
    fuentes = analisis.get("fuentes", [])
    ids_fuente = set()
    for i, f in enumerate(fuentes):
        if not isinstance(f, dict) or not f.get("id") or not str(f.get("url", "")).startswith("http"):
            errores.append(f"fuentes[{i}]: cada fuente necesita 'id' y una 'url' http(s).")
            continue
        ids_fuente.add(f["id"])

    def revisa_fuentes(donde: str, refs: Any) -> None:
        for r in refs or []:
            if r not in ids_fuente:
                errores.append(f"{donde}: cita la fuente '{r}', que no está en 'fuentes'.")

    revisa_fuentes("revision_experta", (rev or {}).get("fuentes") if isinstance(rev, dict) else [])

    # --- cartas
    fichas = analisis.get("cartas", {})
    if not isinstance(fichas, dict):
        errores.append("'cartas' debe ser un objeto {nombre: {rol, estrategia}}.")
        fichas = {}
    for nombre, ficha in fichas.items():
        c = carta(nombre)
        if c is None:
            errores.append(f"cartas: «{nombre}» no está en el mazo.")
            continue
        rol = (ficha or {}).get("rol")
        if rol is not None and rol not in ROLES:
            errores.append(f"cartas «{nombre}»: rol '{rol}' no es uno de {', '.join(ROLES)}.")
        revisa_fuentes(f"cartas «{nombre}»", (ficha or {}).get("fuentes"))
    for c in mazo.principal:
        if c.es_tierra or not c.resuelta:
            continue
        if not (fichas.get(c.nombre) or {}).get("rol"):
            errores.append(f"cartas: falta el rol de «{c.nombre}» (lo decide el experto).")

    # --- sinergias, conflictos y avisos
    for i, s in enumerate(analisis.get("sinergias", [])):
        donde = f"sinergias[{i}] «{s.get('nombre', '')}»"
        if s.get("tipo") not in TIPOS:
            errores.append(f"{donde}: 'tipo' debe ser {', '.join(TIPOS)}.")
        try:
            if not 1 <= int(s.get("fuerza", 0)) <= 3:
                raise ValueError
        except (TypeError, ValueError):
            errores.append(f"{donde}: 'fuerza' debe ser 1, 2 o 3.")
        for campo in ("nombre", "resumen"):
            if not str(s.get(campo, "")).strip():
                errores.append(f"{donde}: falta '{campo}'.")
        piezas = s.get("piezas", [])
        if not piezas:
            errores.append(f"{donde}: no tiene piezas.")
        citas = s.get("citas", [])
        citadas = set()
        for j, ct in enumerate(citas):
            c = carta(ct.get("carta", ""))
            if c is None:
                errores.append(f"{donde}, cita {j + 1}: «{ct.get('carta')}» no está en el mazo.")
                continue
            origen = _cita_valida(ct.get("texto", ""), c.oraculo, rul(c))
            if origen is None:
                errores.append(
                    f"{donde}, cita {j + 1}: «{ct.get('texto', '')}» no aparece literal en el "
                    f"oráculo ni en los rulings de {c.nombre}.")
            else:
                ct["origen"] = origen
                citadas.add(c.nombre)
        for p in piezas:
            c = carta(p)
            if c is None:
                errores.append(f"{donde}: la pieza «{p}» no está en el mazo.")
            elif c.nombre not in citadas:
                errores.append(f"{donde}: la pieza «{c.nombre}» no tiene ninguna cita de su "
                               "oráculo o de sus rulings que la respalde.")
        revisa_fuentes(donde, s.get("fuentes"))

    # --- secuencia de juego
    for i, o in enumerate(analisis.get("orden", [])):
        if o.get("carta") and carta(o["carta"]) is None:
            errores.append(f"orden[{i}]: «{o['carta']}» no está en el mazo.")

    return errores


# ---------------------------------------------------------------- documento

def documento(mazo: Mazo, analisis: dict[str, Any]) -> dict[str, Any]:
    """Une hechos y análisis en el documento que consumen los renderizadores.

    Llamar solo con un análisis que haya pasado `validar`.
    """
    fichas = analisis.get("cartas", {})
    principal = sorted(mazo.principal, key=lambda c: (c.es_tierra, c.mv, c.nombre))
    cartas = []
    for c in principal:
        f = fichas.get(c.nombre) or {}
        cartas.append({
            "nombre": c.nombre,
            "copias": c.copias,
            "coste": c.coste,
            "mv": c.mv,
            "tipo": c.tipo,
            "rol": "tierra" if c.es_tierra and not f.get("rol") else f.get("rol", ""),
            "produce_mana": c.produce_mana,
            "estrategia": f.get("estrategia", ""),
        })

    sinergias = []
    for s in analisis.get("sinergias", []):
        s = dict(s)
        nombres = {c.nombre.lower(): c.nombre for c in mazo.cartas}
        s["piezas"] = [nombres.get(p.strip().lower(), p) for p in s.get("piezas", [])]
        for ct in s.get("citas", []):
            ct["carta"] = nombres.get(ct["carta"].strip().lower(), ct["carta"])
        # El mapa enseña, por carta, la frase de la carta que sostiene la jugada.
        s["evidencia"] = {}
        for ct in s.get("citas", []):
            s["evidencia"].setdefault(ct["carta"], ct["texto"])
        s.setdefault("bloque", "Jugadas")
        s.setdefault("turno", "")
        s.setdefault("pasos", [])
        sinergias.append(s)

    rev = dict(analisis.get("revision_experta", {}))
    return {
        "titulo": analisis.get("titulo") or mazo.nombre,
        "subtitulo": analisis.get("subtitulo") or f"{mazo.total} cartas · {mazo.tierras} tierras",
        "curva": mazo.curva(),
        "cartas": cartas,
        "sinergias": sinergias,
        "orden": analisis.get("orden", []),
        "reglas_oro": analisis.get("reglas_oro", []),
        "planes": analisis.get("planes", []),
        "revision_experta": rev,
        "fuentes": analisis.get("fuentes", []),
        "no_resueltas": mazo.no_resueltas,
        "forjado": {
            "version": __version__,
            "fecha": _dt.date.today().isoformat(),
            "citas_verificadas": sum(len(s.get("citas", [])) for s in sinergias),
        },
    }
