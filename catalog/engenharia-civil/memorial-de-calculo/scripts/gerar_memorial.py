#!/usr/bin/env python3
"""Gera memorial de cálculo (MD + HTML imprimível + DOCX editável) — somente biblioteca padrão.

Entradas:
  --projeto projeto.json      dados da obra e textos (modelo: assets/projeto.exemplo.json)
  --resultados pasta/         arquivos .json gerados pelos scripts das skills (--formato json)
  --saida pasta/              onde gravar MEMORIAL.md / .html / .docx

Exemplo:
  python3 gerar_memorial.py --projeto projeto.json --resultados resultados/ --saida memorial/
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

NORMAS_BASE = ["ABNT NBR 6118:2026 — referência para a revisão técnica (2023 + Emenda 1:2026)",
               "ABNT NBR 6120:2019 — Ações para o cálculo de estruturas de edificações",
               "ABNT NBR 8681 — confirmar edição aplicável e coeficientes"]
NORMA_VENTO = "ABNT NBR 6123 — confirmar edição aplicável e parâmetros"


# ------------------------------------------------------------------ montagem do conteúdo (blocos)

def blocos(projeto: dict, resultados: list[tuple[str, dict]], contexto: dict | None = None) -> list[tuple]:
    """Lista de blocos: ('h', nível, texto) | ('p', texto) | ('table', cabeçalho, linhas) | ('ul', itens)."""
    p = projeto
    B: list[tuple] = [("title", p.get("titulo", "Memorial de Cálculo Estrutural"))]
    ctx = contexto or {}
    local = f"{ctx['municipio']}/{ctx['uf']}" if ctx.get("municipio") else ""
    ident = [("Obra", p.get("obra", "")), ("Endereço", p.get("endereco", "")), ("Município/UF", p.get("municipio", local)), ("Proprietário", p.get("proprietario", "")),
             ("Responsável técnico", p.get("responsavel", "")), ("Registro profissional", p.get("registro", "")),
             ("ART/RRT", p.get("art", "")), ("Data", p.get("data") or dt.date.today().strftime("%d/%m/%Y")),
             ("Revisão", p.get("revisao", "0"))]
    B += [("h", 1, "1. Identificação"), ("table", ["Item", "Descrição"], [[k, v] for k, v in ident if v])]
    B += [("h", 1, "2. Objetivo"), ("p", p.get("objetivo", "Apresentar os critérios, hipóteses e resultados do "
                                                    "dimensionamento dos elementos estruturais listados neste memorial."))]
    normas = list(NORMAS_BASE)
    if any("V0" in r for _, r in resultados):
        normas.append(NORMA_VENTO)
    normas += p.get("normas_extras", [])
    B += [("h", 1, "3. Normas técnicas"), ("ul", normas)]
    pendentes = [(nome, r.get("norma_base_calculo"), r.get("status_normativo") or "sem validação registrada")
                for nome, r in resultados if r.get("status_normativo") != "validado"]
    if pendentes:
        B.append(("p", "Situação normativa: os resultados abaixo são auxiliares e exigem confronto "
                       "com as edições vigentes antes da revisão e assinatura do projeto."))
        B.append(("table", ["Resultado", "Base implementada", "Situação"],
                  [[nome, base or "NBR 6118:2023", situacao] for nome, base, situacao in pendentes]))
    atp = p.get("avaliacao_tecnica") or {}
    B.append(("p", "Avaliação técnica independente do projeto (NBR 6118:2026, item 5.3): "
                   + (atp.get("situacao") or "aplicabilidade e parecer ainda não registrados pelo responsável técnico")
                   + (f"; parecer: {atp['parecer']}" if atp.get("parecer") else "") + "."))
    fontes = [f for f in ctx.get("fontes", []) if f.get("esfera") != "abnt"]
    if fontes:
        B.append(("p", f"Legislação e normas locais consultadas ({local}):"))
        B.append(("ul", [f"{f['titulo']}" + (f" — {f['url']}" if f.get("url") else "") + f" (acesso em {f['acessado_em']}"
                         + ("" if f.get("vigente") == "sim" else "; vigência a confirmar") + ")" for f in fontes]))
    mat = dict(p.get("materiais") or {})
    if ctx.get("caa") and not any("agressividade" in k.lower() for k in mat):
        mat["Classe de agressividade ambiental"] = f"{ctx['caa']['classe']} ({ctx['caa']['agressividade']}, ambiente {ctx['caa']['ambiente']})"
    linhas_mat = [[k, str(v)] for k, v in mat.items()]
    B += [("h", 1, "4. Materiais e durabilidade")]
    B += [("table", ["Parâmetro", "Valor"], linhas_mat)] if linhas_mat else [("p", "Conforme indicado em cada elemento.")]
    B += [("h", 1, "5. Ações")]
    for par in p.get("acoes", ["Ações conforme NBR 6120 e combinações conforme NBR 8681, detalhadas por elemento."]):
        B.append(("p", par))
    B += [("h", 1, "6. Modelo e métodos de cálculo")]
    for par in p.get("metodos", [
        "Lajes maciças: momentos pela teoria de placas delgadas (Kirchhoff), resolvida por diferenças finitas; "
        "flechas pelo modelo de Branson com fluência pelo coeficiente αf (NBR 6118, 17.3.2).",
        "Vigas: flexão simples no ELU com diagrama retangular de tensões e força cortante pelo Modelo de cálculo I.",
        "Pilares: momentos mínimos, efeitos locais de 2ª ordem pelo pilar-padrão com curvatura aproximada e "
        "flexo-compressão oblíqua pela verificação simplificada (17.2.5.2).",
    ]):
        B.append(("p", par))
    B += [("h", 1, "7. Dimensionamento dos elementos")]
    for i, (nome, r) in enumerate(resultados, 1):
        mem = r.get("memoria")
        titulo = (mem or {}).get("titulo") or nome
        B.append(("h", 2, f"7.{i}. {nome} — {titulo}" if nome.lower() not in titulo.lower() else f"7.{i}. {titulo}"))
        if mem:
            B.append(("table", ["Passo", "Cálculo"], [[s["descricao"], s["calculo"]] for s in mem["passos"]]))
            if mem.get("alertas"):
                B.append(("p", "Observações:"))
                B.append(("ul", mem["alertas"]))
        elif "cotas" in r:  # vento
            B.append(("p", f"V0 = {r['V0']} m/s; S1 = {r['S1']}; categoria {r['categoria']}, classe {r['classe']}; S3 = {r['S3']}."))
            B.append(("table", ["z (m)", "S2", "Vk (m/s)", "q (kN/m²)"],
                      [[f"{c['z']:.2f}", f"{c['S2']:.3f}", f"{c['Vk']:.2f}", f"{c['q_kN_m2']:.3f}"] for c in r["cotas"]]))
        elif "envoltoria" in r:  # combinações
            B.append(("table", ["Combinação", "Máximo", "Mínimo"],
                      [[k.replace("_", " "), f"{v['max']:.2f}", f"{v['min']:.2f}"] for k, v in r["envoltoria"].items()]))
        else:
            B.append(("p", "Resultado sem memória estruturada — ver anexo."))
    B += [("h", 1, "8. Considerações finais")]
    for par in p.get("consideracoes", []):
        B.append(("p", par))
    B.append(("p", "Este memorial deve ser lido em conjunto com as plantas de forma e armação. Alterações de uso, "
                   "cargas ou geometria exigem nova verificação pelo responsável técnico."))
    if p.get("responsavel"):
        B += [("sign", p["responsavel"], p.get("registro", ""))]
    return B


# ------------------------------------------------------------------ Markdown

def to_md(B: list[tuple]) -> str:
    out = []
    for b in B:
        if b[0] == "title":
            out += [f"# {b[1]}", ""]
        elif b[0] == "h":
            out += ["#" * (b[1] + 1) + " " + b[2], ""]
        elif b[0] == "p":
            out += [b[1], ""]
        elif b[0] == "ul":
            out += [f"- {i}" for i in b[1]] + [""]
        elif b[0] == "table":
            out += ["| " + " | ".join(b[1]) + " |", "|" + "---|" * len(b[1])]
            out += ["| " + " | ".join(str(c).replace("|", "/") for c in row) + " |" for row in b[2]] + [""]
        elif b[0] == "sign":
            out += ["", "_______________________________", b[1], b[2], ""]
    return "\n".join(out)


# ------------------------------------------------------------------ HTML (A4, imprimir em PDF)

def to_html(B: list[tuple], titulo: str) -> str:
    e = html.escape
    body = []
    for b in B:
        if b[0] == "title":
            body.append(f"<h1>{e(b[1])}</h1>")
        elif b[0] == "h":
            body.append(f"<h{b[1] + 1}>{e(b[2])}</h{b[1] + 1}>")
        elif b[0] == "p":
            body.append(f"<p>{e(b[1])}</p>")
        elif b[0] == "ul":
            body.append("<ul>" + "".join(f"<li>{e(i)}</li>" for i in b[1]) + "</ul>")
        elif b[0] == "table":
            body.append("<table><thead><tr>" + "".join(f"<th>{e(c)}</th>" for c in b[1]) + "</tr></thead><tbody>"
                        + "".join("<tr>" + "".join(f"<td>{e(str(c))}</td>" for c in r) + "</tr>" for r in b[2])
                        + "</tbody></table>")
        elif b[0] == "sign":
            body.append(f'<div class="sign"><div class="line"></div>{e(b[1])}<br>{e(b[2])}</div>')
    css = """
@page{size:A4;margin:20mm 18mm}
body{font:11pt/1.5 "Helvetica Neue",Arial,sans-serif;color:#1b1b1b;background:#fff;max-width:180mm;margin:0 auto;padding:16px}
h1{font-size:18pt;text-align:center;margin:0 0 18px}h2{font-size:13pt;margin-top:22px;border-bottom:1px solid #999}
h3{font-size:11.5pt;margin-top:16px}table{border-collapse:collapse;width:100%;margin:8px 0;font-size:9.5pt;page-break-inside:auto}
th,td{border:1px solid #888;padding:4px 6px;text-align:left;vertical-align:top}th{background:#eee}
tr{page-break-inside:avoid}.sign{margin-top:48px;text-align:center}.sign .line{border-top:1px solid #000;width:60%;margin:0 auto 4px}
@media screen and (prefers-color-scheme:dark){body{color:#e8e8e6;background:#1a1a19}th{background:#2a2a28}th,td{border-color:#555}
.sign .line{border-color:#ccc}}"""
    return (f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' "
            f"content='width=device-width,initial-scale=1'><title>{e(titulo)}</title><style>{css}</style></head><body>"
            + "\n".join(body) + "</body></html>\n")


# ------------------------------------------------------------------ DOCX mínimo (OOXML)

def _run(text: str, bold: bool = False, size: int | None = None) -> str:
    rpr = ("<w:b/>" if bold else "") + (f'<w:sz w:val="{size}"/>' if size else "")
    return f'<w:r>{"<w:rPr>" + rpr + "</w:rPr>" if rpr else ""}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def _par(text: str, style: str | None = None, bold: bool = False, align: str | None = None) -> str:
    ppr = (f'<w:pStyle w:val="{style}"/>' if style else "") + (f'<w:jc w:val="{align}"/>' if align else "")
    return f'<w:p>{"<w:pPr>" + ppr + "</w:pPr>" if ppr else ""}{_run(text, bold)}</w:p>'


def _table(head: list[str], rows: list[list]) -> str:
    border = "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="888888"/>'
                     for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    def row(cells, bold=False):
        return "<w:tr>" + "".join(f'<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/></w:tcPr>{_par(str(c), bold=bold)}</w:tc>'
                                  for c in cells) + "</w:tr>"
    return (f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/><w:tblBorders>{border}</w:tblBorders></w:tblPr>'
            + row(head, True) + "".join(row(r) for r in rows) + "</w:tbl>")


def to_docx(B: list[tuple], path: Path) -> None:
    body = []
    for b in B:
        if b[0] == "title":
            body.append(_par(b[1], "Title", align="center"))
        elif b[0] == "h":
            body.append(_par(b[2], f"Heading{b[1]}"))
        elif b[0] == "p":
            body.append(_par(b[1]))
        elif b[0] == "ul":
            body += [_par("• " + i) for i in b[1]]
        elif b[0] == "table":
            body.append(_table(b[1], b[2]))
            body.append(_par(""))
        elif b[0] == "sign":
            body += [_par(""), _par(""), _par("_______________________________", align="center"),
                     _par(b[1], align="center"), _par(b[2], align="center")]
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {ns}><w:body>' + "".join(body)
                + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1021" w:bottom="1134" '
                  'w:left="1021" w:header="709" w:footer="709" w:gutter="0"/></w:sectPr></w:body></w:document>')

    def style(sid, name, size, bold=True, based="Normal"):
        return (f'<w:style w:type="paragraph" w:styleId="{sid}"><w:name w:val="{name}"/><w:basedOn w:val="{based}"/>'
                f'<w:next w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>'
                f'<w:rPr>{"<w:b/>" if bold else ""}<w:sz w:val="{size}"/></w:rPr></w:style>')
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {ns}>'
              '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
              '<w:sz w:val="21"/><w:lang w:val="pt-BR"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr>'
              '<w:spacing w:after="80" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
              + style("Title", "Title", 34) + style("Heading1", "heading 1", 27) + style("Heading2", "heading 2", 23)
              + "</w:styles>")
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                     '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                     '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)


# ------------------------------------------------------------------ CLI

def ordenar(nome: str) -> tuple:
    """Ações (vento, combinações…) primeiro; depois L1, L2… V1… P1…; números em ordem natural."""
    m = re.match(r"^([lvp])\d", nome.lower())
    pref = {"l": 1, "v": 2, "p": 3}[m.group(1)] if m else 0
    return (pref, [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", nome.lower())])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--projeto", required=True)
    ap.add_argument("--resultados", required=True)
    ap.add_argument("--saida", default="memorial")
    ap.add_argument("--contexto", help="projeto-contexto.json da skill contexto-do-projeto (município, CAA, legislação local)")
    a = ap.parse_args(argv)
    projeto = json.loads(Path(a.projeto).read_text(encoding="utf-8"))
    pasta = Path(a.resultados)
    arquivos = sorted(pasta.glob("*.json"), key=lambda f: ordenar(f.stem))
    if not arquivos:
        sys.exit(f"nenhum .json em {pasta}")
    resultados = [(f.stem, json.loads(f.read_text(encoding="utf-8"))) for f in arquivos]
    contexto = json.loads(Path(a.contexto).read_text(encoding="utf-8")) if a.contexto else None
    if not contexto and Path("projeto-contexto.json").is_file():
        contexto = json.loads(Path("projeto-contexto.json").read_text(encoding="utf-8"))
    B = blocos(projeto, resultados, contexto)
    out = Path(a.saida)
    out.mkdir(parents=True, exist_ok=True)
    titulo = projeto.get("titulo", "Memorial de Cálculo Estrutural")
    (out / "MEMORIAL.md").write_text(to_md(B), encoding="utf-8")
    (out / "MEMORIAL.html").write_text(to_html(B, titulo), encoding="utf-8")
    to_docx(B, out / "MEMORIAL.docx")
    print(json.dumps({"elementos": [n for n, _ in resultados], "arquivos": [str(out / f"MEMORIAL.{x}") for x in ("md", "html", "docx")]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
