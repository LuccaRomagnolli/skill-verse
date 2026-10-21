"""Testes da cotação de materiais (cálculo, ranking, importação e XLSX)."""
import datetime as dt
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "catalog/engenharia-civil/cotacao-materiais"
SCRIPT = SKILL / "scripts/cotacao.py"
sys.path.insert(0, str(SKILL / "scripts"))

import cotacao  # noqa: E402

HOJE = dt.date(2026, 10, 18)


def oferta(fornecedor, preco, conteudo=50, **kw):
    o = {"fornecedor": fornecedor, "produto": "p", "url": f"https://example.com/{fornecedor}", "preco": preco,
         "unidade_venda": "saco", "conteudo": conteudo, "frete": 0, "prazo_dias": 2, "acesso": "2026-10-18",
         "atende": "sim", "confirmado": True}
    o.update(kw)
    return o


def item(ofertas, **kw):
    it = {"item": "1", "descricao": "Cimento CP II", "unidade": "kg", "quantidade": 1000, "ofertas": ofertas}
    it.update(kw)
    return it


def calc(*itens, validade=7):
    return cotacao.calcular({"itens": list(itens)}, validade, HOJE)


def test_exemplo_valida_e_totais():
    dados = json.loads((SKILL / "assets/cotacoes.exemplo.json").read_text(encoding="utf-8"))
    assert cotacao.validar(dados) == []
    r = cotacao.calcular(dados, 7, HOJE)
    cimento, aco, bloco, concreto = r["itens"]
    assert cimento["quantidade"] == pytest.approx(1575)
    assert cimento["escolhida"]["fornecedor"].startswith("Fornecedor A")
    assert cimento["escolhida"]["n_compra"] == 32 and cimento["escolhida"]["total"] == pytest.approx(32 * 39.90)
    # barra 12 m de φ10 vence o pedido mínimo de 300 kg da central de corte e dobra
    assert aco["escolhida"]["n_compra"] == 15
    assert bloco["quantidade"] == 451  # 31,77 × 13,5 × 1,05 = 450,34 → peça inteira
    assert bloco["escolhida"]["total"] == pytest.approx(1150 + 150)
    assert concreto["escolhida"] is None and "4" in r["resumo"]["sem_preco"]
    assert r["resumo"]["total"] == pytest.approx(32 * 39.90 + 15 * 54.90 + 1300)


def test_embalagem_arredonda_e_frete_decide():
    # 1050 kg → 21 sacos; B tem saco mais barato, mas o frete o torna mais caro no total
    r = calc(item([oferta("A", 40.0), oferta("B", 38.0, frete=60)], perda_pct=5))
    o = r["itens"][0]["escolhida"]
    assert o["fornecedor"] == "A" and o["n_compra"] == 21
    ranking = {x["fornecedor"]: x["indice"] for x in r["itens"][0]["ofertas"]}
    assert ranking["A"] == pytest.approx(1.0) and ranking["B"] == pytest.approx((21 * 38 + 60) / (21 * 40))


def test_baixa_confianca_nao_e_recomendada():
    r = calc(item([oferta("barata", 30.0, confirmado=False), oferta("ok", 35.0)]))
    assert r["itens"][0]["escolhida"]["fornecedor"] == "ok"
    barata = next(o for o in r["itens"][0]["ofertas"] if o["fornecedor"] == "barata")
    assert barata["confianca"] == "baixa" and barata["ranking"] == 1


def test_so_baixa_confianca_indica_com_alerta():
    r = calc(item([oferta("velha", 30.0, acesso="2026-09-01")]))
    assert r["itens"][0]["escolhida"]["fornecedor"] == "velha"
    assert any("baixa confiança" in a for a in r["itens"][0]["alertas"])


def test_exclui_nao_atende_e_sob_consulta():
    r = calc(item([oferta("errado", 10.0, atende="nao"),
                   {"fornecedor": "local", "situacao": "sob-consulta", "contato": "tel"},
                   oferta("certo", 40.0)]))
    i = r["itens"][0]
    assert i["escolhida"]["fornecedor"] == "certo"
    assert [o["fornecedor"] for o in i["ofertas"] if o["valida"]] == ["certo"]


def test_preco_abaixo_da_mediana_vira_baixa():
    r = calc(item([oferta("a", 40.0), oferta("b", 42.0), oferta("c", 41.0), oferta("golpe", 15.0)]))
    i = r["itens"][0]
    golpe = next(o for o in i["ofertas"] if o["fornecedor"] == "golpe")
    assert golpe["confianca"] == "baixa" and i["escolhida"]["fornecedor"] == "a"


def test_frete_ausente_e_media_e_fracionavel_com_minimo():
    r = calc(item([oferta("kg", 8.0, conteudo=1, unidade_venda="kg", fracionavel=True, pedido_minimo=300, frete=None)],
                  quantidade=110.31))
    o = r["itens"][0]["escolhida"]
    assert o["confianca"] == "media" and o["n_compra"] == 300 and o["total"] == pytest.approx(2400)


def test_massa_barra_nbr7480():
    assert cotacao.massa_barra(10, 12) == pytest.approx(7.404)
    assert cotacao.massa_barra(12.5, 12) == pytest.approx(11.556)
    with pytest.raises(SystemExit):
        cotacao.massa_barra(11, 12)


def test_validar_aponta_campos():
    erros = cotacao.validar({"itens": [item([{"fornecedor": "x", "preco": 10}]),
                                       item([], quantidade=0)]})
    assert any("conteudo" in e for e in erros) and any("quantidade" in e for e in erros)


def test_importar_csv_de_quantitativos(tmp_path):
    p = tmp_path / "quant.csv"
    p.write_text("servico;unidade;quantidade\nconcreto;m³;5,089\nalvenaria;m²;31,770\naco;kg;110,310\n", encoding="utf-8")
    dados = cotacao.importar(p, None)
    assert [i["quantidade"] for i in dados["itens"]] == pytest.approx([5.089, 31.77, 110.31])
    assert "alerta_servico" in dados["itens"][1] and "alerta_servico" not in dados["itens"][2]


def test_importar_prefere_descricao(tmp_path):
    p = tmp_path / "lista.csv"
    p.write_text("Item;Serviço;Descrição;Un;Qtde\n1.1;Estrutura;Cimento CP II-F-32;saco;30\n", encoding="utf-8")
    it = cotacao.importar(p, None)["itens"][0]
    assert it["item"] == "1.1" and it["descricao"] == "Cimento CP II-F-32" and it["quantidade"] == 30


def test_gerar_xlsx_valido(tmp_path):
    xlsx, csv_out = tmp_path / "c.xlsx", tmp_path / "c.csv"
    out = subprocess.run([sys.executable, str(SCRIPT), "gerar", "--cotacoes", str(SKILL / "assets/cotacoes.exemplo.json"),
                          "--saida", str(xlsx), "--csv", str(csv_out)], capture_output=True, text=True, check=True).stdout
    assert "Total estimado" in out
    with zipfile.ZipFile(xlsx) as z:
        assert z.testzip() is None
        for nome in z.namelist():
            if nome.endswith(".xml") or nome.endswith(".rels"):
                ET.fromstring(z.read(nome))  # XML bem formado
        wb = z.read("xl/workbook.xml").decode()
        assert "Melhor custo-benefício" in wb and "Comparativo" in wb
    rows = cotacao.ler_xlsx(xlsx, "Melhor custo-benefício")
    assert rows[0][5] == "Fornecedor" and rows[1][5].startswith("Fornecedor A")
    assert float(rows[-1][11]) == pytest.approx(32 * 39.90 + 15 * 54.90 + 1300)
    assert csv_out.read_text(encoding="utf-8-sig").startswith("item;material")


def test_pedido_lista_sob_consulta():
    out = subprocess.run([sys.executable, str(SCRIPT), "pedido", "--cotacoes", str(SKILL / "assets/cotacoes.exemplo.json")],
                         capture_output=True, text=True, check=True).stdout
    assert "Concreteira F" in out and "Olaria E" in out and "451 un" in out
