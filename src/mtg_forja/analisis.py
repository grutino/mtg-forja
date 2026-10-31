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
            "cada sinergia con citas literales y cada dato externo con una fuente. "
            "Si ves cambios de cartas muy claros o muy razonables, añádelos en "
            "'mejoras' (máximo 5, con 'formato' y, si se juega en Arena, "
            "'plataforma': 'arena'); si no los hay, no te inventes ninguno."
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
            rulings: Callable[[Any], list[str]] | None = None,
            consultar: Callable[[list[str]], dict[str, dict[str, Any]]] | None = None
            ) -> list[str]:
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

    # --- mulligan
    principal = {c.nombre.lower() for c in mazo.principal}
    errores += _validar_mulligan(analisis.get("mulligan"),
                                 lambda n: n.strip().lower() in principal, ids_fuente)

    # --- base de maná
    errores += _validar_tierras(mazo, analisis.get("tierras"), carta, rul, ids_fuente)

    # --- mejoras propuestas
    errores += _validar_mejoras(mazo, analisis, ids_fuente, carta, rul, consultar)
    return errores


# ---------------------------------------------------------------- base de maná

def _validar_tierras(mazo: Mazo, t: Any, carta: Callable[[str], Any],
                     rul: Callable[[Any], list[str]], ids_fuente: set) -> list[str]:
    """Cómo se juega cada tierra lo explica el experto. Si da el apartado, tiene que
    cubrir todas las tierras del mazo principal, y sus citas tienen que ser literales."""
    if t is None:
        return []
    if not isinstance(t, dict) or not isinstance(t.get("detalle"), dict):
        return ["'tierras' debe ser {resumen, secuencia, detalle: {nombre: {que_hace, como_jugarla}}}."]
    errores: list[str] = []
    tierras = {c.nombre.lower(): c.nombre for c in mazo.principal if c.es_tierra}
    vistas = set()
    for nombre, f in t["detalle"].items():
        clave = str(nombre).strip().lower()
        if clave not in tierras:
            errores.append(f"tierras: «{nombre}» no es una tierra del mazo principal.")
            continue
        vistas.add(clave)
        f = f or {}
        for campo in ("que_hace", "como_jugarla"):
            if not str(f.get(campo, "")).strip():
                errores.append(f"tierras «{nombre}»: falta '{campo}'.")
        for j, ct in enumerate(f.get("citas", []) or []):
            c = carta(ct.get("carta", ""))
            if c is None or _cita_valida(ct.get("texto", ""), c.oraculo, rul(c)) is None:
                errores.append(f"tierras «{nombre}», cita {j + 1}: «{ct.get('texto', '')}» no aparece "
                               f"literal en el oráculo ni en los rulings de «{ct.get('carta')}».")
            else:
                ct["origen"] = _cita_valida(ct.get("texto", ""), c.oraculo, rul(c))
                ct["carta"] = c.nombre
    for clave, nombre in tierras.items():
        if clave not in vistas:
            errores.append(f"tierras: falta explicar «{nombre}».")
    for r in t.get("fuentes", []) or []:
        if r not in ids_fuente:
            errores.append(f"tierras: cita la fuente '{r}', que no está en 'fuentes'.")
    return errores


def _documento_tierras(mazo: Mazo, t: dict[str, Any]) -> dict[str, Any]:
    por_clave = {str(k).strip().lower(): v for k, v in t.get("detalle", {}).items()}
    detalle = []
    for c in sorted((c for c in mazo.principal if c.es_tierra), key=lambda c: -c.copias):
        f = por_clave.get(c.nombre.lower(), {})
        detalle.append({"nombre": c.nombre, "copias": c.copias, "tipo": c.tipo,
                        "basica": c.es_basica, "que_hace": f.get("que_hace", ""),
                        "como_jugarla": f.get("como_jugarla", ""), "citas": f.get("citas", [])})
    return {"resumen": t.get("resumen", ""), "secuencia": t.get("secuencia", []),
            "fuentes": t.get("fuentes", []), "detalle": detalle}


# ---------------------------------------------------------------- mulligan

MANO = 7


def _validar_mulligan(m: Any, en_principal: Callable[[str], bool], ids_fuente: set) -> list[str]:
    """El criterio de mulligan es del experto; aquí solo se comprueba que esté completo
    y que las cartas que nombra estén en el mazo principal."""
    if m is None:
        return []
    if not isinstance(m, dict):
        return ["'mulligan' debe ser un objeto {resumen, quedarse, mulligan, ...}."]
    errores: list[str] = []
    for campo in ("quedarse", "mulligan"):
        lista = m.get(campo)
        if not isinstance(lista, list) or not lista:
            errores.append(f"mulligan: '{campo}' tiene que ser una lista con al menos un criterio.")
            continue
        for i, it in enumerate(lista):
            texto = it if isinstance(it, str) else (it or {}).get("texto", "")
            if not str(texto).strip():
                errores.append(f"mulligan.{campo}[{i}]: falta el texto.")
            if isinstance(it, dict):
                for n in it.get("cartas", []) or []:
                    if not en_principal(str(n)):
                        errores.append(f"mulligan.{campo}[{i}]: «{n}» no está en el mazo principal.")
    t = m.get("tierras")
    if t is not None:
        ok = (isinstance(t, list) and len(t) == 2 and all(isinstance(x, int) for x in t)
              and 0 <= t[0] <= t[1] <= MANO)
        if not ok:
            errores.append("mulligan: 'tierras' debe ser [mínimo, máximo] entre 0 y 7.")
    for i, k in enumerate(m.get("claves", []) or []):
        if not isinstance(k, dict) or not str(k.get("nombre", "")).strip() or not k.get("cartas"):
            errores.append(f"mulligan.claves[{i}]: necesita 'nombre' y 'cartas'.")
            continue
        for n in k["cartas"]:
            if not en_principal(str(n)):
                errores.append(f"mulligan.claves[{i}]: «{n}» no está en el mazo principal.")
    for r in m.get("fuentes", []) or []:
        if r not in ids_fuente:
            errores.append(f"mulligan: cita la fuente '{r}', que no está en 'fuentes'.")
    return errores


def _hiper(exitos: int, total: int, robadas: int, k: int) -> float:
    """Probabilidad de robar exactamente k éxitos (distribución hipergeométrica)."""
    from math import comb
    if k < 0 or k > robadas or k > exitos or robadas - k > total - exitos:
        return 0.0
    return comb(exitos, k) * comb(total - exitos, robadas - k) / comb(total, robadas)


def estadisticas_mano(mazo: Mazo, m: dict[str, Any]) -> dict[str, Any]:
    """Números exactos de la mano inicial. Es aritmética sobre la lista, no criterio."""
    total, tierras = mazo.total, mazo.tierras
    dist = [_hiper(tierras, total, MANO, k) for k in range(MANO + 1)]
    fuera: dict[str, Any] = {"cartas": total, "tierras": tierras,
                             "dist7": [round(p, 4) for p in dist]}
    rango = m.get("tierras")
    if rango:
        lo, hi = rango
        fuera["en_rango_7"] = round(sum(dist[lo:hi + 1]), 4)
        # Mulligan de Londres: robas 7 y pones una al fondo. Con L tierras puedes
        # quedarte con L (si tienes un hechizo que bajar) o con L-1 (si bajas una tierra).
        p6 = 0.0
        for L, p in enumerate(dist):
            posibles = ({L} if L < MANO else set()) | ({L - 1} if L > 0 else set())
            if any(lo <= x <= hi for x in posibles):
                p6 += p
        fuera["en_rango_6"] = round(p6, 4)
    por_nombre = {c.nombre.lower(): c for c in mazo.principal}
    claves = []
    for k in m.get("claves", []) or []:
        nombres = [por_nombre[n.strip().lower()].nombre for n in k["cartas"]
                   if n.strip().lower() in por_nombre]
        copias = sum(por_nombre[n.lower()].copias for n in nombres)
        claves.append({"nombre": k["nombre"], "cartas": nombres, "copias": copias,
                       "p7": round(1 - _hiper(copias, total, MANO, 0), 4)})
    fuera["claves"] = claves
    return fuera


# ---------------------------------------------------------------- mejoras

MAX_MEJORAS = 5
NIVELES = ("clara", "razonable")


def _clave_nombre(nombre: str) -> str:
    from .scryfall import _clave
    return _clave(nombre)


def _validar_mejoras(mazo: Mazo, analisis: dict[str, Any], ids_fuente: set,
                     carta: Callable[[str], Any], rul: Callable[[Any], list[str]],
                     consultar: Callable[[list[str]], dict[str, dict[str, Any]]] | None
                     ) -> list[str]:
    """Las mejoras son cambios de cartas que el experto propone, y solo los muy claros.

    Lo que se comprueba aquí son hechos, no criterio: que lo que sale está en el
    mazo, que lo que entra existe en Scryfall y es legal en el formato (y está en
    Arena si se juega allí), que el mazo sigue teniendo el mismo número de cartas,
    que ninguna pasa de 4 copias salvo las tierras básicas, y que cada cambio va
    respaldado por una cita literal o por una fuente con URL.
    """
    mejoras = analisis.get("mejoras") or []
    if not mejoras:
        return []
    errores: list[str] = []
    if not isinstance(mejoras, list):
        return ["'mejoras' debe ser una lista."]
    if len(mejoras) > MAX_MEJORAS:
        errores.append(f"mejoras: hay {len(mejoras)}; como mucho {MAX_MEJORAS}, y solo las "
                       "muy claras o muy razonables.")
    formato = str(analisis.get("formato", "")).strip().lower()
    plataforma = str(analisis.get("plataforma", "")).strip().lower()
    if not formato:
        errores.append("mejoras: falta 'formato' (p. ej. «standard») para comprobar que lo "
                       "que entra es legal.")

    entran = [str(x.get("carta", "")) for m in mejoras if isinstance(m, dict)
              for x in (m.get("entra") or []) if isinstance(x, dict)]
    fichas = consultar(entran) if (consultar and entran) else {}
    copias = {c.nombre: c.copias for c in mazo.principal}
    basicas = {c.nombre for c in mazo.principal if "Basic Land" in c.tipo}

    for i, m in enumerate(mejoras):
        donde = f"mejoras[{i}] «{(m or {}).get('titulo', '')}»"
        if not isinstance(m, dict):
            errores.append(f"mejoras[{i}]: debe ser un objeto.")
            continue
        for campo in ("titulo", "motivo"):
            if not str(m.get(campo, "")).strip():
                errores.append(f"{donde}: falta '{campo}'.")
        if m.get("nivel") not in NIVELES:
            errores.append(f"{donde}: 'nivel' debe ser {' o '.join(NIVELES)}.")
        sale, entra = m.get("sale") or [], m.get("entra") or []
        if not sale or not entra:
            errores.append(f"{donde}: necesita 'sale' y 'entra' (cambios carta por carta).")

        def n_copias(x: Any) -> int:
            try:
                return int(x.get("copias", 0))
            except (TypeError, ValueError, AttributeError):
                return 0

        total_sale = total_entra = 0
        for x in sale:
            c = carta((x or {}).get("carta", "")) if isinstance(x, dict) else None
            n = n_copias(x)
            total_sale += n
            if c is None or c.nombre not in copias:
                errores.append(f"{donde}: sale «{(x or {}).get('carta')}», que no está en el mazo.")
            elif n < 1 or n > copias.get(c.nombre, 0):
                errores.append(f"{donde}: sale {n} × «{c.nombre}», y el mazo lleva "
                               f"{copias.get(c.nombre, 0)}.")
            else:
                x["carta"] = c.nombre
        for x in entra:
            if not isinstance(x, dict):
                errores.append(f"{donde}: cada carta de 'entra' es {{carta, copias}}.")
                continue
            n = n_copias(x)
            total_entra += n
            nombre = str(x.get("carta", ""))
            if n < 1:
                errores.append(f"{donde}: entra «{nombre}» sin copias.")
            enmazo = carta(nombre)
            if enmazo is not None and not enmazo.banquillo:
                x["carta"] = enmazo.nombre
                x.update(coste=enmazo.coste, tipo=enmazo.tipo)
                tras = copias.get(enmazo.nombre, 0) + n
                if tras > 4 and enmazo.nombre not in basicas:
                    errores.append(f"{donde}: «{enmazo.nombre}» quedaría con {tras} copias.")
                continue
            f = fichas.get(_clave_nombre(nombre))
            if f is None:
                errores.append(f"{donde}: «{nombre}» no se encuentra en Scryfall"
                               + ("." if consultar else " (no se ha podido consultar)."))
                continue
            x.update(carta=f["nombre"], coste=f["coste"], tipo=f["tipo"],
                     scryfall=f["scryfall"], oraculo=f["oraculo"])
            if n > 4 and "Basic Land" not in f["tipo"]:
                errores.append(f"{donde}: «{f['nombre']}» con {n} copias; el máximo es 4.")
            if formato and f["legalidades"].get(formato) != "legal":
                errores.append(f"{donde}: «{f['nombre']}» no es legal en {formato} "
                               f"({f['legalidades'].get(formato, 'sin dato')}).")
            if plataforma == "arena" and "arena" not in f["juegos"]:
                errores.append(f"{donde}: «{f['nombre']}» no está en MTG Arena.")
        if total_sale != total_entra:
            errores.append(f"{donde}: salen {total_sale} cartas y entran {total_entra}; "
                           "el mazo tiene que quedar con las mismas.")

        # respaldo: citas literales (de cartas del mazo o de las que entran) o fuentes
        oraculos_nuevos = {x.get("carta"): x.get("oraculo", "") for x in entra
                           if isinstance(x, dict) and x.get("oraculo")}
        for j, ct in enumerate(m.get("citas") or []):
            c = carta(ct.get("carta", ""))
            if c is not None:
                origen = _cita_valida(ct.get("texto", ""), c.oraculo, rul(c))
                ct["carta"] = c.nombre
            else:
                nuevo = next((k for k in oraculos_nuevos
                              if _clave_nombre(k) == _clave_nombre(ct.get("carta", ""))), None)
                origen = _cita_valida(ct.get("texto", ""), oraculos_nuevos[nuevo], []) if nuevo else None
                if nuevo:
                    ct["carta"] = nuevo
            if origen is None:
                errores.append(f"{donde}, cita {j + 1}: «{ct.get('texto', '')}» no aparece literal "
                               f"en el oráculo ni en los rulings de «{ct.get('carta')}».")
            else:
                ct["origen"] = origen
        for r in m.get("fuentes") or []:
            if r not in ids_fuente:
                errores.append(f"{donde}: cita la fuente '{r}', que no está en 'fuentes'.")
        if not (m.get("citas") or m.get("fuentes")):
            errores.append(f"{donde}: una mejora necesita al menos una cita literal o una "
                           "fuente que la respalde.")
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
        "mejoras": [
            {**m, "entra": [{k: v for k, v in x.items() if k != "oraculo"}
                            for x in m.get("entra", [])]}
            for m in analisis.get("mejoras", [])
        ],
        "formato": analisis.get("formato", ""),
        "tierras_guia": (_documento_tierras(mazo, analisis["tierras"])
                         if isinstance(analisis.get("tierras"), dict) else None),
        "mulligan": ({**analisis["mulligan"],
                      "estadisticas": estadisticas_mano(mazo, analisis["mulligan"])}
                     if isinstance(analisis.get("mulligan"), dict) else None),
        "revision_experta": rev,
        "fuentes": analisis.get("fuentes", []),
        "no_resueltas": mazo.no_resueltas,
        "forjado": {
            "version": __version__,
            "fecha": _dt.date.today().isoformat(),
            "citas_verificadas": sum(len(s.get("citas", [])) for s in sinergias),
        },
    }
