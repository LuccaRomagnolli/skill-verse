#!/usr/bin/env python3
"""Dimensiona viga retangular de concreto armado (flexão simples + força cortante) — NBR 6118:2023.

Exemplos:
  python3 viga.py --b 15 --h 50 --fck 30 --Mk 85 --Vk 70
  python3 viga.py --b 20 --h 60 --fck 25 --Md 180 --Vd 140 --caa II --formato json
  python3 viga.py --b 14 --h 40 --fck 25 --biapoiada --vao 5 --g 12 --q 6   # calcula Mk, Vk
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nbr6118 import (caa_do_projeto, checar_durabilidade, COBRIMENTO, NORMA_REFERENCIA, STATUS_NORMATIVO,
                     Aco, Concreto, Memoria, cisalhamento_modelo1,  # noqa: E402
                     escolher_barras, escolher_estribo, flexao_simples, fmt)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--b", type=float, required=True, help="largura bw (cm)")
    ap.add_argument("--h", type=float, required=True, help="altura (cm)")
    ap.add_argument("--d", type=float, help="altura útil (cm); padrão: h − (c + φt + φl/2) estimado")
    ap.add_argument("--fck", type=float, required=True, help="MPa")
    ap.add_argument("--aco", default="CA-50", choices=["CA-50", "CA-60", "CA-25"])
    ap.add_argument("--caa", choices=["I", "II", "III", "IV"], help="classe de agressividade (padrão: ficha do projeto ou II)")
    ap.add_argument("--agregado", default="granito")
    g = ap.add_argument_group("esforços (informe característicos OU de cálculo OU carregamento)")
    g.add_argument("--Mk", type=float, help="momento característico (kN·m)")
    g.add_argument("--Vk", type=float, help="cortante característico (kN)")
    g.add_argument("--Md", type=float, help="momento de cálculo (kN·m)")
    g.add_argument("--Vd", type=float, help="cortante de cálculo (kN)")
    g.add_argument("--gf", type=float, default=1.4, help="γf para converter característico em cálculo")
    g.add_argument("--biapoiada", action="store_true", help="viga biapoiada com carga uniforme")
    g.add_argument("--vao", type=float, help="vão (m) — com --biapoiada")
    g.add_argument("--g", type=float, default=0.0, help="carga permanente (kN/m), sem peso próprio")
    g.add_argument("--q", type=float, default=0.0, help="carga variável (kN/m)")
    ap.add_argument("--contexto", default="projeto-contexto.json", help="ficha do projeto (skill contexto-do-projeto)")
    ap.add_argument("--formato", choices=["md", "json"], default="md")
    a = ap.parse_args(argv)

    conc, aco = Concreto(a.fck, a.agregado), Aco(a.aco)
    a.caa, origem_caa = caa_do_projeto(a.caa, a.contexto)
    c = COBRIMENTO[a.caa]["viga"]
    mem = Memoria(f"Viga {fmt(a.b,0)}×{fmt(a.h,0)} cm — C{fmt(a.fck,0)}, {a.aco}, CAA {a.caa}")
    mem.alerta(STATUS_NORMATIVO)
    mem.add("Classe de agressividade", f"CAA {a.caa} — {origem_caa}")
    checar_durabilidade(a.fck, a.caa, mem)
    mem.add("Cobrimento nominal (Tab. 7.2)", f"c = {c} mm")

    if a.biapoiada:
        if not a.vao:
            ap.error("--biapoiada exige --vao")
        pp = 25.0 * a.b / 100 * a.h / 100
        p = pp + a.g + a.q
        a.Mk = p * a.vao ** 2 / 8
        a.Vk = p * a.vao / 2
        mem.add("Carregamento", f"pp = 25·{fmt(a.b/100)}·{fmt(a.h/100)} = {fmt(pp)} kN/m; p = pp + g + q = {fmt(p)} kN/m")
        mem.add("Esforços característicos", f"Mk = p·L²/8 = {fmt(a.Mk)} kN·m; Vk = p·L/2 = {fmt(a.Vk)} kN")

    Md = a.Md if a.Md is not None else (a.Mk * a.gf if a.Mk is not None else None)
    Vd = a.Vd if a.Vd is not None else (a.Vk * a.gf if a.Vk is not None else None)
    if Md is None and Vd is None:
        ap.error("informe --Mk/--Md e/ou --Vk/--Vd (ou --biapoiada com --vao)")
    if a.Md is None and a.Mk is not None:
        mem.add("Momento de cálculo", f"Md = γf·Mk = {fmt(a.gf,2)}·{fmt(a.Mk)} = {fmt(Md)} kN·m")
    if a.Vd is None and a.Vk is not None:
        mem.add("Cortante de cálculo", f"Vd = γf·Vk = {fmt(a.gf,2)}·{fmt(a.Vk)} = {fmt(Vd)} kN")

    d = a.d or (a.h - (c + 5 + 8) / 10)  # c + φt 5 mm + φl/2 ≈ 8 mm
    mem.add("Altura útil", f"d = {fmt(d)} cm" + ("" if a.d else " (estimada: h − c − φt − φl/2)"))

    res: dict = {"entrada": vars(a), "d_cm": d}
    if Md is not None:
        fl = flexao_simples(Md, a.b, a.h, d, conc, aco, mem=mem)
        fl["sugestoes"] = escolher_barras(fl["As_cm2"], a.b, c)
        if fl["As2_cm2"] > 0:
            fl["sugestoes_compressao"] = escolher_barras(fl["As2_cm2"], a.b, c)
        res["flexao"] = fl
        if fl["sugestoes"]:
            mem.add("Barras sugeridas (tração)", " · ".join(s["texto"] for s in fl["sugestoes"]))
            real_d = a.h - (c + 5 + fl["sugestoes"][0]["phi_mm"] / 2) / 10
            if fl["sugestoes"][0]["camadas"] > 1 or abs(real_d - d) > 1.0:
                mem.alerta(f"Confira d com o arranjo escolhido (d ≈ {fmt(real_d)} cm para 1 camada); recalcule com --d se necessário.")
        else:
            mem.alerta("Nenhum arranjo com até 2 camadas cabe na largura: aumente bw.")
    if Vd is not None:
        cs = cisalhamento_modelo1(Vd, a.b, d, conc, aco, mem=mem)
        cs["estribo"] = escolher_estribo(cs["Asw_s_cm2_m"], cs["s_max_cm"])
        mem.add("Estribos sugeridos", cs["estribo"]["texto"])
        res["cisalhamento"] = cs

    res["norma_referencia"] = NORMA_REFERENCIA
    res["status_normativo"] = "pendente-validacao-2026"
    res["memoria"] = mem.dict()
    if a.formato == "json":
        print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    else:
        print(mem.markdown())
        print("\n_Verificações não incluídas: ELS (flecha, fissuração), ancoragem, decalagem, torção._")
    return 0


if __name__ == "__main__":
    sys.exit(main())
