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


def test_renderizadores():
    mazo = scryfall.resolver(LISTA, "Prueba")
    doc = motor.documento(mazo, motor.detectar(mazo), titulo="Prueba")
    for modulo in (guia, chuleta, mapa):
        html = modulo.render(doc)
        assert html.startswith("<!DOCTYPE html>")
        assert "Prueba" in html
