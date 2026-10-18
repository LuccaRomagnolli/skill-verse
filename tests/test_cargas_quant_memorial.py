"""Testes de quantitativos e orçamento SINAPI."""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EC = ROOT / "catalog/engenharia-civil"
sys.path.insert(0, str(EC / "quantitativos-sinapi/scripts"))

import quantitativos  # noqa: E402


def run(path, *args):
    return subprocess.run([sys.executable, str(path), *args], capture_output=True, text=True, check=True).stdout


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
