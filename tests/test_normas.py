"""Testes do coletor/índice de normas públicas — offline (HTML de fixture, Http falso, extração simulada)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "mcps/normas-publicas/servidor"))
import normas  # noqa: E402

B = normas.NR_INDICE

INDICE = f"""<html><a href="{B}/nr-1">NR-1</a> <a href="{B}/norma-regulamentadora-no-18-nr-18">NR-18</a>
<a href="{B}/norma-regulamentadora-no-21-nr-21">NR-21</a>
<a href="https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/outra/pasta/norma-regulamentadora-no-37-nr-37">NR-37</a>
<a href="https://www.facebook.com/sharer.php?u={B}/normas-regulamentadoras-nrs">x</a></html>"""

PAGINAS = {
    f"{B}/nr-1": '<h1>Norma Regulamentadora No. 1 (NR-1)</h1><a href="/x/nr-01-atualizada-2022-1.pdf">a</a>'
                 '<a href="/x/nr-01-atualizada-2025.pdf">b</a><a href="/x/guia-nr-01-revisado.pdf">Guia da NR-1</a>',
    f"{B}/norma-regulamentadora-no-18-nr-18":
        '<h1>Norma Regulamentadora No. 18 (NR-18)</h1>'
        '<a href="/arquivos/atas-ctpp/69_reuniao.pdf">ata</a>'
        '<a href="/v/NR18atualizada2026I.pdf">texto 2026</a><a href="/v/nr-18-atualizada-2020.pdf">texto 2020</a>'
        '<a href="/v/nr-10.pdf">outra NR</a>',
    f"{B}/norma-regulamentadora-no-21-nr-21": '<h1>NR-21</h1><a href="/v/nr-21.pdf">texto</a>'
                                              '<a href="/p/portaria_3-214_aprova_as_nrs.pdf">portaria</a>',
    "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/outra/pasta/norma-regulamentadora-no-37-nr-37":
        '<h1>NR-37</h1><a href="/v/nr-37-atualizada-2023.pdf">t</a>'
        '<a href="/v/CARTILHA_PLATAFORMAS.pdf">Cartilha de plataformas</a>',
}


class FakeHttp:
    def __init__(self, paginas=None, binarios=None):
        self.paginas = {B: INDICE, **PAGINAS, **(paginas or {})}
        self.binarios = binarios or {}

    def texto(self, url):
        return self.paginas[url]

    def binario(self, url):
        return self.binarios[url]


@pytest.fixture
def pasta(tmp_path, monkeypatch):
    monkeypatch.setenv("NORMAS_DIR", str(tmp_path / "normas"))
    return tmp_path / "normas"


def test_links_pdf_com_texto():
    h = '<a class="x" href="https://a/b/DNIT_143_2025_ES.pdf">DNIT 143/2025 - ES - Pavimentação - <b>solo-cimento</b></a>'
    assert normas.links_pdf(h) == [("https://a/b/DNIT_143_2025_ES.pdf", "DNIT 143/2025 - ES - Pavimentação - solo-cimento")]


def test_catalogo_nr_escolhe_versao_vigente():
    docs = {d["id"]: d for d in normas.catalogo_nr(FakeHttp())}
    assert docs["nr-18"]["url"].endswith("NR18atualizada2026I.pdf") and docs["nr-18"]["data_ref"] == "2026"
    assert docs["nr-01"]["url"].endswith("nr-01-atualizada-2025.pdf")
    assert docs["nr-21"]["url"].endswith("nr-21.pdf")          # sem ano no nome
    assert docs["nr-37"]["data_ref"] == "2023"                  # página fora da pasta do índice
    assert any(d["grupo"] == "nr-manual" and d["codigo"] == "NR-1" for d in docs.values())
    assert any(d["grupo"] == "nr-manual" and d["codigo"] == "NR-37" for d in docs.values())
    assert not any("reuniao" in d["url"] or "portaria" in d["url"] for d in docs.values())
    assert not any(d["url"].endswith("/nr-10.pdf") for d in docs.values())  # PDF de outra NR na página


def test_catalogo_dnit_codigo_do_titulo(monkeypatch):
    html = ('<a href="https://www.gov.br/dnit/pt-br/assuntos/planejamento-e-pesquisa/ipr/c/DNIT_143_2025_ES.pdf">'
            'DNIT 143/2025 - ES - Pavimentação - Sub-base de solo-cimento</a>')
    paginas = {f"{normas.DNIT_BASE}/{c}": (html if k == "es" else "") for k, c in normas.DNIT_CATEGORIAS.items()}
    docs = normas.catalogo_dnit(FakeHttp(paginas))
    assert len(docs) == 1 and docs[0]["codigo"] == "DNIT 143/2025 - ES" and docs[0]["grupo"] == "dnit-es"
    assert docs[0]["data_ref"] == "2025"


def _popular(pasta, monkeypatch):
    con = normas.db()
    with con:
        for d in normas.catalogo_nr(FakeHttp()):
            con.execute("INSERT INTO docs(id,fonte,grupo,codigo,titulo,url,data_ref) VALUES(?,?,?,?,?,?,?)",
                        (d["id"], d["fonte"], d["grupo"], d["codigo"], d["titulo"], d["url"], d["data_ref"]))
    textos = {
        "nr-18": ["18.13 Sinalização de segurança\n18.13.1 O canteiro de obras deve ser sinalizado com o objetivo de:\n"
                  "a) identificar os locais de apoio;\nb) indicar as saídas de emergência;\n18.13.2 É obrigatório o uso "
                  "de vestimenta de alta visibilidade.",
                  "18.14.1 O sistema de guarda-corpo deve ter travessão superior entre 1,0 m e 1,20 m de altura."],
        "nr-35": ["35.2.1 Aplica-se a toda atividade com diferença de nível acima de 2,0 m (dois metros), onde haja "
                  "risco de queda — trabalho em altura."],
    }
    pdf = {d["url"]: b"%PDF-" + k.encode() for d in normas.catalogo_nr(FakeHttp()) for k in [d["id"]]}
    monkeypatch.setattr(normas, "_extrair", lambda caminho: textos.get(Path(caminho).stem, ["texto curto"]))
    monkeypatch.setattr(normas, "Http", lambda: FakeHttp(binarios=pdf))
    return con


def test_baixar_buscar_e_localizar(pasta, monkeypatch):
    _popular(pasta, monkeypatch)
    res = normas.baixar(["nr-18", "nr-inexistente"], log=lambda m: None)
    assert res[0]["paginas"] == 2 and "erro" in res[1]
    r = normas.buscar("guarda corpo travessão")
    assert r and r[0]["doc_id"] == "nr-18" and r[0]["pagina"] == 2 and "«" in r[0]["trecho"]
    assert normas.buscar("guarda-corpo de altura")[0]["doc_id"] == "nr-18"  # stopwords ignoradas
    assert normas.buscar("sinalizacao")[0]["pagina"] == 1                    # sem acento encontra com acento
    it = normas.localizar_item("nr-18", "18.13.1")
    assert it["pagina"] == 1 and "saídas de emergência" in it["texto"] and "18.13.2" not in it["texto"]
    assert "erro" in normas.localizar_item("nr-18", "18.99.9")
    assert normas.ler("nr-35", 1)["erro"]                                   # não baixado ainda
    assert normas.ler("nr-18", 2)["conteudo"][0]["texto"].startswith("18.14.1")
    assert normas.baixar(["nr-18"], log=lambda m: None)[0]["status"] == "já indexado"


def test_documento_identico_vira_alias(pasta, monkeypatch):
    con = _popular(pasta, monkeypatch)
    with con:
        con.execute("INSERT INTO docs(id,fonte,grupo,codigo,titulo,url) VALUES('nr-18-copia','nr','nr-manual','NR-18','c',"
                    "(SELECT url FROM docs WHERE id='nr-18'))")
    normas.baixar(["nr-18"], log=lambda m: None)
    r = normas.baixar(["nr-18-copia"], log=lambda m: None)
    assert "idêntico a nr-18" in r[0]["status"]
    assert normas.localizar_item("nr-18-copia", "18.13.1")["id"] == "nr-18"
    assert con.execute("SELECT COUNT(*) FROM pag WHERE doc_id='nr-18-copia'").fetchone()[0] == 0


def test_busca_catalogo_e_padrao(pasta, monkeypatch):
    _popular(pasta, monkeypatch)
    assert [d["id"] for d in normas.buscar_catalogo("NR-18")] == ["nr-18"]
    padrao = normas.ids_padrao()
    assert "nr-18" in padrao and "nr-35" in padrao
    assert any(i.startswith("nr-01-") for i in padrao)        # guia da NR-1 entra
    assert not any(i.startswith("nr-37-") for i in padrao)    # NR-37 (petróleo) não é da construção


def test_status(pasta, monkeypatch):
    _popular(pasta, monkeypatch)
    normas.baixar(["nr-18"], log=lambda m: None)
    st = normas.status()
    assert st["fontes"]["nr"]["indexados"] == 1 and "DOU" in st["avisos"]["nr"]


def test_ano_normaliza_dois_digitos():
    assert normas.ano("2025") == 2025 and normas.ano("04") == 2004 and normas.ano("71") == 1971
    assert normas.ano("2026-10-09") == 2026 and normas.ano("") == 0
