"""Testes dos scripts das skills de software: AutoCAD (prancha), Revit (unidades, lançamento),
SOLIDWORKS (perfis) e TQS (lógica pura + API simulada, já que o TQS só existe no Windows)."""
import json
import math
import subprocess
import sys
import types
from argparse import Namespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EC = ROOT / "catalog/engenharia-civil"
for s in ("autocad-assistente", "revit-assistente", "solidworks-assistente", "tqs-assistente"):
    sys.path.insert(0, str(EC / s / "scripts"))

import lancamento  # noqa: E402
import perfis  # noqa: E402
import prancha  # noqa: E402
import revit_unidades  # noqa: E402
import tqs_comum  # noqa: E402
import tqs_dwg  # noqa: E402
import tqs_edificio  # noqa: E402
import tqs_modelo  # noqa: E402
import tqs_processar  # noqa: E402
import tqs_unidades  # noqa: E402


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
            "--obra", "Casa", "--rt", "Eng. X", "--registro", "CREA 1", "--folha", "1/2", "--revisao", "A",
            "--dxf", str(dxf), "--ops", str(ops))
    info = json.loads(r.stdout)
    assert info["papel_mm"] == [841, 594] and info["moldura_desenho"] == [125.0, 50.0, 4155.0, 2920.0]
    assert info["alturas_texto"]["2.5 mm"] == 12.5
    txt = dxf.read_text(encoding="cp1252")
    assert txt.startswith("0\nSECTION") and txt.rstrip().endswith("EOF") and "PRA-CARIMBO" in txt
    assert "$INSUNITS\n70\n5" in txt
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


# =============================================================== TQS — lógica pura

def test_cotas_das_plantas_com_repeticao():
    # Fundação (−1,5), Térreo h=1,5, Tipo h=3,0 ×4 (pisos em 3, 6, 9 e 12), Cobertura h=3,0 acima do último tipo
    cotas = tqs_comum.cotas_das_plantas(-1.5, [0.0, 1.5, 3.0, 3.0], [1, 1, 4, 1])
    assert cotas == [-1.5, 0.0, 3.0, 15.0]


def test_fck_parse():
    assert tqs_comum.fck("C30") == 30 and tqs_comum.fck(25) == 25 and tqs_comum.fck("c25") == 25
    assert tqs_comum.fck("xx") is None and tqs_comum.fck(None) is None


def test_unidades_tqs():
    assert tqs_unidades.converter(1, "tf", "kN") == pytest.approx(9.80665)
    assert tqs_unidades.converter(0.5, "tf/m2", "kN/m2") == pytest.approx(4.903325)
    assert tqs_unidades.converter(2, "tfm", "kNm") == pytest.approx(19.6133)
    assert tqs_unidades.converter(30, "MPa", "kgf/cm2") == pytest.approx(305.915, rel=1e-4)
    with pytest.raises(ValueError):
        tqs_unidades.converter(1, "tf", "m")


def test_conferir_caa_fck_e_cobrimentos():
    dados = {"materials": {"environmentalClass": 1, "beamConcreteStrength": "C25", "columnConcreteStrength": "C20",
                           "foundationConcreteStrength": "C30", "qualityControl": 0},
             "covers": {"beamCover": 3.0, "slabLowerCover": 2.0, "columnCover": 3.0, "foundationCover": 3.0}}
    r = tqs_edificio.conferir(dados)
    st = {i["item"]: i["status"] for i in r["itens"]}
    assert r["caa"] == "II"
    assert st["fck vigas/lajes"] == "OK" and st["fck pilares"] == "ALERTA"
    assert st["cobrimento slabLowerCover"] == "ALERTA" and st["cobrimento beamCover"] == "OK"
    # ficha do projeto em CAA III: prevalece e acusa divergência
    r3 = tqs_edificio.conferir(dados, {"caa": {"classe": "III"}})
    assert r3["caa"] == "III" and r3["itens"][0]["status"] == "ALERTA"
    assert {i["item"]: i["status"] for i in r3["itens"]}["cobrimento beamCover"] == "ALERTA"
    # controle de qualidade: Δc = 5 mm reduz o mínimo
    dados["materials"]["qualityControl"] = 1
    assert {i["item"]: i["status"] for i in tqs_edificio.conferir(dados)["itens"]}["cobrimento slabLowerCover"] == "OK"


def test_conferir_cli_fora_do_windows(tmp_path):
    f = tmp_path / "ed.json"
    f.write_text(json.dumps({"materials": {"caa": "I", "beamConcreteStrength": "C20"}, "covers": {}}))
    r = run(EC / "tqs-assistente/scripts/tqs_edificio.py", "conferir", "--json", str(f), "--contexto", "nao-existe.json")
    assert json.loads(r.stdout)["resumo"]["OK"] >= 1


def test_scripts_tqs_sem_tqs_dao_erro_claro():
    r = run(EC / "tqs-assistente/scripts/tqs_edificio.py", "ler", "--edificio", "X", check=False)
    assert r.returncode == 2 and "tqs_ambiente.py" in json.loads(r.stdout)["erro"]
    amb = json.loads(run(EC / "tqs-assistente/scripts/tqs_ambiente.py").stdout)
    assert amb["bits"] in (32, 64) and amb["recomendacoes"]


def test_processar_plano_e_execucao_simulada():
    plano = tqs_processar.montar_plano(["A", "B"], "completo", {"beams": 2}, True, False)
    assert [t["tarefa"] for t in plano] == ["TaskFolder", "TaskGlobalProc", "TaskRebarSchedule"] * 2
    assert plano[1]["kwargs"]["beams"] == 2 and plano[1]["kwargs"]["columns"] == 2
    with pytest.raises(ValueError):
        tqs_processar.montar_plano(["A"], "esforcos", {"vigas": 1}, False, False)

    chamadas = []

    class Job:
        def EnterTask(self, t):
            chamadas.append(t)

        def Execute(self):
            chamadas.append("EXEC")

    class TaskFolder:
        FOLDER_FRAMES = 7

        def __init__(self, ed, pasta):
            self.v = ("pasta", ed, pasta)

    fake = types.SimpleNamespace(Job=Job, TaskFolder=TaskFolder,
                                 TaskGlobalProc=lambda **kw: ("global", kw), TaskRebarSchedule=lambda: ("ferros",))
    tqs_processar.executar(fake, plano[:3])
    assert chamadas[0].v == ("pasta", "A", 7) and chamadas[1][0] == "global" and chamadas[-1] == "EXEC"


def test_processar_cli_simula_por_padrao():
    r = run(EC / "tqs-assistente/scripts/tqs_processar.py", "--edificios", "A", "--preset", "esforcos")
    assert json.loads(r.stdout)["simulacao"] is True


# --------------------------------------------------------------- TQS — API simulada

class _Obj(types.SimpleNamespace):
    pass


def _fake_build():
    fp = _Obj(floorsPlanNumber=3)
    nomes, alturas, reps, classes = ["Fundacao", "Terreo", "Tipo"], [0.0, 1.5, 2.88], [1, 1, 5], [0, 2, 6]
    fp.GetName = lambda i: nomes[i]
    fp.GetTitle = lambda i: nomes[i].upper()
    fp.GetClass = lambda i: classes[i]
    fp.GetFloorHeight = lambda i: alturas[i]
    fp.GetRepetition = lambda i: reps[i]
    loads = _Obj(GetLoad=lambda pre: ("Permanente", 0, 0, 0, 0, 1.0, 1, 1.4, 0, 0, 0, 1, 1, 0))
    b = _Obj(project=_Obj(projectTitle="Ed", floorHeight=-1.5, concreteCode=3), model=_Obj(structuralModel=1),
             materials=_Obj(environmentalClass=1, beamConcreteStrength="C25", columnConcreteStrength="C30",
                            foundationConcreteStrength="C30", qualityControl=0),
             covers=_Obj(beamCover=3.0, columnCover=3.0, slabLowerCover=2.5), floorsplan=fp, loads=loads)
    mod = types.SimpleNamespace(ICLFUN=0, ICLTER=2, ICLTIP=6, PREFIXOPERM=11)
    return mod, b


def test_edificio_ler_com_api_simulada():
    mod, b = _fake_build()
    d = tqs_edificio.ler(mod, b)
    assert [p["classe"] for p in d["plantas"]] == ["FUN", "TER", "TIP"]
    assert [p["cota_m"] for p in d["plantas"]] == [-1.5, 0.0, 2.88]
    assert d["materials"]["caa"] == "II" and d["carregamentos"]["PERM"]["gamafd"] == 1.4
    assert tqs_edificio.conferir(d)["resumo"]["ALERTA"] == 0


def test_edificio_aplicar_so_campos_permitidos():
    _, b = _fake_build()
    feitas = tqs_edificio.aplicar(b, {"materials": {"beamConcreteStrength": "C30"}})
    assert b.materials.beamConcreteStrength == "C30" and feitas[0]["antes"] == "C25"
    with pytest.raises(ValueError):
        tqs_edificio.aplicar(b, {"materials": {"qualquerCoisa": 1}})
    with pytest.raises(ValueError):
        tqs_edificio.aplicar(b, {"floorsplan": {}})


def test_dwg_resumo_com_iterador_simulado():
    itens = [(1, dict(x1=0, y1=0, x2=100, y2=50, level=10)), (2, dict(x1=10, y1=20, text="P1 20x50", level=20)),
             (3, dict(xc=200, yc=-10, level=10)), (0, {})]

    class It:
        def Begin(self):
            self.i = -1

        def Next(self):
            self.i += 1
            t, attrs = itens[self.i]
            for k in ("x1", "y1", "x2", "y2", "xc", "yc", "text", "level"):
                setattr(self, k, attrs.get(k))
            return t

    mod = types.SimpleNamespace(DWGTYPE_EOF=0, DWGTYPE_LINE=1, DWGTYPE_TEXT=2, DWGTYPE_CIRCLE=3)
    r = tqs_dwg.resumir(mod, types.SimpleNamespace(iterator=It()))
    assert r["por_tipo"] == {"LINE": 1, "TEXT": 1, "CIRCLE": 1}
    assert r["por_nivel"] == {"10": 2, "20": 1}
    assert r["extensao_cm"] == [0, -10, 200, 50] and r["textos"][0]["texto"] == "P1 20x50"


def test_dwg_desenhar_ops():
    log = []

    class Draw:
        def __getattr__(self, nome):
            return lambda *a: log.append((nome, a))

    dwg = types.SimpleNamespace(settings=types.SimpleNamespace(scale=1), draw=Draw(),
                                dim=types.SimpleNamespace(DimHorizontal=lambda *a: log.append(("DimH", a))))
    n = tqs_dwg.desenhar(dwg, [{"t": "nivel", "n": 5}, {"t": "linha", "p": [0, 0, 1, 1]},
                               {"t": "polilinha", "pts": [[0, 0], [1, 0], [1, 1]]},
                               {"t": "texto", "p": [0, 0], "s": "V1"}, {"t": "cota_h", "p": [0, 0, 1, 0, 0, -1]}], 50)
    assert n == 4 and dwg.settings.scale == 50 and dwg.draw.level == 5
    assert ("Line", (0, 0, 1, 1)) in log and ("Text", (0, 0, 0.25, 0.0, "V1")) in log
    with pytest.raises(ValueError):
        tqs_dwg.desenhar(dwg, [{"t": "xyz"}], 50)


def test_modelo_para_revit():
    quad = [[-10, -25], [10, -25], [10, 25], [-10, 25]]                 # 20×50 centrado em (0,0) cm
    modelo = {"edificio": "Ed", "plantas": [
        {"nome": "Fundacao", "pilares": [{"numero": 1, "titulo": "", "tipo_secao": "R", "b1_cm": 20, "h1_cm": 50,
                                          "insercao_cm": [0, 0], "insercao_por": "centro", "poligono_cm": quad}],
         "vigas": [], "lajes": []},
        {"nome": "Terreo ", "pilares": [
            {"numero": 1, "titulo": "", "tipo_secao": "R", "b1_cm": 20, "h1_cm": 50, "angulo_graus": 0,
             "insercao_cm": [999, 999], "insercao_por": "canto", "poligono_cm": [[p[0] + 400, p[1] + 300] for p in quad]},
            {"numero": 2, "titulo": "P2A", "tipo_secao": "L", "b1_cm": 60, "h1_cm": 60, "insercao_cm": [0, 0]}],
         "vigas": [{"numero": 3, "titulo": "", "nos_cm": [[0, 0], [400, 0], [850, 0]],
                    "trechos": [{"de": 0, "ate": 1, "b_cm": 15, "h_cm": 45}, {"de": 1, "ate": 2, "b_cm": 15, "h_cm": 50}]}],
         "lajes": [{"numero": 1, "h_cm": 10}]}]}
    ed = {"plantas": [{"nome": "Fundacao", "cota_m": -1.0, "repeticoes": 1},
                      {"nome": "Terreo", "cota_m": 0.0, "repeticoes": 3}]}
    r = tqs_modelo.para_revit(modelo, ed)
    assert r["niveis"] == [{"nome": "Fundacao", "cota_m": -1.0}, {"nome": "Terreo", "cota_m": 0.0}]
    assert r["pilares"] == [{"nome": "P1", "x_m": 4.0, "y_m": 3.0, "b_cm": 20, "h_cm": 50, "rot_graus": 0,
                             "base": "Fundacao", "topo": "Terreo"}]
    assert [v["h_cm"] for v in r["vigas"]] == [45, 50] and r["vigas"][1]["ate"] == [8.5, 0.0]
    texto = " ".join(r["avisos"])
    assert "P2A" in texto and "repete 3" in texto and "laje" in texto
    # e o resultado alimenta direto o lançamento do Revit
    ops = lancamento.gerar(r)["ops"]
    assert [o["tool"] for o in ops] == ["create_level", "create_point_based_element", "create_line_based_element"]


def test_centroide():
    assert tqs_modelo.centroide([[0, 0], [2, 0], [2, 2], [0, 2]]) == pytest.approx((1, 1))
    assert tqs_modelo.centroide([[0, 0], [1, 1]]) is None
