#!/usr/bin/env python3
"""Laje maciça retangular — momentos, armaduras, flecha e reações nas vigas (NBR 6118:2023).

Momentos pela teoria de placas (diferenças finitas, equivalente às tabelas de Czerny/Bares).
Bordas: 4 letras A (apoiada) / E (engastada) na ordem esquerda, direita, inferior, superior;
lx é o vão horizontal (esquerda→direita), ly o vertical.

Exemplos:
  python3 laje.py --lx 4 --ly 5 --h 10 --g 1.5 --q 1.5 --fck 25 --bordas AEAE
  python3 laje.py --balanco 1.2 --h 12 --g 2 --q 2 --fck 30
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nbr6118 import (caa_do_projeto, checar_durabilidade, COBRIMENTO, ES, Aco, Concreto, Memoria, barras_por_metro,  # noqa: E402
                     flexao_simples, fmt, rho_min)
from placa import resolver_refinado  # noqa: E402

NOMES = ("esquerda", "direita", "inferior", "superior")
ALPHA_F = 1.32  # t0 = 1 mês, t ≥ 70 meses, sem armadura de compressão (item 17.3.2.1.2)


def reacoes(lx: float, ly: float, bordas: str, p: float, n: int = 240) -> dict:
    """Charneiras: 45° entre bordas iguais, 60° a partir do engaste (item 14.7.6.1)."""
    k = [1.0 if b == "E" else math.tan(math.radians(60)) for b in bordas]
    if len(set(bordas)) == 1:
        k = [1.0] * 4
    area = [0.0] * 4
    dx, dy = lx / n, ly / n
    for i in range(n):
        x = (i + 0.5) * dx
        for j in range(n):
            y = (j + 0.5) * dy
            dist = (x * k[0], (lx - x) * k[1], y * k[2], (ly - y) * k[3])
            area[dist.index(min(dist))] += dx * dy
    comp = (ly, ly, lx, lx)
    return {NOMES[i]: p * area[i] / comp[i] for i in range(4)}


def inercia_estadio2(As_cm2_m: float, d_cm: float, alpha_e: float) -> float:
    """III (cm⁴/m) de faixa de 1 m."""
    b, As, d = 100.0, As_cm2_m, d_cm
    a = b / 2
    bb, c = alpha_e * As, -alpha_e * As * d
    x = (-bb + math.sqrt(bb * bb - 4 * a * c)) / (2 * a)
    return b * x ** 3 / 3 + alpha_e * As * (d - x) ** 2


def armar(nome: str, M: float, h: float, d: float, conc, aco, mem, minimo: float) -> dict:
    fl = flexao_simples(M, 100, h, d, conc, aco, mem=Memoria(nome))
    As = max(fl["As_calc_cm2"], minimo)
    barras = barras_por_metro(As, h)
    mem.add(nome, f"m = {fmt(M)} kN·m/m; d = {fmt(d,1)} cm; As = {fmt(fl['As_calc_cm2'])} → adotado {fmt(As)} cm²/m "
                  f"(mín. {fmt(minimo)}) → {barras['texto']}")
    if fl["As2_cm2"] > 0:
        mem.alerta(f"{nome}: precisaria de armadura dupla — aumente h.")
    return {"m_kNm_m": M, "d_cm": d, "As_cm2_m": As, "barras": barras}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lx", type=float, help="vão x (m)")
    ap.add_argument("--ly", type=float, help="vão y (m)")
    ap.add_argument("--bordas", default="AAAA", help="A/E: esquerda, direita, inferior, superior")
    ap.add_argument("--balanco", type=float, help="laje em balanço: comprimento (m)")
    ap.add_argument("--h", type=float, required=True, help="espessura (cm)")
    ap.add_argument("--g", type=float, default=1.0, help="permanente adicional (kN/m²), sem peso próprio")
    ap.add_argument("--q", type=float, required=True, help="variável (kN/m²) — NBR 6120")
    ap.add_argument("--psi2", type=float, default=0.3, help="ψ2 da carga variável (0,3 residencial; 0,4 comercial)")
    ap.add_argument("--fck", type=float, required=True)
    ap.add_argument("--aco", default="CA-50", choices=["CA-50", "CA-60"])
    ap.add_argument("--caa", choices=["I", "II", "III", "IV"], help="classe de agressividade (padrão: ficha do projeto ou II)")
    ap.add_argument("--nu", type=float, default=0.2)
    ap.add_argument("--contexto", default="projeto-contexto.json", help="ficha do projeto (skill contexto-do-projeto)")
    ap.add_argument("--formato", choices=["md", "json"], default="md")
    a = ap.parse_args(argv)

    conc, aco = Concreto(a.fck), Aco(a.aco)
    a.caa, origem_caa = caa_do_projeto(a.caa, a.contexto)
    c = COBRIMENTO[a.caa]["laje"]
    pp = 25 * a.h / 100
    p = pp + a.g + a.q
    pd = 1.4 * p
    pqp = pp + a.g + a.psi2 * a.q
    rmin = rho_min(a.fck)
    As_min_neg = rmin * 100 * a.h
    titulo = (f"Laje em balanço L = {fmt(a.balanco)} m" if a.balanco else
              f"Laje {fmt(a.lx)} × {fmt(a.ly)} m, bordas {a.bordas.upper()}")
    mem = Memoria(f"{titulo} — h = {fmt(a.h,0)} cm, C{fmt(a.fck,0)}")
    mem.add("Cargas", f"pp = 25·{fmt(a.h/100)} = {fmt(pp)}; p = {fmt(p)} kN/m²; pd = 1,4·p = {fmt(pd)} kN/m²; "
                      f"p,qp = g + ψ2·q = {fmt(pqp)} kN/m²")
    mem.add("Classe de agressividade", f"CAA {a.caa} — {origem_caa}")
    checar_durabilidade(a.fck, a.caa, mem)
    mem.add("Cobrimento (Tab. 7.2)", f"c = {c} mm")
    res: dict = {"entrada": vars(a), "cargas": {"pp": pp, "p": p, "pd": pd, "pqp": pqp}}
    d1 = a.h - c / 10 - 0.5  # 1ª camada, φ ≈ 10 mm

    if a.balanco:
        L = a.balanco
        M = pd * L ** 2 / 2
        res["negativo"] = armar("Engaste (negativo)", M, a.h, d1, conc, aco, mem, As_min_neg)
        dist = max(0.2 * res["negativo"]["As_cm2_m"], 0.9, 0.5 * rmin * 100 * a.h)
        res["distribuicao"] = {"As_cm2_m": dist, "barras": barras_por_metro(dist, a.h)}
        mem.add("Armadura de distribuição", f"{fmt(dist)} cm²/m → {res['distribuicao']['barras']['texto']}")
        I = 100 * a.h ** 3 / 12 * 1e-8  # m⁴/m
        w = pqp * L ** 4 / (8 * conc.Ecs * 1e3 * I)  # m
        lim = 2 * L / 250  # balanço: l = 2·L
        mem.add("Flecha (Estádio I)", f"w,i = p·L⁴/(8EI) = {fmt(w*1000)} mm; w,∞ = (1 + {fmt(ALPHA_F)})·w,i = {fmt(w*(1+ALPHA_F)*1000)} mm; "
                                     f"limite 2L/250 = {fmt(lim*1000)} mm")
        res["flecha_mm"] = {"imediata": w * 1000, "total": w * (1 + ALPHA_F) * 1000, "limite": lim * 1000}
        if w * (1 + ALPHA_F) > lim:
            mem.alerta("Flecha acima do limite: aumente h.")
        mem.add("Reação na viga de apoio", f"R = pd·L = {fmt(pd*L)} kN/m (cálculo); M engaste = {fmt(M)} kN·m/m")
        res["reacao_kN_m"] = {"engaste": p * L}
    else:
        if not (a.lx and a.ly):
            ap.error("informe --lx e --ly (ou --balanco)")
        b = a.bordas.upper()
        pl = resolver_refinado(a.lx, a.ly, b, a.nu)
        lam = max(a.lx, a.ly) / min(a.lx, a.ly)
        uma_dir = lam > 2
        mem.add("Método", f"{pl['metodo']}, malha {pl['malha'][0]}×{pl['malha'][1]}, ν = {fmt(a.nu)}; λ = {fmt(lam)}"
                          + (" (> 2: armada em uma direção)" if uma_dir else " (armada em cruz)"))
        l2 = a.lx ** 2
        mx, my = pl["cmx"] * pd * l2, pl["cmy"] * pd * l2
        # menor vão recebe a 1ª camada
        dx_, dy_ = (d1, d1 - 1.0) if a.lx <= a.ly else (d1 - 1.0, d1)
        pos_min = rmin * 100 * a.h * (1.0 if uma_dir else 0.67)
        if not uma_dir:
            res["positivo_x"] = armar("Positivo x", mx, a.h, dx_, conc, aco, mem, pos_min)
            res["positivo_y"] = armar("Positivo y", my, a.h, dy_, conc, aco, mem, pos_min)
        else:  # principal no menor vão; secundária pela Tab. 19.1
            pri, sec = ("x", "y") if a.lx <= a.ly else ("y", "x")
            mm, dd = {"x": mx, "y": my}, {"x": dx_, "y": dy_}
            res[f"positivo_{pri}"] = armar(f"Positivo {pri} (principal)", mm[pri], a.h, dd[pri], conc, aco, mem, pos_min)
            dist = max(0.2 * res[f"positivo_{pri}"]["As_cm2_m"], 0.9, 0.5 * rmin * 100 * a.h)
            res[f"positivo_{sec}"] = armar(f"Positivo {sec} (secundária)", mm[sec], a.h, dd[sec], conc, aco, mem, dist)
        res["negativos"] = {}
        for borda, cm in pl["cneg"].items():
            res["negativos"][borda] = armar(f"Negativo {borda}", abs(cm) * pd * l2, a.h, d1, conc, aco, mem, As_min_neg)
        if res["negativos"]:
            mem.alerta("Momentos negativos de lajes vizinhas devem ser compatibilizados "
                       "(maior entre a média e 80% do maior) antes do detalhamento.")

        # Flecha: Branson (item 17.3.2.1.1)
        Ic = 100 * a.h ** 3 / 12  # cm⁴/m
        Ma = max(pl["cmx"], pl["cmy"]) * pqp * l2  # kN·m/m
        Mr = 1.5 * conc.fctm * 1e3 * (1.0 * (a.h / 100) ** 2 / 6)  # kN·m/m
        main_pos = res["positivo_x"] if pl["cmx"] >= pl["cmy"] else res["positivo_y"]
        if Ma > Mr:
            III = inercia_estadio2(main_pos["As_cm2_m"], main_pos["d_cm"], ES / conc.Ecs)
            r3 = (Mr / Ma) ** 3
            Ieq = min(Ic, r3 * Ic + (1 - r3) * III)
        else:
            Ieq = Ic
        D = conc.Ecs * 1e3 * (Ieq * 1e-8) / (1 - a.nu ** 2)  # rigidez de placa, kN·m
        wi = pl["cw"] * pqp * a.lx ** 4 / D
        wt = wi * (1 + ALPHA_F)
        lim = min(a.lx, a.ly) / 250
        mem.add("Flecha (Branson)", f"Ma = {fmt(Ma)} kN·m/m; Mr = {fmt(Mr)} kN·m/m; Ieq/Ic = {fmt(Ieq/Ic,3)}; "
                                    f"w,i = {fmt(wi*1000)} mm; w,∞ = (1 + {fmt(ALPHA_F)})·w,i = {fmt(wt*1000)} mm; limite l/250 = {fmt(lim*1000)} mm")
        res["flecha_mm"] = {"imediata": wi * 1000, "total": wt * 1000, "limite": lim * 1000, "Ieq_Ic": Ieq / Ic}
        if wt > lim:
            mem.alerta("Flecha acima de l/250: aumente h (ou considere contraflecha, item 13.3).")
        reac = reacoes(a.lx, a.ly, b, p)
        res["reacao_kN_m"] = reac
        mem.add("Reações nas vigas (característica)", "; ".join(f"{k}: {fmt(v)} kN/m" for k, v in reac.items()))
        res["coeficientes"] = pl

    res["memoria"] = mem.dict()
    if a.formato == "json":
        print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    else:
        print(mem.markdown())
        print("\n_Não inclui: punção, cisalhamento em lajes sem estribos (item 19.4), aberturas, cargas concentradas._")
    return 0


if __name__ == "__main__":
    sys.exit(main())
