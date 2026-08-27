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
    # una regla puede emitir varias parejas, así que el id lleva las cartas detrás
    ids = {s.id.split("::")[0] for s in motor.detectar(mazo)}
    # el motor debe encontrar el motor de rampa y las dos trampas del plan de victoria
    assert "tierra-indestructible-cantrip" in ids
    assert "barajar-rompe-posicion" in ids
    assert "fondo-biblioteca-acelera" in ids
    assert "victoria-unica-copia" in ids


def test_una_regla_sale_con_todas_las_cartas_que_encajan():
    """La regla decía "cualquier tierra indestructible", pero solo emitía una pareja.

    En el mazo de ejemplo hay dos —Cascading Cataracts y Rustvale Bridge— y la
    segunda, de la que van cuatro copias, se quedaba suelta en el mapa mientras
    la primera se llevaba la única línea.
    """
    mazo = scryfall.resolver(LISTA, "Prueba")
    con_la_regla = [s for s in motor.detectar(mazo)
                    if s.id.split("::")[0] == "tierra-indestructible-cantrip"]
    tierras = {p for s in con_la_regla for p in s.piezas if p != "Cleansing Wildfire"}
    assert tierras == {"Cascading Cataracts", "Rustvale Bridge"}, tierras

    # y el texto redactado nombra a la tierra de cada pareja, no siempre a la misma
    for s in con_la_regla:
        assert s.piezas[1] in s.resumen, f"el resumen no habla de {s.piezas[1]}"


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
def test_los_dos_motores_detectan_lo_mismo(tmp_path, monkeypatch):
    """reglas.py y motor.js son dos implementaciones del mismo motor.

    Si se separan, el mismo mazo produce documentos distintos según se analice
    desde la web o desde la línea de comandos. Nada más lo vigila.
    """
    # Los dos mazos de ejemplo: el de control y el de dragones. El segundo es el que
    # ejercita volar, el segundo hechizo del turno y los umbrales de fuerza, que el
    # de control no toca — con un solo mazo la prueba pasaba sin mirarlos.
    for fixture, lista, etiqueta in (
        ("fixture-pruebas.json", LISTA, "control"),
        ("fixture-dragones.json",
         (RAIZ / "ejemplos" / "dragones-boros.txt").read_text(encoding="utf-8"), "dragones"),
        ("fixture-blanco.json",
         (RAIZ / "ejemplos" / "blanco-agresivo.txt").read_text(encoding="utf-8"), "blanco"),
        ("fixture-stiflenought.json",
         (RAIZ / "ejemplos" / "stiflenought.txt").read_text(encoding="utf-8"), "stiflenought"),
    ):
        monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / fixture))
        mazo = scryfall.resolver(lista, etiqueta)
        principal = [c for c in mazo.cartas if not c.banquillo]
        entrada = tmp_path / f"mazo-{etiqueta}.json"
        entrada.write_text(json.dumps({
            # fuerza y keywords viajan también: sin ellas el gemelo de JS no puede
            # evaluar los umbrales y la paridad daría un falso verde.
            "principal": [{"nombre": c.nombre, "copias": c.copias, "coste": c.coste,
                           "mv": c.mv, "tipo": c.tipo, "oraculo": c.oraculo, "rol": c.rol,
                           "es_tierra": c.es_tierra, "es_basica": c.es_basica,
                           "fuerza": c.fuerza, "keywords": c.keywords}
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
        py = [s.id for s in lexico.completo(mazo)]
        js = json.loads(proc.stdout)
        assert py == js, (f"los motores se separan en el mazo de {etiqueta}: "
                          f"solo python {[x for x in py if x not in js][:3]} · "
                          f"solo js {[x for x in js if x not in py][:3]}")


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


def test_no_avisa_de_mana_si_la_tierra_si_da_color(monkeypatch):
    """«Solo produce incoloro» hay que comprobarlo, no suponerlo.

    Maelstrom of the Spirit Dragon dice «Add {C}», pero también «{T}: Add one mana
    of any color» sin coste extra, para pagar dragones. El motor avisaba contra los
    tres dragones a los que esa tierra existe justo para lanzar.
    """
    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-dragones.json"))
    lista = (RAIZ / "ejemplos" / "dragones-boros.txt").read_text(encoding="utf-8")
    s = motor.detectar(scryfall.resolver(lista, "Dragones"))
    falsos = [x for x in s if x.id.split("::")[0] == "doble-simbolo-tierra-incolora"]
    assert not falsos, f"vuelve el aviso falso de maná: {[x.piezas for x in falsos]}"

    # pero el aviso legítimo no puede desaparecer: en el mazo de control la tierra
    # cobra {5} por el color, así que en los primeros turnos es incolora de verdad
    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-pruebas.json"))
    s = motor.detectar(scryfall.resolver(LISTA, "Prueba"))
    reales = [x for x in s if x.id.split("::")[0] == "doble-simbolo-tierra-incolora"]
    assert reales, "el aviso de maná que sí es cierto se ha perdido"


def test_un_tutor_solo_encuentra_lo_que_dice_buscar(monkeypatch):
    """«Search your library for an artifact or enchantment card» no es un tutor de todo.

    Enlightened Tutor tiene que salir con los artefactos y encantamientos del mazo,
    y con ninguna criatura. Antes no salía con nada: el concepto de búsqueda solo
    premiaba cartas que dijeran «you win the game».
    """
    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-blanco.json"))
    lista = (RAIZ / "ejemplos" / "blanco-agresivo.txt").read_text(encoding="utf-8")
    mazo = scryfall.resolver(lista, "Blanco")

    encontradas = {p for s in lexico.completo(mazo)
                   if s.id.split("::")[0] == "tutor-por-tipo"
                   for p in s.piezas if p != "Enlightened Tutor"}
    assert encontradas == {"Worship", "Parallax Wave", "Cursed Scroll",
                           "Seal of Cleansing", "Phyrexian Furnace"}, encontradas

    # ninguna criatura: el tutor no las busca
    criaturas = {c.nombre for c in mazo.principal if "Creature" in c.tipo}
    assert not (encontradas & criaturas)


def test_un_aviso_de_base_de_mana_no_se_repite(monkeypatch):
    """El aviso es el mismo lo digas una vez u ocho.

    Al hacer que cada regla emitiera todas sus parejas, este pasó de una línea roja
    a ocho contra la misma tierra: ocho veces el mismo consejo no es más información.
    """
    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-blanco.json"))
    lista = (RAIZ / "ejemplos" / "blanco-agresivo.txt").read_text(encoding="utf-8")
    s = motor.detectar(scryfall.resolver(lista, "Blanco"))
    avisos = [x for x in s if x.id.split("::")[0] == "doble-simbolo-tierra-incolora"]
    assert len(avisos) == 1, f"el aviso sale {len(avisos)} veces"


def test_un_efecto_no_alcanza_lo_que_no_puede_apuntar(monkeypatch):
    """Daydream dice «exile target creature you control»: no toca encantamientos.

    El motor razonaba «esto reparpadea permanentes» + «esto tiene disparo al
    entrar» = sinergia, sin comprobar nunca que el primero pudiera apuntar al
    segundo. Salía Daydream con Seam Rip, que es un encantamiento: la jugada no
    es floja, es imposible.
    """
    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-dragones.json"))
    lista = (RAIZ / "ejemplos" / "dragones-boros.txt").read_text(encoding="utf-8")
    mazo = scryfall.resolver(lista, "Dragones")

    con_daydream = {p for s in lexico.completo(mazo)
                    if s.id.split("::")[0] == "entra-en-juego" and "Daydream" in s.piezas
                    for p in s.piezas if p != "Daydream"}
    assert "Seam Rip" not in con_daydream, "vuelve a parpadear un encantamiento"
    # y las criaturas con disparo al entrar siguen saliendo
    assert {"Nova Hellkite", "Magmatic Hellkite"} <= con_daydream, con_daydream


def test_un_efecto_sobre_permanentes_si_alcanza_a_todo():
    """«Return target permanent» sí llega a un encantamiento: no hay que filtrarlo."""
    assert lexico._tipos_objetivo("Exile target creature you control") == {"creature"}
    todo = set(lexico.TIPOS)
    assert lexico._tipos_objetivo("Return target permanent to its owner's hand") == todo
    assert lexico._tipos_objetivo("exile target nonland permanent") == todo - {"land"}
    # sin ningún tipo nombrado no se puede afirmar nada, así que no se filtra
    assert lexico._tipos_objetivo("Flicker it") == todo


def test_un_simbolo_de_mana_en_el_texto_no_tumba_el_analisis():
    """El texto de las reglas habla de costes, y "{1}" es un símbolo, no un hueco.

    Con str.format, un mazo con Daze reventaba entero: la regla dice «el rival
    paga el {1} sin despeinarse» y format lo leía como argumento posicional. La
    web no se enteraba —sustituye por expresión regular— así que además los dos
    motores daban cosas distintas para el mismo mazo.
    """
    assert motor._sustituir("{a} paga el {1}", {"a": "Daze"}) == "Daze paga el {1}"
    assert motor._sustituir("cuesta {U}{U}", {}) == "cuesta {U}{U}"
    assert motor._sustituir("{a} y {b}", {"a": "X", "b": "Y"}) == "X y Y"

    # y ninguna regla puede tumbar el motor por mucho símbolo que lleve encima
    from mtg_forja.modelo import Carta, Mazo
    mazo = Mazo(nombre="P")
    mazo.cartas.append(Carta(nombre="Daze", copias=3, tipo="Instant", mv=2,
        oraculo="You may return an Island you control to its owner's hand rather than "
                "pay this spell's mana cost. Counter target spell unless its controller pays {1}."))
    for i in range(17):
        mazo.cartas.append(Carta(nombre="Island", copias=1, tipo="Basic Land — Island",
                                 mv=0, oraculo="({T}: Add {U}.)"))
    motor.detectar(mazo)   # basta con que no lance


def test_el_disparo_que_te_perjudica_y_quien_lo_cancela(monkeypatch):
    """Phyrexian Dreadnought es un 12/12 por {1} si cancelas su propio disparo.

    El motor daba por bueno que todo disparo al entrar es valor. Aquí es un
    lastre, y media lista existe para neutralizarlo: Stifle lo contrarresta y
    Vision Charm hace desvanecerse el artefacto. Era el combo del mazo y no
    salía ninguna de las dos.
    """
    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-stiflenought.json"))
    lista = (RAIZ / "ejemplos" / "stiflenought.txt").read_text(encoding="utf-8")
    mazo = scryfall.resolver(lista, "Stiflenought")

    respuestas = {p for s in lexico.completo(mazo)
                  if s.id.split("::")[0] == "disparo-que-perjudica"
                  for p in s.piezas if p != "Phyrexian Dreadnought"}
    assert respuestas == {"Stifle", "Vision Charm"}, respuestas


def test_una_carta_azul_cualquiera_no_es_una_sinergia(monkeypatch):
    """Misdirection exilia «a blue card»: en un mazo monoazul lo cumple todo.

    Eran nueve líneas para decir que el mazo es azul, y dejaban a Misdirection
    como nudo principal del mapa. El consejo útil —cada uso cuesta dos cartas—
    habla de Misdirection sola, así que es nota de una carta, no pareja.
    """
    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-stiflenought.json"))
    lista = (RAIZ / "ejemplos" / "stiflenought.txt").read_text(encoding="utf-8")
    s = lexico.completo(scryfall.resolver(lista, "Stiflenought"))

    parejas = [x for x in s if "Misdirection" in x.piezas and len(x.piezas) > 1]
    assert not parejas, f"Misdirection vuelve a emparejarse: {[x.piezas for x in parejas]}"
    # pero el aviso sobre la propia carta se conserva
    assert any(x.piezas == ["Misdirection"] for x in s), "se ha perdido el aviso"


def test_contraste_encuentra_el_ruling_que_documenta_el_combo(monkeypatch):
    """Un combo conocido suele estar explicado en el ruling oficial de la carta.

    Phyrexian Dreadnought + Stifle lleva veinte años documentado, y Wizards lo
    dice con todas las letras. Deducirlo a ciegas cuando la fuente oficial ya lo
    explica es trabajar de más y peor.
    """
    from mtg_forja import contraste

    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-stiflenought.json"))
    lista = (RAIZ / "ejemplos" / "stiflenought.txt").read_text(encoding="utf-8")
    mazo = scryfall.resolver(lista, "Stiflenought")

    # los rulings reales de Scryfall, fijados aquí para no depender de la red
    falsos = {
        "Phyrexian Dreadnought": [
            'Reverted to its original wording, this now has an "enters" triggered '
            "ability. During resolution of the triggered ability, you choose one option.",
            'Phasing in does not trigger "enters" abilities, so you don\'t have to '
            "sacrifice again if it phases in.",
        ],
    }
    r = contraste.contrastar(mazo, lexico.completo(mazo),
                             buscar_rulings=lambda c: falsos.get(c.nombre, []))

    apoyadas = {tuple(sorted(x["piezas"])) for x in r["contrastes"]}
    assert ("Phyrexian Dreadnought", "Stifle") in apoyadas, apoyadas
    assert ("Phyrexian Dreadnought", "Vision Charm") in apoyadas, apoyadas

    # y el aviso de que esto no demuestra nada no puede desaparecer por descuido
    assert "no demuestra" in r["atencion"]


def test_contraste_no_se_rompe_sin_red(monkeypatch):
    """Los rulings son una consulta extra: sin ellos el análisis sigue igual."""
    from mtg_forja import contraste

    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-stiflenought.json"))
    lista = (RAIZ / "ejemplos" / "stiflenought.txt").read_text(encoding="utf-8")
    mazo = scryfall.resolver(lista, "Stiflenought")

    r = contraste.contrastar(mazo, lexico.completo(mazo), buscar_rulings=lambda c: [])
    assert r["contrastes"] == [] and r["parejas_analizadas"] > 0


def test_contraste_no_confunde_contrarrestar_con_contadores():
    """"countered" es contrarrestar y "counters" son contadores +1/+1.

    Reduciéndolas a la misma raíz, un ruling sobre contrahechizos casaba con
    cualquier carta que pusiera contadores.
    """
    from mtg_forja import contraste

    ruling = "A spell cast using flashback will always be exiled, whether it resolves or is countered."
    assert not contraste._apoya(ruling, "Put a +1/+1 counter on it. Draw a card.")
    # pero el término compartido de verdad sí vale: este es el ruling literal
    # de Phyrexian Dreadnought, y es el que documenta el combo con Vision Charm
    oficial = ('Phasing in does not trigger "enters" abilities, so you don\'t have '
               "to sacrifice again if it phases in.")
    assert contraste._apoya(oficial, "Target artifact phases out.") == ["phases"]


def test_etiquetas_no_confunden_fallo_de_red_con_ausencia(monkeypatch):
    """Un 429 no significa «esta carta no lleva la etiqueta».

    Tragarse el error y dar la etiqueta por vacía convierte un fallo de red en un
    dato, y el informe pasa a mentir con toda la confianza del mundo.
    """
    import urllib.error

    from mtg_forja import etiquetas

    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-stiflenought.json"))
    lista = (RAIZ / "ejemplos" / "stiflenought.txt").read_text(encoding="utf-8")
    mazo = scryfall.resolver(lista, "Stiflenought")
    monkeypatch.setattr(etiquetas, "PAUSA", 0)

    def se_cae(consulta):
        if "drawback" in consulta:
            raise urllib.error.URLError("429")
        return ["Vision Charm"] if "phasing" in consulta else []

    r = etiquetas.de_mazo(mazo, etiquetas=["drawback", "phasing"], pedir=se_cae)

    assert r["por_etiqueta"] == {"phasing": ["Vision Charm"]}
    assert r["etiquetas_sin_comprobar"] == ["drawback"], r["etiquetas_sin_comprobar"]
    assert "no ausentes" in r["atencion"]


def test_etiquetas_sin_red_no_rompen_nada(monkeypatch):
    """Es una fuente externa: si no responde, el análisis sigue sin ella."""
    import urllib.error

    from mtg_forja import etiquetas

    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-stiflenought.json"))
    lista = (RAIZ / "ejemplos" / "stiflenought.txt").read_text(encoding="utf-8")
    monkeypatch.setattr(etiquetas, "PAUSA", 0)

    def nada(consulta):
        raise urllib.error.URLError("sin red")

    r = etiquetas.de_mazo(scryfall.resolver(lista, "S"), etiquetas=["drawback"], pedir=nada)
    assert r["por_carta"] == {} and r["etiquetas_sin_comprobar"] == ["drawback"]


def test_el_vocabulario_de_etiquetas_es_usable():
    """etiquetas.json tiene que viajar en el paquete y traer las que importan."""
    from mtg_forja import etiquetas

    v = etiquetas.cargar()
    assert len(v) >= 30, f"solo {len(v)} etiquetas"
    # las tres que destaparon los combos de los mazos de prueba
    for imprescindible in ("drawback", "phasing", "pitch-spell"):
        assert imprescindible in v, imprescindible
    assert all(isinstance(n, int) and n >= 10 for n in v.values())


def test_compartir_etiqueta_no_es_tener_sinergia(monkeypatch):
    """Foil y Misdirection son las dos `pitch-spell`, y no combinan.

    La etiqueta funcional de Scryfall las clasifica juntas, igual que agrupa a
    Counterspell con Daze. Eso es una categoría, no una interacción: de hecho
    compiten, porque las dos se pagan con cartas de la mano.

    Lo que sí es una sinergia está al lado y es más concreto: Gush devuelve Islas
    a tu mano y Foil necesita descartar una Isla de la mano para lanzarse gratis.
    """
    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-stiflenought.json"))
    lista = (RAIZ / "ejemplos" / "stiflenought.txt").read_text(encoding="utf-8")
    s = lexico.completo(scryfall.resolver(lista, "Stiflenought"))

    assert not any({"Foil", "Misdirection"} <= set(x.piezas) for x in s), \
        "compartir etiqueta no puede convertirse en una línea del mapa"

    devuelven = {p for x in s if x.id.split("::")[0] == "tierra-a-la-mano"
                 for p in x.piezas if p != "Foil"}
    assert devuelven == {"Gush", "Daze", "Thwart"}, devuelven


def test_todos_los_costes_pagados_con_islas_salen_con_la_isla(monkeypatch):
    """La regla decía literalmente "return an Island": estaba escrita para Daze.

    En ese mazo hay cuatro hechizos que se pagan con Islas y solo salía uno. Gush
    devuelve dos, Thwart tres y Foil descarta una, y las tres formas fallaban por
    el singular o por el verbo. Diecisiete Islas no están ahí por el maná.

    Ahora es un concepto que empareja por subtipo, así que vale para los cinco
    colores y para los tres verbos del ciclo.
    """
    monkeypatch.setenv("MTG_FORJA_FIXTURE", str(RAIZ / "ejemplos" / "fixture-stiflenought.json"))
    lista = (RAIZ / "ejemplos" / "stiflenought.txt").read_text(encoding="utf-8")
    s = lexico.completo(scryfall.resolver(lista, "Stiflenought"))

    con_isla = {p for x in s if x.id.split("::")[0] == "tierra-como-coste"
                for p in x.piezas if p != "Island"}
    assert con_isla == {"Daze", "Gush", "Thwart", "Foil"}, con_isla


def test_la_tierra_que_paga_es_la_del_tipo_correcto():
    """Foil descarta una Isla y Fireblast sacrifica Montañas: no se cruzan.

    La regla original decía literalmente «return an Island», así que valía para
    una carta. El ciclo real recorre los cinco colores y tres verbos —devolver,
    descartar y sacrificar—, y generalizarla dentro de las reglas escritas habría
    emparejado Foil con una Montaña, porque allí el tipo va fijo en la pieza.
    """
    from mtg_forja.modelo import Carta, Mazo

    mazo = Mazo(nombre="Prueba")
    mazo.cartas.append(Carta(nombre="Foil", copias=4, tipo="Instant", mv=4,
        oraculo="You may discard an Island card and another card rather than pay "
                "this spell's mana cost. Counter target spell."))
    mazo.cartas.append(Carta(nombre="Fireblast", copias=4, tipo="Instant", mv=6,
        oraculo="You may sacrifice two Mountains rather than pay this spell's mana "
                "cost. Fireblast deals 4 damage to any target."))
    mazo.cartas.append(Carta(nombre="Island", copias=10, tipo="Basic Land — Island",
                             mv=0, oraculo=""))
    mazo.cartas.append(Carta(nombre="Mountain", copias=10, tipo="Basic Land — Mountain",
                             mv=0, oraculo=""))

    parejas = {tuple(sorted(x.piezas)) for x in lexico.detectar(mazo)
               if x.id.split("::")[0] == "tierra-como-coste"}
    assert parejas == {("Foil", "Island"), ("Fireblast", "Mountain")}, parejas


def test_el_coste_alternativo_no_es_solo_de_tierras():
    """También se paga sacrificando criaturas, tapándolas o exiliando artefactos."""
    from mtg_forja.modelo import Carta, Mazo

    mazo = Mazo(nombre="Prueba")
    mazo.cartas.append(Carta(nombre="Delraich", copias=2, tipo="Creature — Horror", mv=6,
        oraculo="You may sacrifice three black creatures rather than pay this spell's "
                "mana cost. Trample"))
    mazo.cartas.append(Carta(nombre="Bicho", copias=4, tipo="Creature — Zombie", mv=2,
                             oraculo="Menace"))
    mazo.cartas.append(Carta(nombre="Trasto", copias=4, tipo="Artifact", mv=2,
                             oraculo="{T}: Add {C}."))
    mazo.cartas.append(Carta(nombre="Llano", copias=8, tipo="Basic Land — Plains",
                             mv=0, oraculo=""))

    con_delraich = {p for x in lexico.detectar(mazo)
                    if x.id.split("::")[0] == "permanente-como-coste"
                    for p in x.piezas if p != "Delraich"}
    # el coste dice "creatures": ni el artefacto ni la tierra sirven para pagarlo
    assert con_delraich == {"Bicho"}, con_delraich


def test_la_comunidad_pesa_mas_que_el_motor():
    """Si un catálogo cataloga el combo y el motor no lo une, el hueco es nuestro."""
    from mtg_forja import contraste
    from mtg_forja.modelo import Carta, Mazo

    mazo = Mazo(nombre="Prueba")
    for n in ("Pieza A", "Pieza B"):
        mazo.cartas.append(Carta(nombre=n, copias=4, tipo="Artifact", mv=2, oraculo="{T}: Add {C}."))

    catalogo = {"completos": [{"cartas": ["Pieza A", "Pieza B"],
                               "produce": "maná infinito", "pasos": ["p"]}]}
    r = contraste.contrastar(mazo, [], buscar_rulings=lambda c: [],
                             combos_comunidad=catalogo)

    falta = r["la_comunidad_ve_lo_que_nosotros_no"]
    assert len(falta) == 1 and falta[0]["cartas"] == ["Pieza A", "Pieza B"]
    assert "pesa MÁS" in r["atencion"]


def test_un_concepto_sin_etiqueta_no_es_sospechoso():
    """Distinguir «nadie lo comprobó» de «nadie lo respalda».

    Mapear conceptos a etiquetas a la fuerza daba refuerzos y alarmas falsas: un
    premio tribal no es un `lord`. Sin correspondencia clara, no se mapea.
    """
    from mtg_forja import etiquetas

    mapeo = etiquetas.por_concepto()
    assert "tribu" not in mapeo, "un premio tribal no es un lord"
    conocidas = set(etiquetas.cargar())
    for concepto, tags in mapeo.items():
        assert tags, concepto
        assert set(tags) <= conocidas, f"{concepto} apunta a etiquetas que no existen"
