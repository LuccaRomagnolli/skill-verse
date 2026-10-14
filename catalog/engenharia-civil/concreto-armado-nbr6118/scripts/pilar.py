#!/usr/bin/env python3
"""Pilar retangular de concreto armado — NBR 6118:2023.

- Pré-dimensionamento (--predim): área estimada pela carga e posição do pilar.
- Dimensionamento: momento mínimo, efeitos de 2ª ordem pelo pilar-padrão com curvatura
  aproximada (item 15.8.3.3.2, λ ≤ 90) e armadura simétrica por flexo-compressão
  (diagrama parábola-retângulo), com verificação de flexão oblíqua simplificada (17.2.5.2).

Exemplos:
  python3 pilar.py --predim --Nk 900 --fck 30 --posicao extremidade
  python3 pilar.py --bx 20 --by 50 --lex 2.8 --ley 2.8 --Nk 1100 --fck 30 \
      --Mx-topo 20 --Mx-base -10 --barras-face 3 --faces 4
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nbr6118 import (COBRIMENTO, Aco, Concreto, Memoria, camadas_retangulo,  # noqa: E402
                     fmt, momento_resistente)

POSICAO = {"intermediario": 1.3, "extremidade": 1.5, "canto": 1.8}


def gamma_n(b_cm: float) -> float:
    """Tabela 13.1 — pilares com menor dimensão entre 14 e 19 cm."""
    if b_cm < 14:
        raise ValueError("menor dimensão < 14 cm não é permitida para pilares (item 13.2.3)")
    return 1.0 if b_cm >= 19 else 1.95 - 0.05 * b_cm


def direcao(nome: str, h_cm: float, le_m: float, Nd_kN: float, M_topo: float, M_base: float,
            nu: float, mem: Memoria) -> dict:
    """Momento total de cálculo numa direção (h = dimensão paralela ao plano de flexão)."""
    h = h_cm / 100
    lam = 3.46 * le_m / h
    M1min = Nd_kN * (0.015 + 0.03 * h)
    MA, MB = (M_topo, M_base) if abs(M_topo) >= abs(M_base) else (M_base, M_topo)
    M1A = abs(MA)
    if M1A < M1min:
        ab = 1.0
        M1A_ef = M1min
        txt_ab = "αb = 1,0 (M1d < M1d,mín)"
    else:
        ratio = (MB / MA) if MA else 0.0  # sinal: mesmo sentido (curvatura simples) positivo
        ab = max(0.4, 0.6 + 0.4 * ratio)
        M1A_ef = M1A
        txt_ab = f"αb = 0,6 + 0,4·MB/MA = {fmt(ab,3)}"
    e1 = M1A_ef / Nd_kN
    lam1 = min(90.0, max(35.0, (25 + 12.5 * e1 / h) / ab))
    mem.add(f"Direção {nome}: esbeltez", f"λ = 3,46·le/h = 3,46·{fmt(le_m)}/{fmt(h)} = {fmt(lam,1)}; "
                                          f"{txt_ab}; λ1 = (25 + 12,5·e1/h)/αb = {fmt(lam1,1)}")
    mem.add(f"Direção {nome}: momento mínimo", f"M1d,mín = Nd·(0,015 + 0,03·h) = {fmt(M1min)} kN·m; M1d,A = {fmt(M1A_ef)} kN·m")
    if lam > 90:
        raise ValueError(f"λ = {lam:.1f} > 90 na direção {nome}: use pilar-padrão com rigidez κ/método geral (fora do escopo)")
    M1real = abs(MA)
    if lam <= lam1:
        mem.add(f"Direção {nome}: 2ª ordem", f"λ ≤ λ1 → dispensada; Md,tot,mín = {fmt(M1min)}; Md,tot = {fmt(M1real)} kN·m")
        return {"lambda": lam, "lambda1": lam1, "M1d_min": M1min, "Md_tot": M1real, "Md_tot_min": M1min,
                "segunda_ordem": False}
    inv_r = min(0.005 / (h * (nu + 0.5)), 0.005 / h)
    M2 = Nd_kN * le_m ** 2 / 10 * inv_r
    ab_real = max(0.4, 0.6 + 0.4 * (MB / MA)) if MA else 1.0
    Mtot = max(ab_real * M1real + M2, M1real)
    Mtot_min = M1min + M2
    mem.add(f"Direção {nome}: 2ª ordem", f"1/r = 0,005/[h(ν + 0,5)] = {fmt(inv_r,4)} 1/m; M2d = Nd·le²/10·1/r = {fmt(M2)} kN·m; "
                                         f"Md,tot = {fmt(Mtot)}; Md,tot,mín = M1d,mín + M2d = {fmt(Mtot_min)} kN·m")
    return {"lambda": lam, "lambda1": lam1, "M1d_min": M1min, "Md_tot": Mtot, "Md_tot_min": Mtot_min,
            "segunda_ordem": True, "M2d": M2}


def mrd(Nd_N, b_mm, h_mm, d2_mm, nface, faces, As_mm2, conc, aco) -> float:
    m = momento_resistente(Nd_N, b_mm, h_mm, camadas_retangulo(h_mm, d2_mm, nface, faces), As_mm2, conc, aco)
    return 0.0 if m is None else m


def dimensionar(Nd_kN, bx, by, Mx, My, d2_cm, nface, faces, conc, aco, As_min, As_max,
                Mx_min: float = 0.0, My_min: float = 0.0) -> tuple[float, dict]:
    """Menor As (cm²) que atende, com Nd:
    - situação de projeto: (Mx/MRx)^1,2 + (My/MRy)^1,2 ≤ 1 (item 17.2.5.2);
    - envoltória mínima (11.3.3.4.3): elipse de semieixos Mx_min, My_min contida na envoltória resistente.

    bx, by em cm. Mx atua no plano da dimensão bx (flexão em torno do eixo y), My no plano de by.
    """
    Nd = Nd_kN * 1e3

    def util(As_cm2: float) -> tuple[float, float, float]:
        As = As_cm2 * 100
        mrx = mrd(Nd, by * 10, bx * 10, d2_cm * 10, nface, faces, As, conc, aco) / 1e6
        mry = mrd(Nd, bx * 10, by * 10, d2_cm * 10, nface, faces, As, conc, aco) / 1e6
        if mrx <= 0 or mry <= 0:
            return 99.0, mrx, mry
        u_proj = (Mx / mrx) ** 1.2 + (My / mry) ** 1.2
        u_min = max((abs(Mx_min * math.cos(t)) / mrx) ** 1.2 + (abs(My_min * math.sin(t)) / mry) ** 1.2
                    for t in (i * math.pi / 72 for i in range(37)))
        return max(u_proj, u_min), mrx, mry

    u, mrx, mry = util(As_min)
    if u <= 1:
        return As_min, {"MRdx": mrx, "MRdy": mry, "utilizacao": u}
    u_hi, *_ = util(As_max)
    if u_hi > 1:
        return math.inf, {"utilizacao_com_As_max": u_hi}
    lo, hi = As_min, As_max
    for _ in range(40):
        mid = (lo + hi) / 2
        if util(mid)[0] <= 1:
            hi = mid
        else:
            lo = mid
    u, mrx, mry = util(hi)
    return hi, {"MRdx": mrx, "MRdy": mry, "utilizacao": u}


def escolher_barras_pilar(As_cm2: float, n_total: int, bmin_cm: float) -> dict | None:
    for phi in (10.0, 12.5, 16.0, 20.0, 25.0, 32.0):
        if phi > bmin_cm * 10 / 8:
            break
        area = n_total * math.pi * phi ** 2 / 4 / 100
        if area >= As_cm2:
            return {"n": n_total, "phi_mm": phi, "As_ef_cm2": round(area, 2),
                    "texto": f"{n_total} φ{phi:g} ({fmt(area)} cm²)".replace(".", ",")}
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--predim", action="store_true", help="só pré-dimensionamento da seção")
    ap.add_argument("--posicao", choices=list(POSICAO), default="intermediario")
    ap.add_argument("--bx", type=float, help="dimensão x (cm)")
    ap.add_argument("--by", type=float, help="dimensão y (cm)")
    ap.add_argument("--lex", type=float, help="comprimento de flambagem para flexão no plano x (m)")
    ap.add_argument("--ley", type=float, help="comprimento de flambagem para flexão no plano y (m)")
    ap.add_argument("--Nk", type=float, help="normal característica (kN)")
    ap.add_argument("--Nd", type=float, help="normal de cálculo (kN)")
    for e in ("x", "y"):
        ap.add_argument(f"--M{e}-topo", type=float, default=0.0, help=f"M1d no topo, plano {e} (kN·m, cálculo)")
        ap.add_argument(f"--M{e}-base", type=float, default=0.0, help=f"M1d na base, plano {e} (kN·m, cálculo); "
                        "mesmo sinal do topo = curvatura simples")
    ap.add_argument("--fck", type=float, required=True)
    ap.add_argument("--aco", default="CA-50", choices=["CA-50", "CA-60"])
    ap.add_argument("--caa", default="II", choices=["I", "II", "III", "IV"])
    ap.add_argument("--barras-face", type=int, default=2, help="barras por face (≥ 2)")
    ap.add_argument("--faces", type=int, choices=[2, 4], default=4, help="armadura em 2 ou nas 4 faces")
    ap.add_argument("--formato", choices=["md", "json"], default="md")
    a = ap.parse_args(argv)

    conc, aco = Concreto(a.fck), Aco(a.aco)
    if a.Nd is None and a.Nk is None:
        ap.error("informe --Nk ou --Nd")

    if a.predim:
        Nk = a.Nk if a.Nk is not None else a.Nd / 1.4
        alfa = POSICAO[a.posicao]
        sigma = 0.85 * conc.fcd + 0.015 * 420  # MPa, ρ = 1,5 %, σs(2‰) ≈ 420 MPa
        Ac = alfa * 1.4 * Nk * 1e3 / sigma / 100  # cm²
        lado = max(19.0, math.ceil(math.sqrt(Ac) / 5) * 5)
        out = {"Ac_cm2": Ac, "posicao": a.posicao, "alfa": alfa, "sugestao": f"{lado:g} × {max(lado, math.ceil(Ac/lado/5)*5):g} cm"}
        if a.formato == "json":
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            print(f"Ac,est = α·1,4·Nk/(0,85·fcd + ρ·σs) = {fmt(alfa)}·1,4·{fmt(Nk,0)}/({fmt(sigma)} MPa) = {fmt(Ac,0)} cm²"
                  f"\nSugestão: {out['sugestao']} (α = {fmt(alfa,1)} para pilar de {a.posicao}). "
                  "Estimativa empírica — confirme com o dimensionamento completo.")
        return 0

    for k in ("bx", "by", "lex", "ley"):
        if getattr(a, k) is None:
            ap.error(f"--{k} é obrigatório no dimensionamento")
    bmin = min(a.bx, a.by)
    gn = gamma_n(bmin)
    Nd = a.Nd if a.Nd is not None else 1.4 * a.Nk
    Nd *= gn
    c = COBRIMENTO[a.caa]["pilar"]
    d2 = (c + 5 + 8) / 10  # c + φt + φl/2 (cm)
    Ac = a.bx * a.by
    nu = Nd * 1e3 / (Ac * 100 * conc.fcd)
    mem = Memoria(f"Pilar {fmt(a.bx,0)}×{fmt(a.by,0)} cm — C{fmt(a.fck,0)}, {a.aco}, CAA {a.caa}")
    mem.add("Esforço normal", f"Nd = γn·γf·Nk = {fmt(gn,2)}·{fmt(Nd/gn)} = {fmt(Nd)} kN; ν = Nd/(Ac·fcd) = {fmt(nu,3)}")
    try:
        dx = direcao("x", a.bx, a.lex, Nd, a.Mx_topo * gn, a.Mx_base * gn, nu, mem)
        dy = direcao("y", a.by, a.ley, Nd, a.My_topo * gn, a.My_base * gn, nu, mem)
    except ValueError as e:
        print(f"ERRO: {e}")
        return 2

    As_min = max(0.15 * Nd * 1e3 / aco.fyd / 100, 0.004 * Ac)
    As_max = 0.04 * Ac  # fora da região de emendas (8% com traspasse)
    nface = max(2, a.barras_face)
    n_total = 4 * nface - 4 if a.faces == 4 else 2 * nface
    As, info = dimensionar(Nd, a.bx, a.by, dx["Md_tot"], dy["Md_tot"], d2, nface, a.faces, conc, aco, As_min, As_max,
                           dx["Md_tot_min"], dy["Md_tot_min"])
    mem.add("Limites de armadura", f"As,mín = máx(0,15·Nd/fyd; 0,4%·Ac) = {fmt(As_min)} cm²; As,máx = 4%·Ac = {fmt(As_max)} cm²")
    res = {"entrada": vars(a), "gamma_n": gn, "Nd_kN": Nd, "nu": nu, "x": dx, "y": dy, "As_min": As_min}
    if math.isinf(As):
        mem.alerta("Seção insuficiente mesmo com 4% de armadura: aumente a seção ou o fck.")
        res["As_cm2"] = None
    else:
        mem.add("Flexo-compressão oblíqua", f"projeto: (Mx/MRx)^1,2 + (My/MRy)^1,2 ≤ 1 com Mx = {fmt(dx['Md_tot'])}, "
                                            f"My = {fmt(dy['Md_tot'])} kN·m; envoltória mínima elíptica com semieixos "
                                            f"{fmt(dx['Md_tot_min'])} e {fmt(dy['Md_tot_min'])} kN·m")
        mem.add("Armadura calculada", f"As = {fmt(As)} cm² (MRd,x = {fmt(info['MRdx'])}; MRd,y = {fmt(info['MRdy'])} kN·m; "
                                      f"utilização = {fmt(info['utilizacao'],3)})")
        barras = escolher_barras_pilar(As, n_total, bmin)
        res.update({"As_cm2": As, "verificacao": info, "barras": barras})
        if barras:
            phi_t = max(5.0, barras["phi_mm"] / 4)
            s_t = min(200, bmin * 10, 12 * barras["phi_mm"])
            mem.add("Detalhamento", f"{barras['texto']} em {a.faces} faces; estribos φ{phi_t:g} c/ {fmt(s_t/10,0)} cm "
                                    "(φt ≥ φ/4 e 5 mm; s ≤ 20 cm, menor dimensão e 12φ)".replace(".", ","))
            res["estribos"] = {"phi_mm": phi_t, "s_cm": s_t / 10}
        else:
            mem.alerta(f"Nenhuma bitola ≤ b/8 atende com {n_total} barras: aumente --barras-face.")
    res["memoria"] = mem.dict()
    if a.formato == "json":
        print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    else:
        print(mem.markdown())
        print("\n_Hipóteses: pilar contraventado (nós fixos), sem cargas transversais, λ ≤ 90 (fluência dispensada)._")
    return 0


if __name__ == "__main__":
    sys.exit(main())
