#!/usr/bin/env python3
"""Levantamento de quantitativos de estrutura e alvenaria a partir de uma lista de elementos (JSON).

Modelo de entrada: assets/elementos.exemplo.json. Unidades em metros; bitolas em mm.

  python3 quantitativos.py elementos.json [--perda-aco 10] [--vaos total|excedente-2m2] [--formato md|json|csv]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

KG_M = {5.0: 0.154, 6.3: 0.245, 8.0: 0.395, 10.0: 0.617, 12.5: 0.963, 16.0: 1.578,
        20.0: 2.466, 25.0: 3.853, 32.0: 6.313}


def concreto(e: dict, h_laje: float) -> tuple[float, float, str]:
    """(volume m³, fôrma m², descrição) de um elemento."""
    q = e.get("qtd", 1)
    t = e["tipo"]
    if t == "viga":
        L, b, h = e["comprimento"], e["b"], e["h"]
        hl = e.get("h_laje", h_laje)  # laje apoiada sobre a viga: fôrma lateral desconta a espessura da laje
        return q * b * h * L, q * L * (b + 2 * (h - hl) + (hl if e.get("borda") else 0)), f"{b:.2f}×{h:.2f}×{L:.2f}"
    if t == "pilar":
        H, bx, by = e["altura"], e["bx"], e["by"]
        return q * bx * by * H, q * 2 * (bx + by) * H, f"{bx:.2f}×{by:.2f}×{H:.2f}"
    if t == "laje":
        lx, ly, h = e["lx"], e["ly"], e["h"]
        return q * lx * ly * h, q * lx * ly, f"{lx:.2f}×{ly:.2f}, h={h:.2f}"
    if t == "sapata":
        a, b, h = e["a"], e["b"], e["h"]
        return q * a * b * h, q * 2 * (a + b) * h, f"{a:.2f}×{b:.2f}×{h:.2f}"
    if t == "bloco":  # volume livre informado
        return q * e["volume"], q * e.get("forma", 0.0), "volume informado"
    raise ValueError(f"tipo de elemento desconhecido: {t}")


def area_alvenaria(p: dict, regra: str) -> tuple[float, float, float]:
    bruta = p["comprimento"] * p["altura"] * p.get("qtd", 1)
    desc = 0.0
    for v in p.get("vaos", []):
        a = v[0] * v[1] * (v[2] if len(v) > 2 else 1)
        desc += a if regra == "total" else max(0.0, a - 2.0)
    return bruta, desc, bruta - desc


def calcular(dados: dict, perda_aco: float, regra_vaos: str) -> dict:
    h_laje = dados.get("h_laje_padrao", 0.10)
    linhas, tot = [], defaultdict(float)
    for e in dados.get("concreto", []):
        v, f, d = concreto(e, h_laje)
        linhas.append({"id": e["id"], "tipo": e["tipo"], "dimensoes": d, "qtd": e.get("qtd", 1),
                       "concreto_m3": round(v, 4), "forma_m2": round(f, 3)})
        tot["concreto_m3"] += v
        tot["forma_m2"] += f
        tot[f"concreto_{e['tipo']}_m3"] += v
    aco = defaultdict(float)
    for b in dados.get("aco", []):
        phi = float(b["phi"])
        if phi not in KG_M:
            raise ValueError(f"bitola {phi} mm fora da tabela NBR 7480")
        aco[phi] += b["n"] * b["comprimento"] * KG_M[phi] * b.get("qtd", 1)
    aco_tab = [{"phi_mm": k, "kg": round(v, 2), "kg_com_perda": round(v * (1 + perda_aco / 100), 2)}
               for k, v in sorted(aco.items())]
    tot["aco_kg"] = sum(a["kg_com_perda"] for a in aco_tab)
    alv = []
    for p in dados.get("alvenaria", []):
        bruta, desc, liq = area_alvenaria(p, regra_vaos)
        alv.append({"id": p["id"], "bruta_m2": round(bruta, 3), "vaos_m2": round(desc, 3), "liquida_m2": round(liq, 3),
                    "espessura": p.get("espessura")})
        tot["alvenaria_m2"] += liq
    if tot["concreto_m3"]:
        tot["taxa_aco_kg_m3"] = tot["aco_kg"] / tot["concreto_m3"]
        tot["taxa_forma_m2_m3"] = tot["forma_m2"] / tot["concreto_m3"]
    return {"concreto": linhas, "aco": aco_tab, "alvenaria": alv, "totais": {k: round(v, 3) for k, v in tot.items()},
            "criterios": {"perda_aco_%": perda_aco, "desconto_vaos": regra_vaos, "h_laje_padrao_m": h_laje}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo")
    ap.add_argument("--perda-aco", type=float, default=10.0, help="perda/transpasse de aço em %% (padrão 10)")
    ap.add_argument("--vaos", choices=["total", "excedente-2m2"], default="total",
                    help="desconto de vãos na alvenaria: total (padrão) ou só o que excede 2 m² por vão")
    ap.add_argument("--formato", choices=["md", "json", "csv"], default="md")
    a = ap.parse_args(argv)
    r = calcular(json.loads(Path(a.arquivo).read_text(encoding="utf-8")), a.perda_aco, a.vaos)
    if a.formato == "json":
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif a.formato == "csv":
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(["servico", "unidade", "quantidade"])
        for k, u in (("concreto_m3", "m³"), ("forma_m2", "m²"), ("aco_kg", "kg"), ("alvenaria_m2", "m²")):
            if k in r["totais"]:
                w.writerow([k.split("_")[0], u, f"{r['totais'][k]:.3f}".replace(".", ",")])
        print(buf.getvalue(), end="")
    else:
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            imprimir_md(r, a)
        # números no padrão brasileiro (vírgula decimal)
        print(re.sub(r"(\d)\.(\d)", r"\1,\2", buf.getvalue()), end="")
    return 0


def imprimir_md(r: dict, a) -> None:
    print("### Concreto e fôrmas\n\n| Elemento | Tipo | Dimensões (m) | Qtd | Concreto (m³) | Fôrma (m²) |\n|---|---|---|---|---|---|")
    for l in r["concreto"]:
        print(f"| {l['id']} | {l['tipo']} | {l['dimensoes']} | {l['qtd']} | {l['concreto_m3']:.3f} | {l['forma_m2']:.2f} |")
    if r["aco"]:
        print(f"\n### Aço (perda {a.perda_aco:g}%)\n\n| Bitola | kg | kg c/ perda |\n|---|---|---|")
        for x in r["aco"]:
            print(f"| φ{x['phi_mm']:g} | {x['kg']:.1f} | {x['kg_com_perda']:.1f} |")
    if r["alvenaria"]:
        print(f"\n### Alvenaria (vãos: {a.vaos})\n\n| Parede | Bruta (m²) | Vãos (m²) | Líquida (m²) |\n|---|---|---|---|")
        for x in r["alvenaria"]:
            print(f"| {x['id']} | {x['bruta_m2']:.2f} | {x['vaos_m2']:.2f} | {x['liquida_m2']:.2f} |")
    print("\n### Totais\n")
    for k, v in r["totais"].items():
        print(f"- {k}: {v:.2f}")


if __name__ == "__main__":
    sys.exit(main())
