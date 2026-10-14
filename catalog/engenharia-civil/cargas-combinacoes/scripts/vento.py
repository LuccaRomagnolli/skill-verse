#!/usr/bin/env python3
"""Velocidade característica e pressão dinâmica do vento — NBR 6123:1988.

Vk = V0·S1·S2·S3     q = 0,613·Vk² (N/m²)     S2 = b·Fr·(z/10)^p

Exemplos:
  python3 vento.py --V0 35 --categoria IV --classe B --alturas 3 6 9 12 15 --S3-grupo 2
  python3 vento.py --V0 40 --categoria III --classe C --altura-total 45 --passo 3 --Ca 1.3 --largura 20
"""
from __future__ import annotations

import argparse
import json
import sys

# Tabela 1 (parâmetros meteorológicos): categoria → classe → (b, p); Fr só para categoria II
S2_PARAM = {
    "I": {"A": (1.10, 0.06), "B": (1.11, 0.065), "C": (1.12, 0.07)},
    "II": {"A": (1.00, 0.085), "B": (1.00, 0.09), "C": (1.00, 0.10)},
    "III": {"A": (0.94, 0.10), "B": (0.94, 0.105), "C": (0.93, 0.115)},
    "IV": {"A": (0.86, 0.12), "B": (0.85, 0.125), "C": (0.84, 0.135)},
    "V": {"A": (0.74, 0.15), "B": (0.73, 0.16), "C": (0.71, 0.175)},
}
FR = {"A": 1.00, "B": 0.98, "C": 0.95}
S3 = {1: 1.10, 2: 1.00, 3: 0.95, 4: 0.88, 5: 0.83}
S3_TXT = {1: "edificações cuja ruína afeta segurança/socorro (hospitais, quartéis…)",
          2: "residências, hotéis, comércio, indústria com alta ocupação",
          3: "edificações de baixa ocupação (depósitos, silos, instalações rurais)",
          4: "vedações (telhas, vidros, painéis)",
          5: "edificações temporárias e estruturas em construção"}


def classe_por_dimensao(dmax: float) -> str:
    return "A" if dmax <= 20 else ("B" if dmax <= 50 else "C")


def s2(z: float, categoria: str, classe: str) -> float:
    b, p = S2_PARAM[categoria][classe]
    return b * FR[classe] * (max(z, 5.0) / 10) ** p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--V0", type=float, required=True, help="velocidade básica (m/s) — mapa de isopletas, Figura 1")
    ap.add_argument("--S1", type=float, default=1.0, help="fator topográfico (1,0 plano; 0,9 vales protegidos; morros: item 5.2)")
    ap.add_argument("--categoria", required=True, choices=list(S2_PARAM), help="rugosidade do terreno (I a V)")
    ap.add_argument("--classe", choices=["A", "B", "C"], help="A ≤ 20 m; B 20–50 m; C > 50 m (maior dimensão)")
    ap.add_argument("--maior-dimensao", type=float, help="maior dimensão horizontal ou vertical (m) — define a classe")
    ap.add_argument("--S3-grupo", type=int, default=2, choices=list(S3))
    ap.add_argument("--alturas", type=float, nargs="*", help="cotas z (m)")
    ap.add_argument("--altura-total", type=float, help="gera cotas de --passo em --passo até a altura total")
    ap.add_argument("--passo", type=float, default=3.0)
    ap.add_argument("--Ca", type=float, help="coeficiente de arrasto (Figura 4/5) para calcular força por andar")
    ap.add_argument("--largura", type=float, help="largura de fachada exposta (m), perpendicular ao vento")
    ap.add_argument("--formato", choices=["md", "json"], default="md")
    a = ap.parse_args(argv)

    classe = a.classe or (classe_por_dimensao(a.maior_dimensao) if a.maior_dimensao else None)
    if not classe:
        ap.error("informe --classe ou --maior-dimensao")
    zs = a.alturas or []
    if a.altura_total:
        n = int(round(a.altura_total / a.passo))
        zs = [round(a.passo * (i + 1), 3) for i in range(n)]
    if not zs:
        ap.error("informe --alturas ou --altura-total")
    s3 = S3[a.S3_grupo]
    linhas = []
    for i, z in enumerate(zs):
        f2 = s2(z, a.categoria, classe)
        vk = a.V0 * a.S1 * f2 * s3
        q = 0.613 * vk ** 2 / 1000  # kN/m²
        linha = {"z": z, "S2": f2, "Vk": vk, "q_kN_m2": q}
        if a.Ca and a.largura:
            h_inf = (z - zs[i - 1]) if i else z
            h_sup = (zs[i + 1] - z) if i + 1 < len(zs) else 0.0
            area = a.largura * (h_inf + h_sup) / 2
            linha["F_kN"] = a.Ca * q * area
        linhas.append(linha)
    res = {"V0": a.V0, "S1": a.S1, "categoria": a.categoria, "classe": classe, "S3": s3,
           "S3_grupo": S3_TXT[a.S3_grupo], "cotas": linhas}
    if a.formato == "json":
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    b, p = S2_PARAM[a.categoria][classe]
    print(f"### Vento — NBR 6123:1988\n\nV0 = {a.V0} m/s · S1 = {a.S1} · categoria {a.categoria}, classe {classe} "
          f"(b = {b}, Fr = {FR[classe]}, p = {p}) · S3 = {s3} ({S3_TXT[a.S3_grupo]})\n")
    cab = "| z (m) | S2 | Vk (m/s) | q (kN/m²) |" + (" F (kN) |" if a.Ca and a.largura else "")
    print(cab)
    print("|" + "---|" * (cab.count("|") - 1))
    for l in linhas:
        extra = f" {l['F_kN']:.2f} |" if "F_kN" in l else ""
        print(f"| {l['z']:.2f} | {l['S2']:.3f} | {l['Vk']:.2f} | {l['q_kN_m2']:.3f} |{extra}")
    if a.Ca and a.largura:
        print(f"\nForça por nível: F = Ca·q·Ae, Ca = {a.Ca}, largura {a.largura} m, área de influência meia altura acima/abaixo.")
    print("\n_Confira V0 no mapa de isopletas e se há revisão vigente da NBR 6123 para o seu projeto._")
    return 0


if __name__ == "__main__":
    sys.exit(main())
