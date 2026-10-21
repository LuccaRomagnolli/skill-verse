#!/usr/bin/env python3
"""Cotação de materiais na web: lê a planilha de quantitativos, compara as ofertas pesquisadas e gera a planilha
de melhor custo-benefício (XLSX, stdlib pura).

O agente pesquisa os preços (busca web + página do produto) e registra as ofertas em cotacoes.json; este script
faz TODA a conta: perdas, conversão de embalagem, arredondamento de compra, frete, total, ranking e alertas.

  python3 cotacao.py importar --arquivo quantitativos.xlsx [--aba NOME] [--saida cotacoes.json]
  python3 cotacao.py massa-barra --bitola 10 [--comprimento 12]
  python3 cotacao.py validar --cotacoes cotacoes.json
  python3 cotacao.py gerar   --cotacoes cotacoes.json --saida cotacao.xlsx [--csv cotacao.csv] [--validade-dias 7]
  python3 cotacao.py pedido  --cotacoes cotacoes.json [--fornecedor "Nome"]

Formato de cotacoes.json: veja assets/cotacoes.exemplo.json.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import re
import statistics
import sys
import unicodedata
import zipfile
from pathlib import Path
from xml.etree.ElementTree import iterparse
from xml.sax.saxutils import escape

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# NBR 7480:2022 — massa linear nominal (kg/m) das barras e fios de aço para concreto armado
MASSA_LINEAR = {5.0: 0.154, 6.3: 0.245, 8.0: 0.395, 10.0: 0.617, 12.5: 0.963, 16.0: 1.578, 20.0: 2.466,
                25.0: 3.853, 32.0: 6.313, 40.0: 9.865}

ATENDE = ("sim", "parcial", "nao")
UNIDADES_INTEIRAS = ("un", "und", "unid", "unidade", "pc", "peca", "cj", "conjunto", "barra", "saco", "rolo", "lata")
SITUACOES = ("preco-publico", "sob-consulta", "indisponivel")
# Termos que indicam serviço (m², m³ de execução) e não material de compra
TERMOS_SERVICO = ("alvenaria", "forma", "revestimento", "reboco", "emboco", "chapisco", "contrapiso", "pintura",
                  "assentamento", "execucao", "lancamento", "armacao", "impermeabilizacao", "concretagem")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def num(s) -> float | None:
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s or "").strip().replace("R$", "").strip()
    if not s:
        return None
    if re.match(r"^-?\d+(\.\d+)?(e-?\d+)?$", s, re.I):
        return float(s)
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def brl(v: float | None) -> str:
    if v is None:
        return "—"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt(v: float, casas: int = 2) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ------------------------------------------------------------------ leitura da planilha de quantitativos

def _col_idx(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def ler_xlsx(path: Path, aba: str | None = None) -> list[list[str]]:
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(path) as z:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            with z.open("xl/sharedStrings.xml") as f:
                for _, el in iterparse(f):
                    if el.tag == NS + "si":
                        shared.append("".join(t.text or "" for t in el.iter(NS + "t")))
                        el.clear()
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rmap = {r.get("Id"): r.get("Target") for r in rels}
        sheets = [(s.get("name"), rmap[s.get(RNS + "id")]) for s in wb.iter(NS + "sheet")]
        if aba:
            alvo = [t for n, t in sheets if norm(n) == norm(aba)]
            if not alvo:
                raise SystemExit(f"aba '{aba}' não encontrada. Abas: {', '.join(n for n, _ in sheets)}")
            target = alvo[0]
        else:
            target = sheets[0][1]
        target = target.lstrip("/")
        target = target if target.startswith("xl/") else "xl/" + target
        rows: list[list[str]] = []
        with z.open(target) as f:
            for _, el in iterparse(f):
                if el.tag != NS + "row":
                    continue
                row: list[str] = []
                for c in el.iter(NS + "c"):
                    i = _col_idx(c.get("r", "A1"))
                    t = c.get("t")
                    v = c.find(NS + "v")
                    if t == "s" and v is not None:
                        val = shared[int(v.text)]
                    elif t == "inlineStr":
                        val = "".join(x.text or "" for x in c.iter(NS + "t"))
                    else:
                        val = v.text if v is not None else ""
                    while len(row) < i:
                        row.append("")
                    row.append(val or "")
                rows.append(row)
                el.clear()
        return rows


def ler_tabela(path: Path, aba: str | None = None) -> list[list[str]]:
    if path.suffix.lower() in (".csv", ".txt"):
        raw = path.read_bytes()
        txt = raw.decode("utf-8-sig") if raw[:3] == b"\xef\xbb\xbf" else _decodificar(raw)
        try:
            dialect = csv.Sniffer().sniff(txt[:5000], delimiters=";,\t")
            return [r for r in csv.reader(txt.splitlines(), dialect)]
        except csv.Error:
            return [r for r in csv.reader(txt.splitlines(), delimiter=";")]
    return ler_xlsx(path, aba)


def _decodificar(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def achar_cabecalho(rows: list[list[str]]) -> tuple[int, dict[str, int]]:
    """Acha a linha com descrição, unidade e quantidade. 'descricao' tem prioridade sobre 'servico'/'material'."""
    for i, r in enumerate(rows[:60]):
        cols: dict[str, int] = {}
        alternativa_desc = None
        for j, c in enumerate(r):
            n = norm(c)
            if not n:
                continue
            if n.startswith("descri") and "descricao" not in cols:
                cols["descricao"] = j
            elif any(n.startswith(t) for t in ("servico", "material", "insumo", "especifica")) and alternativa_desc is None:
                alternativa_desc = j
            elif (n.startswith("unid") or n in ("un", "un.", "und")) and "unidade" not in cols:
                cols["unidade"] = j
            elif (n.startswith("quant") or n.startswith("qtd") or n.startswith("qtde")) and "quantidade" not in cols:
                cols["quantidade"] = j
            elif n.startswith("item") and "item" not in cols:
                cols["item"] = j
            elif n.startswith("codigo") and "codigo" not in cols:
                cols["codigo"] = j
        if "descricao" not in cols and alternativa_desc is not None:
            cols["descricao"] = alternativa_desc
        if {"descricao", "unidade", "quantidade"} <= cols.keys():
            return i, cols
    raise SystemExit("não achei o cabeçalho (descrição/serviço/material, unidade, quantidade). "
                     "Informe --aba ou exporte a aba certa como CSV com essas três colunas.")


def parece_servico(descricao: str, unidade: str) -> bool:
    d, u = norm(descricao), norm(unidade).replace("²", "2").replace("³", "3")
    return any(re.search(rf"\b{t}\b", d) for t in TERMOS_SERVICO) and u in ("m2", "m3", "kg")


def importar(path: Path, aba: str | None) -> dict:
    rows = ler_tabela(path, aba)
    h, cols = achar_cabecalho(rows)
    itens = []
    largura = max(cols.values()) + 1
    for k, r in enumerate(rows[h + 1:], start=h + 2):
        r = r + [""] * (largura - len(r))
        desc = str(r[cols["descricao"]]).strip()
        qtd = num(r[cols["quantidade"]])
        if not desc or qtd is None or qtd <= 0:
            continue
        un = str(r[cols["unidade"]]).strip()
        it = {"item": str(r[cols["item"]]).strip() if "item" in cols and str(r[cols["item"]]).strip() else str(len(itens) + 1),
              "descricao": desc, "unidade": un, "quantidade": qtd, "perda_pct": 0, "especificacao": "",
              "origem": f"{path.name}, linha {k}", "ofertas": []}
        if "codigo" in cols and str(r[cols["codigo"]]).strip():
            it["codigo_referencia"] = str(r[cols["codigo"]]).strip()
        if parece_servico(desc, un):
            it["alerta_servico"] = ("parece serviço, não material: decomponha em insumos com 'derivado_de' "
                                    "(coeficiente da composição analítica) antes de pesquisar")
        itens.append(it)
    if not itens:
        raise SystemExit("nenhum item com descrição e quantidade positiva abaixo do cabeçalho")
    return {"obra": "", "local": {"municipio": "", "uf": "", "cep": ""}, "data_pesquisa": dt.date.today().isoformat(),
            "planilha_origem": path.name, "itens": itens}


# ------------------------------------------------------------------ cálculo

def massa_barra(bitola: float, comprimento: float) -> float:
    m = MASSA_LINEAR.get(round(float(bitola), 1))
    if m is None:
        raise SystemExit(f"bitola {bitola} mm fora da tabela NBR 7480 ({', '.join(f'{b:g}' for b in MASSA_LINEAR)})")
    return round(m * comprimento, 3)


def quantidade_item(it: dict) -> tuple[float, float]:
    """(quantidade base, quantidade com perda) na unidade do item; peças inteiras arredondam para cima."""
    d = it.get("derivado_de")
    if d:
        base = float(d["quantidade_servico"]) * float(d["coeficiente"])
    else:
        base = float(it["quantidade"])
    qtd = base * (1 + float(it.get("perda_pct") or 0) / 100)
    return base, float(math.ceil(qtd - 1e-9)) if eh_inteiro(it.get("unidade", "")) else qtd


def _data(s) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def eh_inteiro(unidade: str) -> bool:
    return norm(unidade).rstrip(".") in UNIDADES_INTEIRAS


def avaliar_oferta(o: dict, qtd: float, hoje: dt.date, validade: int) -> dict:
    situacao = o.get("situacao") or "preco-publico"
    atende = o.get("atende") or "sim"
    r = {"fornecedor": o.get("fornecedor", ""), "produto": o.get("produto", ""), "url": o.get("url", ""),
         "unidade_venda": o.get("unidade_venda", ""), "conteudo": o.get("conteudo"), "preco": o.get("preco"),
         "frete": None, "prazo_dias": o.get("prazo_dias"), "cidade": o.get("cidade", ""), "acesso": o.get("acesso", ""),
         "contato": o.get("contato", ""), "atende": atende, "situacao": situacao, "obs": o.get("obs", ""),
         "alertas": [], "n_compra": None, "preco_un_item": None, "subtotal": None, "total": None,
         "custo_efetivo": None, "confianca": None, "valida": False}
    if situacao != "preco-publico" or atende == "nao":
        r["alertas"].append("sob consulta" if situacao == "sob-consulta" else
                            "indisponível" if situacao == "indisponivel" else "não atende à especificação")
        return r
    preco, conteudo = num(o.get("preco")), num(o.get("conteudo"))
    if preco is None or preco <= 0 or conteudo is None or conteudo <= 0:
        r["alertas"].append("preço ou conteúdo da embalagem ausente")
        return r
    frete = num(o.get("frete"))
    fracionavel = bool(o.get("fracionavel"))
    n = qtd / conteudo if fracionavel else math.ceil(qtd / conteudo - 1e-9)
    minimo = num(o.get("pedido_minimo")) or 0
    if minimo and n < minimo:
        r["alertas"].append(f"pedido mínimo {fmt(minimo, 0)} {r['unidade_venda']}: compra ajustada")
        n = minimo
    subtotal = n * preco
    total = subtotal + (frete or 0)
    r.update(preco=preco, conteudo=conteudo, frete=frete, n_compra=n, preco_un_item=preco / conteudo,
             subtotal=subtotal, total=total, custo_efetivo=total / qtd if qtd else None, valida=True)

    baixa, media = [], []
    if atende == "parcial":
        baixa.append("atende parcialmente à especificação")
    if not r["url"]:
        baixa.append("sem link da oferta")
    if o.get("confirmado") is False:
        baixa.append("preço não confirmado na página do produto")
    acesso = _data(r["acesso"])
    if acesso is None:
        baixa.append("sem data de acesso")
    elif (hoje - acesso).days > validade:
        baixa.append(f"preço com mais de {validade} dias")
    if frete is None:
        media.append("frete não informado")
    if r["prazo_dias"] in (None, ""):
        media.append("prazo não informado")
    r["confianca"] = "baixa" if baixa else "media" if media else "alta"
    r["alertas"] += baixa + media
    return r


def calcular(dados: dict, validade: int = 7, hoje: dt.date | None = None) -> dict:
    hoje = hoje or _data(dados.get("data_pesquisa")) or dt.date.today()
    itens_out = []
    for it in dados["itens"]:
        base, qtd = quantidade_item(it)
        ofertas = [avaliar_oferta(o, qtd, hoje, validade) for o in it.get("ofertas") or []]
        validas = [o for o in ofertas if o["valida"]]
        validas.sort(key=lambda o: (o["total"], o["prazo_dias"] if isinstance(o["prazo_dias"], (int, float)) else 9e9))
        # preço muito abaixo da mediana costuma ser erro de unidade/embalagem ou golpe
        if len(validas) >= 3:
            med = statistics.median(o["preco_un_item"] for o in validas)
            for o in validas:
                if o["preco_un_item"] < 0.5 * med:
                    o["alertas"].append("preço < 50% da mediana: confira unidade, embalagem e idoneidade do vendedor")
                    o["confianca"] = "baixa"
        confiaveis = [o for o in validas if o["confianca"] != "baixa"]
        escolhida = (confiaveis or validas or [None])[0]
        menor = validas[0]["total"] if validas else None
        for pos, o in enumerate(validas, 1):
            o["ranking"] = pos
            o["indice"] = o["total"] / menor if menor else None
        alertas = []
        if it.get("alerta_servico") and not it.get("derivado_de"):
            alertas.append(it["alerta_servico"])
        if escolhida is None:
            alertas.append("sem preço público: pedir cotação" if ofertas else "sem ofertas pesquisadas")
        elif not confiaveis:
            alertas.append("só há ofertas de baixa confiança: confirme antes de usar")
        if escolhida and len(validas) < 3:
            alertas.append(f"{len(validas)} oferta(s) com preço (recomendado: 3 fornecedores distintos)")
        ref = it.get("referencia") or {}
        variacao = None
        if escolhida and num(ref.get("preco_unitario")):
            variacao = (escolhida["preco_un_item"] / num(ref["preco_unitario"]) - 1) * 100
        itens_out.append({"item": str(it.get("item", "")), "descricao": it["descricao"],
                          "especificacao": it.get("especificacao", ""), "unidade": it["unidade"],
                          "quantidade_base": base, "perda_pct": float(it.get("perda_pct") or 0), "quantidade": qtd,
                          "derivado_de": it.get("derivado_de"), "ofertas": ofertas, "escolhida": escolhida,
                          "referencia": ref, "variacao_ref_pct": variacao, "alertas": alertas})

    total = sum(i["escolhida"]["total"] for i in itens_out if i["escolhida"])
    cotados = sum(1 for i in itens_out if i["escolhida"])

    fornecedores: dict[str, dict] = {}
    for i in itens_out:
        for o in i["ofertas"]:
            f = fornecedores.setdefault(o["fornecedor"], {"fornecedor": o["fornecedor"], "itens_cotados": 0,
                                                          "itens_recomendados": 0, "total_cotado": 0.0,
                                                          "sob_consulta": 0, "contato": "", "cidade": "", "_itens": set()})
            f["contato"] = f["contato"] or o["contato"] or o["url"]
            f["cidade"] = f["cidade"] or o["cidade"]
            if o["valida"]:
                if i["item"] not in f["_itens"]:
                    f["_itens"].add(i["item"])
                    f["itens_cotados"] += 1
                    f["total_cotado"] += min(x["total"] for x in i["ofertas"]
                                             if x["valida"] and x["fornecedor"] == o["fornecedor"])
            elif o["situacao"] == "sob-consulta":
                f["sob_consulta"] += 1
            if i["escolhida"] is o:
                f["itens_recomendados"] += 1
    for f in fornecedores.values():
        f["cobre_todos"] = f["itens_cotados"] == len(itens_out) and len(itens_out) > 0
        del f["_itens"]
    forn = sorted(fornecedores.values(), key=lambda f: (-f["itens_recomendados"], -f["itens_cotados"], f["total_cotado"]))

    return {"obra": dados.get("obra", ""), "local": dados.get("local") or {}, "data_pesquisa": hoje.isoformat(),
            "validade_dias": validade, "itens": itens_out, "fornecedores": forn,
            "resumo": {"itens": len(itens_out), "cotados": cotados, "total": total,
                       "sem_preco": [i["item"] for i in itens_out if not i["escolhida"]]}}


# ------------------------------------------------------------------ validação

def validar(dados: dict) -> list[str]:
    erros = []
    if not dados.get("itens"):
        return ["sem 'itens'"]
    for it in dados["itens"]:
        k = f"item {it.get('item', '?')}"
        for campo in ("descricao", "unidade"):
            if not it.get(campo):
                erros.append(f"{k}: falta '{campo}'")
        d = it.get("derivado_de")
        if d:
            for campo in ("quantidade_servico", "coeficiente", "fonte"):
                if d.get(campo) in (None, ""):
                    erros.append(f"{k}: derivado_de sem '{campo}'")
        elif num(it.get("quantidade")) is None or num(it.get("quantidade")) <= 0:
            erros.append(f"{k}: 'quantidade' deve ser positiva")
        for j, o in enumerate(it.get("ofertas") or [], 1):
            ko = f"{k}, oferta {j}"
            if not o.get("fornecedor"):
                erros.append(f"{ko}: falta 'fornecedor'")
            if (o.get("atende") or "sim") not in ATENDE:
                erros.append(f"{ko}: 'atende' deve ser {'/'.join(ATENDE)}")
            sit = o.get("situacao") or "preco-publico"
            if sit not in SITUACOES:
                erros.append(f"{ko}: 'situacao' deve ser {'/'.join(SITUACOES)}")
            if sit == "preco-publico":
                for campo in ("preco", "conteudo", "unidade_venda", "url", "acesso"):
                    if o.get(campo) in (None, ""):
                        erros.append(f"{ko}: falta '{campo}' (oferta com preço público)")
            elif not (o.get("contato") or o.get("url")):
                erros.append(f"{ko}: oferta sob consulta precisa de 'contato' ou 'url'")
    return erros


# ------------------------------------------------------------------ XLSX (stdlib)

def _col(n: int) -> str:
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


class Formula(str):
    """Fórmula do Excel (sem '=') com valor em cache para leitores que não recalculam."""

    def __new__(cls, f: str, cache=None):
        o = super().__new__(cls, f)
        o.cache = cache
        return o


# estilos: 0 padrão, 1 cabeçalho, 2 moeda, 3 número, 4 texto quebrado, 5 total moeda, 6 título, 7 índice, 8 link
ESTILOS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="3"><numFmt numFmtId="164" formatCode="&quot;R$&quot; #,##0.00"/><numFmt numFmtId="165" formatCode="#,##0.000"/><numFmt numFmtId="166" formatCode="0.00"/></numFmts>
<fonts count="4"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font><font><b/><sz val="13"/><name val="Calibri"/></font><font><u/><sz val="11"/><color rgb="FF0563C1"/><name val="Calibri"/></font></fonts>
<fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFDDEBF7"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="9">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"><alignment wrapText="1" vertical="center"/></xf>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"><alignment vertical="top"/></xf>
<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment wrapText="1" vertical="top"/></xf>
<xf numFmtId="164" fontId="2" fillId="3" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1"/>
<xf numFmtId="0" fontId="2" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
<xf numFmtId="166" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"><alignment vertical="top"/></xf>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def _celula(ref: str, v, estilo: int) -> str:
    s = f' s="{estilo}"' if estilo else ""
    if v is None or v == "":
        return f'<c r="{ref}"{s}/>' if estilo else ""
    if isinstance(v, Formula):
        cache = v.cache
        if isinstance(cache, (int, float)) and not isinstance(cache, bool):
            return f'<c r="{ref}"{s}><f>{escape(str(v))}</f><v>{cache}</v></c>'
        return f'<c r="{ref}"{s} t="str"><f>{escape(str(v))}</f><v>{escape(str(cache or ""))}</v></c>'
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f'<c r="{ref}"{s}><v>{round(v, 6)}</v></c>'
    txt = escape(str(v)).replace("\n", "&#10;")
    return f'<c r="{ref}"{s} t="inlineStr"><is><t xml:space="preserve">{txt}</t></is></c>'


def _aba_xml(linhas: list[list[tuple]], larguras: list[float], congelar: int = 1) -> str:
    cols = "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(larguras, 1))
    painel = (f'<sheetViews><sheetView workbookViewId="0"><pane ySplit="{congelar}" topLeftCell="A{congelar + 1}" '
              f'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>') if congelar else ""
    rows = []
    for i, linha in enumerate(linhas, 1):
        cells = "".join(_celula(f"{_col(j)}{i}", v, e) for j, (v, e) in enumerate(linha))
        rows.append(f'<row r="{i}">{cells}</row>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'{painel}<cols>{cols}</cols><sheetData>{"".join(rows)}</sheetData></worksheet>')


def escrever_xlsx(path: Path, abas: list[tuple[str, list[list[tuple]], list[float], int]]) -> None:
    ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>']
    sheets, rels = [], []
    for k, (nome, *_r) in enumerate(abas, 1):
        ct.append(f'<Override PartName="/xl/worksheets/sheet{k}.xml" '
                  'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        sheets.append(f'<sheet name="{escape(nome[:31])}" sheetId="{k}" r:id="rId{k}"/>')
        rels.append(f'<Relationship Id="rId{k}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                    f'Target="worksheets/sheet{k}.xml"/>')
    n = len(abas)
    rels.append(f'<Relationship Id="rId{n + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
                'Target="styles.xml"/>')
    ct.append("</Types>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "".join(ct))
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                   'Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   f'<sheets>{"".join(sheets)}</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f'{"".join(rels)}</Relationships>')
        z.writestr("xl/styles.xml", ESTILOS)
        for k, (_nome, linhas, larguras, congelar) in enumerate(abas, 1):
            z.writestr(f"xl/worksheets/sheet{k}.xml", _aba_xml(linhas, larguras, congelar))


def _link(url: str, texto: str = "abrir"):
    if not url or not re.match(r"^https?://", url) or len(url) > 250:
        return (url, 0)
    return (Formula(f'HYPERLINK("{url.replace(chr(34), "%22")}","{texto}")', texto), 8)


def _embalagem(o: dict) -> str:
    if not o.get("unidade_venda"):
        return ""
    return f"{o['unidade_venda']} ({fmt(o['conteudo'], 3).rstrip('0').rstrip(',')})" if o.get("conteudo") else o["unidade_venda"]


def montar_abas(r: dict) -> list[tuple]:
    H = 1
    # --- Melhor custo-benefício (fórmulas editáveis: total = qtd compra × preço + frete)
    cab = ["Item", "Material (quantitativo)", "Un.", "Qtd. c/ perda", "Produto encontrado", "Fornecedor",
           "Embalagem (conteúdo na un. do item)", "Qtd. a comprar", "Preço da embalagem", "Preço por un. do item",
           "Frete", "Total estimado", "Confiança", "Link", "Acesso", "Alertas"]
    melhor = [[(c, H) for c in cab]]
    for i in r["itens"]:
        o = i["escolhida"]
        lin = len(melhor) + 1
        alertas = "; ".join(i["alertas"] + (o["alertas"] if o else []))
        if o:
            melhor.append([(i["item"], 0), (i["descricao"] + (f"\n{i['especificacao']}" if i["especificacao"] else ""), 4),
                           (i["unidade"], 0), (i["quantidade"], 3), (o["produto"], 4), (o["fornecedor"], 4),
                           (_embalagem(o), 4), (o["n_compra"], 3), (o["preco"], 2),
                           (Formula(f"I{lin}/{o['conteudo']}", o["preco_un_item"]), 2), (o["frete"] or 0, 2),
                           (Formula(f"H{lin}*I{lin}+K{lin}", o["total"]), 2), (o["confianca"], 0), _link(o["url"]),
                           (o["acesso"], 0), (alertas, 4)])
        else:
            melhor.append([(i["item"], 0), (i["descricao"], 4), (i["unidade"], 0), (i["quantidade"], 3),
                           ("— sem preço público —", 4), ("", 0), ("", 0), ("", 0), ("", 0), ("", 0), ("", 0),
                           ("", 2), ("", 0), ("", 0), ("", 0), (alertas, 4)])
    n = len(melhor)
    melhor.append([("", 0)] * 10 + [("TOTAL ESTIMADO", 6), (Formula(f"SUM(L2:L{n})", r["resumo"]["total"]), 5)])
    larg_melhor = [6, 38, 6, 12, 42, 24, 22, 11, 13, 13, 11, 15, 10, 9, 11, 50]

    # --- Comparativo (todas as ofertas)
    cab2 = ["Item", "Material", "Ranking", "Índice custo-benefício (1,00 = menor total)", "Fornecedor", "Produto",
            "Embalagem", "Preço da embalagem", "Preço por un. do item", "Qtd. a comprar", "Frete", "Total", "Prazo (dias)",
            "Cidade", "Atende à especificação", "Situação", "Confiança", "Link", "Acesso", "Alertas / obs."]
    comp = [[(c, H) for c in cab2]]
    for i in r["itens"]:
        ords = sorted(i["ofertas"], key=lambda o: (not o["valida"], o.get("ranking") or 0))
        for o in ords:
            comp.append([(i["item"], 0), (i["descricao"], 4), (o.get("ranking") or "", 0), (o.get("indice"), 7),
                         (o["fornecedor"], 4), (o["produto"], 4), (_embalagem(o), 4), (o["preco"] if o["valida"] else None, 2),
                         (o["preco_un_item"], 2), (o["n_compra"], 3), (o["frete"], 2), (o["total"], 2),
                         (o["prazo_dias"], 0), (o["cidade"], 0), (o["atende"], 0), (o["situacao"], 0),
                         (o["confianca"] or "", 0), _link(o["url"]), (o["acesso"], 0),
                         ("; ".join(o["alertas"] + ([o["obs"]] if o["obs"] else [])), 4)])
    larg_comp = [6, 30, 8, 14, 24, 40, 20, 13, 13, 11, 11, 14, 9, 16, 12, 14, 10, 9, 11, 50]

    # --- Por fornecedor
    cab3 = ["Fornecedor", "Itens com preço", "Itens em que é a melhor opção", "Soma dos itens cotados",
            "Cobre todos os itens?", "Itens sob consulta", "Cidade", "Contato / site"]
    forn = [[(c, H) for c in cab3]]
    for f in r["fornecedores"]:
        forn.append([(f["fornecedor"], 4), (f["itens_cotados"], 0), (f["itens_recomendados"], 0), (f["total_cotado"], 2),
                     ("sim" if f["cobre_todos"] else "não", 0), (f["sob_consulta"], 0), (f["cidade"], 0),
                     (f["contato"], 4)])
    larg_forn = [30, 12, 14, 18, 12, 12, 18, 45]

    # --- Pedir cotação (sem preço público)
    cab4 = ["Item", "Material", "Especificação", "Un.", "Quantidade a cotar", "Fornecedor", "Contato / site", "Obs."]
    ped = [[(c, H) for c in cab4]]
    for i in r["itens"]:
        for o in i["ofertas"]:
            if o["situacao"] == "sob-consulta":
                ped.append([(i["item"], 0), (i["descricao"], 4), (i["especificacao"], 4), (i["unidade"], 0),
                            (i["quantidade"], 3), (o["fornecedor"], 4), (o["contato"] or o["url"], 4), (o["obs"], 4)])
        if not i["ofertas"]:
            ped.append([(i["item"], 0), (i["descricao"], 4), (i["especificacao"], 4), (i["unidade"], 0),
                        (i["quantidade"], 3), ("(pesquisar fornecedores)", 4), ("", 0), ("", 0)])
    larg_ped = [6, 36, 36, 6, 14, 26, 40, 30]

    # --- Resumo e premissas
    loc = r["local"]
    local = ", ".join(x for x in (loc.get("municipio"), loc.get("uf"), loc.get("cep")) if x)
    res = r["resumo"]
    resumo = [[("Cotação de materiais — pesquisa de preços na web", 6)],
              [("Obra", 0), (r["obra"] or "—", 0)],
              [("Local de entrega", 0), (local or "—", 0)],
              [("Data da pesquisa", 0), (r["data_pesquisa"], 0)],
              [("Itens", 0), (res["itens"], 0)],
              [("Itens com preço", 0), (res["cotados"], 0)],
              [("Itens sem preço público", 0), (", ".join(res["sem_preco"]) or "nenhum", 4)],
              [("Total estimado (itens com preço)", 0), (res["total"], 5)],
              [("", 0)],
              [("Critério de custo-benefício", 6)],
              [("1. Só entram ofertas que atendem à especificação e têm preço público.", 4)],
              [("2. Total = embalagens inteiras necessárias (com perda e pedido mínimo) × preço + frete informado.", 4)],
              [("3. Recomendada = menor total entre ofertas de confiança alta ou média; empate decidido pelo prazo.", 4)],
              [(f"4. Confiança baixa: atende parcialmente, sem link, preço não confirmado na página, acesso há mais de "
                f"{r['validade_dias']} dias ou preço < 50% da mediana. Média: frete ou prazo não informado.", 4)],
              [("", 0)],
              [("Limites", 6)],
              [("Preços de varejo on-line mudam diariamente e dependem de CEP, estoque, forma de pagamento e frete. "
                "Esta planilha é estimativa de compra, não proposta comercial: confirme preço, frete e prazo com o "
                "fornecedor antes de comprar. Não substitui a pesquisa de preços formal exigida em contratações "
                "públicas.", 4)]]
    larg_res = [36, 90]
    return [("Resumo", resumo, larg_res, 0), ("Melhor custo-benefício", melhor, larg_melhor, 1),
            ("Comparativo", comp, larg_comp, 1), ("Por fornecedor", forn, larg_forn, 1),
            ("Pedir cotação", ped, larg_ped, 1)]


def escrever_csv(path: Path, r: dict) -> None:
    campos = ["item", "material", "unidade", "quantidade", "produto", "fornecedor", "embalagem", "qtd_compra",
              "preco_embalagem", "preco_un_item", "frete", "total", "confianca", "url", "acesso"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(campos)
        for i in r["itens"]:
            o = i["escolhida"] or {}
            vals = [i["item"], i["descricao"], i["unidade"], i["quantidade"], o.get("produto", ""), o.get("fornecedor", ""),
                    _embalagem(o) if o else "", o.get("n_compra"), o.get("preco"), o.get("preco_un_item"), o.get("frete"),
                    o.get("total"), o.get("confianca", ""), o.get("url", ""), o.get("acesso", "")]
            w.writerow([fmt(v, 2 if k >= 8 else 3) if isinstance(v, float) else ("" if v is None else v)
                        for k, v in enumerate(vals)])


def imprimir_md(r: dict) -> None:
    loc = r["local"]
    print(f"### Cotação de materiais — {r['obra'] or 'obra'} ({loc.get('municipio', '')}/{loc.get('uf', '')}, "
          f"pesquisa {r['data_pesquisa']})\n")
    print("| Item | Material | Qtd. | Fornecedor | Compra | Total | Confiança |\n|---|---|---|---|---|---|---|")
    for i in r["itens"]:
        o = i["escolhida"]
        qtd = f"{fmt(i['quantidade'], 2)} {i['unidade']}"
        if o:
            print(f"| {i['item']} | {i['descricao'][:50]} | {qtd} | {o['fornecedor'][:30]} | "
                  f"{fmt(o['n_compra'], 2 if not float(o['n_compra']).is_integer() else 0)} × {o['unidade_venda']} | "
                  f"{brl(o['total'])} | {o['confianca']} |")
        else:
            print(f"| {i['item']} | {i['descricao'][:50]} | {qtd} | — sem preço público — | | | |")
    res = r["resumo"]
    print(f"\n**Total estimado: {brl(res['total'])}** ({res['cotados']} de {res['itens']} itens com preço)")
    alertas = [(i["item"], a) for i in r["itens"] for a in i["alertas"] + (i["escolhida"]["alertas"] if i["escolhida"] else [])]
    if alertas:
        print("\nAlertas:")
        for item, a in alertas:
            print(f"- item {item}: {a}")
    variacoes = [i for i in r["itens"] if i["variacao_ref_pct"] is not None]
    if variacoes:
        print("\nComparação com a referência informada:")
        for i in variacoes:
            print(f"- item {i['item']}: {i['variacao_ref_pct']:+.1f}% vs. {i['referencia'].get('fonte', 'referência')}")


# ------------------------------------------------------------------ comandos

def _carregar(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cmd_importar(a) -> int:
    dados = importar(Path(a.arquivo), a.aba)
    saida = Path(a.saida)
    saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(dados['itens'])} item(ns) importado(s) para {saida}\n\n| Item | Descrição | Un. | Qtd. |\n|---|---|---|---|")
    for it in dados["itens"]:
        print(f"| {it['item']} | {it['descricao'][:70]} | {it['unidade']} | {fmt(it['quantidade'], 3)} |")
    servicos = [it["item"] for it in dados["itens"] if it.get("alerta_servico")]
    if servicos:
        print(f"\nItens que parecem serviços (decompor em materiais antes de pesquisar): {', '.join(servicos)}")
    return 0


def cmd_massa_barra(a) -> int:
    m = massa_barra(a.bitola, a.comprimento)
    print(json.dumps({"bitola_mm": a.bitola, "comprimento_m": a.comprimento, "massa_kg": m,
                      "fonte": "NBR 7480:2022, massa linear nominal"}, ensure_ascii=False))
    return 0


def cmd_validar(a) -> int:
    erros = validar(_carregar(a.cotacoes))
    for e in erros:
        print(f"- {e}")
    print("ok" if not erros else f"\n{len(erros)} problema(s)")
    return 1 if erros else 0


def cmd_gerar(a) -> int:
    dados = _carregar(a.cotacoes)
    erros = validar(dados)
    if erros:
        for e in erros:
            print(f"- {e}", file=sys.stderr)
        print("corrija cotacoes.json (rode 'validar') antes de gerar", file=sys.stderr)
        return 1
    r = calcular(dados, a.validade_dias)
    imprimir_md(r)
    escrever_xlsx(Path(a.saida), montar_abas(r))
    print(f"\nPlanilha salva em {a.saida}")
    if a.csv:
        escrever_csv(Path(a.csv), r)
        print(f"CSV salvo em {a.csv} (abre no Excel com ';').")
    if a.json:
        Path(a.json).write_text(json.dumps(r, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return 0


def cmd_pedido(a) -> int:
    dados = _carregar(a.cotacoes)
    loc = dados.get("local") or {}
    alvo = norm(a.fornecedor) if a.fornecedor else None
    grupos: dict[str, list] = {}
    for it in dados["itens"]:
        _, qtd = quantidade_item(it)
        ofertas = it.get("ofertas") or []
        if alvo:
            forn = [o["fornecedor"] for o in ofertas if norm(o.get("fornecedor", "")) == alvo]
        else:
            forn = [o["fornecedor"] for o in ofertas if o.get("situacao") == "sob-consulta"]
            if not ofertas:
                forn = ["(fornecedor a definir)"]
        for f in dict.fromkeys(forn):
            grupos.setdefault(f, []).append((it, qtd))
    if not grupos:
        print("nenhum item para pedir cotação")
        return 1
    for f, itens in grupos.items():
        print(f"--- Pedido de cotação: {f} ---\n")
        print(f"Olá! Gostaria de uma cotação para entrega em {loc.get('municipio', '<cidade>')}/{loc.get('uf', '<UF>')}"
              f"{', CEP ' + loc['cep'] if loc.get('cep') else ''}:\n")
        for k, (it, qtd) in enumerate(itens, 1):
            esp = f" — {it['especificacao']}" if it.get("especificacao") else ""
            print(f"{k}. {it['descricao']}{esp}: {fmt(qtd, 0 if qtd.is_integer() else 2)} {it['unidade']}")
        print("\nPor favor, informe preço unitário, embalagem, frete, prazo de entrega, condição de pagamento e "
              "validade da proposta. Obrigado!\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("importar", help="lê a planilha de quantitativos e cria cotacoes.json")
    p.add_argument("--arquivo", required=True)
    p.add_argument("--aba")
    p.add_argument("--saida", default="cotacoes.json")
    p = sub.add_parser("massa-barra", help="massa de uma barra de aço (NBR 7480) para converter barra → kg")
    p.add_argument("--bitola", type=float, required=True, help="mm")
    p.add_argument("--comprimento", type=float, default=12.0, help="m (padrão 12)")
    p = sub.add_parser("validar")
    p.add_argument("--cotacoes", required=True)
    p = sub.add_parser("gerar", help="calcula e gera a planilha XLSX")
    p.add_argument("--cotacoes", required=True)
    p.add_argument("--saida", default="cotacao.xlsx")
    p.add_argument("--csv")
    p.add_argument("--json", help="grava o resultado calculado em JSON (para outras skills)")
    p.add_argument("--validade-dias", type=int, default=7)
    p = sub.add_parser("pedido", help="texto de pedido de cotação para itens sob consulta")
    p.add_argument("--cotacoes", required=True)
    p.add_argument("--fornecedor")
    a = ap.parse_args(argv)
    return {"importar": cmd_importar, "massa-barra": cmd_massa_barra, "validar": cmd_validar, "gerar": cmd_gerar,
            "pedido": cmd_pedido}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
