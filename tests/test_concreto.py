"""Testes dos scripts de concreto armado contra soluções fechadas e referências clássicas."""
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "catalog/engenharia-civil/concreto-armado-nbr6118/scripts"
sys.path.insert(0, str(SCRIPTS))

from nbr6118 import (Aco, Concreto, as_minima_flexao, camadas_retangulo, cisalhamento_modelo1,  # noqa: E402
                     escolher_barras, esforcos_secao, flexao_simples, momento_resistente, rho_min)
from placa import resolver_refinado  # noqa: E402


def run(script, *args):
    out = subprocess.run([sys.executable, str(SCRIPTS / script), *args, "--formato", "json"],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


# --------------------------------------------------------------- materiais

def test_materiais_c25():
    c = Concreto(25)
    assert c.fcd == pytest.approx(17.857, rel=1e-3)
    assert c.fctm == pytest.approx(2.565, rel=1e-3)
    assert c.Eci == pytest.approx(28000, rel=1e-3)
    assert c.Ecs == pytest.approx(24150, rel=1e-3)


def test_parametros_alta_resistencia():
    c = Concreto(70)
    assert c.alpha_c == pytest.approx(0.765)
    assert c.eta_c == pytest.approx((40 / 70) ** (1 / 3))
    assert c.sigma(c.eps_cu) == pytest.approx(c.alpha_c * c.eta_c * c.fcd)
    assert c.lam == pytest.approx(0.75)
    assert c.xd_lim == 0.35


def test_rho_min_interpola():
    assert rho_min(30) == pytest.approx(0.0015)
    assert rho_min(37.5) == pytest.approx((0.164 + 0.179) / 2 / 100)


# --------------------------------------------------------------- vigas

def test_flexao_simples_solucao_fechada():
    # bw = 20, d = 45, C20, Md = 140 kN·m
    r = flexao_simples(140, 20, 50, 45, Concreto(20), Aco())
    fcd = 20 / 1.4
    x = 450 / 0.8 * (1 - math.sqrt(1 - 2 * 140e6 / (0.85 * fcd * 200 * 450 ** 2)))
    As = 140e6 / (500 / 1.15 * (450 - 0.4 * x)) / 100
    assert r["As_cm2"] == pytest.approx(As, rel=1e-6)
    assert r["As2_cm2"] == 0


def test_flexao_c70_inclui_eta_c():
    c = Concreto(70)
    r = flexao_simples(250, 20, 50, 45, c, Aco())
    alpha_efetivo = c.alpha_c * (40 / 70) ** (1 / 3)
    x = 450 / c.lam * (1 - math.sqrt(1 - 2 * 250e6 / (alpha_efetivo * c.fcd * 200 * 450 ** 2)))
    as_esperada = 250e6 / ((500 / 1.15) * (450 - c.lam * x / 2)) / 100
    assert r["As_calc_cm2"] == pytest.approx(as_esperada)
    assert r["As2_cm2"] == 0


def test_armadura_minima_para_outros_acos_e_altura_util():
    c = Concreto(25)
    as_ca50 = as_minima_flexao(20, 50, 40, c, Aco("CA-50"))
    as_ca25 = as_minima_flexao(20, 50, 40, c, Aco("CA-25"))
    as_d_menor = as_minima_flexao(20, 50, 35, c, Aco("CA-50"))
    assert as_ca25 > as_ca50
    assert as_d_menor >= as_ca50


def test_barras_sugeridas_nao_ultrapassam_cobrimento_nominal():
    opcoes = escolher_barras(15, 20, 25)
    assert opcoes and all(o["phi_mm"] <= 25 for o in opcoes)


def test_armadura_dupla_quando_excede_limite():
    r = flexao_simples(150, 15, 40, 36, Concreto(25), Aco())
    assert r["x_d"] == pytest.approx(0.45)
    assert r["As2_cm2"] > 0


def test_cisalhamento():
    r = cisalhamento_modelo1(112, 20, 45, Concreto(20), Aco())
    assert r["VRd2_kN"] == pytest.approx(0.27 * 0.92 * 20 / 1.4 * 200 * 450 / 1e3, rel=1e-6)
    assert r["Asw_s_cm2_m"] == pytest.approx((112e3 - r["Vc_kN"] * 1e3) / (0.9 * 450 * 434.78) * 10, rel=1e-3)


def test_viga_cli_biapoiada():
    r = run("viga.py", "--b", "15", "--h", "45", "--fck", "25", "--biapoiada", "--vao", "5", "--g", "12", "--q", "6")
    p = 25 * 0.15 * 0.45 + 18
    assert r["entrada"]["Mk"] == pytest.approx(p * 25 / 8)
    assert r["flexao"]["sugestoes"]


# --------------------------------------------------------------- placas (Timoshenko & Woinowsky-Krieger)

@pytest.mark.parametrize("ly,bordas,cw,cmx,cmy", [
    (1.0, "AAAA", 0.00406, 0.0479, 0.0479),
    (2.0, "AAAA", 0.01013, 0.1017, 0.0464),
    (1.0, "EEEE", 0.00126, 0.0231, 0.0231),
])
def test_placa_timoshenko(ly, bordas, cw, cmx, cmy):
    r = resolver_refinado(1.0, ly, bordas, nu=0.3)
    assert r["cw"] == pytest.approx(cw, rel=0.015)
    assert r["cmx"] == pytest.approx(cmx, rel=0.015)
    assert r["cmy"] == pytest.approx(cmy, rel=0.03)


def test_placa_engaste_borda():
    r = resolver_refinado(1.0, 1.0, "EEEE", nu=0.3)
    assert r["cneg"]["esquerda"] == pytest.approx(-0.0513, rel=0.01)
    r = resolver_refinado(1.0, 1.5, "EEEE", nu=0.3)
    assert r["cneg"]["esquerda"] == pytest.approx(-0.0757, rel=0.01)


def test_laje_uma_direcao_biengastada():
    r = run("laje.py", "--lx", "3", "--ly", "9", "--h", "10", "--q", "2", "--fck", "25", "--bordas", "EEAA")
    pd = r["cargas"]["pd"]
    assert r["positivo_x"]["m_kNm_m"] == pytest.approx(pd * 9 / 24, rel=0.02)
    assert r["negativos"]["esquerda"]["m_kNm_m"] == pytest.approx(pd * 9 / 12, rel=0.02)


def test_laje_borda_apoiada_pede_armadura_negativa():
    r = run("laje.py", "--lx", "4", "--ly", "5", "--h", "12", "--q", "2", "--fck", "25")
    assert any("19.3.3.2" in a for a in r["memoria"]["alertas"])


def test_emenda_alertas_de_balanco_e_flecha():
    r = run("laje.py", "--balanco", "1.2", "--h", "12", "--q", "2", "--fck", "30")
    alertas = " ".join(r["memoria"]["alertas"])
    assert "20.6" in alertas and "ações permanentes" in alertas
    assert "23.3" in alertas and "deslocamento total" in alertas


def test_reacoes_somam_carga_total():
    r = run("laje.py", "--lx", "4", "--ly", "5", "--h", "10", "--q", "1.5", "--fck", "25", "--bordas", "AEAE")
    reac = r["reacao_kN_m"]
    total = (reac["esquerda"] + reac["direita"]) * 5 + (reac["inferior"] + reac["superior"]) * 4
    assert total == pytest.approx(r["cargas"]["p"] * 20, rel=1e-3)


# --------------------------------------------------------------- pilares

def test_compressao_centrada():
    c, s = Concreto(25), Aco()
    N, M = esforcos_secao(1e9, 200, 400, camadas_retangulo(400, 40, 2, 2), 800, c, s)
    esperado = 0.85 * 25 / 1.4 * 200 * 400 + 800 * (210000 * 0.002 - 0.85 * 25 / 1.4)
    assert N == pytest.approx(esperado, rel=1e-4)
    assert M == pytest.approx(0, abs=1e3)


def test_flexao_pura_secao_simetrica():
    # 4 cm² por face, b = 20, h = 50, d' = 4: T = As·fyd; braço entre (d − d') e (d − 0) ⇒ 73,0 < MRd < 80,0
    m = momento_resistente(0, 200, 500, camadas_retangulo(500, 40, 2, 2), 800, Concreto(25), Aco()) / 1e6
    T = 400 * 500 / 1.15
    assert T * 0.420 / 1e3 < m < T * 0.460 / 1e3


def test_pilar_cli():
    r = run("pilar.py", "--bx", "20", "--by", "50", "--lex", "2.8", "--ley", "2.8", "--Nk", "1100", "--fck", "30",
            "--Mx-topo", "20", "--Mx-base", "-10", "--barras-face", "3")
    assert r["x"]["segunda_ordem"] is True
    assert r["y"]["segunda_ordem"] is False
    assert r["As_min"] <= r["As_cm2"] <= 40
    assert r["verificacao"]["utilizacao"] <= 1.0 + 1e-6


def test_gamma_n_pilar_esbelto():
    r = run("pilar.py", "--bx", "15", "--by", "40", "--lex", "2.8", "--ley", "2.8", "--Nk", "300", "--fck", "25")
    assert r["gamma_n"] == pytest.approx(1.20)
