"""Testes das skills de cargas/vento, quantitativos/SINAPI e memorial."""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EC = ROOT / "catalog/engenharia-civil"
sys.path.insert(0, str(EC / "cargas-combinacoes/scripts"))
sys.path.insert(0, str(EC / "quantitativos-sinapi/scripts"))

import combinacoes  # noqa: E402
import quantitativos  # noqa: E402
import vento  # noqa: E402


def run(path, *args):
    return subprocess.run([sys.executable, str(path), *args], capture_output=True, text=True, check=True).stdout


# --------------------------------------------------------------- combinações

def test_elu_com_vento_secundario():
    acoes = [combinacoes.parse(s) for s in ("G:permanente:120", "Q:comercial:45", "W0:vento:30:vento", "W90:vento:-25:vento")]
    r = combinacoes.combinar(acoes)
    assert r["envoltoria"]["ELU"]["max"] == pytest.approx(1.4 * 120 + 1.4 * (45 + 0.6 * 30))
    assert r["envoltoria"]["ELU"]["min"] == pytest.approx(1.0 * 120 + 1.4 * (-25))
    assert r["envoltoria"]["ELS_quase_permanente"]["max"] == pytest.approx(120 + 0.4 * 45)


def test_grupo_exclusivo_nao_soma_ventos():
    acoes = [combinacoes.parse(s) for s in ("G:permanente:10", "W0:vento:5:v", "W90:vento:5:v")]
    r = combinacoes.combinar(acoes)
    assert r["envoltoria"]["ELU"]["max"] == pytest.approx(1.4 * 10 + 1.4 * 5)


def test_so_permanentes():
    r = combinacoes.combinar([combinacoes.parse("G:permanente:10")])
    assert r["envoltoria"]["ELU"]["max"] == pytest.approx(14)


# --------------------------------------------------------------- vento

def test_s2_categoria_ii_classe_a_10m():
    assert vento.s2(10, "II", "A") == pytest.approx(1.0)


def test_s2_minimo_5m():
    assert vento.s2(3, "IV", "B") == pytest.approx(vento.s2(5, "IV", "B"))


def test_pressao_dinamica():
    out = json.loads(run(EC / "cargas-combinacoes/scripts/vento.py", "--V0", "40", "--categoria", "II", "--classe", "A",
                         "--alturas", "10", "--formato", "json"))
    c = out["cotas"][0]
    assert c["Vk"] == pytest.approx(40.0)
    assert c["q_kN_m2"] == pytest.approx(0.613 * 1600 / 1000)


# --------------------------------------------------------------- quantitativos

def test_quantitativos_exemplo():
    dados = json.loads((EC / "quantitativos-sinapi/assets/elementos.exemplo.json").read_text(encoding="utf-8"))
    r = quantitativos.calcular(dados, 10, "total")
    t = r["totais"]
    assert t["concreto_m3"] == pytest.approx(2.0 + 0.3375 + 0.48 + 0.672 + 1.6, rel=1e-3)
    v1 = next(l for l in r["concreto"] if l["id"] == "V1")
    assert v1["forma_m2"] == pytest.approx(5 * (0.15 + 2 * 0.35 + 0.10))
    fachada = r["alvenaria"][0]
    assert fachada["vaos_m2"] == pytest.approx(1.44 + 1.89)


def test_vaos_regra_excedente():
    r = quantitativos.calcular({"alvenaria": [{"id": "p", "comprimento": 5, "altura": 3, "vaos": [[1, 1], [2, 2]]}]},
                               0, "excedente-2m2")
    assert r["alvenaria"][0]["vaos_m2"] == pytest.approx(2.0)


# --------------------------------------------------------------- SINAPI (planilha sintética)

def _xlsx(path: Path, rows: list[list]) -> None:
    strings: list[str] = []

    def cell(ref, v):
        if isinstance(v, (int, float)):
            return f'<c r="{ref}"><v>{v}</v></c>'
        strings.append(str(v))
        return f'<c r="{ref}" t="s"><v>{len(strings) - 1}</v></c>'
    sheet_rows = []
    for i, r in enumerate(rows, 1):
        cells = "".join(cell(f"{chr(65 + j)}{i}", v) for j, v in enumerate(r) if v != "")
        sheet_rows.append(f'<row r="{i}">{cells}</row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rns = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook {ns} {rns}><sheets><sheet name="Sintetico" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="x" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", f'<worksheet {ns}><sheetData>{"".join(sheet_rows)}</sheetData></worksheet>')
        z.writestr("xl/sharedStrings.xml", f'<sst {ns}>' + "".join(f"<si><t>{s}</t></si>" for s in strings) + "</sst>")


@pytest.fixture
def planilha(tmp_path):
    p = tmp_path / "SINAPI_teste.xlsx"
    _xlsx(p, [["SINAPI - CUSTO DE COMPOSIÇÕES"], ["PERÍODO 09/2026"], [""],
              ["CODIGO DA COMPOSICAO", "DESCRICAO DA COMPOSICAO", "UNIDADE", "CUSTO TOTAL"],
              [94965, "CONCRETO FCK = 25MPA, TRAÇO 1:2,3:2,7 (EM MASSA SECA DE CIMENTO/ AREIA MÉDIA/ BRITA 1)", "M3", 512.34],
              [92873, "LANÇAMENTO COM USO DE BALDES, ADENSAMENTO E ACABAMENTO DE CONCRETO EM ESTRUTURAS", "M3", "189,50"]])
    return p


def test_sinapi_busca_e_orcamento(planilha, tmp_path):
    script = EC / "quantitativos-sinapi/scripts/sinapi.py"
    out = run(script, "buscar", "--arquivo", str(planilha), "--termo", "concreto fck 25")
    assert "94965" in out and "512.34" in out
    itens = tmp_path / "itens.json"
    itens.write_text(json.dumps([{"codigo": "94965", "quantidade": 2}, {"codigo": "92873", "quantidade": 2}]))
    csv_out = tmp_path / "orc.csv"
    out = run(script, "orcar", "--arquivo", str(planilha), "--itens", str(itens), "--bdi", "25", "--saida", str(csv_out))
    total = (512.34 + 189.50) * 2 * 1.25
    assert f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") in out
    assert csv_out.read_text(encoding="utf-8-sig").count("\n") == 3


# --------------------------------------------------------------- memorial

def test_memorial_gera_tres_formatos(tmp_path):
    res = tmp_path / "resultados"
    res.mkdir()
    conc = EC / "concreto-armado-nbr6118/scripts"
    (res / "V1.json").write_text(run(conc / "viga.py", "--b", "15", "--h", "45", "--fck", "25", "--Mk", "50", "--formato", "json"))
    (res / "L1.json").write_text(run(conc / "laje.py", "--lx", "4", "--ly", "5", "--h", "10", "--q", "1.5", "--fck", "25",
                                     "--formato", "json"))
    out = tmp_path / "memorial"
    run(EC / "memorial-de-calculo/scripts/gerar_memorial.py", "--projeto",
        str(EC / "memorial-de-calculo/assets/projeto.exemplo.json"), "--resultados", str(res), "--saida", str(out))
    md = (out / "MEMORIAL.md").read_text(encoding="utf-8")
    assert md.index("7.1. L1") < md.index("7.2. V1")
    assert "pendente-validacao-2026" in md
    assert "<table>" in (out / "MEMORIAL.html").read_text(encoding="utf-8")
    with zipfile.ZipFile(out / "MEMORIAL.docx") as z:
        assert "word/document.xml" in z.namelist()
