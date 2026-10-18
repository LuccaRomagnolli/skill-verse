#!/usr/bin/env python3
"""Gera o detalhe da seção transversal de viga ou pilar retangular (forma, estribo, barras, cotas, textos).

Saídas:
  --ops arquivo.json   lista de chamadas para o MCP do AutoCAD (layer/entity/annotation), em ordem
  --dxf arquivo.dxf    desenho DXF (R12, abre em qualquer CAD) — não precisa de AutoCAD

Unidades do desenho: centímetros (1 unidade = 1 cm). Origem no canto inferior esquerdo da seção.

Exemplos:
  python3 detalhe_secao.py --b 15 --h 45 --c 3 --inf 3x12.5 --sup 2x8 --estribo 5 --s 13 --nome V1 --dxf V1.dxf
  python3 detalhe_secao.py --b 20 --h 50 --c 3 --pilar 3 --phi 20 --estribo 5 --s 20 --nome P1 --ops P1.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

LAYERS = [  # nome, cor ACI
    ("EST-FORMA", 7), ("EST-ESTRIBO", 3), ("EST-BARRA", 1), ("EST-COTA", 2), ("EST-TEXTO", 4),
]


def dec(s: str) -> str:
    """Vírgula decimal só entre dígitos (preserva 'inf.')."""
    return re.sub(r"(\d)\.(\d)", r"\1,\2", s)


# Cobrimento nominal de vigas e pilares por CAA (cm) — NBR 6118 Tabela 7.2
COBRIMENTO_VP = {"I": 2.5, "II": 3.0, "III": 4.0, "IV": 5.0}


def cobrimento_da_ficha(contexto: str | None) -> float | None:
    f = Path(contexto) if contexto else None
    if f and f.is_file():
        caa = (json.loads(f.read_text(encoding="utf-8")).get("caa") or {}).get("classe")
        return COBRIMENTO_VP.get(caa)
    return None


def parse_barras(s: str) -> tuple[int, float]:
    n, phi = s.lower().replace("φ", "").split("x")
    return int(n), float(phi.replace(",", "."))


def linha_barras(n: int, phi_mm: float, y: float, x0: float, x1: float) -> list[tuple[float, float, float]]:
    r = phi_mm / 20  # cm
    if n == 1:
        return [((x0 + x1) / 2, y, r)]
    return [(x0 + i * (x1 - x0) / (n - 1), y, r) for i in range(n)]


def geometria(a) -> dict:
    b, h, c = a.b, a.h, a.c
    et = a.estribo / 10  # cm
    ent: list[dict] = []
    ent.append({"t": "rect", "layer": "EST-FORMA", "p": [0, 0, b, h]})
    # estribo: retângulo no eixo do estribo
    o = c + et / 2
    ent.append({"t": "rect", "layer": "EST-ESTRIBO", "p": [o, o, b - o, h - o]})
    barras = []
    if a.pilar:
        n, phi = a.pilar, a.phi
        r = phi / 20
        e = c + et + r
        xs = [e + i * (b - 2 * e) / (n - 1) for i in range(n)]
        ys = [e + i * (h - 2 * e) / (n - 1) for i in range(n)]
        pts = {(x, e) for x in xs} | {(x, h - e) for x in xs} | {(e, y) for y in ys} | {(b - e, y) for y in ys}
        barras = [(x, y, r) for x, y in sorted(pts)]
        desc_barras = f"{len(barras)} φ{phi:g}"
    else:
        desc = []
        if a.inf:
            n, phi = parse_barras(a.inf)
            r = phi / 20
            barras += linha_barras(n, phi, c + et + r, c + et + r, b - c - et - r)
            desc.append(f"{n} φ{phi:g} (inf.)")
        if a.sup:
            n, phi = parse_barras(a.sup)
            r = phi / 20
            barras += linha_barras(n, phi, h - c - et - r, c + et + r, b - c - et - r)
            desc.append(f"{n} φ{phi:g} (sup.)")
        desc_barras = " + ".join(desc)
    for x, y, r in barras:
        ent.append({"t": "circle", "layer": "EST-BARRA", "p": [round(x, 3), round(y, 3), round(r, 3)]})
    # cotas
    ent.append({"t": "dim", "layer": "EST-COTA", "p": [0, 0, b, 0], "pos": [b / 2, -6]})
    ent.append({"t": "dim", "layer": "EST-COTA", "p": [b, 0, b, h], "pos": [b + 6, h / 2]})
    # textos
    th = max(1.5, min(b, h) / 12)
    txt_est = f"Estribo φ{a.estribo:g} c/{a.s:g}" if a.s else f"Estribo φ{a.estribo:g}"
    ent.append({"t": "text", "layer": "EST-TEXTO", "p": [0, h + 3 * th], "h": th * 1.3,
                "s": dec(f"{a.nome} — {b:g}×{h:g}")})
    ent.append({"t": "text", "layer": "EST-TEXTO", "p": [0, -12], "h": th, "s": dec(desc_barras)})
    ent.append({"t": "text", "layer": "EST-TEXTO", "p": [0, -12 - 1.8 * th], "h": th, "s": dec(txt_est)})
    ent.append({"t": "text", "layer": "EST-TEXTO", "p": [0, -12 - 3.6 * th], "h": th * 0.8, "s": dec(f"c = {a.c:g} cm")})
    return {"entidades": ent, "nome": a.nome}


def deslocar(g: dict, dx: float, dy: float) -> None:
    for e in g["entidades"]:
        p = e["p"]
        if e["t"] in ("rect", "dim"):
            e["p"] = [p[0] + dx, p[1] + dy, p[2] + dx, p[3] + dy]
            if "pos" in e:
                e["pos"] = [e["pos"][0] + dx, e["pos"][1] + dy]
        else:
            e["p"] = [p[0] + dx, p[1] + dy, *p[2:]]


# ------------------------------------------------------------------ MCP AutoCAD

def para_ops(g: dict, layers=LAYERS) -> list[dict]:
    ops = [{"tool": "layer", "operation": "create", "data": {"name": n, "color": c}} for n, c in layers]
    for e in g["entidades"]:
        p = e["p"]
        if e["t"] == "line":
            ops.append({"tool": "entity", "operation": "create_line", "x1": p[0], "y1": p[1], "x2": p[2], "y2": p[3],
                        "layer": e["layer"]})
        elif e["t"] == "rect":
            ops.append({"tool": "entity", "operation": "create_rectangle", "x1": p[0], "y1": p[1], "x2": p[2], "y2": p[3],
                        "layer": e["layer"]})
        elif e["t"] == "circle":  # barra cheia: polígono de 24 lados + hachura SOLID (funciona nos dois backends)
            cx, cy, r = p
            pts = [[round(cx + r * math.cos(2 * math.pi * k / 24), 4), round(cy + r * math.sin(2 * math.pi * k / 24), 4)]
                   for k in range(24)]
            ops.append({"tool": "entity", "operation": "create_polyline", "points": pts, "data": {"closed": True},
                        "layer": e["layer"]})
            ops.append({"tool": "entity", "operation": "create_hatch", "entity_id": "$anterior", "data": {"pattern": "SOLID"}})
        elif e["t"] == "dim":
            ops.append({"tool": "annotation", "operation": "create_dimension_linear",
                        "data": {"x1": p[0], "y1": p[1], "x2": p[2], "y2": p[3], "dim_x": e["pos"][0], "dim_y": e["pos"][1]}})
        elif e["t"] == "text":
            ops.append({"tool": "annotation", "operation": "create_text",
                        "data": {"x": p[0], "y": p[1], "text": e["s"], "height": round(e["h"], 2), "layer": e["layer"]}})
    ops.append({"tool": "view", "operation": "zoom_extents"})
    return ops


# ------------------------------------------------------------------ DXF R12

def dxf_txt(s: str) -> str:
    """Escapa Unicode em DXF R12 para preservar acentos no AutoCAD."""
    s = s.replace("φ", "%%c").replace("—", "-").replace("×", "x")
    return "".join(c if ord(c) < 128 else f"\\U+{ord(c):04X}" for c in s)


def para_dxf(gs: list[dict], layers=LAYERS, insunits: int = 5) -> str:
    """insunits: 4 = mm, 5 = cm, 6 = m."""
    L = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "9", "$DWGCODEPAGE", "3", "ANSI_1252",
         "9", "$INSUNITS", "70", str(insunits), "0", "ENDSEC",
         "0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER", "70", str(len(layers))]
    for n, c in layers:
        L += ["0", "LAYER", "2", n, "70", "0", "62", str(c), "6", "CONTINUOUS"]
    L += ["0", "ENDTAB", "0", "TABLE", "2", "STYLE", "70", "1",
          "0", "STYLE", "2", "SV-TEXT", "70", "0", "40", "0", "41", "1", "50", "0", "71", "0",
          "42", "2.5", "3", "Arial.ttf", "4", "", "0", "ENDTAB", "0", "ENDSEC",
          "0", "SECTION", "2", "ENTITIES"]

    def line(x1, y1, x2, y2, layer):
        return ["0", "LINE", "8", layer, "10", f"{x1}", "20", f"{y1}", "11", f"{x2}", "21", f"{y2}"]

    for g in gs:
        for e in g["entidades"]:
            p, lay = e["p"], e["layer"]
            if e["t"] == "line":
                L += line(*p, lay)
            elif e["t"] == "rect":
                x1, y1, x2, y2 = p
                L += ["0", "POLYLINE", "8", lay, "66", "1", "70", "1"]
                for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
                    L += ["0", "VERTEX", "8", lay, "10", f"{x}", "20", f"{y}"]
                L += ["0", "SEQEND", "8", lay]
            elif e["t"] == "circle":
                L += ["0", "CIRCLE", "8", lay, "10", f"{p[0]}", "20", f"{p[1]}", "40", f"{p[2]}"]
                # preenchimento: anel com largura = diâmetro (polilinha de largura, compatível R12)
                r = p[2] / 2
                L += ["0", "POLYLINE", "8", lay, "66", "1", "70", "1", "40", f"{p[2]}", "41", f"{p[2]}"]
                for ang in (0, 180):
                    L += ["0", "VERTEX", "8", lay, "10", f"{p[0] + r * math.cos(math.radians(ang))}",
                          "20", f"{p[1] + r * math.sin(math.radians(ang))}", "42", "1"]
                L += ["0", "SEQEND", "8", lay]
            elif e["t"] == "dim":  # cota desenhada como linhas + texto (portável)
                x1, y1, x2, y2 = p
                px, py = e["pos"]
                if y1 == y2:
                    L += line(x1, py, x2, py, lay) + line(x1, y1 - 1, x1, py - 1, lay) + line(x2, y2 - 1, x2, py - 1, lay)
                    val, tx, ty, rot = abs(x2 - x1), (x1 + x2) / 2, py + 0.8, 0
                else:
                    L += line(px, y1, px, y2, lay) + line(x1 + 1, y1, px + 1, y1, lay) + line(x2 + 1, y2, px + 1, y2, lay)
                    val, tx, ty, rot = abs(y2 - y1), px - 0.8, (y1 + y2) / 2, 90
                L += ["0", "TEXT", "8", lay, "7", "SV-TEXT", "10", f"{tx}", "20", f"{ty}", "40", "2", "1", f"{val:g}".replace(".", ","),
                      "50", f"{rot}", "72", "1", "11", f"{tx}", "21", f"{ty}"]
            elif e["t"] == "text":
                L += ["0", "TEXT", "8", lay, "7", "SV-TEXT", "10", f"{p[0]}", "20", f"{p[1]}", "40", f"{e['h']:.2f}", "1", dxf_txt(e["s"])]
    L += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--b", type=float, required=True, help="largura (cm)")
    ap.add_argument("--h", type=float, required=True, help="altura (cm)")
    ap.add_argument("--c", type=float, help="cobrimento (cm); padrão: pela CAA da ficha do projeto (NBR 6118 Tab. 7.2) ou 3,0")
    ap.add_argument("--contexto", default="projeto-contexto.json", help="ficha do projeto (skill contexto-do-projeto)")
    ap.add_argument("--estribo", type=float, default=5.0, help="φ do estribo (mm)")
    ap.add_argument("--s", type=float, help="espaçamento dos estribos (cm), só para o texto")
    ap.add_argument("--inf", help="viga: barras inferiores, ex. 3x12.5")
    ap.add_argument("--sup", default="2x8", help="viga: barras superiores (porta-estribo), ex. 2x8")
    ap.add_argument("--pilar", type=int, help="pilar: barras por face (distribuição nas 4 faces)")
    ap.add_argument("--phi", type=float, default=12.5, help="pilar: bitola longitudinal (mm)")
    ap.add_argument("--nome", default="SEÇÃO")
    ap.add_argument("--origem", type=float, nargs=2, default=[0, 0], help="posição do canto inferior esquerdo (cm)")
    ap.add_argument("--ops", help="grava JSON de operações para o MCP do AutoCAD")
    ap.add_argument("--dxf", help="grava arquivo DXF")
    a = ap.parse_args(argv)
    if not a.pilar and not a.inf:
        ap.error("viga: informe --inf; pilar: informe --pilar")
    if a.c is None:
        a.c = cobrimento_da_ficha(a.contexto) or 3.0
    g = geometria(a)
    deslocar(g, *a.origem)
    if a.ops:
        Path(a.ops).write_text(json.dumps(para_ops(g), indent=1, ensure_ascii=False), encoding="utf-8")
    if a.dxf:
        Path(a.dxf).write_text(para_dxf([g]), encoding="cp1252", errors="replace")
    print(json.dumps({"nome": a.nome, "entidades": len(g["entidades"]), "ops": a.ops, "dxf": a.dxf}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
