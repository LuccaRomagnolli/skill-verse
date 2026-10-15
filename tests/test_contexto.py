"""Testes da ficha de contexto do projeto, das travas de importação web e do memorial com contexto."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EC = ROOT / "catalog/engenharia-civil"
CTX = EC / "contexto-do-projeto/scripts/contexto.py"
sys.path.insert(0, str(ROOT / "mcps/normas-publicas/servidor"))
import normas  # noqa: E402


def ctx(*args, home):
    return subprocess.run([sys.executable, str(CTX), *args], capture_output=True, text=True,
                          env={"SKILLVERSE_HOME": str(home), "PATH": "/usr/bin:/bin"})


def test_ficha_com_perfil_padrao_e_checklist(tmp_path):
    sv = tmp_path / "sv"
    assert ctx("perfil", "--municipio", "Goiânia", "--uf", "go", home=sv).returncode == 0
    r = ctx("iniciar", "--pasta", str(tmp_path), "--projeto", "Sobrado", "--uso", "residencial-multifamiliar",
            "--ambiente", "marinho", home=sv)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["municipio"] == "Goiânia" and out["uf"] == "GO"
    assert out["caa"]["classe"] == "III"
    assert any("Corpo de Bombeiros" in p for p in out["pesquisar"])
    assert any("vagas" in p for p in out["pesquisar"])  # extra do uso multifamiliar
    assert ctx("iniciar", "--pasta", str(tmp_path), home=sv).returncode != 0  # não sobrescreve sem --forcar


def test_fonte_marca_checklist_e_md(tmp_path):
    sv = tmp_path / "sv"
    ctx("iniciar", "--pasta", str(tmp_path), "--municipio", "Curitiba", "--uf", "PR", home=sv)
    assert ctx("fonte", "--pasta", str(tmp_path), "--checklist", "c99", "--esfera", "municipal", "--tipo", "x",
               "--titulo", "y", home=sv).returncode != 0
    ctx("fonte", "--pasta", str(tmp_path), "--checklist", "c1", "--esfera", "municipal", "--tipo", "Código de Obras",
        "--titulo", "Lei X — Código de Obras", "--url", "https://x.gov.br/l.pdf", "--vigente", "sim", home=sv)
    ctx("nao-aplica", "--pasta", str(tmp_path), "--checklist", "c5", "--motivo", "isento", home=sv)
    ctx("pendencia", "--pasta", str(tmp_path), "--texto", "Confirmar zona do lote", home=sv)
    md = (tmp_path / "projeto-contexto.md").read_text(encoding="utf-8")
    assert "Lei X — Código de Obras" in md and "`c1`" not in md and "`c5`" not in md and "`c2`" in md
    assert "Confirmar zona do lote" in md


def test_ficha_exige_municipio_valido(tmp_path):
    assert ctx("iniciar", "--pasta", str(tmp_path), "--municipio", "X", "--uf", "ZZ", home=tmp_path / "sv").returncode != 0


# --------------------------------------------------------------- travas de importação web

@pytest.fixture
def pasta(tmp_path, monkeypatch):
    monkeypatch.setenv("NORMAS_DIR", str(tmp_path / "normas"))
    return tmp_path


class FakeHttp:
    def __init__(self, dados):
        self.dados = dados

    def binario(self, url):
        return self.dados


def test_bloqueia_sites_de_copias(pasta):
    for url in ("https://www.scribd.com/doc/1/NBR-6118", "https://www.passeidireto.com/arquivo/1/nbr"):
        assert "não autorizadas" in normas.importar_url(url, "x")["erro"]


def test_recusa_exemplar_abnt(pasta, monkeypatch):
    monkeypatch.setattr(normas, "Http", lambda: FakeHttp(b"%PDF-fake"))
    monkeypatch.setattr(normas, "_extrair", lambda c: ["ABNT NBR 6118:2023\nExemplar para uso exclusivo - FULANO", "texto"])
    r = normas.importar_url("https://algum-site.com/nbr6118.pdf", "NBR 6118")
    assert "protegido por direito autoral" in r["erro"]
    assert not list((pasta / "normas" / "pdf").glob("*"))


def test_importa_lei_municipal_html(pasta, monkeypatch):
    html = ("<html><nav>menu</nav><h1>Lei 123/2020 — Código de Obras</h1><p>Art. 10. O afastamento frontal mínimo "
            "é de 5,00 m.</p><script>x()</script></html>").encode()
    monkeypatch.setattr(normas, "Http", lambda: FakeHttp(html))
    r = normas.importar_url("https://camara.exemplo.sp.leg.br/lei123", "Lei 123/2020 — Código de Obras")
    assert r["fonte"] == "local" and r["paginas"] == 1
    res = normas.buscar("afastamento frontal", fonte="local")
    assert res and "5,00" in res[0]["trecho"] and "menu" not in normas.ler(r["id"], 1)["conteudo"][0]["texto"]


# --------------------------------------------------------------- memorial com contexto

def test_memorial_inclui_contexto(tmp_path):
    sv = tmp_path / "sv"
    ctx("iniciar", "--pasta", str(tmp_path), "--municipio", "Santos", "--uf", "SP", "--ambiente", "marinho", home=sv)
    ctx("fonte", "--pasta", str(tmp_path), "--checklist", "c1", "--esfera", "municipal", "--tipo", "Código de Obras",
        "--titulo", "LC 84/1992 — Código de Edificações de Santos", "--url", "https://x.sp.gov.br", "--vigente", "sim", home=sv)
    res = tmp_path / "resultados"
    res.mkdir()
    (res / "V1.json").write_text(subprocess.run(
        [sys.executable, str(EC / "concreto-armado-nbr6118/scripts/viga.py"), "--b", "15", "--h", "45", "--fck", "30",
         "--Mk", "40", "--formato", "json"], capture_output=True, text=True, check=True).stdout)
    subprocess.run([sys.executable, str(EC / "memorial-de-calculo/scripts/gerar_memorial.py"), "--projeto",
                    str(EC / "memorial-de-calculo/assets/projeto.exemplo.json"), "--resultados", str(res),
                    "--saida", str(tmp_path / "m"), "--contexto", str(tmp_path / "projeto-contexto.json")], check=True)
    md = (tmp_path / "m/MEMORIAL.md").read_text(encoding="utf-8")
    assert "Santos/SP" in md and "Código de Edificações de Santos" in md


# --------------------------------------------------------------- integração da ficha com as outras skills

def _ficha(pasta, ambiente, home):
    assert ctx("iniciar", "--pasta", str(pasta), "--municipio", "Santos", "--uf", "SP", "--ambiente", ambiente,
               home=home).returncode == 0


def _run(script, *args, cwd):
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, cwd=cwd, check=True).stdout


def test_scripts_de_concreto_leem_caa_da_ficha(tmp_path):
    _ficha(tmp_path, "marinho", tmp_path / "sv")
    conc = EC / "concreto-armado-nbr6118/scripts"
    v = json.loads(_run(conc / "viga.py", "--b", "15", "--h", "45", "--fck", "25", "--Mk", "40", "--formato", "json",
                        cwd=tmp_path))
    passos = {p["descricao"]: p["calculo"] for p in v["memoria"]["passos"]}
    assert "CAA III" in passos["Classe de agressividade"] and "ficha do projeto" in passos["Classe de agressividade"]
    assert passos["Cobrimento nominal (Tab. 7.2)"] == "c = 40 mm"
    assert any("C30" in a for a in v["memoria"]["alertas"])               # C25 < mínimo da CAA III
    l = json.loads(_run(conc / "laje.py", "--lx", "4", "--ly", "5", "--h", "12", "--q", "1.5", "--fck", "30",
                        "--formato", "json", cwd=tmp_path))
    assert any("c = 35 mm" in p["calculo"] for p in l["memoria"]["passos"])
    p = json.loads(_run(conc / "pilar.py", "--bx", "20", "--by", "40", "--lex", "2.8", "--ley", "2.8", "--Nk", "600",
                        "--fck", "30", "--caa", "II", "--formato", "json", cwd=tmp_path))
    assert any("CAA II — informada" in x["calculo"] for x in p["memoria"]["passos"])  # --caa prevalece


def test_sem_ficha_usa_padrao_e_avisa(tmp_path):
    v = json.loads(_run(EC / "concreto-armado-nbr6118/scripts/viga.py", "--b", "15", "--h", "45", "--fck", "25",
                        "--Mk", "40", "--formato", "json", cwd=tmp_path))
    assert any("sem ficha" in p["calculo"] for p in v["memoria"]["passos"])


def test_detalhe_autocad_usa_cobrimento_da_ficha(tmp_path):
    _ficha(tmp_path, "industrial-agressivo", tmp_path / "sv")
    _run(EC / "autocad-assistente/scripts/detalhe_secao.py", "--b", "20", "--h", "50", "--inf", "3x16", "--nome", "V2",
         "--ops", "ops.json", cwd=tmp_path)
    assert '"c = 5 cm"' in (tmp_path / "ops.json").read_text(encoding="utf-8")
