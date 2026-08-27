"""Motor deductivo: encuentra sinergias que nadie ha escrito.

`reglas.json` describe parejas concretas de cartas, así que solo encuentra lo que
alguien se molestó en escribir — no escala a los treinta mil naipes de Magic.
Este módulo trabaja al revés: `lexico.json` describe **recursos**, y de cada carta
se deduce qué produce, qué premia y qué rompe. Una sinergia es entonces
«A produce R y B premia R», y un conflicto «A rompe R y B depende de R».

Añadir un concepto cubre de golpe todas las parejas que lo compartan, así que el
esfuerzo crece con el número de mecánicas del juego, no con el de mazos.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .modelo import Carta, Mazo
from .reglas import Sinergia

RUTA = Path(__file__).with_name("lexico.json")
_CACHE: list[dict[str, Any]] | None = None

# Los topes existen para que un mazo de sesenta cartas no salga hecho una maraña,
# pero no deben esconder el motor del mazo. Una carta que premia cada hechizo que
# lanzas SÍ tiene sinergia con los diez, y verlas todas es justo lo interesante:
# por eso el límite es por carta y no por concepto.
TOPE_SINERGIAS = 40
TOPE_CONFLICTOS = 10
POR_CARTA = 12

# Palabras de combate sin concepto propio. Ojo: estar aquí solo significa que
# ninguna carta suele fijarse en ellas. En cuanto una lo hace —Momo abarata las
# criaturas con volar— dejan de ser decorado y les toca concepto: por eso volar
# ya no está en esta lista.
EVERGREEN = {
    "Vigilance", "Menace", "Deathtouch", "Reach", "Trample", "Haste",
    "First strike", "Double strike", "Defender", "Hexproof", "Shroud", "Ward",
    "Indestructible", "Protection", "Flash", "Enchant", "Equip", "Crew",
}


def cargar(ruta: str | Path | None = None) -> list[dict[str, Any]]:
    global _CACHE
    if ruta is None and _CACHE is not None:
        return _CACHE
    datos = json.loads(Path(ruta or RUTA).read_text(encoding="utf-8"))["conceptos"]
    if ruta is None:
        _CACHE = datos
    return datos


_RECORDATORIO = re.compile(r"\([^)]*\)")


def texto_reglas(oraculo: str, nombre: str = "") -> str:
    """El oráculo listo para analizar: sin recordatorios ni el nombre propio.

    Dos fuentes de falsos positivos, ambas comprobadas sobre cartas reales:

    - El **texto recordatorio** entre paréntesis explica mecánicas que la carta no
      tiene. El de retrospectiva de Snapcaster Mage dice «exile it», y sin quitarlo
      la carta pasaba por odio al cementerio.
    - El **nombre propio**, porque las cartas antiguas se citan a sí mismas. Lightning
      Storm lleva «Storm» en el nombre y colaba como si tuviera la mecánica Tormenta.
    """
    t = _RECORDATORIO.sub(" ", oraculo)
    for forma in sorted({nombre, nombre.split(",")[0].strip()} - {""}, key=len, reverse=True):
        t = re.sub(r"\b" + re.escape(forma) + r"\b", " esta carta ", t)
    return " ".join(t.split())


def _encaja(carta: Carta, bloque: dict[str, Any] | None, oraculo: str | None = None) -> str:
    """Devuelve la evidencia si la carta cumple el bloque, o '' si no."""
    if not bloque or not carta.resuelta:
        return ""
    oraculo = texto_reglas(carta.oraculo, carta.nombre) if oraculo is None else oraculo
    if "tipo" in bloque and not re.search(bloque["tipo"], carta.tipo, re.I):
        return ""
    if "no_tipo" in bloque and re.search(bloque["no_tipo"], carta.tipo, re.I):
        return ""
    if "mv_min" in bloque and carta.mv < bloque["mv_min"]:
        return ""
    if "mv_max" in bloque and carta.mv > bloque["mv_max"]:
        return ""
    if "fuerza_min" in bloque:
        try:
            if float(carta.fuerza) < bloque["fuerza_min"]:
                return ""
        except (TypeError, ValueError):
            # Fuerza variable ("*", "1+*"): no se puede afirmar el umbral.
            return ""
    if "no_oracle" in bloque and re.search(bloque["no_oracle"], oraculo, re.I | re.S):
        return ""
    patrones = bloque.get("oracle") or []
    if not patrones:
        # Bloque puramente estructural (tipo o coste): la evidencia es la línea de tipo.
        estructural = any(k in bloque for k in ("tipo", "mv_min", "mv_max", "fuerza_min"))
        if "fuerza_min" in bloque:
            return f"{carta.tipo} · fuerza {carta.fuerza}"
        return carta.tipo if estructural else ""
    for patron in patrones:
        m = re.search(patron, oraculo, re.I | re.S)
        if m:
            return _frase(oraculo, m)
    return ""


def _frase(texto: str, m: re.Match[str]) -> str:
    """La oración del oráculo que ha disparado el patrón, para poder citarla."""
    ini = texto.rfind(".", 0, m.start()) + 1
    fin = texto.find(".", m.end())
    fin = len(texto) if fin == -1 else fin + 1
    return " ".join(texto[ini:fin].split())[:240]


def _papeles(mazo: Mazo, conceptos: list[dict[str, Any]]) -> dict[str, dict[str, list]]:
    """Para cada concepto, qué cartas lo producen, lo premian y lo rompen."""
    limpio = {c.nombre: texto_reglas(c.oraculo, c.nombre) for c in mazo.principal}
    fuera: dict[str, dict[str, list]] = {}
    for c in conceptos:
        reparto = {"produce": [], "premia": [], "rompe": []}
        for papel in reparto:
            for carta in mazo.principal:
                ev = _encaja(carta, c.get(papel), limpio[carta.nombre])
                if ev:
                    reparto[papel].append((carta, ev))
        fuera[c["id"]] = reparto
    return fuera


def _texto(bloque: dict[str, Any] | None, por_defecto: str) -> str:
    return (bloque or {}).get("texto", por_defecto)


def detectar(mazo: Mazo, conceptos: list[dict[str, Any]] | None = None) -> list[Sinergia]:
    """Deduce sinergias y conflictos cruzando los papeles de cada concepto."""
    conceptos = conceptos if conceptos is not None else cargar()
    reparto = _papeles(mazo, conceptos)
    salida: list[Sinergia] = []

    for c in conceptos:
        r = reparto[c["id"]]
        # Sinergia: alguien produce el recurso y alguien lo aprovecha.
        for (a, eva), (b, evb), tipo, bl_a, bl_b in _parejas(c, r):
            if a.nombre == b.nombre:
                continue
            fuerza = min(4, c.get("fuerza", 2) + (1 if min(a.copias, b.copias) >= 3 else 0))
            salida.append(Sinergia(
                id=f"{c['id']}::{tipo}::{a.nombre}::{b.nombre}",
                nombre=f"{a.nombre} y {b.nombre}",
                bloque=_BLOQUE.get(tipo, "Motor"),
                tipo=tipo,
                fuerza=fuerza,
                turno="",
                piezas=[a.nombre, b.nombre],
                resumen=(f"{{a}} {_texto(c.get(bl_a), 'aporta')} y "
                         f"{{b}} {_texto(c.get(bl_b), 'lo aprovecha')}."),
                pasos=[],
                evidencia={a.nombre: eva, b.nombre: evb},
            ))

    # Los conflictos van primero a propósito: si una pareja sale a la vez como
    # sinergia y como conflicto, gana el aviso. Antes ganaba la sinergia y el
    # conflicto se descartaba por pareja repetida.
    salida.sort(key=lambda s: (0 if s.tipo == "conflicto" else 1, -s.fuerza, s.id))
    return _podar(salida)


_BLOQUE = {"sinergia": "Motor", "conflicto": "Conflictos"}


def _subtipos(tipo: str) -> set[str]:
    """Los subtipos de una línea de tipo: lo que va tras el guion largo."""
    if "—" not in tipo:
        return set()
    return {x.lower() for x in tipo.split("—")[-1].split()}


def _parejas(c: dict[str, Any], r: dict[str, list]):
    # Un concepto tribal no puede casar cualquier criatura con cualquier premio:
    # el subtipo de la carta tiene que ser el que menciona la otra. Sin esto, un
    # Human Monk salía emparejado con un premio a los Dragones.
    empareja = c.get("emparejar_subtipo")
    for a, eva in r["produce"]:
        for b, evb in r["premia"]:
            if empareja and not any(s in evb.lower() for s in _subtipos(a.tipo)):
                continue
            yield (a, eva), (b, evb), "sinergia", "produce", "premia"
    for a, eva in r["rompe"]:
        for b, evb in r["premia"]:
            yield (a, eva), (b, evb), "conflicto", "rompe", "premia"


def completo(mazo: Mazo, reglas_: list[dict[str, Any]] | None = None,
             conceptos: list[dict[str, Any]] | None = None) -> list[Sinergia]:
    """El análisis entero: primero lo escrito, después lo deducido.

    Las reglas con nombre van delante porque llevan título, pasos y avisos
    redactados. El léxico rellena lo que ninguna regla cubre, que es casi todo
    en cuanto te sales de los arquetipos que alguien se sentó a escribir.
    """
    from . import reglas as motor

    nombradas = motor.detectar(mazo, reglas_)
    cubiertas = {tuple(sorted(s.piezas)) for s in nombradas}
    deducidas = [s for s in detectar(mazo, conceptos)
                 if tuple(sorted(s.piezas)) not in cubiertas]
    return nombradas + deducidas


def cobertura(mazo: Mazo, conceptos: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Qué parte del mazo entiende el motor, y sobre todo qué NO entiende.

    Resolver una carta contra Scryfall siempre funciona, incluso con colecciones
    que aún no han salido. Entenderla es otra cosa: si el mazo trae una mecánica
    nueva y nadie ha escrito un concepto para ella, el motor la lee y no ve nada.

    Esta función no arregla eso — lo hace visible. Dice qué cartas quedan fuera
    del análisis y qué mecánicas con nombre no toca ningún concepto, que es la
    lista de lo que hay que escribir para cubrir la colección.
    """
    conceptos = conceptos if conceptos is not None else cargar()
    reparto = _papeles(mazo, conceptos)

    papeles: dict[str, list[str]] = {}
    for c in conceptos:
        for papel, aciertos in reparto[c["id"]].items():
            for carta, _ in aciertos:
                papeles.setdefault(carta.nombre, []).append(f"{c['id']}:{papel}")

    # Las tierras básicas no dicen nada del plan: no cuentan como punto ciego.
    interesantes = [c for c in mazo.principal if not c.es_basica]
    ciegas = [c.nombre for c in interesantes if c.nombre not in papeles]

    texto_conceptos = json.dumps(conceptos, ensure_ascii=False).lower()
    mecanicas: dict[str, dict[str, Any]] = {}
    for c in mazo.principal:
        for k in c.keywords:
            if k in EVERGREEN:      # palabras de combate: no definen sinergias
                continue
            m = mecanicas.setdefault(k, {"cartas": 0, "cubierta": k.lower() in texto_conceptos})
            m["cartas"] += c.copias

    sin_cubrir = sorted((k for k, v in mecanicas.items() if not v["cubierta"]),
                        key=lambda k: -mecanicas[k]["cartas"])

    # Leer una carta no es relacionarla. Una carta puede encajar en un concepto y
    # aun así quedarse sin pareja: es exactamente lo que se ve en el mapa como un
    # círculo suelto, y es la señal que de verdad delata un hueco del léxico.
    enlazadas = {p for s in completo(mazo, conceptos=conceptos) for p in s.piezas}
    sueltas = [c.nombre for c in interesantes if c.nombre not in enlazadas
               and not c.es_tierra]

    leidas = len(interesantes) - len(ciegas)
    return {
        "cartas_analizables": len(interesantes),
        "cartas_que_el_motor_lee": leidas,
        "porcentaje": round(100 * leidas / len(interesantes)) if interesantes else 0,
        "cartas_invisibles": ciegas,
        "cartas_sin_relacion": sueltas,
        "mecanicas_del_mazo": {k: v["cartas"] for k, v in
                               sorted(mecanicas.items(), key=lambda kv: -kv[1]["cartas"])},
        "mecanicas_sin_concepto": sin_cubrir,
        "veredicto": (
            "El motor no cubre este mazo: escribe conceptos para las mecánicas listadas, "
            "o analízalo por MCP, donde el modelo lee el oráculo y razona."
            if sin_cubrir or leidas < len(interesantes) * 0.7
            else f"Quedan {len(sueltas)} cartas sin ninguna relación. Si alguna es "
                 "importante en el mazo, ahí falta un concepto: mira su texto y "
                 "compáralo con lexico.json, o analízala por MCP."
            if sueltas
            else "El motor cubre las mecánicas de este mazo."
        ),
    }


def _podar(sinergias: list[Sinergia]) -> list[Sinergia]:
    """Quita repeticiones y limita el ruido.

    Una misma pareja de cartas puede compartir varios conceptos; se queda la
    conexión más fuerte. Y una carta no puede acaparar la página entera.
    """
    vistas: set[tuple[str, ...]] = set()
    # El cupo por carta se cuenta APARTE para sinergias y conflictos. Si no, una
    # carta muy conectada gastaba su cupo en sinergias y su conflicto —que es lo
    # que de verdad hay que avisar— no llegaba a salir.
    veces: dict[tuple[str, str], int] = {}
    cupo = {"sinergia": TOPE_SINERGIAS, "conflicto": TOPE_CONFLICTOS}
    fuera: list[Sinergia] = []
    for s in sinergias:
        par = tuple(sorted(s.piezas))
        if par in vistas or cupo.get(s.tipo, 0) <= 0:
            continue
        if any(veces.get((n, s.tipo), 0) >= POR_CARTA for n in s.piezas):
            continue
        vistas.add(par)
        cupo[s.tipo] -= 1
        for n in s.piezas:
            veces[(n, s.tipo)] = veces.get((n, s.tipo), 0) + 1
        fuera.append(s)
    return fuera
