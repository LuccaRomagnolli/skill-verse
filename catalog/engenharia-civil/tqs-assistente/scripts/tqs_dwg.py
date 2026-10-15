#!/usr/bin/env python3
"""Desenhos do TQS (módulo TQSDwg; geometria em cm e graus).

  ler      ARQ.DWG [--saida f.json] [--textos 300]   resumo: contagem por tipo e por nível, extensão, textos
  exportar ARQ.DWG SAIDA.DXF|SAIDA.PDF               converte (o PDF usa a configuração de plotagem do TQS)
  desenhar OPS.json SAIDA.DWG [--escala 50]          cria desenho TQS a partir de operações simples

OPS.json: [{"t":"nivel","n":10}, {"t":"linha","p":[x1,y1,x2,y2]}, {"t":"retangulo","p":[x1,y1,x2,y2]},
           {"t":"circulo","p":[xc,yc,r]}, {"t":"texto","p":[x,y],"h":0.25,"ang":0,"s":"P1 20x50"},
           {"t":"polilinha","pts":[[x,y],...]}, {"t":"cota_h","p":[x1,y1,x2,y2,x3,y3]}]
Alturas de texto e de símbolos são em cm de PAPEL × escala (a 1:50, h = 0,25 vira 12,5 cm no modelo).
Os desenhos gerados pelo TQS (formas, armações) devem ser alterados no próprio TQS: este script não edita
desenhos existentes, só lê, converte ou cria novos.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tqs_comum import emitir, falhar, importar, principal, valor  # noqa: E402


class Caixa:
    def __init__(self) -> None:
        self.xmin = self.ymin = float("inf")
        self.xmax = self.ymax = float("-inf")

    def add(self, x, y) -> None:
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            self.xmin, self.xmax = min(self.xmin, x), max(self.xmax, x)
            self.ymin, self.ymax = min(self.ymin, y), max(self.ymax, y)

    def lista(self):
        return None if self.xmin == float("inf") else [self.xmin, self.ymin, self.xmax, self.ymax]


def resumir(TQSDwg, dwg, max_textos: int = 300) -> dict:
    nomes = {getattr(TQSDwg, k): k.replace("DWGTYPE_", "") for k in dir(TQSDwg) if k.startswith("DWGTYPE_")}
    it = dwg.iterator
    por_tipo, por_nivel, textos, caixa = Counter(), Counter(), [], Caixa()
    it.Begin()
    while True:
        t = it.Next()
        if t == getattr(TQSDwg, "DWGTYPE_EOF", 0):
            break
        nome = nomes.get(t, str(t))
        por_tipo[nome] += 1
        por_nivel[valor(it, "level", "?")] += 1
        if nome in ("LINE",):
            caixa.add(valor(it, "x1"), valor(it, "y1"))
            caixa.add(valor(it, "x2"), valor(it, "y2"))
        elif nome in ("CIRCLE", "ARC"):
            caixa.add(valor(it, "xc"), valor(it, "yc"))
        elif nome == "TEXT":
            caixa.add(valor(it, "x1"), valor(it, "y1"))
            if len(textos) < max_textos:
                textos.append({"texto": valor(it, "text"), "x": valor(it, "x1"), "y": valor(it, "y1"),
                               "nivel": valor(it, "level")})
    return {"por_tipo": dict(por_tipo), "por_nivel": {str(k): v for k, v in sorted(por_nivel.items(), key=str)},
            "extensao_cm": caixa.lista(), "textos": textos, "textos_truncados": len(textos) >= max_textos}


def desenhar(dwg, ops: list[dict], escala: float) -> int:
    dwg.settings.scale = escala
    d = dwg.draw
    n = 0
    for op in ops:
        t, p = op.get("t"), op.get("p", [])
        if t == "nivel":
            d.level = int(op["n"])
            continue
        if t == "linha":
            d.Line(*p)
        elif t == "retangulo":
            d.Rectangle(*p)
        elif t == "circulo":
            d.Circle(*p)
        elif t == "texto":
            d.Text(p[0], p[1], op.get("h", 0.25), op.get("ang", 0.0), op["s"])
        elif t == "polilinha":
            d.PolyStart()
            for x, y in op["pts"]:
                d.PolyEnterPoint(x, y)
            d.Polyline()
        elif t == "cota_h":
            dwg.dim.DimHorizontal(*p)
        elif t == "cota_v":
            dwg.dim.DimVertical(*p)
        else:
            raise ValueError(f"operação desconhecida: {t}")
        n += 1
    return n


@principal
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("acao", choices=["ler", "exportar", "desenhar"])
    ap.add_argument("arquivo")
    ap.add_argument("destino", nargs="?")
    ap.add_argument("--escala", type=float, default=50.0)
    ap.add_argument("--textos", type=int, default=300)
    ap.add_argument("--saida")
    a = ap.parse_args(argv)
    TQSDwg = importar("TQSDwg")
    dwg = TQSDwg.Dwg()
    if a.acao == "desenhar":
        if not a.destino:
            ap.error("desenhar: informe o DWG de saída")
        dwg.file.New()
        n = desenhar(dwg, json.loads(Path(a.arquivo).read_text(encoding="utf-8")), a.escala)
        st = dwg.file.SaveAs(a.destino)
        if st not in (0, None):
            return falhar(f"não gravou {a.destino}")
        emitir({"ok": True, "entidades": n, "arquivo": a.destino})
        return 0
    if dwg.file.Open(a.arquivo) != 0:
        return falhar(f"não abri {a.arquivo}")
    if a.acao == "ler":
        emitir({"arquivo": a.arquivo, **resumir(TQSDwg, dwg, a.textos)}, a.saida)
    else:
        if not a.destino or Path(a.destino).suffix.upper() not in (".DXF", ".PDF", ".DWG"):
            ap.error("exportar: destino .DXF, .PDF ou .DWG")
        st = dwg.file.SaveAs(a.destino)
        if st not in (0, None):
            return falhar(f"o TQS não gravou {a.destino} (código {st})")
        emitir({"ok": True, "arquivo": a.destino})
    dwg.file.Close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
