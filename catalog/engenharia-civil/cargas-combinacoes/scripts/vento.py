#!/usr/bin/env python3
"""Vk e pressão dinâmica auxiliares — base NBR 6123:2023, errata de 2025 pendente.

Vk = V0·S1·S2·S3     q = 0,613·Vk² (N/m²)     S2 = b·Fr·(z/10)^p

Exemplos:
  python3 vento.py --V0 35 --S1 1 --categoria IV --classe B --alturas 3 6 9 12 15 --S3-grupo 3
  python3 vento.py --V0 40 --S1 1 --categoria III --classe C --altura-total 45 --passo 3 --S3-grupo 3 --Ca 1.3 --fv 1 --largura 20
"""
from __future__ import annotations

import argparse
import json
import math
import sys

# Tabela 1 (parâmetros meteorológicos): categoria → classe → (bm, p); Fr é o da categoria II.
S2_PARAM = {
    "I": {"A": (1.10, 0.06), "B": (1.11, 0.065), "C": (1.12, 0.07)},
    "II": {"A": (1.00, 0.085), "B": (1.00, 0.09), "C": (1.00, 0.10)},
    "III": {"A": (0.94, 0.10), "B": (0.94, 0.105), "C": (0.93, 0.115)},
    "IV": {"A": (0.86, 0.12), "B": (0.85, 0.125), "C": (0.84, 0.135)},
    "V": {"A": (0.74, 0.15), "B": (0.73, 0.16), "C": (0.71, 0.175)},
}
FR = {"A": 1.00, "B": 0.98, "C": 0.95}
ZG = {"I": 250, "II": 300, "III": 350, "IV": 420, "V": 500}
S3 = {1: 1.11, 2: 1.06, 3: 1.00, 4: 0.95, 5: 0.83}
S3_TXT = {1: "edificações cuja ruína afeta segurança/socorro (hospitais, quartéis…)",
          2: "alto risco à vida, inclusive aglomerações, creches e escolas nos limiares da Tabela 4",
          3: "residências, hotéis, comércio e indústrias usuais",
          4: "edificações sem ocupação humana e sem circulação no entorno",
          5: "temporárias não reutilizáveis ou em construção, dentro do limite de duração"}


def classe_por_dimensao(dmax: float) -> str:
    return "A" if dmax <= 20 else ("B" if dmax <= 50 else "C")


def s2(z: float, categoria: str, classe: str) -> float:
    if not math.isfinite(z) or z <= 0 or z > ZG[categoria]:
        raise ValueError(f"altura z deve estar entre 0 e zg={ZG[categoria]} m para categoria {categoria}")
    b, p = S2_PARAM[categoria][classe]
    return b * FR[classe] * (max(z, 10.0 if categoria == "V" else 5.0) / 10) ** p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--V0", type=float, required=True, help="velocidade básica (m/s) — mapa de isopletas, Figura 1")
    ap.add_argument("--S1", type=float, required=True, help="fator topográfico confirmado pelo projetista (item 5.2)")
    ap.add_argument("--categoria", required=True, choices=list(S2_PARAM), help="rugosidade do terreno (I a V)")
    ap.add_argument("--classe", choices=["A", "B", "C"], help="A ≤ 20 m; B 20–50 m; C > 50 m (maior dimensão)")
    ap.add_argument("--maior-dimensao", type=float, help="maior dimensão horizontal ou vertical (m) — define a classe")
    ap.add_argument("--S3-grupo", type=int, required=True, choices=list(S3))
    ap.add_argument("--alturas", type=float, nargs="*", help="cotas z (m)")
    ap.add_argument("--altura-total", type=float, help="gera cotas de --passo em --passo até a altura total")
    ap.add_argument("--passo", type=float, default=3.0)
    ap.add_argument("--Ca", type=float, help="coeficiente de arrasto (Figura 4/5) para calcular força por andar")
    ap.add_argument("--fv", type=float, help="fator de vizinhança confirmado (item 6.4), necessário para força")
    ap.add_argument("--largura", type=float, help="largura de fachada exposta (m), perpendicular ao vento")
    ap.add_argument("--formato", choices=["md", "json"], default="md")
    a = ap.parse_args(argv)

    if not all(math.isfinite(v) and v > 0 for v in (a.V0, a.S1, a.passo)):
        ap.error("V0, S1 e passo devem ser positivos e finitos")
    if any(x is not None for x in (a.Ca, a.fv, a.largura)) and not all(
            x is not None and math.isfinite(x) and x > 0 for x in (a.Ca, a.fv, a.largura)):
        ap.error("para força informe --Ca, --fv e --largura, todos positivos e finitos")
    if a.alturas is not None and a.altura_total is not None:
        ap.error("use --alturas ou --altura-total, não ambos")

    if a.maior_dimensao is not None and (not math.isfinite(a.maior_dimensao) or a.maior_dimensao <= 0):
        ap.error("maior dimensão deve ser positiva e finita")
    if a.classe and a.maior_dimensao and a.classe != classe_por_dimensao(a.maior_dimensao):
        ap.error("classe informada diverge da maior dimensão")
    classe = a.classe or (classe_por_dimensao(a.maior_dimensao) if a.maior_dimensao else None)
    if not classe:
        ap.error("informe --classe ou --maior-dimensao")
    zs = a.alturas or []
    if a.altura_total is not None:
        if not math.isfinite(a.altura_total) or a.altura_total <= 0:
            ap.error("altura total deve ser positiva e finita")
        n = int(a.altura_total / a.passo)
        zs = [round(a.passo * (i + 1), 6) for i in range(n) if a.passo * (i + 1) < a.altura_total]
        zs.append(a.altura_total)
    if not zs:
        ap.error("informe --alturas ou --altura-total")
    if any(not math.isfinite(z) or z <= 0 or z > ZG[a.categoria] for z in zs) or zs != sorted(set(zs)):
        ap.error(f"alturas devem ser únicas, crescentes e até zg={ZG[a.categoria]} m")
    s3 = S3[a.S3_grupo]
    linhas = []
    for i, z in enumerate(zs):
        f2 = s2(z, a.categoria, classe)
        vk = a.V0 * a.S1 * f2 * s3
        q = 0.613 * vk ** 2 / 1000  # kN/m²
        linha = {"z": z, "S2": f2, "Vk": vk, "q_kN_m2": q}
        if a.Ca is not None:
            # Cada cota representa a faixa desde a cota anterior; soma das áreas = largura × altura final.
            dz = z - (zs[i - 1] if i else 0.0)
            area = a.largura * dz
            linha["Ae_m2"] = area
            linha["F_kN"] = a.Ca * q * area * a.fv
        linhas.append(linha)
    res = {"norma_base_calculo": "ABNT NBR 6123:2023, itens 4.2/4.3.3/5.1-5.4 e Tabelas 1/2/4",
           "status_normativo": "base-2023-auditada-errata-1-2025-e-aplicabilidade-pendentes",
           "V0": a.V0, "S1": a.S1, "categoria": a.categoria, "classe": classe, "S3": s3,
           "S3_grupo": a.S3_grupo, "S3_descricao": S3_TXT[a.S3_grupo], "Ca": a.Ca, "fv": a.fv,
           "limites": ["vento estático simplificado; não cobre pressão em fachadas/coberturas, dinâmica ou vizinhança complexa",
                       "V0, S1, terreno, S3, Ca e fv exigem confirmação no caso concreto",
                       "pressão na cota superior de cada faixa usada como aproximação para força por nível",
                       "Errata 1:2025 e edição vigente ainda precisam ser confrontadas"], "cotas": linhas}
    if a.formato == "json":
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    b, p = S2_PARAM[a.categoria][classe]
    print(f"### Vento — NBR 6123:2023 (errata pendente)\n\nV0 = {a.V0} m/s · S1 = {a.S1} · categoria {a.categoria}, classe {classe} "
          f"(b = {b}, Fr = {FR[classe]}, p = {p}) · S3 = {s3} ({S3_TXT[a.S3_grupo]})\n")
    cab = "| z (m) | S2 | Vk (m/s) | q (kN/m²) |" + (" F (kN) |" if a.Ca is not None else "")
    print(cab)
    print("|" + "---|" * (cab.count("|") - 1))
    for l in linhas:
        extra = f" {l['F_kN']:.2f} |" if "F_kN" in l else ""
        print(f"| {l['z']:.2f} | {l['S2']:.3f} | {l['Vk']:.2f} | {l['q_kN_m2']:.3f} |{extra}")
    if a.Ca is not None:
        print(f"\nForça por faixa: Fa = Ca·q·Ae·fv; Ca={a.Ca}, fv={a.fv}, largura={a.largura} m. "
              "Ae = largura × intervalo até a cota; q tomado na cota superior.")
    print("\n_Cálculo auxiliar. Confirmar a Errata 1:2025, parâmetros locais e aplicabilidade antes do projeto._")
    return 0


if __name__ == "__main__":
    sys.exit(main())
