"""Casos geométricos e integração de prévia dos cortes arquitetônicos."""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "catalog/engenharia-civil/planta-arquitetonica"
sys.path.insert(0, str(SKILL / "scripts"))
import planta  # noqa: E402


def exemplo():
    return json.loads((SKILL / "assets/planta.exemplo.json").read_text(encoding="utf-8"))


def test_corte_intercepta_janela_porta_paredes_e_pisos(tmp_path):
    d = exemplo()
    manifesto = planta.gerar(d, tmp_path)
    assert manifesto["projeto"]["revisao"] == "A"
    assert not manifesto["avisos"]
    dxf = (tmp_path / "corte-A-A.dxf").read_text(encoding="cp1252")
    assert "$INSUNITS\n70\n6" in dxf
    assert "ARQ-PAREDE" in dxf and "ARQ-PISO" in dxf and "ARQ-NIVEL" in dxf
    g, _ = planta.corte(d, d["cortes"][0], *planta.validar(d))
    paredes = [e["p"] for e in g["entidades"] if e["layer"] == "ARQ-PAREDE" and e["t"] == "rect"]
    assert [round(r[3] - r[1], 2) for r in paredes] == [.9, .9, .9]
    assert len([e for e in g["entidades"] if e["layer"] == "ARQ-PISO" and e["t"] == "rect"]) == 2


def test_previa_bim_converte_unidades_e_exige_mapeamento(tmp_path):
    planta.gerar(exemplo(), tmp_path)
    plano = json.loads((tmp_path / "planos-bim.json").read_text())
    revit = plano["revit"]
    assert revit[0]["args"]["data"][1]["elevation"] == 3000
    parede = revit[1]["args"]["data"][0]
    assert parede["thickness"] == 150 and parede["height"] == 3000
    janela = revit[-1]["args"]["data"][0]
    assert janela["hostWallId"] == "$parede:PA-S" and janela["typeId"] == "$tipo:J1"
    arch = plano["archicad"]
    paredes = next(o for o in arch if o["tool"] == "execute_write_api_command" and o["args"]["name"] == "CreateWalls")
    assert paredes["args"]["confirm"] is False
    assert paredes["args"]["params"]["wallsData"][0]["floorIndex"] == "$pavimento:Terreo"
    janelas = next(o for o in arch if o["tool"] == "execute_write_api_command" and o["args"]["name"] == "CreateWindows")
    assert janelas["args"]["params"]["windowsData"][0]["centerOffset"] == 0


def test_calibracao_pdf_imagem_e_abertura_em_pixels():
    d = json.loads((SKILL / "assets/planta-pixels.exemplo.json").read_text(encoding="utf-8"))
    out = planta.calibrar(d, [100, 100], [500, 100], 4, controle_px=[500, 100, 500, 400], controle_m=3)
    assert out["paredes"][0]["ate"] == [4, 0]
    assert out["paredes"][1]["ate"] == [4, -3]
    assert out["aberturas"][0]["centro_m"] == 2
    assert out["aberturas"][0]["largura_m"] == 1.2
    assert out["fonte"]["calibracao"]["m_por_px"] == .01
    assert out["fonte"]["calibracao"]["segunda_medida_conferida"]["desvio_relativo"] == 0
    assert d["unidade"] == "px"
    with pytest.raises(ValueError, match="segunda medida diverge"):
        planta.calibrar(d, [100, 100], [500, 100], 4, controle_px=[500, 100, 500, 400], controle_m=2)


def test_rejeita_abertura_fora_da_parede_e_corte_de_comprimento_zero():
    d = exemplo()
    d["aberturas"][0]["centro_m"] = 3.9
    with pytest.raises(ValueError, match="fora da parede"):
        planta.validar(d)
    d = exemplo()
    d["cortes"][0]["ate"] = copy.deepcopy(d["cortes"][0]["de"])
    with pytest.raises(ValueError, match="comprimento zero"):
        planta.validar(d)


def test_extracao_controlada_de_layer_dxf_e_unidade(tmp_path):
    cad = planta._cad()
    g = {"entidades": [{"t": "line", "layer": "ARQ-EIXO-PAREDE", "p": [0, 0, 400, 0]},
                       {"t": "line", "layer": "OUTRO", "p": [0, 20, 400, 20]}]}
    path = tmp_path / "planta.dxf"
    path.write_text(cad.para_dxf([g], [("ARQ-EIXO-PAREDE", 1), ("OUTRO", 2)], 5), encoding="cp1252")
    d = planta.extrair_dxf(path, "ARQ-EIXO-PAREDE", "cm", "Obra", "A", "Terreo", 0, 3, .15,
                           [["A-A", "2", "-1", "2", "1"]])
    assert len(d["paredes"]) == 1 and d["paredes"][0]["ate"] == [4, 0]
    assert d["fonte"]["insunits"] == 5
    with pytest.raises(ValueError, match="diverge"):
        planta.extrair_dxf(path, "ARQ-EIXO-PAREDE", "m", "Obra", "A", "Terreo", 0, 3, .15,
                           [["A-A", "2", "-1", "2", "1"]])
    curved = path.read_text(encoding="cp1252").replace("0\nLINE\n8\nARQ-EIXO-PAREDE", "0\nARC\n8\nARQ-EIXO-PAREDE", 1)
    path.write_text(curved, encoding="cp1252")
    with pytest.raises(ValueError, match="converta/revise"):
        planta.extrair_dxf(path, "ARQ-EIXO-PAREDE", "cm", "Obra", "A", "Terreo", 0, 3, .15,
                           [["A-A", "2", "-1", "2", "1"]])
