#!/usr/bin/env python3
"""Coletor e índice local de normas e manuais PÚBLICOS (NRs, DNIT/IPR, SINAPI/Caixa).

Só baixa documentos publicados gratuitamente pelos órgãos oficiais, respeitando robots.txt
e um intervalo entre requisições. Normas ABNT (NBR) NÃO são coletadas: são protegidas por
direito autoral e vendidas pela ABNT.

Dados em $NORMAS_DIR (padrão ~/.mcpcad/normas-publicas): normas.db (SQLite + FTS5) e pdf/.

  python3 normas.py catalogo [--fonte nr|dnit|sinapi]     atualiza a lista de documentos (metadados)
  python3 normas.py baixar --padrao                        NRs da construção civil
  python3 normas.py baixar --ids nr-18 nr-35               documentos específicos
  python3 normas.py baixar --grupo sinapi-caderno --busca alvenaria --max 5
  python3 normas.py buscar "guarda-corpo altura"           busca no texto indexado
  python3 normas.py catalogo-buscar "concreto"             busca nos títulos do catálogo
  python3 normas.py ler nr-18 --pagina 12
  python3 normas.py item nr-18 18.13.4
  python3 normas.py importar-url https://.../codigo-de-obras.pdf --titulo "Código de Obras de X" --esfera municipal
  python3 normas.py importar arquivo.pdf --titulo "NBR 9050:2020 (gratuita)"   documento obtido pelo usuário
  python3 normas.py status

Requer: pypdf (extração de texto) e certifi. Executado via `uv run --with pypdf --with certifi`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import http.cookiejar
import json
import os
import re
import sqlite3
import ssl
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

UA = "MCPcad-normas/1.0 (coleta de documentos publicos; uso pessoal do usuario)"
INTERVALO = 0.8  # s entre requisições ao mesmo host

NR_INDICE = ("https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-"
             "colegiados/comissao-tripartite-partitaria-permanente/normas-regulamentadora/normas-regulamentadoras-vigentes")
DNIT_BASE = "https://www.gov.br/dnit/pt-br/assuntos/planejamento-e-pesquisa/ipr"
DNIT_CATEGORIAS = {
    "es": "coletanea-de-normas/coletanea-de-normas/especificacao-de-servico-es",
    "em": "coletanea-de-normas/coletanea-de-normas/especificacao-de-material-em",
    "me": "coletanea-de-normas/coletanea-de-normas/metodo-de-ensaio-me",
    "pro": "coletanea-de-normas/coletanea-de-normas/procedimento-pro",
    "pad": "coletanea-de-normas/coletanea-de-normas/padronizacao-pad",
    "ie": "coletanea-de-normas/coletanea-de-normas/instrucao-de-ensaio-ie",
    "ter": "coletanea-de-normas/coletanea-de-normas/terminologia-ter",
    "cla": "coletanea-de-normas/coletanea-de-normas/classificacao-cla",
    "manual": "coletanea-de-manuais/vigentes",
}
CAIXA = "https://www.caixa.gov.br"
SINAPI_CATEGORIAS = {533: "sinapi-caderno", 754: "sinapi-metodologia", 958: "sinapi-insumos", 764: "sinapi-parametricas"}

# NRs com aplicação direta em obras de construção civil (conjunto baixado por padrão)
NRS_PADRAO = [1, 6, 8, 10, 11, 12, 17, 18, 23, 24, 33, 35]

FONTES = {
    "nr": "Normas Regulamentadoras — Ministério do Trabalho e Emprego (atos oficiais, uso livre). "
          "O texto não substitui o publicado no DOU.",
    "dnit": "DNIT/IPR — reprodução permitida desde que citado o DNIT como fonte e mantido o texto.",
    "sinapi": "SINAPI — CAIXA/IBGE, publicações técnicas de livre acesso.",
    "usuario": "Documento fornecido pelo usuário (uso pessoal).",
    "local": "Legislação/norma pública local (município, estado, Corpo de Bombeiros, concessionária) obtida no "
             "endereço indicado em 'url'. Confira a vigência na fonte oficial.",
}


# ------------------------------------------------------------------ infraestrutura

def data_dir() -> Path:
    d = Path(os.environ.get("NORMAS_DIR", Path.home() / "SkillVerse" / "normas-publicas"))
    (d / "pdf").mkdir(parents=True, exist_ok=True)
    return d


def db() -> sqlite3.Connection:
    con = sqlite3.connect(data_dir() / "normas.db")
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS docs(
            id TEXT PRIMARY KEY, fonte TEXT, grupo TEXT, codigo TEXT, titulo TEXT, url TEXT,
            data_ref TEXT, baixado INTEGER DEFAULT 0, paginas INTEGER, sem_texto INTEGER DEFAULT 0,
            caminho TEXT, sha1 TEXT, atualizado_em TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS pag USING fts5(
            doc_id UNINDEXED, pagina UNINDEXED, texto, tokenize='unicode61 remove_diacritics 2');
        CREATE TABLE IF NOT EXISTS meta(chave TEXT PRIMARY KEY, valor TEXT);
    """)
    if "alias_de" not in {r[1] for r in con.execute("PRAGMA table_info(docs)")}:
        con.execute("ALTER TABLE docs ADD COLUMN alias_de TEXT")
    return con


def resolver(con: sqlite3.Connection, doc_id: str) -> str:
    """Documentos idênticos publicados com nomes diferentes apontam para um só (alias_de)."""
    r = con.execute("SELECT alias_de FROM docs WHERE id=?", (doc_id,)).fetchone()
    return r["alias_de"] if r and r["alias_de"] else doc_id


def agora() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", sem_acento(s)).strip("-")[:80]


class Http:
    """urllib com cookies, robots.txt e intervalo por host."""

    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        try:  # certificados do certifi quando disponíveis (Python sem cadeia de certificados do sistema)
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ModuleNotFoundError:
            ctx = ssl.create_default_context()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar),
                                              urllib.request.HTTPSHandler(context=ctx))
        self.robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self.ultimo: dict[str, float] = {}

    def permitido(self, url: str) -> bool:
        host = urllib.parse.urlsplit(url)
        base = f"{host.scheme}://{host.netloc}"
        if base not in self.robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                txt = self._get(base + "/robots.txt", checar=False).decode("utf-8", "replace")
                rp.parse(txt.splitlines())
            except Exception:  # noqa: BLE001 — sem robots.txt acessível: tudo permitido
                rp.parse([])
            self.robots[base] = rp
        return self.robots[base].can_fetch(UA, url)

    def _get(self, url: str, checar: bool = True, headers: dict | None = None, tentativas: int = 3) -> bytes:
        if checar and not self.permitido(url):
            raise PermissionError(f"robots.txt não permite: {url}")
        host = urllib.parse.urlsplit(url).netloc
        espera = INTERVALO - (time.time() - self.ultimo.get(host, 0))
        if espera > 0:
            time.sleep(espera)
        req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
        for i in range(tentativas):
            try:
                with self.op.open(req, timeout=90) as r:
                    self.ultimo[host] = time.time()
                    return r.read()
            except urllib.error.HTTPError as e:
                if e.code in (404, 403) or i == tentativas - 1:
                    raise
            except (urllib.error.URLError, TimeoutError):
                if i == tentativas - 1:
                    raise
            time.sleep(2 * (i + 1))
        raise RuntimeError("inalcançável")

    def texto(self, url: str) -> str:
        return self._get(url).decode("utf-8", "replace")

    def json(self, url: str) -> dict:
        return json.loads(self._get(url, headers={"Accept": "application/json;odata=verbose"}))

    def binario(self, url: str) -> bytes:
        return self._get(url)


def links_pdf(page_html: str) -> list[tuple[str, str]]:
    """[(url, texto do link)] dos PDFs de uma página."""
    out = []
    for m in re.finditer(r'<a\b[^>]*href="([^"]+?\.pdf)(?:[?#][^"]*)?"[^>]*>(.*?)</a>', page_html, re.S | re.I):
        texto = html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
        out.append((html.unescape(m.group(1)), re.sub(r"\s+", " ", texto).strip()))
    vistos, uniq = set(), []
    for u, t in out:
        if u not in vistos:
            vistos.add(u)
            uniq.append((u, t))
    return uniq


# ------------------------------------------------------------------ fontes → catálogo

def catalogo_nr(h: Http) -> list[dict]:
    idx = h.texto(NR_INDICE)
    # páginas de cada NR (algumas ficam fora da pasta do índice, ex.: NR-37)
    paginas = sorted(set(re.findall(
        r'href="(https://www\.gov\.br/trabalho-e-emprego/[^"]+/(?:nr-\d+|norma-regulamentadora-no-\d+-nr-\d+))"', idx)))
    docs = []
    for p in paginas:
        n = int(re.search(r"(\d+)$", p).group(1))
        pg = h.texto(p)
        m = re.search(r"<h1[^>]*>(.*?)</h1>", pg, re.S)
        nome = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))).strip() if m else f"NR-{n}"
        textos, manuais = [], []
        for url, txt in links_pdf(pg):
            arq = urllib.parse.unquote(url.rsplit("/", 1)[-1])
            a = sem_acento(arq)
            if re.search(r"atas?[-_]ctpp|historico|sst-portarias|reuniao|relatorio|nota[-_]tecnica", sem_acento(url)):
                continue
            mt = re.search(r"nr[-_]?0*(\d+)[-_]?atualizad[ao][-_]?(\d{4})", a)
            if mt and int(mt.group(1)) == n:
                textos.append((int(mt.group(2)), arq, url))
            elif re.fullmatch(rf"nr[-_]?0*{n}\.pdf", a):  # sem ano no nome (ex.: nr-21.pdf)
                textos.append((0, arq, url))
            elif re.search(r"manual|guia|cartilha|perguntas|faq", a) and (re.search(rf"nr[-_]?0*{n}(?!\d)", a) or "nr" not in a):
                manuais.append((arq, url, txt))
        if textos:
            ano, arq, url = max(textos, key=lambda t: (t[0], t[1]))
            docs.append({"id": f"nr-{n:02d}", "fonte": "nr", "grupo": "nr", "codigo": f"NR-{n}",
                         "titulo": nome, "url": url, "data_ref": str(ano) if ano else ""})
        for arq, url, txt in manuais:
            docs.append({"id": f"nr-{n:02d}-{slug(Path(arq).stem)}"[:90], "fonte": "nr", "grupo": "nr-manual",
                         "codigo": f"NR-{n}", "titulo": f"NR-{n} — {txt or Path(arq).stem.replace('_', ' ')}",
                         "url": url, "data_ref": ""})
    return docs


def catalogo_dnit(h: Http) -> list[dict]:
    docs = []
    for cod, caminho in DNIT_CATEGORIAS.items():
        pg = h.texto(f"{DNIT_BASE}/{caminho}")
        for url, txt in links_pdf(pg):
            if "/ipr/" not in url:
                continue
            arq = urllib.parse.unquote(url.rsplit("/", 1)[-1])
            m = re.match(r"((?:DNIT|DNER)[\s-]*[A-Z]*\s*\d+/\d+(?:\s*[-–]\s*[A-Z]+)?)", txt)
            codigo = m.group(1).strip() if m else Path(arq).stem.upper()
            ano = re.search(r"/(\d{2,4})", codigo)
            docs.append({"id": "dnit-" + slug(Path(arq).stem), "fonte": "dnit", "grupo": f"dnit-{cod}",
                         "codigo": codigo, "titulo": txt or Path(arq).stem, "url": url,
                         "data_ref": ano.group(1) if ano else ""})
    return docs


def catalogo_sinapi(h: Http) -> list[dict]:
    h.texto(f"{CAIXA}/site/Paginas/downloads.aspx")  # cookie de sessão do site
    docs = []
    for cat, grupo in SINAPI_CATEGORIAS.items():
        q = (f"{CAIXA}/_api/web/lists/getbytitle('Downloads')/Items?$select=Title,Modified,FileLeafRef,EncodedAbsUrl,"
             f"Categoria/ID&$expand=Categoria&$filter=Categoria/ID eq {cat} and FSObjType eq 0 and "
             f"OData__ModerationStatus eq 0&$top=5000&$orderby=Modified desc")
        res = h.json(urllib.parse.quote(q, safe=":/?&=$,'()"))["d"]["results"]
        for x in res:
            arq = x["FileLeafRef"]
            if not arq.lower().endswith(".pdf"):
                continue
            titulo = (x.get("Title") or Path(arq).stem).replace("SINAPI-CT-", "").replace("-", " ").strip()
            docs.append({"id": "sinapi-" + slug(Path(arq).stem.replace("SINAPI-CT-", "ct-")), "fonte": "sinapi",
                         "grupo": grupo, "codigo": "SINAPI", "titulo": titulo,
                         "url": x["EncodedAbsUrl"].replace("http://", "https://"), "data_ref": x["Modified"][:10]})
    return docs


COLETORES = {"nr": catalogo_nr, "dnit": catalogo_dnit, "sinapi": catalogo_sinapi}


def atualizar_catalogo(fontes: list[str] | None = None, log=print) -> dict:
    h, con, res = Http(), db(), {}
    for f in fontes or list(COLETORES):
        try:
            docs = COLETORES[f](h)
        except Exception as e:  # noqa: BLE001 — uma fonte fora do ar não derruba as outras
            res[f] = f"erro: {type(e).__name__}: {e}"
            log(f"  ! {f}: {res[f]}")
            continue
        with con:
            for d in docs:
                old = con.execute("SELECT url, baixado FROM docs WHERE id=?", (d["id"],)).fetchone()
                if old and old["url"] != d["url"] and old["baixado"]:
                    d["_desatualizado"] = True  # nova versão publicada: reindexa no próximo baixar
                con.execute("""INSERT INTO docs(id,fonte,grupo,codigo,titulo,url,data_ref,atualizado_em)
                               VALUES(?,?,?,?,?,?,?,?)
                               ON CONFLICT(id) DO UPDATE SET grupo=excluded.grupo, codigo=excluded.codigo,
                               titulo=excluded.titulo, url=excluded.url, data_ref=excluded.data_ref,
                               atualizado_em=excluded.atualizado_em,
                               baixado=CASE WHEN docs.url=excluded.url THEN docs.baixado ELSE 0 END""",
                            (d["id"], d["fonte"], d["grupo"], d["codigo"], d["titulo"], d["url"], d["data_ref"], agora()))
            con.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (f"catalogo_{f}", agora()))
        res[f] = len(docs)
        log(f"  • {f}: {len(docs)} documentos no catálogo")
    return res


# ------------------------------------------------------------------ download + indexação

def _extrair(caminho: Path) -> list[str]:
    try:
        import pypdf
    except ModuleNotFoundError as e:  # pragma: no cover
        raise SystemExit("pypdf não instalado — rode via: uv run --with pypdf python normas.py ...") from e
    r = pypdf.PdfReader(str(caminho))
    out = []
    for p in r.pages:
        try:
            out.append(p.extract_text() or "")
        except Exception:  # noqa: BLE001 — página corrompida não impede o resto
            out.append("")
    return out


def indexar(con: sqlite3.Connection, doc_id: str, caminho: Path, sha1: str) -> dict:
    paginas = _extrair(caminho)
    sem_texto = sum(len(t.strip()) for t in paginas) < 50 * max(1, len(paginas))
    with con:
        con.execute("DELETE FROM pag WHERE doc_id=?", (doc_id,))
        con.executemany("INSERT INTO pag(doc_id,pagina,texto) VALUES(?,?,?)",
                        [(doc_id, i + 1, t) for i, t in enumerate(paginas) if t.strip()])
        con.execute("UPDATE docs SET baixado=1, paginas=?, sem_texto=?, caminho=?, sha1=?, atualizado_em=? WHERE id=?",
                    (len(paginas), int(sem_texto), str(caminho), sha1, agora(), doc_id))
    return {"id": doc_id, "paginas": len(paginas), "sem_texto": sem_texto}


def baixar(ids: list[str], log=print, forcar: bool = False) -> list[dict]:
    con, h, out = db(), Http(), []
    for i in ids:
        d = con.execute("SELECT * FROM docs WHERE id=?", (i,)).fetchone()
        if not d:
            out.append({"id": i, "erro": "não está no catálogo (rode 'catalogo' ou confira o id)"})
            continue
        if d["baixado"] and not forcar:
            out.append({"id": i, "status": "já indexado", "paginas": d["paginas"]})
            continue
        try:
            dados = h.binario(d["url"])
            if not dados.startswith(b"%PDF"):
                raise ValueError("resposta não é PDF")
            sha1 = hashlib.sha1(dados).hexdigest()
            igual = con.execute("SELECT id FROM docs WHERE sha1=? AND id<>? AND baixado=1", (sha1, i)).fetchone()
            if igual:
                with con:
                    con.execute("UPDATE docs SET baixado=1, alias_de=?, sha1=?, atualizado_em=? WHERE id=?",
                                (igual["id"], sha1, agora(), i))
                log(f"  • {i}: idêntico a {igual['id']} (não duplicado no índice)")
                out.append({"id": i, "status": f"idêntico a {igual['id']}"})
                continue
            caminho = data_dir() / "pdf" / f"{i}.pdf"
            caminho.write_bytes(dados)
            r = indexar(con, i, caminho, sha1)
            log(f"  • {i}: {r['paginas']} pág." + (" (digitalizado, sem texto)" if r["sem_texto"] else ""))
            out.append(r)
        except Exception as e:  # noqa: BLE001
            log(f"  ! {i}: {type(e).__name__}: {e}")
            out.append({"id": i, "erro": f"{type(e).__name__}: {e}"})
    return out


def ids_por_filtro(grupo: str | None, busca: str | None, maximo: int) -> list[str]:
    con = db()
    rows = con.execute("SELECT id, codigo, titulo, grupo FROM docs" + (" WHERE grupo=?" if grupo else ""),
                       (grupo,) if grupo else ()).fetchall()
    termos = sem_acento(busca).split() if busca else []
    sel = [r["id"] for r in rows if all(t in sem_acento(f"{r['id']} {r['codigo']} {r['titulo']}") for t in termos)]
    return sel[:maximo]


def ids_padrao() -> list[str]:
    """Textos das NRs da construção + manuais/guias oficiais dessas NRs (sem os de outros setores)."""
    ids = [f"nr-{n:02d}" for n in NRS_PADRAO]
    codigos = {f"NR-{n}" for n in NRS_PADRAO}
    for r in db().execute("SELECT id, codigo, titulo FROM docs WHERE grupo='nr-manual' ORDER BY id"):
        t = sem_acento(r["titulo"])
        if r["codigo"] in codigos and re.search(r"manual|guia|cartilha", t) and \
                not re.search(r"portu|couro|usuario|sesmt|vestimenta|psicossociais|elaboracao e revisao", t):
            ids.append(r["id"])
    return ids


def importar(arquivo: Path, titulo: str, codigo: str = "") -> dict:
    """Indexa um PDF que o próprio usuário obteve (ex.: NBR 9050 distribuída gratuitamente)."""
    dados = arquivo.read_bytes()
    doc_id = "usuario-" + slug(codigo or titulo)
    destino = data_dir() / "pdf" / f"{doc_id}.pdf"
    destino.write_bytes(dados)
    con = db()
    with con:
        con.execute("""INSERT OR REPLACE INTO docs(id,fonte,grupo,codigo,titulo,url,data_ref,atualizado_em)
                       VALUES(?,?,?,?,?,?,?,?)""", (doc_id, "usuario", "usuario", codigo, titulo, arquivo.as_uri(), "", agora()))
    return indexar(con, doc_id, destino, hashlib.sha1(dados).hexdigest())


# ------------------------------------------------------------------ documentos públicos locais (via URL)

# Sites que hospedam cópias não autorizadas de normas técnicas: nunca baixar deles.
HOSTS_BLOQUEADOS = ("scribd.", "passeidireto.", "studocu.", "docero.", "pdfcoffee.", "dokumen.", "idoc.", "kupdf.",
                    "vdocuments.", "documents.pub", "doku.pub", "pt.slideshare.", "slideshare.", "academia.edu",
                    "docplayer.", "1library.", "pdfslide.", "fdocumentos.", "docslide.", "baixardoc.", "dokumen.pub")
# Marcas de exemplar vendido pela ABNT (texto protegido por direito autoral)
MARCAS_ABNT = (r"exemplar\s+para\s+uso\s+exclusivo", r"©\s*ABNT\s*\d{4}",
               r"todos\s+os\s+direitos\s+reservados.{0,300}ABNT", r"ABNT.{0,300}todos\s+os\s+direitos\s+reservados")


def _html_para_paginas(conteudo: str, tamanho: int = 3500) -> list[str]:
    conteudo = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", conteudo)
    conteudo = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</tr>", "\n", conteudo)
    texto = html.unescape(re.sub(r"<[^>]+>", " ", conteudo))
    texto = "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in texto.splitlines())
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    paginas, atual = [], ""
    for par in texto.split("\n"):
        if len(atual) + len(par) > tamanho and atual:
            paginas.append(atual)
            atual = ""
        atual += par + "\n"
    return paginas + ([atual] if atual.strip() else [])


def eh_texto_abnt_protegido(paginas: list[str]) -> bool:
    amostra = "\n".join(paginas[:4])
    return any(re.search(m, amostra, re.I | re.S) for m in MARCAS_ABNT)


def importar_url(url: str, titulo: str, esfera: str = "municipal", log=print) -> dict:
    """Baixa e indexa um documento PÚBLICO (lei municipal, IT de bombeiros, norma de concessionária).

    Recusa sites de cópias não autorizadas e qualquer documento com marcas de exemplar ABNT.
    """
    partes = urllib.parse.urlsplit(url)
    if partes.scheme not in ("https", "http"):
        return {"erro": "URL inválida"}
    host = partes.netloc.lower()
    if any(b in host for b in HOSTS_BLOQUEADOS):
        return {"erro": f"{host} hospeda cópias não autorizadas de documentos — use a fonte oficial"}
    h = Http()
    try:
        dados = h.binario(url)
    except Exception as e:  # noqa: BLE001
        return {"erro": f"{type(e).__name__}: {e}"}
    doc_id = "local-" + slug(titulo)
    con = db()
    pdf = dados.startswith(b"%PDF")
    destino = data_dir() / "pdf" / f"{doc_id}.{'pdf' if pdf else 'html'}"
    destino.write_bytes(dados)
    if pdf:
        paginas = _extrair(destino)
    else:
        paginas = _html_para_paginas(dados.decode("utf-8", "replace"))
    if eh_texto_abnt_protegido(paginas):
        destino.unlink(missing_ok=True)
        return {"erro": "O documento parece ser um exemplar de norma ABNT protegido por direito autoral. "
                        "Não foi indexado. Use a cópia licenciada do usuário ou sínteses próprias."}
    sha1 = hashlib.sha1(dados).hexdigest()
    with con:
        con.execute("""INSERT OR REPLACE INTO docs(id,fonte,grupo,codigo,titulo,url,data_ref,atualizado_em)
                       VALUES(?,?,?,?,?,?,?,?)""", (doc_id, "local", f"local-{esfera}", esfera, titulo, url,
                                                    dt.date.today().isoformat(), agora()))
        con.execute("DELETE FROM pag WHERE doc_id=?", (doc_id,))
        con.executemany("INSERT INTO pag(doc_id,pagina,texto) VALUES(?,?,?)",
                        [(doc_id, i + 1, t) for i, t in enumerate(paginas) if t.strip()])
        sem_texto = sum(len(t.strip()) for t in paginas) < 50 * max(1, len(paginas))
        con.execute("UPDATE docs SET baixado=1, paginas=?, sem_texto=?, caminho=?, sha1=? WHERE id=?",
                    (len(paginas), int(sem_texto), str(destino), sha1, doc_id))
    log(f"  • {doc_id}: {len(paginas)} pág.")
    return {"id": doc_id, "paginas": len(paginas), "sem_texto": sem_texto, "fonte": "local"}


# ------------------------------------------------------------------ consulta

STOPWORDS = set("""a o e é as os ao aos à às de da do das dos em no na nos nas num numa para pra por pelo pela pelos
pelas com sem sob sobre que qual quais um uma uns umas se ou entre até como mais menos ser deve devem quando""".split())


def _fts(consulta: str, modo_ou: bool = False) -> str:
    termos = re.findall(r"[\wÀ-ÿ.]+", consulta)
    termos = [t.strip(".") for t in termos if len(t.strip(".")) > 1 and t.strip(".").lower() not in STOPWORDS]
    return (" OR " if modo_ou else " ").join(f'"{t}"' for t in termos)


def buscar(consulta: str, fonte: str | None = None, limite: int = 8) -> list[dict]:
    con = db()
    out: list[dict] = []
    for ou in (False, True):
        q = _fts(consulta, ou)
        if not q:
            return []
        sql = ("SELECT p.doc_id, p.pagina, snippet(pag, 2, '«', '»', ' … ', 24) AS trecho, bm25(pag) AS score, "
               "d.titulo, d.codigo, d.fonte, d.url, d.data_ref FROM pag p JOIN docs d ON d.id = p.doc_id "
               "WHERE pag MATCH ?" + (" AND d.fonte = ?" if fonte else "") + " ORDER BY score LIMIT ?")
        args = (q, fonte, limite) if fonte else (q, limite)
        out = [dict(r) | {"modo": "todas as palavras" if not ou else "qualquer palavra"} for r in con.execute(sql, args)]
        if out:
            break
    for r in out:
        r.pop("score", None)
        r["trecho"] = re.sub(r"\s+", " ", r["trecho"])
    return out


def buscar_catalogo(consulta: str, fonte: str | None = None, limite: int = 20) -> list[dict]:
    con = db()
    termos = sem_acento(consulta).split()
    rows = con.execute("SELECT id, fonte, grupo, codigo, titulo, data_ref, baixado, url FROM docs"
                       + (" WHERE fonte=?" if fonte else ""), (fonte,) if fonte else ()).fetchall()
    sel = [dict(r) for r in rows if all(t in sem_acento(f"{r['id']} {r['codigo']} {r['titulo']}") for t in termos)]
    sel.sort(key=lambda r: (-r["baixado"], -ano(r["data_ref"]), r["id"]))  # mais recentes primeiro
    return sel[:limite]


def ano(ref: str | None) -> int:
    """'2025', '2025-03-10', '04' (DNIT 058/04) ou '71' → ano com 4 dígitos (0 se desconhecido)."""
    m = re.match(r"(\d{2,4})", ref or "")
    if not m:
        return 0
    a = int(m.group(1))
    return a if a >= 100 else (2000 + a if a <= 40 else 1900 + a)


def ler(doc_id: str, pagina: int, quantidade: int = 1) -> dict:
    con = db()
    doc_id = resolver(con, doc_id)
    d = con.execute("SELECT id, titulo, codigo, fonte, url, paginas, baixado FROM docs WHERE id=?", (doc_id,)).fetchone()
    if not d:
        return {"erro": f"documento '{doc_id}' não encontrado"}
    if not d["baixado"]:
        return {"erro": f"'{doc_id}' está no catálogo mas não foi baixado — use baixar primeiro"}
    rows = con.execute("SELECT pagina, texto FROM pag WHERE doc_id=? AND pagina BETWEEN ? AND ? ORDER BY pagina",
                       (doc_id, pagina, pagina + max(1, min(quantidade, 5)) - 1)).fetchall()
    return {**dict(d), "fonte_aviso": FONTES[d["fonte"]],
            "conteudo": [{"pagina": r["pagina"], "texto": r["texto"]} for r in rows]}


def localizar_item(doc_id: str, item: str, linhas: int = 25) -> dict:
    """Trecho que começa no item numerado (ex.: 18.13.4) até o próximo item do mesmo nível ou acima."""
    con = db()
    doc_id = resolver(con, doc_id)
    rows = con.execute("SELECT pagina, texto FROM pag WHERE doc_id=? ORDER BY pagina", (doc_id,)).fetchall()
    if not rows:
        return {"erro": f"'{doc_id}' não está indexado"}
    alvo = re.compile(rf"^\s*{re.escape(item)}(?:\.|\s|$)")
    nivel = item.count(".")
    proximo = re.compile(r"^\s*(\d+(?:\.\d+){0,%d})(?:\.|\s)" % nivel)
    out, pag_ini, capturando = [], None, False
    for r in rows:
        for ln in r["texto"].splitlines():
            if not capturando and alvo.match(ln):
                capturando, pag_ini = True, r["pagina"]
                out.append(ln)
                continue
            if capturando:
                m = proximo.match(ln)
                if (m and m.group(1) != item and not m.group(1).startswith(item + ".")) or len(out) >= linhas:
                    return {"id": doc_id, "item": item, "pagina": pag_ini, "texto": "\n".join(out)}
                out.append(ln)
    if out:
        return {"id": doc_id, "item": item, "pagina": pag_ini, "texto": "\n".join(out)}
    return {"erro": f"item {item} não encontrado em {doc_id} (tente buscar pelo assunto)"}


def status() -> dict:
    con = db()
    por_fonte = {r["fonte"]: {"catalogo": r["n"], "indexados": r["b"]} for r in con.execute(
        "SELECT fonte, COUNT(*) n, SUM(baixado) b FROM docs GROUP BY fonte")}
    meta = {r["chave"]: r["valor"] for r in con.execute("SELECT * FROM meta")}
    tam = sum(f.stat().st_size for f in (data_dir() / "pdf").glob("*.pdf"))
    return {"pasta": str(data_dir()), "fontes": por_fonte, "atualizacoes": meta, "pdf_mb": round(tam / 1e6, 1),
            "avisos": FONTES}


# ------------------------------------------------------------------ CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("catalogo")
    p.add_argument("--fonte", choices=list(COLETORES), action="append")
    p = sub.add_parser("baixar")
    p.add_argument("--ids", nargs="*")
    p.add_argument("--padrao", action="store_true", help="NRs da construção civil")
    p.add_argument("--grupo")
    p.add_argument("--busca")
    p.add_argument("--max", type=int, default=10)
    p.add_argument("--forcar", action="store_true")
    p = sub.add_parser("buscar")
    p.add_argument("consulta")
    p.add_argument("--fonte")
    p.add_argument("--limite", type=int, default=8)
    p = sub.add_parser("catalogo-buscar")
    p.add_argument("consulta")
    p.add_argument("--fonte")
    p = sub.add_parser("ler")
    p.add_argument("id")
    p.add_argument("--pagina", type=int, default=1)
    p.add_argument("--n", type=int, default=1)
    p = sub.add_parser("item")
    p.add_argument("id")
    p.add_argument("item")
    p = sub.add_parser("importar-url")
    p.add_argument("url")
    p.add_argument("--titulo", required=True)
    p.add_argument("--esfera", default="municipal")
    p = sub.add_parser("importar")
    p.add_argument("arquivo")
    p.add_argument("--titulo", required=True)
    p.add_argument("--codigo", default="")
    sub.add_parser("status")
    a = ap.parse_args(argv)

    def show(x):
        print(json.dumps(x, indent=2, ensure_ascii=False))

    if a.cmd == "catalogo":
        r = atualizar_catalogo(a.fonte)
        return 0 if any(isinstance(v, int) for v in r.values()) else 1
    if a.cmd == "baixar":
        ids = list(a.ids or [])
        if a.padrao:
            ids += ids_padrao()
        if a.grupo or a.busca:
            ids += ids_por_filtro(a.grupo, a.busca, a.max)
        if not ids:
            ap.error("informe --ids, --padrao, --grupo ou --busca")
        r = baixar(list(dict.fromkeys(ids)), forcar=a.forcar)
        return 0 if any("erro" not in x for x in r) else 2  # falha parcial não interrompe a instalação
    if a.cmd == "buscar":
        show(buscar(a.consulta, a.fonte, a.limite))
    elif a.cmd == "catalogo-buscar":
        show(buscar_catalogo(a.consulta, a.fonte))
    elif a.cmd == "ler":
        show(ler(a.id, a.pagina, a.n))
    elif a.cmd == "item":
        show(localizar_item(a.id, a.item))
    elif a.cmd == "importar-url":
        r = importar_url(a.url, a.titulo, a.esfera)
        show(r)
        return 0 if "erro" not in r else 2
    elif a.cmd == "importar":
        show(importar(Path(a.arquivo), a.titulo, a.codigo))
    elif a.cmd == "status":
        show(status())
    return 0


if __name__ == "__main__":
    sys.exit(main())
