#!/usr/bin/env python3
"""Busca composições/insumos SINAPI e monta orçamento com BDI — lê a planilha oficial da Caixa (.xlsx) ou CSV.

A planilha é baixada pelo usuário no site da Caixa (SINAPI → Relatórios mensais, UF e mês desejados,
desonerado ou não). O leitor identifica sozinho a linha de cabeçalho (código, descrição, unidade, custo).

  python3 sinapi.py colunas --arquivo SINAPI.xlsx [--aba NOME]
  python3 sinapi.py buscar  --arquivo SINAPI.xlsx --termo "concreto fck 25" [--limite 15]
  python3 sinapi.py orcar   --arquivo SINAPI.xlsx --itens itens.json --bdi 25 [--saida orcamento.csv]

itens.json: [{"codigo": "94965", "quantidade": 12.5, "item": "1.1"}, ...]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
import zipfile
from pathlib import Path
from xml.etree.ElementTree import iterparse

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------------------ leitura

def _col_idx(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def ler_xlsx(path: Path, aba: str | None = None) -> list[list[str]]:
    with zipfile.ZipFile(path) as z:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            with z.open("xl/sharedStrings.xml") as f:
                for _, el in iterparse(f):
                    if el.tag == NS + "si":
                        shared.append("".join(t.text or "" for t in el.iter(NS + "t")))
                        el.clear()
        # aba → arquivo
        import xml.etree.ElementTree as ET
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
    if path.suffix.lower() == ".csv":
        raw = path.read_bytes()
        txt = raw.decode("utf-8-sig") if raw[:3] == b"\xef\xbb\xbf" else raw.decode("latin-1")
        dialect = csv.Sniffer().sniff(txt[:5000], delimiters=";,\t")
        return [r for r in csv.reader(txt.splitlines(), dialect)]
    return ler_xlsx(path, aba)


def achar_cabecalho(rows: list[list[str]]) -> tuple[int, dict[str, int]]:
    for i, r in enumerate(rows[:60]):
        cols = {}
        for j, c in enumerate(r):
            n = norm(c)
            if "codigo" in n and "codigo" not in cols and "classe" not in n and "agrupador" not in n:
                cols["codigo"] = j
            elif n.startswith("descri") and "descricao" not in cols and "classe" not in n:
                cols["descricao"] = j
            elif n.startswith("unid") and "unidade" not in cols:
                cols["unidade"] = j
            elif ("custo" in n or "preco" in n) and "custo" not in cols and "%" not in n:
                cols["custo"] = j
        if {"codigo", "descricao", "unidade", "custo"} <= cols.keys():
            return i, cols
    raise SystemExit("não achei o cabeçalho (código, descrição, unidade, custo). "
                     "Rode 'colunas' e informe --aba, ou exporte a aba certa como CSV.")


def num(s: str) -> float | None:
    s = str(s).strip()
    if not s:
        return None
    if re.match(r"^-?\d+(\.\d+)?(e-?\d+)?$", s, re.I):
        return float(s)
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def carregar(path: Path, aba: str | None) -> dict[str, dict]:
    rows = ler_tabela(path, aba)
    h, cols = achar_cabecalho(rows)
    base = {}
    for r in rows[h + 1:]:
        if len(r) <= max(cols.values()):
            r = r + [""] * (max(cols.values()) + 1 - len(r))
        cod = str(r[cols["codigo"]]).strip()
        if cod.endswith(".0"):
            cod = cod[:-2]
        custo = num(r[cols["custo"]])
        if not cod or custo is None:
            continue
        base[cod] = {"codigo": cod, "descricao": r[cols["descricao"]].strip(), "unidade": r[cols["unidade"]].strip(),
                     "custo": custo}
    return base


# ------------------------------------------------------------------ comandos

def cmd_colunas(a) -> int:
    rows = ler_tabela(Path(a.arquivo), a.aba)
    for i, r in enumerate(rows[:15]):
        print(i, " | ".join(c[:30] for c in r if c))
    return 0


def cmd_buscar(a) -> int:
    base = carregar(Path(a.arquivo), a.aba)
    termos = norm(a.termo).split()
    achados = [v for v in base.values() if all(t in norm(v["descricao"]) for t in termos)]
    achados.sort(key=lambda v: len(v["descricao"]))
    print(f"{len(achados)} resultado(s) para '{a.termo}'\n\n| Código | Descrição | Un. | Custo (R$) |\n|---|---|---|---|")
    for v in achados[: a.limite]:
        print(f"| {v['codigo']} | {v['descricao'][:120]} | {v['unidade']} | {v['custo']:.2f} |")
    return 0


def cmd_orcar(a) -> int:
    base = carregar(Path(a.arquivo), a.aba)
    itens = json.loads(Path(a.itens).read_text(encoding="utf-8"))
    linhas, total, faltando = [], 0.0, []
    for k, it in enumerate(itens, 1):
        cod = str(it["codigo"]).strip()
        ref = base.get(cod)
        if not ref:
            faltando.append(cod)
            continue
        q = float(it["quantidade"])
        cu_bdi = ref["custo"] * (1 + a.bdi / 100)
        sub = q * cu_bdi
        total += sub
        linhas.append({"item": it.get("item", str(k)), "codigo": cod, "descricao": ref["descricao"], "unidade": ref["unidade"],
                       "quantidade": q, "custo_unitario": ref["custo"], "preco_unitario_bdi": round(cu_bdi, 2),
                       "total": round(sub, 2)})
    print(f"### Orçamento — BDI {a.bdi:g}%\n\n| Item | Código | Descrição | Un. | Qtd | C. unit. | P. unit. c/ BDI | Total |\n|---|---|---|---|---|---|---|---|")
    for l in linhas:
        print(f"| {l['item']} | {l['codigo']} | {l['descricao'][:80]} | {l['unidade']} | {l['quantidade']:.2f} | "
              f"{l['custo_unitario']:.2f} | {l['preco_unitario_bdi']:.2f} | {l['total']:.2f} |")
    print(f"\n**Total: R$ {total:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
    if faltando:
        print(f"\nCódigos não encontrados nesta planilha: {', '.join(faltando)}")
    if a.saida:
        with open(a.saida, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()) if linhas else ["item"], delimiter=";")
            w.writeheader()
            for l in linhas:
                w.writerow({k: (str(v).replace(".", ",") if isinstance(v, float) else v) for k, v in l.items()})
        print(f"\nCSV salvo em {a.saida} (abre no Excel).")
    return 1 if faltando else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nome in ("colunas", "buscar", "orcar"):
        p = sub.add_parser(nome)
        p.add_argument("--arquivo", required=True)
        p.add_argument("--aba")
        if nome == "buscar":
            p.add_argument("--termo", required=True)
            p.add_argument("--limite", type=int, default=15)
        if nome == "orcar":
            p.add_argument("--itens", required=True)
            p.add_argument("--bdi", type=float, default=0.0)
            p.add_argument("--saida")
    a = ap.parse_args(argv)
    return {"colunas": cmd_colunas, "buscar": cmd_buscar, "orcar": cmd_orcar}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
