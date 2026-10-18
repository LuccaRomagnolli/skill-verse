"""Testes dos scripts das skills de software: AutoCAD (prancha), Revit (unidades, lançamento),
SOLIDWORKS (perfis)."""
import json
import math
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EC = ROOT / "catalog/engenharia-civil"
for s in ("autocad-assistente", "revit-assistente", "solidworks-assistente"):
    sys.path.insert(0, str(EC / s / "scripts"))

import lancamento  # noqa: E402
import perfis  # noqa: E402
import prancha  # noqa: E402
import revit_unidades  # noqa: E402


def run(path, *args, check=True):
    return subprocess.run([sys.executable, str(path), *args], capture_output=True, text=True, check=check)


# =============================================================== AutoCAD — prancha

def test_fator_e_alturas_de_texto():
    assert prancha.fator(50, "cm") == 5.0          # 1 mm de papel a 1:50 = 5 cm no modelo
    assert prancha.fator(100, "m") == pytest.approx(0.1)
    assert prancha.fator(1, "mm") == 1.0


def test_cabe_prefere_maior_escala_e_menor_formato():
    ops = prancha.cabe(18.5, 12.0, "m")
    assert ops[0]["escala"] == "1:20" and ops[0]["formato"] == "A0"
    a50 = [o for o in ops if o["escala"] == "1:50"]
    assert a50[0]["formato"] == "A2"               # menor formato que cabe em 1:50
    assert all(o["ocupacao"] <= 0.85 + 1e-9 for o in ops)


def test_prancha_gera_moldura_carimbo_e_dxf(tmp_path):
    dxf, ops = tmp_path / "a1.dxf", tmp_path / "a1.json"
    r = run(EC / "autocad-assistente/scripts/prancha.py", "--formato", "A1", "--escala", "50", "--unidade", "cm",
            "--obra", "Casa", "--conteudo", "Conteúdo", "--rt", "Eng. X", "--registro", "CREA 1", "--folha", "1/2", "--revisao", "A",
            "--dxf", str(dxf), "--ops", str(ops))
    info = json.loads(r.stdout)
    assert info["papel_mm"] == [841, 594] and info["moldura_desenho"] == [125.0, 50.0, 4155.0, 2920.0]
    assert info["alturas_texto"]["2.5 mm"] == 12.5
    txt = dxf.read_text(encoding="cp1252")
    assert txt.startswith("0\nSECTION") and txt.rstrip().endswith("EOF") and "PRA-CARIMBO" in txt
    assert "$INSUNITS\n70\n5" in txt
    assert "Arial.ttf" in txt and "7\nSV-TEXT" in txt
    assert "Conte\\U+00FAdo" in txt
    lista = json.loads(ops.read_text(encoding="utf-8"))
    assert {o["tool"] for o in lista} == {"layer", "entity", "annotation", "view"}
    assert any(o.get("operation") == "create_line" for o in lista)
    assert any("CREA 1" in (o.get("data") or {}).get("text", "") for o in lista)


def test_prancha_vertical_inverte_papel():
    a = Namespace(formato="A3", vertical=True, escala=1, unidade="mm", obra="", local="", cliente="", conteudo="",
                  rt="", registro="", art="", folha="1/1", revisao="", data="01/01/2026")
    assert prancha.geometria(a)["info"]["papel_mm"] == [297, 420]


# =============================================================== Revit

def test_unidades_revit():
    assert revit_unidades.converter(1, "ft", "mm") == pytest.approx(304.8)
    assert revit_unidades.converter(3.5, "m", "ft") == pytest.approx(3500 / 304.8)
    assert revit_unidades.converter(1, "m3", "ft3") == pytest.approx(35.3146667, rel=1e-6)
    assert revit_unidades.converter(180, "graus", "rad") == pytest.approx(math.pi)
    with pytest.raises(ValueError):
        revit_unidades.converter(1, "m", "m2")


def _exemplo():
    return json.loads((EC / "revit-assistente/assets/lancamento.exemplo.json").read_text(encoding="utf-8"))


def test_lancamento_exemplo_ordem_unidades_e_tipos():
    r = lancamento.gerar(_exemplo())
    tools = [o["tool"] for o in r["ops"]]
    assert tools == ["create_level", "send_code_to_revit", "create_point_based_element",
                     "create_line_based_element", "create_surface_based_element"]
    niveis = r["ops"][0]["args"]["data"]
    assert [n["elevation"] for n in niveis] == [-1000.0, 0.0, 3060.0]
    p1 = r["ops"][2]["args"]["data"][0]
    assert p1["typeId"] == "$tipo:P 20x40" and p1["height"] == 4060.0 and p1["baseLevel"] == -1000.0
    v1 = r["ops"][3]["args"]["data"][0]
    assert v1["locationLine"]["p1"]["x"] == 8500.0 and v1["thickness"] == 150.0 and v1["height"] == 450.0
    laje = r["ops"][4]["args"]["data"][0]
    assert "typeId" not in laje and laje["thickness"] == 100.0 and len(laje["boundary"]["outerLoop"]) == 4
    assert {t["nome"] for t in r["tipos"]} == {"P 20x40", "P 20x50", "V 15x45", "V 15x40"}
    cs = r["tipos_csharp"]
    assert "Garantir(BuiltInCategory.OST_StructuralColumns, \"P 20x50\", 200.0, 500.0)" in cs
    assert "return new { tipos = res, avisos = avisos };" in cs and "Transaction" not in cs
    assert r["ops"][1]["requer_confirmacao"] and "Grid.Create" in r["ops"][1]["args"]["code"]


def test_lancamento_eixos_uniformes_usam_create_grid():
    d = {"eixos": {"x": [{"nome": "1", "pos_m": 0}, {"nome": "2", "pos_m": 5}, {"nome": "3", "pos_m": 10}],
                   "y": [{"nome": "A", "pos_m": 0}, {"nome": "B", "pos_m": 4}]}}
    g = lancamento.gerar(d)["ops"][0]
    assert g["tool"] == "create_grid"
    assert g["args"]["xCount"] == 3 and g["args"]["xSpacing"] == 5000.0 and g["args"]["xNamingStyle"] == "numeric"
    assert g["args"]["yStartLabel"] == "A" and g["args"]["yNamingStyle"] == "alphabetic"


def test_lancamento_avisos():
    d = {"niveis": [{"nome": "T", "cota_m": 0}],
         "pilares": [{"nome": "P1", "x_m": 0, "y_m": 0, "b_cm": 20, "h_cm": 20, "base": "T", "topo": "X"}],
         "vigas": [{"nome": "V1", "de": [1, 1], "ate": [1, 1], "b_cm": 15, "h_cm": 40, "nivel": "T"}]}
    av = lancamento.gerar(d)["avisos"]
    assert any("V1" in a for a in av) and any("X" in a for a in av)


def test_lancamento_marcas_csharp():
    cs = lancamento.marcas_csharp({"P1": 123456, "V1": 987})
    assert 'M("123456", "P1");' in cs and "ALL_MODEL_MARK" in cs and "new ElementId(" not in cs


def test_lancamento_cli(tmp_path):
    out = tmp_path / "ops.json"
    r = run(EC / "revit-assistente/scripts/lancamento.py", str(EC / "revit-assistente/assets/lancamento.exemplo.json"),
            "--saida", str(out))
    assert json.loads(r.stdout)["ops"] == 5 and json.loads(out.read_text(encoding="utf-8"))["tipos_csharp"]


# =============================================================== SOLIDWORKS — perfis

def _ns(**kw):
    base = dict(plano="Front", densidade=7850.0, material="ASTM A36 Steel", nome=None, comprimento=None, furos=None)
    base.update(kw)
    return Namespace(**base)


def test_perfil_I_area_e_massa():
    r = perfis.calcular("I", _ns(d=200, bf=100, tw=5.6, tf=8.5, comprimento=6000))
    area = 2 * 100 * 8.5 + (200 - 2 * 8.5) * 5.6
    assert r["area_mm2"] == pytest.approx(area)
    assert r["massa_linear_kg_m"] == pytest.approx(area * 1e-6 * 7850, abs=1e-3)
    assert r["massa_kg"] == pytest.approx(area * 6000 * 1e-9 * 7850, abs=1e-3)
    seq = [o["tool"] for o in r["ops"]]
    assert seq[:3] == ["solidworks_new_part", "solidworks_create_sketch", "solidworks_sketch_profile"]
    assert seq[-1] == "solidworks_get_mass_properties"
    assert r["ops"][3]["args"]["depth"] == 6000


def test_perfis_U_Ue_L_tubos_barra():
    assert perfis.calcular("U", _ns(d=150, bf=50, tw=5, tf=8, comprimento=1000))["area_mm2"] == pytest.approx(
        2 * 50 * 8 + (150 - 16) * 5)
    ue = perfis.calcular("Ue", _ns(d=150, bf=60, c=20, t=2, comprimento=1000))["area_mm2"]
    assert ue == pytest.approx((150 + 2 * 60 + 2 * 20 - 4 * 2) * 2)   # linha média aproximada por cantos vivos
    assert perfis.calcular("L", _ns(b1=50, b2=50, t=5, comprimento=1000))["area_mm2"] == pytest.approx(475)
    tr = perfis.calcular("tubo-ret", _ns(b=100, h=50, t=3, comprimento=1000))
    assert tr["area_mm2"] == pytest.approx(100 * 50 - 94 * 44) and sum(o["tool"] == "solidworks_sketch_rectangle"
                                                                     for o in tr["ops"]) == 2
    tc = perfis.calcular("tubo-cir", _ns(D=100, t=5, comprimento=1000))
    assert tc["area_mm2"] == pytest.approx(math.pi / 4 * (100 ** 2 - 90 ** 2), abs=0.01)
    assert perfis.calcular("barra", _ns(D=20, comprimento=1000))["massa_linear_kg_m"] == pytest.approx(2.466, abs=1e-3)


def test_chapa_com_furos_e_validacoes():
    r = perfis.calcular("chapa", _ns(b=300, h=300, t=16, furos="-110,-110,22;110,110,22"))
    assert r["area_mm2"] == pytest.approx(300 * 300 - 2 * math.pi / 4 * 22 ** 2)
    assert r["ops"][-3]["args"]["depth"] == 16      # extrusão = espessura (antes de material e massa)
    assert sum(o["tool"] == "solidworks_sketch_circle" for o in r["ops"]) == 2
    with pytest.raises(ValueError, match="sai da chapa"):
        perfis.calcular("chapa", _ns(b=100, h=100, t=10, furos="45,0,20"))
    with pytest.raises(ValueError):
        perfis.calcular("I", _ns(d=100, bf=100, tw=5, tf=60, comprimento=1000))
    with pytest.raises(ValueError, match="comprimento"):
        perfis.calcular("L", _ns(b1=50, b2=50, t=5))


def test_perfis_cli_exige_parametros():
    r = run(EC / "solidworks-assistente/scripts/perfis.py", "I", "--d", "200", check=False)
    assert r.returncode != 0 and "faltam" in r.stderr
