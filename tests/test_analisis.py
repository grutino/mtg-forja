"""El análisis lo escribe un experto; la forja solo comprueba y dibuja.

Corren sin red, con el fixture de ejemplo.
"""
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
os.environ["MTG_FORJA_FIXTURE"] = str(RAIZ / "ejemplos" / "fixture-pruebas.json")

from mtg_forja import analisis as an  # noqa: E402
from mtg_forja import cli, scryfall  # noqa: E402
from mtg_forja.render import chuleta, guia, mapa  # noqa: E402

LISTA = (RAIZ / "ejemplos" / "prueba.txt").read_text(encoding="utf-8")
SIN_RULINGS = lambda c: []  # noqa: E731
RULINGS_KARN = {"Karn, the Great Creator": [
    "Karn's first ability affects only artifacts on the battlefield."]}


def rulings(c):
    return RULINGS_KARN.get(c.nombre, [])


def mazo():
    return scryfall.resolver(LISTA, "Prueba")


def analisis_bueno():
    m = mazo()
    roles = {c.nombre: {"rol": "motor", "estrategia": "x"} for c in m.principal if not c.es_tierra}
    return {
        "titulo": "Prueba",
        "revision_experta": {"revisor": "Claude Opus 5.5", "fecha": "2026-10-23",
                             "veredicto": "Mazo de control con plan alternativo.",
                             "fuentes": ["f1"]},
        "fuentes": [{"id": "f1", "titulo": "Lista de referencia",
                     "url": "https://example.org/lista"}],
        "cartas": roles,
        "sinergias": [{
            "nombre": "Tierras que sobreviven a tu propio Wildfire",
            "tipo": "sinergia", "fuerza": 3, "turno": "T3",
            "piezas": ["Cleansing Wildfire", "Rustvale Bridge"],
            "resumen": "Destruyes tu tierra indestructible: no muere, pero robas.",
            "citas": [
                {"carta": "Cleansing Wildfire", "texto": "Destroy target land."},
                {"carta": "Rustvale Bridge", "texto": "Rustvale Bridge is indestructible."},
            ],
        }],
    }


def test_un_analisis_bien_citado_pasa():
    assert an.validar(mazo(), analisis_bueno(), SIN_RULINGS) == []


def test_sin_revision_experta_no_sale_nada():
    a = analisis_bueno()
    del a["revision_experta"]
    errores = an.validar(mazo(), a, SIN_RULINGS)
    assert any("revision_experta" in e for e in errores)


def test_la_revision_tiene_que_valorar_no_solo_firmar():
    a = analisis_bueno()
    a["revision_experta"]["veredicto"] = ""
    assert any("veredicto" in e for e in an.validar(mazo(), a, SIN_RULINGS))


def test_una_cita_inventada_se_rechaza():
    """El caso que originó el cambio: atribuir a una carta algo que no dice."""
    a = analisis_bueno()
    a["sinergias"][0]["citas"][1]["texto"] = "you gain life for each card in your hand"
    errores = an.validar(mazo(), a, SIN_RULINGS)
    assert any("no aparece literal" in e for e in errores)
    assert any("no tiene ninguna cita" in e for e in errores)


def test_cada_pieza_necesita_su_propia_cita():
    a = analisis_bueno()
    a["sinergias"][0]["citas"].pop()
    errores = an.validar(mazo(), a, SIN_RULINGS)
    assert any("Rustvale Bridge" in e and "no tiene ninguna cita" in e for e in errores)


def test_una_carta_que_no_esta_en_el_mazo_se_rechaza():
    a = analisis_bueno()
    a["sinergias"][0]["piezas"].append("Lightning Bolt")
    assert any("Lightning Bolt" in e for e in an.validar(mazo(), a, SIN_RULINGS))


def test_un_ruling_oficial_vale_como_cita():
    a = analisis_bueno()
    a["sinergias"].append({
        "nombre": "Karn no apaga tus propios artefactos", "tipo": "aviso", "fuerza": 2,
        "piezas": ["Karn, the Great Creator"], "resumen": "Solo los del rival.",
        "citas": [{"carta": "Karn, the Great Creator",
                   "texto": "affects only artifacts on the battlefield"}]})
    assert an.validar(mazo(), a, rulings) == []
    assert a["sinergias"][1]["citas"][0]["origen"] == "ruling"


def test_las_comillas_tipograficas_no_invalidan_una_cita_literal():
    a = analisis_bueno()
    a["sinergias"][0]["citas"][0]["texto"] = "Destroy  target\nland."
    assert an.validar(mazo(), a, SIN_RULINGS) == []


def test_una_fuente_externa_necesita_url():
    a = analisis_bueno()
    a["fuentes"][0]["url"] = "lo vi en un foro"
    errores = an.validar(mazo(), a, SIN_RULINGS)
    assert any("url" in e for e in errores)
    assert any("'f1'" in e for e in errores)


def test_el_rol_de_cada_carta_lo_pone_el_experto():
    a = analisis_bueno()
    del a["cartas"]["Sunfall"]
    assert any("falta el rol de «Sunfall»" in e for e in an.validar(mazo(), a, SIN_RULINGS))


def test_los_datos_para_el_experto_no_traen_interpretaciones():
    d = an.datos_para_experto(mazo(), rulings)
    assert "sinergias" not in d
    karn = next(c for c in d["cartas"] if c["nombre"].startswith("Karn"))
    assert karn["rulings"] and karn["oraculo"]
    assert "rol" not in karn


def test_el_documento_lleva_firma_citas_y_fuentes():
    m, a = mazo(), analisis_bueno()
    assert an.validar(m, a, SIN_RULINGS) == []
    doc = an.documento(m, a)
    assert doc["revision_experta"]["revisor"] == "Claude Opus 5.5"
    assert doc["forjado"]["citas_verificadas"] == 2
    assert doc["sinergias"][0]["evidencia"]["Rustvale Bridge"].endswith("indestructible.")
    for r in (guia, chuleta, mapa):
        html = r.render(doc)
        assert "Claude Opus 5.5" in html


def test_el_cli_no_forja_un_analisis_invalido(tmp_path, monkeypatch):
    monkeypatch.setattr(scryfall, "rulings", SIN_RULINGS)
    lista = tmp_path / "mazo.txt"
    lista.write_text(LISTA, encoding="utf-8")
    malo = analisis_bueno()
    malo["sinergias"][0]["citas"][0]["texto"] = "Exile all opponents."
    (tmp_path / "a.json").write_text(json.dumps(malo), encoding="utf-8")
    salida = tmp_path / "salida"
    assert cli.main(["forjar", str(lista), "-a", str(tmp_path / "a.json"),
                     "-o", str(salida)]) == 2
    assert not salida.exists()

    (tmp_path / "b.json").write_text(json.dumps(analisis_bueno()), encoding="utf-8")
    assert cli.main(["forjar", str(lista), "-a", str(tmp_path / "b.json"),
                     "-o", str(salida)]) == 0
    assert {p.name for p in salida.iterdir()} == {
        "prueba.html", "documento.json", "arena.txt"}


def test_el_cli_viejo_explica_el_cambio(tmp_path, capsys):
    lista = tmp_path / "mazo.txt"
    lista.write_text(LISTA, encoding="utf-8")
    assert cli.main([str(lista)]) == 1
    assert "experto" in capsys.readouterr().err
