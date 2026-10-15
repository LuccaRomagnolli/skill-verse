#!/usr/bin/env python3
"""Conversões de unidade para o Revit (o modelo interno do Revit é em PÉS e RADIANOS).

- As ferramentas do MCP `revit` recebem milímetros e graus e convertem sozinhas.
- O código C# enviado por `send_code_to_revit` trabalha nas unidades internas: comprimento em pés
  (1 ft = 304,8 mm, exato), área em ft², volume em ft³, ângulo em radianos.

Uso:
  python3 revit_unidades.py 3.5 m ft          # 3,5 m em pés
  python3 revit_unidades.py 12.47 ft3 m3      # volume lido de um parâmetro → m³
  python3 revit_unidades.py 90 graus rad
"""
from __future__ import annotations

import argparse
import json
import math
import sys

MM_POR_PE = 304.8

# fator para converter a unidade em "base" (mm, mm², mm³, rad)
COMPRIMENTO = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "ft": MM_POR_PE, "in": 25.4}
AREA = {"mm2": 1.0, "cm2": 100.0, "m2": 1e6, "ft2": MM_POR_PE ** 2, "in2": 25.4 ** 2}
VOLUME = {"mm3": 1.0, "cm3": 1e3, "m3": 1e9, "ft3": MM_POR_PE ** 3, "in3": 25.4 ** 3, "l": 1e6}
ANGULO = {"rad": 1.0, "graus": math.pi / 180, "deg": math.pi / 180}
GRANDEZAS = (COMPRIMENTO, AREA, VOLUME, ANGULO)


def converter(valor: float, de: str, para: str) -> float:
    de, para = de.lower(), para.lower()
    for tabela in GRANDEZAS:
        if de in tabela and para in tabela:
            return valor * tabela[de] / tabela[para]
    raise ValueError(f"não converto {de} em {para} (grandezas diferentes ou unidade desconhecida)")


def mm_para_pes(mm: float) -> float:
    return mm / MM_POR_PE


def pes_para_mm(ft: float) -> float:
    return ft * MM_POR_PE


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
    print(json.dumps({"valor": a.valor, "de": a.de, "para": a.para, "resultado": round(r, 9)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
