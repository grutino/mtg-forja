"""Pruebas mínimas que corren sin red, con el fixture de ejemplo."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
os.environ["MTG_FORJA_FIXTURE"] = str(RAIZ / "ejemplos" / "fixture-pruebas.json")

from mtg_forja import lexico  # noqa: E402
from mtg_forja import reglas as motor  # noqa: E402
from mtg_forja import scryfall  # noqa: E402
from mtg_forja.modelo import parsear_lista  # noqa: E402
from mtg_forja.render import chuleta, guia, mapa  # noqa: E402

LISTA = (RAIZ / "ejemplos" / "prueba.txt").read_text(encoding="utf-8")


def test_parseo_formatos():
    filas = parsear_lista("Deck\n4 Cleansing Wildfire (ZNR) 137\n2x Mountain\nSideboard\n1 Plains")
    assert (4, "Cleansing Wildfire", False) in filas
    assert (2, "Mountain", False) in filas
    assert (1, "Plains", True) in filas


def test_parseo_de_exportaciones_reales():
    """Moxfield marca el foil, Archidekt cuelga categorías y ManaBox exporta CSV."""
    assert parsear_lista("4 Lightning Bolt (M10) 146 *F*") == [(4, "Lightning Bolt", False)]
    assert parsear_lista("4x Lightning Bolt (m10) 146 [Burn]") == [(4, "Lightning Bolt", False)]
    # el maybeboard de Archidekt no es mazo principal
    assert parsear_lista("1x Pyroblast (ice) 213 [Maybeboard{noPrice}]") == [(1, "Pyroblast", True)]
    assert parsear_lista(
        'Name,Set code,Collector number,Quantity\n"Sol Ring",ltc,284,3'
    ) == [(3, "Sol Ring", False)]


def test_resolucion_y_curva():
    mazo = scryfall.resolver(LISTA, "Prueba")
    assert mazo.total == 30
    assert mazo.basicas == 5
    assert not mazo.no_resueltas
    assert mazo.buscar("Sunfall").mv == 5


def test_deteccion():
    mazo = scryfall.resolver(LISTA, "Prueba")
    ids = {s.id for s in motor.detectar(mazo)}
    # el motor debe encontrar el motor de rampa y las dos trampas del plan de victoria
    assert "tierra-indestructible-cantrip" in ids
    assert "barajar-rompe-posicion" in ids
    assert "fondo-biblioteca-acelera" in ids
    assert "victoria-unica-copia" in ids


def test_evidencia_es_texto_de_oraculo():
    mazo = scryfall.resolver(LISTA, "Prueba")
    for s in motor.detectar(mazo):
        for nombre, ev in s.evidencia.items():
            carta = mazo.buscar(nombre)
            assert ev, f"sin evidencia para {nombre}"
            assert ev.split()[0] in " ".join(carta.oraculo.split()) or carta.tipo


def test_nombre_sin_tilde_resuelve():
    """Scryfall responde con la grafía canónica; pedir sin tilde debe casar igual."""
    assert scryfall._clave("Palantir of Orthanc") == scryfall._clave("Palantír of Orthanc")
    assert scryfall._clave("Teferi's Protection") == scryfall._clave("Teferi’s Protection")
    # y la caché tiene que caer en el mismo archivo para las dos grafías
    assert scryfall._slug("Palantir of Orthanc") == scryfall._slug("Palantír of Orthanc")


def test_json_incrustado_no_corta_el_bloque_script():
    """Los tres HTML llevan el documento dentro de un <script>: hay que escapar "<"."""
    hostil = "</script><h1>ups"
    doc = {
        "titulo": "Prueba", "subtitulo": "1 carta", "curva": {"1": 1},
        "cartas": [{"nombre": hostil, "copias": 1, "coste": "{1}", "mv": 1,
                    "tipo": "Artifact", "rol": "motor"}],
        # el mapa solo incrusta las cartas que aparecen en alguna sinergia
        "sinergias": [{"id": "x", "nombre": "Prueba", "bloque": "Motor",
                       "tipo": "sinergia", "fuerza": 2, "turno": "medio",
                       "piezas": [hostil], "resumen": "r", "pasos": ["p"],
                       "evidencia": {hostil: "ev"}}],
        "orden": [], "reglas_oro": [], "no_resueltas": [],
    }
    for modulo in (guia, chuleta, mapa):
        html = modulo.render(doc)
        assert hostil not in html, f"{modulo.__name__} deja el cierre sin escapar"
        assert "\\u003c/script>" in html, f"{modulo.__name__} no escapa el documento"


@pytest.mark.skipif(shutil.which("node") is None, reason="hace falta node")
def test_los_dos_motores_detectan_lo_mismo(tmp_path):
    """reglas.py y motor.js son dos implementaciones del mismo motor.

    Si se separan, el mismo mazo produce documentos distintos según se analice
    desde la web o desde la línea de comandos. Nada más lo vigila.
    """
    mazo = scryfall.resolver(LISTA, "Prueba")
    principal = [c for c in mazo.cartas if not c.banquillo]
    entrada = tmp_path / "mazo.json"
    entrada.write_text(json.dumps({
        "principal": [{"nombre": c.nombre, "copias": c.copias, "coste": c.coste,
                       "mv": c.mv, "tipo": c.tipo, "oraculo": c.oraculo, "rol": c.rol,
                       "es_tierra": c.es_tierra, "es_basica": c.es_basica}
                      for c in principal],
        "total": mazo.total, "tierras": mazo.tierras, "basicas": mazo.basicas,
    }, ensure_ascii=False), encoding="utf-8")

    guion = (
        "global.fetch=()=>{throw new Error('sin red')};"
        f"require({str(RAIZ / 'docs' / 'motor.js')!r});"
        "const fs=require('fs');"
        f"const mazo=JSON.parse(fs.readFileSync({str(entrada)!r},'utf8'));"
        f"const r=JSON.parse(fs.readFileSync({str(RAIZ / 'docs' / 'reglas.json')!r},'utf8')).reglas;"
        f"const l=JSON.parse(fs.readFileSync({str(RAIZ / 'docs' / 'lexico.json')!r},'utf8')).conceptos;"
        "console.log(JSON.stringify(Forja.completo(mazo,r,l).map(s=>s.id)));"
    )
    proc = subprocess.run(["node", "-e", guion], capture_output=True, text=True, check=True)

    # `completo` cubre las dos mitades: las reglas escritas y lo que deduce el léxico.
    assert [s.id for s in lexico.completo(mazo)] == json.loads(proc.stdout)


def test_cli_falla_si_no_resuelve_nada(tmp_path):
    """Sin red los tres documentos saldrían vacíos: hay que avisar, no fingir éxito."""
    from mtg_forja import cli

    lista = tmp_path / "mazo.txt"
    lista.write_text("4 Carta Inventada Que No Existe\n", encoding="utf-8")
    salida = tmp_path / "salida"

    assert cli.main([str(lista), "-o", str(salida)]) == 1
    assert not salida.exists(), "no debe dejar HTML vacíos por el camino"


def test_combos_no_rompen_el_analisis_si_falla_la_api(monkeypatch, tmp_path):
    """Commander Spellbook es una fuente externa: si no responde, se sigue sin ella."""
    from mtg_forja import combos

    monkeypatch.setattr(combos, "CACHE_COMBOS", tmp_path / "combos")
    monkeypatch.delenv("MTG_FORJA_COMBOS_FIXTURE", raising=False)

    def caida(*a, **k):
        raise TimeoutError("la API no contesta")

    monkeypatch.setattr(combos.urllib.request, "urlopen", caida)
    r = combos.buscar(scryfall.resolver(LISTA, "Prueba"))

    assert r["completos"] == [] and r["casi_completos"] == []
    assert "aviso" in r, "tiene que decir por qué viene vacío"


def test_combos_resume_lo_que_importa(monkeypatch):
    """Del combo se guardan las cartas, qué produce y los pasos redactados."""
    from mtg_forja import combos

    fixture = RAIZ / "ejemplos" / "fixture-combos.json"
    monkeypatch.setenv("MTG_FORJA_COMBOS_FIXTURE", str(fixture))
    r = combos.buscar(scryfall.resolver(LISTA, "Prueba"))

    assert "Commander Spellbook" in r["fuente"]
    # el aviso de que no es oráculo verificado no puede desaparecer por descuido
    assert "oráculo" in r["atencion"]
    assert r["casi_completos"], "el fixture trae combos casi completos"
    uno = r["casi_completos"][0]
    assert uno["cartas"] and uno["produce"] and uno["pasos"]


def test_el_pip_incoloro_no_choca_con_la_ficha_de_carta():
    """La guía usa `.c` para la ficha de carta, de 118px de ancho.

    Cuando el pip de maná genérico se llamaba `.pip.c`, esa regla ganaba por ir
    después con la misma especificidad y el círculo salía como un óvalo.
    """
    from mtg_forja.render import comun

    marca = comun.pips("{4}")
    assert 'class="pip c"' not in marca, "vuelve a chocar con la ficha de carta"
    assert 'class="pip inc"' in marca
    assert ".pip.inc{" in comun.PIPS

    # y la mitad de JavaScript tiene que decir exactamente lo mismo
    js = (RAIZ / "src" / "mtg_forja" / "render" / "comun.js").read_text(encoding="utf-8")
    assert 'class="pip c"' not in js and ".pip.inc{" in js


def test_el_mapa_muestra_todas_las_cartas_y_solo_enlaces_reales():
    """Todas las cartas salen como nodo, pero solo se une lo que de verdad interactúa.

    Los enlaces de maná se probaron y se retiraron: ataban casi todo con casi todo
    y el grafo dejaba de leerse. Una tierra suelta dice más que una maraña.
    """
    mazo = scryfall.resolver(LISTA, "Prueba")
    doc = motor.documento(mazo, lexico.completo(mazo), titulo="Prueba")
    datos = mapa._datos(doc)

    # toda carta del mazo principal es un nodo, tenga relaciones o no
    for c in doc["cartas"]:
        assert c["nombre"] in datos["cartas"], f"{c['nombre']} no sale en el mapa"

    # y no queda ni rastro de los enlaces de maná
    assert not [e for e in datos["enlaces"] if e.get("m")], "vuelven los enlaces de maná"

    # cada enlace nace de una sinergia o conflicto entre dos cartas del mazo
    parejas = {tuple(sorted(s["piezas"][i:i + 2]))
               for s in doc["sinergias"] for i in range(len(s["piezas"]) - 1)}
    for e in datos["enlaces"]:
        assert tuple(sorted((e["a"], e["b"]))) in parejas, f"enlace sin origen: {e}"

    # y alguna carta queda suelta, que es justo lo que queríamos permitir
    atadas = {e["a"] for e in datos["enlaces"]} | {e["b"] for e in datos["enlaces"]}
    assert set(datos["cartas"]) - atadas, "el mazo de prueba debería tener cartas sueltas"

def test_cobertura_distingue_leer_de_entender():
    """Resolver una carta y entenderla son cosas distintas, y hay que poder verlo."""
    mazo = scryfall.resolver(LISTA, "Prueba")
    c = lexico.cobertura(mazo)

    assert c["cartas_analizables"] > 0
    assert 0 <= c["porcentaje"] <= 100
    # una mecánica de combate no es un hueco del léxico
    assert not ({"Flying", "Vigilance", "Trample"} & set(c["mecanicas_sin_concepto"]))
    # toda carta invisible tiene que ser una carta real del mazo
    nombres = {x.nombre for x in mazo.principal}
    assert set(c["cartas_invisibles"]) <= nombres


def test_rulings_degradan_sin_romper(monkeypatch, tmp_path):
    """Los rulings son una consulta extra: si no hay red, el análisis sigue igual."""
    monkeypatch.setattr(scryfall, "RULINGS", tmp_path / "rulings")

    def caida(*a, **k):
        raise TimeoutError("sin red")

    monkeypatch.setattr(scryfall.urllib.request, "urlopen", caida)
    carta = scryfall.resolver(LISTA, "Prueba").principal[0]
    carta.rulings_uri = "https://api.scryfall.com/cards/x/rulings"

    assert scryfall.rulings(carta) == []
    # y sin URL ni siquiera lo intenta
    carta.rulings_uri = ""
    assert scryfall.rulings(carta) == []


def test_metadata_de_arena_no_es_una_carta():
    """La sección About de Arena trae "Name <mazo>" y se colaba como carta."""
    r = parsear_lista("About\nName Draft Deck\n\nDeck\n2 Attercop\n1 Nameless Inversion")
    assert (2, "Attercop", False) in r
    assert (1, "Nameless Inversion", False) in r, "no puede comerse una carta real"
    assert not any("Draft Deck" in n for _, n, _ in r)


def test_hibrido_no_exige_los_dos_colores():
    """{G/U} se paga con verde O azul: no puede avisar de falta de azul."""
    from mtg_forja import hechos

    duros, hibridos = hechos._exigencia("{2}{G/U}")
    assert not duros, "un híbrido no exige ningún color concreto"
    assert hibridos == [["U", "G"]] or hibridos == [["G", "U"]]
    # y uno normal sí exige
    duros, hibridos = hechos._exigencia("{1}{B}{B}")
    assert duros["B"] == 2 and not hibridos


def test_umbral_de_fuerza():
    """Mecánicas como Ferocious piden "una criatura de fuerza 4 o más"."""
    from mtg_forja.modelo import Carta

    bloque = {"tipo": "Creature", "fuerza_min": 4}
    grande = Carta(nombre="G", tipo="Creature — Wolf", fuerza="5", oraculo="")
    pequena = Carta(nombre="P", tipo="Creature — Spider", fuerza="2", oraculo="")
    variable = Carta(nombre="V", tipo="Creature — Elf", fuerza="*", oraculo="")

    assert lexico._encaja(grande, bloque), "una 5/5 sí enciende el umbral"
    assert not lexico._encaja(pequena, bloque), "una 2/2 no puede encenderlo"
    # fuerza variable: no se puede afirmar, así que no cuenta
    assert not lexico._encaja(variable, bloque)


def test_efecto_solo_del_rival_no_es_conflicto_propio():
    """«destroy target nonbasic land an opponent controls» no ataca tus tierras.

    Magmatic Hellkite destruye tierras DEL RIVAL, y el mapa pintaba cinco avisos
    rojos contra las tierras propias. Un aviso falso es peor que ningún aviso.
    """
    from mtg_forja.modelo import Carta

    concepto = next(c for c in lexico.cargar() if c["id"] == "tierras-no-basicas")
    solo_rival = Carta(nombre="Hellkite", tipo="Creature — Dragon",
                       oraculo="When this creature enters, destroy target nonbasic "
                               "land an opponent controls.")
    simetrica = Carta(nombre="Ruina", tipo="Sorcery",
                      oraculo="Destroy target nonbasic land.")

    assert not lexico._encaja(solo_rival, concepto["rompe"]), "solo alcanza al rival"
    assert lexico._encaja(simetrica, concepto["rompe"]), "esta sí te puede tocar"


def test_tribal_empareja_por_subtipo_real():
    """Un premio a los Dragones no casa con un Human Monk."""
    from mtg_forja.modelo import Carta

    concepto = next(c for c in lexico.cargar() if c["id"] == "tribu")
    assert concepto.get("emparejar_subtipo"), "el concepto tribal debe exigir el subtipo"

    dragon = Carta(nombre="D", tipo="Creature — Dragon", oraculo="Flying")
    monje = Carta(nombre="M", tipo="Creature — Human Monk", oraculo="")
    reparto = {"produce": [(dragon, "Creature — Dragon"), (monje, "Creature — Human Monk")],
               "premia": [(Carta(nombre="P", tipo="Land", oraculo=""),
                           "Search your library for a Dragon card")],
               "rompe": []}
    casadas = {a.nombre for (a, _), _, _, _, _ in lexico._parejas(concepto, reparto)}
    assert casadas == {"D"}, f"el monje no debería casar: {casadas}"


def test_renderizadores():
    mazo = scryfall.resolver(LISTA, "Prueba")
    doc = motor.documento(mazo, motor.detectar(mazo), titulo="Prueba")
    for modulo in (guia, chuleta, mapa):
        html = modulo.render(doc)
        assert html.startswith("<!DOCTYPE html>")
        assert "Prueba" in html

def test_una_carta_eje_se_conecta_con_todos_sus_companeros():
    """Si una carta premia CADA hechizo que lanzas, tiene que salir con todos.

    El tope por concepto dejaba solo tres parejas y escondía el motor del mazo:
    en un mazo de quemar, Thermo-Alchemist aparecía con dos hechizos de seis.
    """
    from mtg_forja.modelo import Carta, Mazo

    eje = Carta(nombre="Eje", copias=4, tipo="Creature — Wizard", mv=2,
                oraculo="Whenever you cast an instant or sorcery spell, untap this creature.")
    mazo = Mazo(nombre="Prueba")
    mazo.cartas.append(eje)
    for i in range(6):
        mazo.cartas.append(Carta(nombre=f"Hechizo {i}", copias=4, tipo="Instant", mv=1,
                                 oraculo="This spell deals 3 damage to any target."))

    s = lexico.detectar(mazo)
    con_el_eje = [x for x in s if "Eje" in x.piezas]
    assert len(con_el_eje) == 6, f"solo salen {len(con_el_eje)} de 6 compañeros"


def test_el_conflicto_gana_a_la_sinergia_en_la_misma_pareja():
    """Odiar el cementerio no es llenarlo, y avisar importa más que halagar."""
    from mtg_forja.modelo import Carta, Mazo

    mazo = Mazo(nombre="Prueba")
    mazo.cartas.append(Carta(nombre="Odio", copias=2, tipo="Enchantment", mv=2,
        oraculo="If a card would be put into a graveyard from anywhere, exile it instead."))
    mazo.cartas.append(Carta(nombre="Goloso", copias=4, tipo="Creature", mv=2,
        oraculo="As long as there are two or more cards in your graveyard, this creature gets +1/+0."))

    s = lexico.detectar(mazo)
    par = [x for x in s if set(x.piezas) == {"Odio", "Goloso"}]
    assert par, "la pareja no aparece"
    assert par[0].tipo == "conflicto", "debería avisar del conflicto, no venderlo como sinergia"


def test_una_carta_que_se_fija_en_volar_no_queda_suelta():
    """Momo abarata las criaturas con volar: no puede salir desconectado.

    Volar estaba en la lista de palabras de combate «que no definen sinergias».
    Es falso en cuanto otra carta se fija en ellas, y el mapa dejaba la carta
    clave del mazo flotando sin una sola línea.
    """
    from mtg_forja.modelo import Carta, Mazo

    mazo = Mazo(nombre="Prueba")
    mazo.cartas.append(Carta(nombre="Momo", copias=1, tipo="Creature — Bat", mv=1,
        oraculo="Flying\nThe first creature spell with flying you cast during each of "
                "your turns costs {1} less to cast."))
    for i in range(3):
        mazo.cartas.append(Carta(nombre=f"Dragón {i}", copias=1, tipo="Creature — Dragon",
                                 mv=5, oraculo="Flying"))
    mazo.cartas.append(Carta(nombre="Terrestre", copias=1, tipo="Creature — Bear", mv=2,
                             oraculo="Vigilance"))

    con_momo = [x for x in lexico.detectar(mazo) if "Momo" in x.piezas]
    assert len(con_momo) == 3, f"Momo sale con {len(con_momo)} voladores de 3"
    assert not any("Terrestre" in x.piezas for x in con_momo), "un oso no vuela"


def test_el_segundo_hechizo_del_turno_es_un_recurso():
    """«Flurry» pide encadenar dos hechizos: los baratos son quienes lo permiten."""
    from mtg_forja.modelo import Carta, Mazo

    mazo = Mazo(nombre="Prueba")
    mazo.cartas.append(Carta(nombre="Flurrioso", copias=2, tipo="Creature — Spirit", mv=2,
        oraculo="Whenever you cast your second spell each turn, create a 1/1 white "
                "Spirit creature token with flying."))
    for i in range(2):
        mazo.cartas.append(Carta(nombre=f"Truco {i}", copias=4, tipo="Instant", mv=1,
                                 oraculo="Scry 1. Draw a card."))
    mazo.cartas.append(Carta(nombre="Carota", copias=1, tipo="Sorcery", mv=7,
                             oraculo="Draw seven cards."))

    con_flurry = [x for x in lexico.detectar(mazo) if "Flurrioso" in x.piezas]
    baratos = {p for x in con_flurry for p in x.piezas if p != "Flurrioso"}
    assert baratos == {"Truco 0", "Truco 1"}, f"debería casar solo con los baratos: {baratos}"


def test_el_mazo_de_dragones_no_deja_suelta_su_carta_clave(monkeypatch):
    """El mazo real que destapó los dos fallos, congelado como regresión.

    Sam mandó el mapa de su mazo de dragones: Momo, del que lleva cuatro copias,
    flotaba sin una sola línea, y Magmatic Hellkite pintaba conflictos rojos
    contra sus propias tierras porque destruye tierras DEL RIVAL.
    """
    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-dragones.json"))
    lista = (RAIZ / "ejemplos" / "dragones-boros.txt").read_text(encoding="utf-8")
    mazo = scryfall.resolver(lista, "Dragones Boros")
    assert mazo.total == 60, f"el mazo son 60 cartas, no {mazo.total}"

    s = lexico.completo(mazo)
    momo = [x for x in s if "Momo, Friendly Flier" in x.piezas]
    assert len(momo) >= 5, f"Momo vuelve a quedarse suelto: {len(momo)} conexiones"

    tierras = {c.nombre for c in mazo.principal if c.es_tierra}
    for x in s:
        if x.tipo == "conflicto" and "Magmatic Hellkite" in x.piezas:
            chocan = tierras & set(x.piezas)
            assert not chocan, f"vuelve el aviso falso contra tus tierras: {chocan}"
