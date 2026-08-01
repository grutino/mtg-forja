"""Pruebas mínimas que corren sin red, con el fixture de ejemplo."""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
os.environ["MTG_FORJA_FIXTURE"] = str(RAIZ / "ejemplos" / "fixture-pruebas.json")

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


def test_renderizadores():
    mazo = scryfall.resolver(LISTA, "Prueba")
    doc = motor.documento(mazo, motor.detectar(mazo), titulo="Prueba")
    for modulo in (guia, chuleta, mapa):
        html = modulo.render(doc)
        assert html.startswith("<!DOCTYPE html>")
        assert "Prueba" in html
