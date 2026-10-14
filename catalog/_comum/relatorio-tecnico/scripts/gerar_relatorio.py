#!/usr/bin/env python3
"""Converte um relatório em Markdown (com cabeçalho de metadados) em DOCX editável e HTML A4 — só stdlib.

Markdown aceito: # / ## / ### títulos, parágrafos, listas (- e 1.), tabelas |…|, **negrito**,
imagens ![legenda](caminho/foto.jpg) (PNG/JPEG, embutidas no DOCX e no HTML) e "---" (quebra de página).

Cabeçalho (antes do primeiro título), uma chave por linha:
  ---
  titulo: Laudo Técnico de Vistoria
  subtitulo: Fissuras na fachada norte
  autor: Eng. Fulano de Tal — CREA-UF 000000/D
  local: Brasília/DF
  data: 14/10/2026
  ---

  python3 gerar_relatorio.py relatorio.md --saida pasta/ [--nome LAUDO]
"""
from __future__ import annotations

import argparse
import base64
import html
import re
import struct
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

EMU_CM = 360000


# ------------------------------------------------------------------ parsing

def parse(md: str) -> tuple[dict, list[tuple]]:
    meta: dict = {}
    lines = md.splitlines()
    if lines and lines[0].strip() == "---":
        end = lines.index("---", 1)
        for l in lines[1:end]:
            if ":" in l:
                k, v = l.split(":", 1)
                meta[k.strip()] = v.strip()
        lines = lines[end + 1:]
    blocks: list[tuple] = []
    para: list[str] = []
    table: list[str] = []
    lst: tuple[str, list[str]] | None = None

    def flush():
        nonlocal para, table, lst
        if para:
            blocks.append(("p", " ".join(para)))
            para = []
        if table:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table
                    if not re.match(r"^\|?[\s:|-]+\|?$", r.strip())]
            blocks.append(("table", rows[0], rows[1:]))
            table = []
        if lst:
            blocks.append(lst)
            lst = None

    for l in lines:
        s = l.strip()
        if not s:
            flush()
            continue
        if s == "---":
            flush()
            blocks.append(("pagebreak",))
        elif m := re.match(r"^(#{1,3})\s+(.*)", s):
            flush()
            blocks.append(("h", len(m.group(1)), m.group(2)))
        elif m := re.match(r"^!\[(.*?)\]\((.*?)\)$", s):
            flush()
            blocks.append(("img", m.group(1), m.group(2)))
        elif s.startswith("|"):
            if para or lst:
                flush()
            table.append(s)
        elif m := re.match(r"^(?:[-*]|(\d+)[.)])\s+(.*)", s):
            kind = "ol" if m.group(1) else "ul"
            if para or table or (lst and lst[0] != kind):
                flush()
            lst = lst or (kind, [])
            lst[1].append(m.group(2))
        else:
            if table or lst:
                flush()
            para.append(s)
    flush()
    return meta, blocks


def img_size(data: bytes) -> tuple[int, int]:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    raise ValueError("imagem não é PNG/JPEG")


# ------------------------------------------------------------------ HTML

def inline_html(s: str) -> str:
    s = html.escape(s)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


def to_html(meta: dict, blocks: list[tuple], base: Path) -> str:
    out = [f"<header><h1>{html.escape(meta.get('titulo', 'Relatório Técnico'))}</h1>"]
    if meta.get("subtitulo"):
        out.append(f"<p class='sub'>{html.escape(meta['subtitulo'])}</p>")
    info = " · ".join(html.escape(meta[k]) for k in ("autor", "local", "data") if meta.get(k))
    out.append(f"<p class='info'>{info}</p></header>")
    fig = 0
    for b in blocks:
        if b[0] == "h":
            out.append(f"<h{b[1] + 1}>{inline_html(b[2])}</h{b[1] + 1}>")
        elif b[0] == "p":
            out.append(f"<p>{inline_html(b[1])}</p>")
        elif b[0] in ("ul", "ol"):
            out.append(f"<{b[0]}>" + "".join(f"<li>{inline_html(i)}</li>" for i in b[1]) + f"</{b[0]}>")
        elif b[0] == "table":
            out.append("<table><thead><tr>" + "".join(f"<th>{inline_html(c)}</th>" for c in b[1]) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline_html(c)}</td>" for c in r) + "</tr>" for r in b[2])
                       + "</tbody></table>")
        elif b[0] == "img":
            fig += 1
            p = (base / b[2]).resolve()
            data = p.read_bytes()
            mime = "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"
            out.append(f"<figure><img src='data:{mime};base64,{base64.b64encode(data).decode()}' alt='{html.escape(b[1])}'>"
                       f"<figcaption>Figura {fig} — {html.escape(b[1])}</figcaption></figure>")
        elif b[0] == "pagebreak":
            out.append("<div class='pb'></div>")
    css = """@page{size:A4;margin:22mm 18mm}
body{font:11pt/1.55 "Helvetica Neue",Arial,sans-serif;color:#1b1b1b;background:#fff;max-width:180mm;margin:0 auto;padding:16px}
header{text-align:center;border-bottom:2px solid #333;margin-bottom:18px;padding-bottom:8px}h1{font-size:19pt;margin:0}
.sub{font-size:12.5pt;margin:4px 0}.info{color:#555;font-size:10pt}h2{font-size:13.5pt;margin-top:22px}h3{font-size:12pt}
h4{font-size:11pt}table{border-collapse:collapse;width:100%;font-size:9.5pt;margin:8px 0}th,td{border:1px solid #888;padding:4px 6px;
text-align:left;vertical-align:top}th{background:#eee}figure{margin:12px 0;text-align:center;page-break-inside:avoid}
img{max-width:100%;max-height:110mm}figcaption{font-size:9.5pt;color:#444}.pb{page-break-after:always}
@media screen and (prefers-color-scheme:dark){body{color:#e8e8e6;background:#1a1a19}th{background:#2a2a28}.info,figcaption{color:#aaa}
header{border-color:#aaa}}"""
    return (f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
            f"initial-scale=1'><title>{html.escape(meta.get('titulo', 'Relatório'))}</title><style>{css}</style></head><body>"
            + "\n".join(out) + "</body></html>\n")


# ------------------------------------------------------------------ DOCX

def runs(s: str) -> str:
    out = []
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", s)):
        if part:
            rpr = "<w:rPr><w:b/></w:rPr>" if i % 2 else ""
            out.append(f'<w:r>{rpr}<w:t xml:space="preserve">{escape(part)}</w:t></w:r>')
    return "".join(out)


def par(s: str, style: str | None = None, align: str | None = None) -> str:
    ppr = (f'<w:pStyle w:val="{style}"/>' if style else "") + (f'<w:jc w:val="{align}"/>' if align else "")
    return f'<w:p>{"<w:pPr>" + ppr + "</w:pPr>" if ppr else ""}{runs(s)}</w:p>'


def to_docx(meta: dict, blocks: list[tuple], base: Path, path: Path) -> None:
    body = [par(meta.get("titulo", "Relatório Técnico"), "Title", "center")]
    if meta.get("subtitulo"):
        body.append(par(meta["subtitulo"], "Subtitle", "center"))
    body.append(par(" · ".join(meta[k] for k in ("autor", "local", "data") if meta.get(k)), align="center"))
    media: list[tuple[str, bytes]] = []
    fig = 0
    border = "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="888888"/>'
                     for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    for b in blocks:
        if b[0] == "h":
            body.append(par(b[2], f"Heading{b[1]}"))
        elif b[0] == "p":
            body.append(par(b[1]))
        elif b[0] in ("ul", "ol"):
            body += [par(("• " if b[0] == "ul" else f"{i}. ") + t) for i, t in enumerate(b[1], 1)]
        elif b[0] == "table":
            def row(cells, head=False):
                return "<w:tr>" + "".join("<w:tc>" + par(f"**{c}**" if head else c) + "</w:tc>" for c in cells) + "</w:tr>"
            body.append(f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/><w:tblBorders>{border}</w:tblBorders></w:tblPr>'
                        + row(b[1], True) + "".join(row(r) for r in b[2]) + "</w:tbl>")
            body.append(par(""))
        elif b[0] == "img":
            fig += 1
            data = (base / b[2]).read_bytes()
            w, h = img_size(data)
            cx = int(15 * EMU_CM)
            cy = int(cx * h / w)
            if cy > 11 * EMU_CM:
                cy = int(11 * EMU_CM)
                cx = int(cy * w / h)
            ext = "png" if data[:4] == b"\x89PNG" else "jpeg"
            rid = f"rIdImg{fig}"
            media.append((f"image{fig}.{ext}", data))
            body.append(
                '<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
                f'<wp:inline><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{fig}" name="Figura {fig}"/>'
                '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
                f'<pic:nvPicPr><pic:cNvPr id="{fig}" name="image{fig}.{ext}"/><pic:cNvPicPr/></pic:nvPicPr>'
                f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
                f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"/></pic:spPr>'
                '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
            body.append(par(f"Figura {fig} — {b[1]}", "Caption", "center"))
        elif b[0] == "pagebreak":
            body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
    ns = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
          'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
          'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
          'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {ns}><w:body>' + "".join(body)
                + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1247" w:right="1021" w:bottom="1247" '
                  'w:left="1021" w:header="709" w:footer="709" w:gutter="0"/></w:sectPr></w:body></w:document>')

    def st(sid, name, size, bold=True, extra=""):
        return (f'<w:style w:type="paragraph" w:styleId="{sid}"><w:name w:val="{name}"/><w:basedOn w:val="Normal"/>'
                f'<w:qFormat/><w:pPr><w:spacing w:before="200" w:after="100"/>{extra}</w:pPr><w:rPr>{"<w:b/>" if bold else ""}'
                f'<w:sz w:val="{size}"/></w:rPr></w:style>')
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault>'
              '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="22"/><w:lang w:val="pt-BR"/></w:rPr>'
              '</w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="100" w:line="300" w:lineRule="auto"/><w:jc w:val="both"/>'
              '</w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
              '<w:name w:val="Normal"/><w:qFormat/></w:style>'
              + st("Title", "Title", 36) + st("Subtitle", "Subtitle", 26, False) + st("Heading1", "heading 1", 28)
              + st("Heading2", "heading 2", 24) + st("Heading3", "heading 3", 22) + st("Caption", "caption", 18, False)
              + "</w:styles>")
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
          '<Default Extension="jpeg" ContentType="image/jpeg"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                + "".join(f'<Relationship Id="rIdImg{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                          f'Target="media/{n}"/>' for i, (n, _) in enumerate(media, 1))
                + "</Relationships>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        for n, data in media:
            z.writestr(f"word/media/{n}", data)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo")
    ap.add_argument("--saida", default=".")
    ap.add_argument("--nome", help="nome base dos arquivos (padrão: nome do .md)")
    a = ap.parse_args(argv)
    src = Path(a.arquivo)
    meta, blocks = parse(src.read_text(encoding="utf-8"))
    faltando = [b[2] for b in blocks if b[0] == "img" and not (src.parent / b[2]).is_file()]
    if faltando:
        sys.exit("imagens não encontradas: " + ", ".join(faltando))
    out = Path(a.saida)
    out.mkdir(parents=True, exist_ok=True)
    nome = a.nome or src.stem
    (out / f"{nome}.html").write_text(to_html(meta, blocks, src.parent), encoding="utf-8")
    to_docx(meta, blocks, src.parent, out / f"{nome}.docx")
    n_fig = sum(1 for b in blocks if b[0] == "img")
    print(f"{out / (nome + '.docx')}\n{out / (nome + '.html')}\n{len(blocks)} blocos, {n_fig} figura(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
