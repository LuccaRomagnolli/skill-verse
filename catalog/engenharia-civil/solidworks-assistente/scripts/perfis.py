#!/usr/bin/env python3
"""Perfis e chapas de aço → chamadas do MCP `solidworks` + área, massa linear e peso.

Todas as dimensões em mm. Massa com aço de 7850 kg/m³ (padrão; mude com --densidade).
Cantos vivos: perfis laminados reais têm raio de concordância, então a área de catálogo do fabricante
é ligeiramente maior. Para orçamento, prefira a massa nominal do catálogo quando o usuário tiver.

Tipos e parâmetros:
  chapa    --b --h --t [--furos "x,y,d;x,y,d"]   (b × h em planta, espessura t; furos a partir do centro)
  I        --d --bf --tw --tf                     (I/H/W soldado ou laminado, simétrico)
  U        --d --bf --tw --tf                     (U laminado/soldado, alma à esquerda)
  Ue       --d --bf --c --t                       (U enrijecido de chapa dobrada; c = enrijecedor)
  L        --b1 --b2 --t                          (cantoneira)
  tubo-ret --b --h --t
  tubo-cir --D --t
  barra    --D

Exemplos:
  python3 perfis.py I --d 200 --bf 100 --tw 5.6 --tf 8.5 --comprimento 6000 --nome "Viga W200" --ops w200.json
  python3 perfis.py chapa --b 300 --h 300 --t 16 --furos "-110,-110,22;110,-110,22;110,110,22;-110,110,22" --nome "Chapa de base"
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

DENSIDADE_ACO = 7850.0  # kg/m³
MATERIAL_SW = "ASTM A36 Steel"  # nome na biblioteca "SOLIDWORKS Materials" (alternativa: "Plain Carbon Steel")


def area_poligono(pts: list[tuple[float, float]]) -> float:
    """Fórmula do laço (shoelace), mm²."""
    s = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def contorno(tipo: str, a) -> list[tuple[float, float]] | None:
    """Contorno fechado (anti-horário) centrado na origem quando o perfil é simétrico."""
    if tipo == "I":
        d, bf, tw, tf = a.d, a.bf, a.tw, a.tf
        x, y = bf / 2, d / 2
        return [(-x, -y), (x, -y), (x, -y + tf), (tw / 2, -y + tf), (tw / 2, y - tf), (x, y - tf), (x, y),
                (-x, y), (-x, y - tf), (-tw / 2, y - tf), (-tw / 2, -y + tf), (-x, -y + tf)]
    if tipo == "U":
        d, bf, tw, tf = a.d, a.bf, a.tw, a.tf
        y = d / 2
        return [(0, -y), (bf, -y), (bf, -y + tf), (tw, -y + tf), (tw, y - tf), (bf, y - tf), (bf, y), (0, y)]
    if tipo == "Ue":
        d, bf, c, t = a.d, a.bf, a.c, a.t
        y = d / 2
        return [(0, -y), (bf, -y), (bf, -y + c), (bf - t, -y + c), (bf - t, -y + t), (t, -y + t), (t, y - t),
                (bf - t, y - t), (bf - t, y - c), (bf, y - c), (bf, y), (0, y)]
    if tipo == "L":
        b1, b2, t = a.b1, a.b2, a.t
        return [(0, 0), (b1, 0), (b1, t), (t, t), (t, b2), (0, b2)]
    if tipo == "chapa":
        return [(-a.b / 2, -a.h / 2), (a.b / 2, -a.h / 2), (a.b / 2, a.h / 2), (-a.b / 2, a.h / 2)]
    return None


def validar(tipo: str, a) -> list[str]:
    erros = []
    if tipo in ("I", "U") and (2 * a.tf >= a.d or a.tw >= a.bf):
        erros.append("mesas/alma incompatíveis com d e bf")
    if tipo == "Ue" and (a.c <= a.t or 2 * a.c >= a.d or 2 * a.t >= a.bf):
        erros.append("enrijecedor c deve ser > t e < d/2; 2t < bf")
    if tipo == "L" and (a.t >= min(a.b1, a.b2)):
        erros.append("t deve ser menor que as abas")
    if tipo == "tubo-ret" and 2 * a.t >= min(a.b, a.h):
        erros.append("2t deve ser menor que b e h")
    if tipo == "tubo-cir" and 2 * a.t >= a.D:
        erros.append("2t deve ser menor que D")
    return erros


def furos(spec: str | None) -> list[tuple[float, float, float]]:
    if not spec:
        return []
    out = []
    for item in spec.split(";"):
        x, y, d = (float(v) for v in item.split(","))
        out.append((x, y, d))
    return out


def calcular(tipo: str, a) -> dict:
    erros = validar(tipo, a)
    if erros:
        raise ValueError("; ".join(erros))
    ops = [{"tool": "solidworks_new_part", "args": {}},
           {"tool": "solidworks_create_sketch", "args": {"plane": a.plano}}]
    pts = contorno(tipo, a)
    if pts:
        area = area_poligono(pts)
        segs = [{"type": "LINE", "x": round(x, 4), "y": round(y, 4)} for x, y in pts[1:]]
        ops.append({"tool": "solidworks_sketch_profile",
                    "args": {"startX": round(pts[0][0], 4), "startY": round(pts[0][1], 4), "segments": segs, "close": True}})
    elif tipo == "tubo-ret":
        area = a.b * a.h - (a.b - 2 * a.t) * (a.h - 2 * a.t)
        ops += [{"tool": "solidworks_sketch_rectangle", "args": {"width": a.b, "height": a.h, "centerX": 0, "centerY": 0}},
                {"tool": "solidworks_sketch_rectangle",
                 "args": {"width": a.b - 2 * a.t, "height": a.h - 2 * a.t, "centerX": 0, "centerY": 0}}]
    elif tipo == "tubo-cir":
        area = math.pi / 4 * (a.D ** 2 - (a.D - 2 * a.t) ** 2)
        ops += [{"tool": "solidworks_sketch_circle", "args": {"centerX": 0, "centerY": 0, "radius": a.D / 2}},
                {"tool": "solidworks_sketch_circle", "args": {"centerX": 0, "centerY": 0, "radius": a.D / 2 - a.t}}]
    elif tipo == "barra":
        area = math.pi / 4 * a.D ** 2
        ops.append({"tool": "solidworks_sketch_circle", "args": {"centerX": 0, "centerY": 0, "radius": a.D / 2}})
    else:
        raise ValueError(f"tipo desconhecido: {tipo}")

    fs = furos(getattr(a, "furos", None)) if tipo == "chapa" else []
    for x, y, d in fs:
        if abs(x) + d / 2 >= a.b / 2 or abs(y) + d / 2 >= a.h / 2:
            raise ValueError(f"furo ({x},{y}) ⌀{d} sai da chapa")
        ops.append({"tool": "solidworks_sketch_circle", "args": {"centerX": x, "centerY": y, "radius": d / 2}})
        area -= math.pi / 4 * d ** 2

    # chapa: extrusão = espessura; perfis: extrusão = comprimento
    prof = a.t if tipo == "chapa" else a.comprimento
    if not prof or prof <= 0:
        raise ValueError("informe --comprimento (mm) para perfis")
    ops.append({"tool": "solidworks_create_extrusion", "args": {"depth": prof}})
    ops.append({"tool": "solidworks_set_material", "args": {"material": a.material}})
    if a.nome:
        ops.append({"tool": "solidworks_rename_feature", "args": {"name": "$ultima_extrusao", "newName": a.nome}})
    ops.append({"tool": "solidworks_get_mass_properties", "args": {}})

    volume_mm3 = area * prof
    massa = volume_mm3 * 1e-9 * a.densidade
    res = {"tipo": tipo, "area_mm2": round(area, 2), "volume_cm3": round(volume_mm3 / 1000, 2),
           "massa_kg": round(massa, 3), "densidade_kg_m3": a.densidade, "ops": ops,
           "conferencia": "compare massa_kg com solidworks_get_mass_properties (diferença < 1% esperada)"}
    if tipo != "chapa":
        res["massa_linear_kg_m"] = round(area * 1e-6 * a.densidade, 3)
        res["comprimento_mm"] = prof
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tipo", choices=["chapa", "I", "U", "Ue", "L", "tubo-ret", "tubo-cir", "barra"])
    for p in ("b", "h", "t", "d", "bf", "tw", "tf", "c", "b1", "b2", "D"):
        ap.add_argument(f"--{p}", type=float)
    ap.add_argument("--furos", help='chapa: "x,y,d;x,y,d" em mm, a partir do centro')
    ap.add_argument("--comprimento", type=float, help="comprimento do perfil (mm)")
    ap.add_argument("--plano", default="Front", help="plano do esboço: Front, Top ou Right")
    ap.add_argument("--densidade", type=float, default=DENSIDADE_ACO)
    ap.add_argument("--material", default=MATERIAL_SW)
    ap.add_argument("--nome", help="nome da feature na árvore (ex.: 'Chapa de base P1')")
    ap.add_argument("--ops", help="grava só a lista de chamadas do MCP neste arquivo")
    a = ap.parse_args(argv)
    req = {"chapa": "b h t", "I": "d bf tw tf", "U": "d bf tw tf", "Ue": "d bf c t", "L": "b1 b2 t",
           "tubo-ret": "b h t", "tubo-cir": "D t", "barra": "D"}[a.tipo].split()
    faltam = [p for p in req if getattr(a, p) is None]
    if faltam:
        ap.error(f"{a.tipo}: faltam --{', --'.join(faltam)}")
    try:
        res = calcular(a.tipo, a)
    except ValueError as e:
        ap.error(str(e))
    if a.ops:
        Path(a.ops).write_text(json.dumps(res["ops"], indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "ops" or not a.ops}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
