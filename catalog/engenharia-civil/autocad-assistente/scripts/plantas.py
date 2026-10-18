#!/usr/bin/env python3
"""Gera plantas de fôrma e pranchas DXF/ops a partir do modelo estrutural v1."""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from argparse import Namespace
from pathlib import Path

from detalhe_secao import para_dxf, para_ops
import prancha

LAYERS = [("EST-EIXO", 8), ("EST-PILAR", 1), ("EST-VIGA", 2), ("EST-LAJE", 3),
          ("EST-TEXTO", 4), ("EST-COTA", 7)]


def _modelo():
    f = Path(__file__).resolve().parents[2] / "modelo-estrutural/scripts/modelo.py"
    spec = importlib.util.spec_from_file_location("skillverse_modelo_cad", f)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def planta(d: dict, nivel: str) -> dict:
    cotas = {n["id"]: n["cota_m"] for n in d["niveis"]}
    if nivel not in cotas:
        raise ValueError(f"nível inexistente: {nivel}")
    pontos = []
    for l in d.get("lajes", []):
        if l["nivel"] == nivel:
            pontos.extend(l["contorno"])
    for v in d.get("vigas", []):
        if v["nivel"] == nivel:
            pontos += [v["de"], v["ate"]]
    for p in d.get("pilares", []):
        if cotas[p["base"]] <= cotas[nivel] <= cotas[p["topo"]]:
            pontos.append([p["x_m"], p["y_m"]])
    if not pontos:
        raise ValueError(f"nível {nivel}: sem peças")
    xmin, xmax = min(x for x, _ in pontos), max(x for x, _ in pontos)
    ymin, ymax = min(y for _, y in pontos), max(y for _, y in pontos)
    ent = []

    def line(x1, y1, x2, y2, lay):
        ent.append({"t": "line", "layer": lay, "p": [round(x1, 5), round(y1, 5), round(x2, 5), round(y2, 5)]})

    def label(x, y, s):
        ent.append({"t": "text", "layer": "EST-TEXTO", "p": [round(x, 5), round(y, 5)], "s": s, "h": .14})

    for axis in d.get("eixos", {}).get("x", []):
        x = axis["pos_m"]
        line(x, ymin - .45, x, ymax + .45, "EST-EIXO")
        label(x + .05, ymax + .5, str(axis["nome"]))
    for axis in d.get("eixos", {}).get("y", []):
        y = axis["pos_m"]
        line(xmin - .45, y, xmax + .45, y, "EST-EIXO")
        label(xmax + .5, y + .05, str(axis["nome"]))
    for l in d.get("lajes", []):
        if l["nivel"] != nivel:
            continue
        vertices = l["contorno"]
        for a, b in zip(vertices, vertices[1:] + vertices[:1]):
            line(*a, *b, "EST-LAJE")
        cx = sum(x for x, _ in vertices) / len(vertices)
        cy = sum(y for _, y in vertices) / len(vertices)
        label(cx, cy, f"{l['id']} h={l['espessura_m'] * 100:g}cm")
    for v in d.get("vigas", []):
        if v["nivel"] != nivel:
            continue
        (x1, y1), (x2, y2) = v["de"], v["ate"]
        length = math.hypot(x2 - x1, y2 - y1)
        ox = -(y2 - y1) / length * v["b_m"] / 2
        oy = (x2 - x1) / length * v["b_m"] / 2
        line(x1 + ox, y1 + oy, x2 + ox, y2 + oy, "EST-VIGA")
        line(x1 - ox, y1 - oy, x2 - ox, y2 - oy, "EST-VIGA")
        if abs(y2 - y1) < 1e-9:
            tx, ty = (x1 + x2) / 2, y1 + v["b_m"] / 2 + .08
        elif abs(x2 - x1) < 1e-9:
            tx, ty = x1 + v["b_m"] / 2 + .08, (y1 + y2) / 2
        else:
            tx, ty = (x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy
        label(tx, ty, f"{v['id']} {v['b_m'] * 100:g}x{v['h_m'] * 100:g}")
    for p in d.get("pilares", []):
        if not cotas[p["base"]] <= cotas[nivel] <= cotas[p["topo"]]:
            continue
        x, y = p["x_m"], p["y_m"]
        ent.append({"t": "rect", "layer": "EST-PILAR", "p": [x - p["b_m"] / 2, y - p["h_m"] / 2, x + p["b_m"] / 2, y + p["h_m"] / 2]})
        label(x + p["b_m"] / 2 + .05, y + p["h_m"] / 2 + .05, p["id"])
    # Cotas estáticas em metros: o DXF R12 não recebe DIMENSION nativa deste gerador.
    # A medida escrita é explícita e deve ser refeita/conferida no AutoCAD.
    if xmax > xmin:
        line(xmin, ymin - .55, xmax, ymin - .55, "EST-COTA")
        line(xmin, ymin - .48, xmin, ymin - .62, "EST-COTA")
        line(xmax, ymin - .48, xmax, ymin - .62, "EST-COTA")
        label((xmin + xmax) / 2, ymin - .8, f"{xmax - xmin:.3f} m")
    if ymax > ymin:
        line(xmin - .55, ymin, xmin - .55, ymax, "EST-COTA")
        line(xmin - .48, ymin, xmin - .62, ymin, "EST-COTA")
        line(xmin - .48, ymax, xmin - .62, ymax, "EST-COTA")
        label(xmin - 1.4, (ymin + ymax) / 2, f"{ymax - ymin:.3f} m")
    label(xmin, ymax + .9, f"PLANTA DE FORMA {nivel} - REV {d['projeto']['revisao']}")
    return {"nome": nivel, "entidades": ent, "limites": [xmin, ymin, xmax, ymax]}


def secao_forma(d: dict) -> dict:
    ent, x = [], 0.0
    seen = set()
    for tipo in ("pilares", "vigas"):
        for e in d.get(tipo, []):
            key = (tipo, e["b_m"], e["h_m"])
            if key in seen:
                continue
            seen.add(key)
            b, h = e["b_m"], e["h_m"]
            ent.append({"t": "rect", "layer": "EST-PILAR" if tipo == "pilares" else "EST-VIGA", "p": [x, 0, x + b, h]})
            ent.append({"t": "text", "layer": "EST-TEXTO", "p": [x, h + .1], "s": f"{tipo[:-1].upper()} {b * 100:g}x{h * 100:g} cm", "h": .08})
            x += max(b + .8, 1.5)
    ent.append({"t": "text", "layer": "EST-TEXTO", "p": [0, -.3], "s": "SECOES DE FORMA - SEM ARMADURA / DETALHAMENTO", "h": .1})
    return {"nome": "secoes-forma", "entidades": ent}


def gerar(d: dict, saida: Path, formato="A3", escala=50):
    m = _modelo()
    m.validar(d)
    saida.mkdir(parents=True, exist_ok=True)
    resumo = {"projeto": d["projeto"], "sha256_entrada": m.digest(d), "plantas": [], "secoes": None,
              "estado": "desenho-de-apoio; revisar no AutoCAD"}
    for n in d["niveis"]:
        try:
            g = planta(d, n["id"])
        except ValueError as exc:
            if "sem peças" in str(exc):
                continue
            raise
        slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in n["id"])
        base = saida / f"planta-{slug}"
        (base.with_suffix(".dxf")).write_text(para_dxf([g], LAYERS, 6), encoding="cp1252", errors="replace")
        (base.with_suffix(".ops.json")).write_text(json.dumps(para_ops(g, LAYERS), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Prancha em espaço do modelo, na unidade m, com carimbo da revisão.
        args = Namespace(formato=formato, escala=escala, unidade="m", vertical=False, obra=d["projeto"]["id"],
                         local="", cliente="", conteudo=f"Planta de forma {n['id']}", rt="", registro="", art="",
                         folha="01/01", revisao=d["projeto"]["revisao"], data="")
        folha = prancha.geometria(args)
        k = prancha.fator(escala, "m")
        pw, ph = prancha.FORMATOS[formato]
        xmin, ymin, xmax, ymax = g["limites"]
        origem_x = (prancha.MARGEM_ESQ + 12) * k
        origem_y = (prancha.MARGEM[formato] + 65) * k
        if xmax - xmin > (pw - prancha.MARGEM_ESQ - prancha.MARGEM[formato] - 25) * k or ymax - ymin > (ph - 2 * prancha.MARGEM[formato] - 80) * k:
            raise ValueError(f"{n['id']}: planta não cabe em {formato} 1:{escala}; escolha formato/escala apropriados")
        trans = json.loads(json.dumps(g))
        for e in trans["entidades"]:
            p = e["p"]
            if e["t"] == "text":
                e["p"] = [p[0] - xmin + origem_x, p[1] - ymin + origem_y]
            else:
                e["p"] = [p[0] - xmin + origem_x, p[1] - ymin + origem_y, p[2] - xmin + origem_x, p[3] - ymin + origem_y]
        folha["entidades"] += trans["entidades"]
        (saida / f"prancha-{slug}.dxf").write_text(para_dxf([folha], LAYERS + prancha.LAYERS_PRANCHA, 6), encoding="cp1252", errors="replace")
        resumo["plantas"].append({"nivel": n["id"], "dxf": str(base.with_suffix(".dxf")),
                                  "ops": str(base.with_suffix(".ops.json")), "prancha_dxf": str(saida / f"prancha-{slug}.dxf")})
    if d.get("pilares") or d.get("vigas"):
        g = secao_forma(d)
        p = saida / "secoes-forma.dxf"
        p.write_text(para_dxf([g], LAYERS, 6), encoding="cp1252", errors="replace")
        resumo["secoes"] = str(p)
    (saida / "manifesto-cad.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return resumo


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("modelo", type=Path)
    ap.add_argument("--saida", type=Path, required=True)
    ap.add_argument("--formato", choices=prancha.FORMATOS, default="A3")
    ap.add_argument("--escala", type=int, choices=prancha.ESCALAS, default=50)
    a = ap.parse_args()
    d = json.loads(a.modelo.read_text(encoding="utf-8"))
    print(json.dumps(gerar(d, a.saida, a.formato, a.escala), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
