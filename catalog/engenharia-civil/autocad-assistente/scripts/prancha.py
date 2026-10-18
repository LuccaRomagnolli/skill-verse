#!/usr/bin/env python3
"""Prancha de desenho: formato A0–A4 com margens, moldura e carimbo, na escala e na unidade do desenho.

Desenha no espaço do modelo, já multiplicado pela escala (o jeito mais simples de plotar pelo MCP, que não
cria layouts/viewports). Também responde "qual formato e escala cabem este desenho" (--cabe).

Saídas:
  --ops arquivo.json   chamadas para o MCP do AutoCAD (mesmo formato do detalhe_secao.py)
  --dxf arquivo.dxf    DXF R12 pronto, sem precisar do AutoCAD
  (sempre) JSON no stdout com fator de escala, área útil e alturas de texto convertidas

Exemplos:
  python3 prancha.py --formato A1 --escala 50 --unidade cm --obra "Residência Silva" --conteudo "Planta de fôrmas" \\
      --rt "Eng. Fulano" --registro "CREA-GO 0000" --folha 1/3 --ops A1.json --dxf A1.dxf
  python3 prancha.py --cabe 18.5 12.0 --unidade m        # desenho de 18,5 × 12,0 m: sugere formato e escala
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from detalhe_secao import dec, para_dxf, para_ops  # noqa: E402

# Formatos da série A (ISO 216; NBR 16752:2020, que substituiu a NBR 10068): largura × altura em mm, deitada
FORMATOS = {"A0": (1189, 841), "A1": (841, 594), "A2": (594, 420), "A3": (420, 297), "A4": (297, 210)}
# Margens usuais (mm): esquerda maior para encadernação; demais lados conforme o formato
MARGEM_ESQ = 25.0
MARGEM = {"A0": 10.0, "A1": 10.0, "A2": 7.0, "A3": 7.0, "A4": 7.0}
LARGURA_CARIMBO = {"A0": 175.0, "A1": 175.0, "A2": 178.0, "A3": 178.0, "A4": 178.0}
# Escalas usuais em projeto de edificações (redução), da maior para a menor
ESCALAS = [1, 2, 5, 10, 20, 25, 50, 75, 100, 125, 200, 250, 500, 1000, 2000]
# Alturas de letra usuais em desenho técnico (mm no papel)
ALTURAS_TEXTO_MM = [2.5, 3.5, 5.0, 7.0]
MM_POR_UNIDADE = {"mm": 1.0, "cm": 10.0, "m": 1000.0}
INSUNITS = {"mm": 4, "cm": 5, "m": 6}

LAYERS_PRANCHA = [("PRA-MOLDURA", 7), ("PRA-CARIMBO", 7), ("PRA-TEXTO", 4)]


def fator(escala: float, unidade: str) -> float:
    """Unidades do desenho por mm de papel: 1 mm no papel a 1:escala = escala mm reais."""
    return escala / MM_POR_UNIDADE[unidade]


def area_util_mm(formato: str, vertical: bool = False) -> tuple[float, float]:
    """Largura × altura (mm) dentro da moldura (o carimbo ocupa só o canto inferior direito)."""
    w, h = FORMATOS[formato]
    if vertical:
        w, h = h, w
    m = MARGEM[formato]
    return w - MARGEM_ESQ - m, h - 2 * m


def cabe(largura: float, altura: float, unidade: str, folga: float = 0.85) -> list[dict]:
    """Combinações formato/escala em que um desenho de largura × altura (na unidade dada) cabe,
    usando no máximo `folga` da área útil (sobra para cotas, textos e carimbo). Mais legível primeiro."""
    real_mm = (largura * MM_POR_UNIDADE[unidade], altura * MM_POR_UNIDADE[unidade])
    out = []
    for fmt in FORMATOS:
        for vertical in (False, True):
            uw, uh = area_util_mm(fmt, vertical)
            uh -= 60.0  # reserva altura do carimbo
            for esc in ESCALAS:
                pw, ph = real_mm[0] / esc, real_mm[1] / esc
                if pw <= uw * folga and ph <= uh * folga:
                    out.append({"formato": fmt, "orientacao": "vertical" if vertical else "horizontal",
                                "escala": f"1:{esc}", "ocupacao": round(max(pw / uw, ph / uh), 2)})
                    break
    # prefere a maior escala (desenho maior) e, empatando, o menor formato
    ordem = list(FORMATOS)
    out.sort(key=lambda r: (int(r["escala"].split(":")[1]), -ordem.index(r["formato"])))
    return out


def geometria(a) -> dict:
    k = fator(a.escala, a.unidade)
    w, h = FORMATOS[a.formato]
    if a.vertical:
        w, h = h, w
    m, me = MARGEM[a.formato], MARGEM_ESQ
    lc = LARGURA_CARIMBO[a.formato]
    ent: list[dict] = []

    def R(x1, y1, x2, y2, lay):
        ent.append({"t": "rect", "layer": lay, "p": [round(x1 * k, 4), round(y1 * k, 4), round(x2 * k, 4), round(y2 * k, 4)]})

    def Ln(x1, y1, x2, y2, lay="PRA-CARIMBO"):
        ent.append({"t": "line", "layer": lay, "p": [round(x1 * k, 4), round(y1 * k, 4), round(x2 * k, 4), round(y2 * k, 4)]})

    def T(x, y, s, hmm):
        if not s:
            return
        ent.append({"t": "text", "layer": "PRA-TEXTO", "p": [round(x * k, 4), round(y * k, 4)], "h": round(hmm * k, 4),
                    "s": s})

    R(0, 0, w, h, "PRA-MOLDURA")          # limite do papel (linha de corte)
    R(me, m, w - m, h - m, "PRA-MOLDURA")  # moldura
    # carimbo no canto inferior direito, encostado na moldura
    x0, x1, y0 = w - m - lc, w - m, m
    linhas = [  # (rótulo, valor, altura da faixa mm)
        ("RESPONSÁVEL TÉCNICO", f"{a.rt}  {a.registro}".strip(), 10),
        ("ART/RRT", a.art, 9),
        ("DATA / ESCALA / FOLHA", f"{a.data}   1:{a.escala:g}   {a.folha}", 9),
        ("CONTEÚDO", a.conteudo, 10),
        ("CLIENTE", a.cliente, 9),
        ("OBRA", f"{a.obra}" + (f" — {a.local}" if a.local else ""), 10),
    ]
    y = y0
    for rotulo, valor, alt in linhas:
        Ln(x0, y + alt, x1, y + alt)
        T(x0 + 2, y + alt - 2.3, rotulo, 1.8)
        T(x0 + 2, y + 1.5, dec(valor), 3.5 if alt >= 10 else 2.5)
        y += alt
    if a.revisao:
        Ln(x1 - 30, y0, x1 - 30, y0 + linhas[0][2])
        T(x1 - 28, y0 + 1.6, f"REV. {a.revisao}", 2.5)
    R(x0, y0, x1, y, "PRA-CARIMBO")
    altura_carimbo = y - y0
    uw, uh = area_util_mm(a.formato, a.vertical)
    info = {
        "formato": a.formato, "orientacao": "vertical" if a.vertical else "horizontal",
        "papel_mm": [w, h], "escala": f"1:{a.escala:g}", "unidade": a.unidade,
        "fator_unidades_por_mm_papel": k,
        "moldura_desenho": [me * k, m * k, (w - m) * k, (h - m) * k],
        "area_livre_acima_do_carimbo": [x0 * k, (y0 + altura_carimbo) * k, (w - m) * k, (h - m) * k],
        "area_util_papel_mm": [uw, uh],
        "alturas_texto": {f"{t:g} mm": round(t * k, 4) for t in ALTURAS_TEXTO_MM},
    }
    return {"entidades": ent, "nome": f"prancha-{a.formato}", "info": info}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--formato", choices=list(FORMATOS), default="A1")
    ap.add_argument("--vertical", action="store_true", help="prancha em pé (padrão: deitada)")
    ap.add_argument("--escala", type=float, default=50, help="denominador da escala (50 = 1:50)")
    ap.add_argument("--unidade", choices=list(MM_POR_UNIDADE), default="cm", help="unidade do desenho")
    ap.add_argument("--obra", default="")
    ap.add_argument("--local", default="", help="município/UF ou endereço")
    ap.add_argument("--cliente", default="")
    ap.add_argument("--conteudo", default="", help="o que a prancha mostra")
    ap.add_argument("--rt", default="", help="responsável técnico")
    ap.add_argument("--registro", default="", help="CREA/CAU")
    ap.add_argument("--art", default="", help="número da ART/RRT")
    ap.add_argument("--folha", default="01/01")
    ap.add_argument("--revisao", default="")
    ap.add_argument("--data", default=_dt.date.today().strftime("%d/%m/%Y"))
    ap.add_argument("--cabe", type=float, nargs=2, metavar=("LARGURA", "ALTURA"),
                    help="só sugere formato/escala para um desenho deste tamanho (na --unidade)")
    ap.add_argument("--ops")
    ap.add_argument("--dxf")
    a = ap.parse_args(argv)

    if a.cabe:
        print(json.dumps({"desenho": a.cabe, "unidade": a.unidade, "opcoes": cabe(*a.cabe, a.unidade)[:6]},
                         ensure_ascii=False, indent=1))
        return 0
    g = geometria(a)
    if a.ops:
        Path(a.ops).write_text(json.dumps(para_ops(g, LAYERS_PRANCHA), indent=1, ensure_ascii=False), encoding="utf-8")
    if a.dxf:
        Path(a.dxf).write_text(para_dxf([g], LAYERS_PRANCHA, INSUNITS[a.unidade]), encoding="cp1252", errors="replace")
    print(json.dumps({**g["info"], "ops": a.ops, "dxf": a.dxf}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
