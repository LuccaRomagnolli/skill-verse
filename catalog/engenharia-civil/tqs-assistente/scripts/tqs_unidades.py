#!/usr/bin/env python3
"""Conversões entre as unidades do TQS (tf, tf/m, tf/m², tf·m, cm) e o SI usado nas outras skills.

1 tf = 9,80665 kN (exato, gravidade padrão). Uso:
  python scripts/tqs_unidades.py 12.5 tf kN
  python scripts/tqs_unidades.py 0.35 tf/m2 kN/m2
  python scripts/tqs_unidades.py 4.2 tfm kNm
"""
from __future__ import annotations

import argparse
import json
import sys

G = 9.80665  # kN por tf

# fator para a unidade-base de cada grandeza (kN, kN/m, kN/m², kN·m, m)
TABELAS = [
    {"kn": 1.0, "tf": G, "kgf": G / 1000, "n": 1e-3},
    {"kn/m": 1.0, "tf/m": G, "kgf/m": G / 1000},
    {"kn/m2": 1.0, "kpa": 1.0, "tf/m2": G, "kgf/m2": G / 1000, "kgf/cm2": G * 10, "mpa": 1000.0},
    {"knm": 1.0, "kn.m": 1.0, "tfm": G, "tf.m": G, "kgfm": G / 1000},
    {"m": 1.0, "cm": 0.01, "mm": 0.001},
]


def converter(valor: float, de: str, para: str) -> float:
    de, para = de.lower().replace("²", "2").replace("·", "."), para.lower().replace("²", "2").replace("·", ".")
    for t in TABELAS:
        if de in t and para in t:
            return valor * t[de] / t[para]
    raise ValueError(f"não converto {de} em {para}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("valor", type=float)
    ap.add_argument("de")
    ap.add_argument("para")
    a = ap.parse_args(argv)
    try:
        r = converter(a.valor, a.de, a.para)
    except ValueError as e:
        ap.error(str(e))
    print(json.dumps({"valor": a.valor, "de": a.de, "para": a.para, "resultado": round(r, 6)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
