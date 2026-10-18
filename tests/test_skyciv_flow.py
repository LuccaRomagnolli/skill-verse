"""Contratos do modelo compartilhado e da integração SkyCiv, sem gastar créditos."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "catalog/engenharia-civil/modelo-estrutural/assets/modelo.exemplo.json"
MAP = EXAMPLE.with_name("mapa-acoes.exemplo.json")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


modelo = module("modelo_fluxo", "catalog/engenharia-civil/modelo-estrutural/scripts/modelo.py")
client = module("skyciv_client_fluxo", "mcps/skyciv/servidor/client.py")


@pytest.fixture
def exemplo():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_modelo_preserva_ids_unidades_e_combinacao(exemplo):
    out = modelo.para_skyciv(exemplo)
    s3d = out["modelo"]
    assert len(s3d["nodes"]) == 8
    assert out["ids"]["pecas"]["V1"] == 5
    assert s3d["sections"]["1"]["info"]["dimensions"] == {"b": 200.0, "h": 400.0}
    assert s3d["plates"]["1"]["thickness"] == 120
    assert s3d["pressures"]["1"]["z_mag"] == -2
    assert s3d["load_combinations"]["1"]["SW1"] == 1.4
    assert modelo.para_revit(exemplo)["pilares"][0]["b_cm"] == 20


def test_modelo_recusa_fonte_grupo_e_apoio_invalidos(exemplo):
    for edit in (
        lambda d: d["acoes"][0].update(origem={}),
        lambda d: d["combinacoes"][0]["fatores"].update(NADA=1.0),
        lambda d: d["apoios"][0].update(ponto=[99, 0, 0]),
    ):
        d = copy.deepcopy(exemplo)
        edit(d)
        with pytest.raises(ValueError):
            modelo.para_skyciv(d)


def test_mapa_acao_confere_valor_unidade_e_origem(exemplo):
    mapa = json.loads(MAP.read_text(encoding="utf-8"))
    assert modelo.conferir_mapa(exemplo, mapa)["acoes_conferidas"] == 1
    mapa["zonas"][0]["acoes"][0]["valor"] = 3
    with pytest.raises(ValueError, match="diverge"):
        modelo.conferir_mapa(exemplo, mapa)


def test_plano_insere_malha_antes_da_analise_e_nao_expoe_chave(exemplo):
    s = modelo.para_skyciv(exemplo)
    p = client.plano_requisicao(s, "cliente", "segredo", False)
    assert [f["function"] for f in p["functions"]] == ["S3D.session.start", "S3D.model.set", "S3D.model.mesh",
        "S3D.model.solve", "S3D.results.get"]
    assert p["options"]["validate_input"] is True
    assert "segredo" not in json.dumps(client.limpar(p))


def test_analise_exige_confirmacao_e_registra_credito_sem_repeticao(exemplo, tmp_path, monkeypatch):
    entrada = tmp_path / "modelo.json"
    entrada.write_text(json.dumps(exemplo), encoding="utf-8")
    (tmp_path / "mapa-acoes.exemplo.json").write_bytes(MAP.read_bytes())
    chamadas = []

    def enviar(p):
        chamadas.append(p)
        nomes = [f["function"] for f in p["functions"]]
        funcoes = [{"response": {"function": n, "status": 0, "data": {"1": {"name": "EXEMPLO-ELU", "reactions": {}}} if n == "S3D.results.get" else {}}} for n in nomes]
        return {"response": {"status": 0, "monthly_api_credits": {"used_this_call": 1}}, "functions": funcoes}

    monkeypatch.setattr(client, "enviar", enviar)
    monkeypatch.setenv("SKYCIV_USERNAME", "cliente")
    monkeypatch.setenv("SKYCIV_API_KEY", "segredo")
    assert client.analisar(str(entrada), False, False)["requer_confirmacao"]
    assert not chamadas
    r = client.analisar(str(entrada), True, False)
    assert r["ok"] and len(chamadas) == 1
    manifest = json.loads(Path(r["manifesto"]).read_text())
    assert manifest["creditos"]["used_this_call"] == 1
    assert manifest["ids"]["pecas"]["V1"] == 5
    assert "segredo" not in Path(r["pasta"], "resposta.json").read_text()


def test_falha_incerta_gera_pendencia_sem_retry(exemplo, tmp_path, monkeypatch):
    entrada = tmp_path / "modelo.json"
    entrada.write_text(json.dumps(exemplo), encoding="utf-8")
    (tmp_path / "mapa-acoes.exemplo.json").write_bytes(MAP.read_bytes())
    monkeypatch.setenv("SKYCIV_USERNAME", "cliente")
    monkeypatch.setenv("SKYCIV_API_KEY", "segredo")
    chamadas = []

    def falhar(p):
        chamadas.append(p)
        raise RuntimeError("resposta incerta")

    monkeypatch.setattr(client, "enviar", falhar)
    r = client.analisar(str(entrada), True, False)
    assert r["estado"] == "incerto" and len(chamadas) == 1
    assert json.loads(Path(r["pasta"], "falha.json").read_text())["estado"] == "incerto"


def test_erro_do_relatorio_preserva_resultados_da_analise(exemplo, tmp_path, monkeypatch):
    entrada = tmp_path / "modelo.json"
    entrada.write_text(json.dumps(exemplo), encoding="utf-8")
    (tmp_path / "mapa-acoes.exemplo.json").write_bytes(MAP.read_bytes())
    monkeypatch.setenv("SKYCIV_USERNAME", "cliente")
    monkeypatch.setenv("SKYCIV_API_KEY", "segredo")

    def enviar(p):
        funcoes = [{"status": 0, "function": f["function"], "data": {"1": {"name": "EXEMPLO-ELU"}} if f["function"] == "S3D.results.get" else {}}
                   for f in p["functions"]]
        funcoes[-1]["status"] = 1
        return {"response": {"status": 1, "monthly_api_credits": {"used_this_call": 1}}, "functions": funcoes}

    monkeypatch.setattr(client, "enviar", enviar)
    r = client.analisar(str(entrada), True, True)
    assert r["ok"] and "Relatório" in r["aviso_relatorio"]
    assert Path(r["pasta"], "resultados.json").is_file()


def test_cad_e_archicad_usam_mesma_revisao(exemplo, tmp_path):
    # Import das ferramentas de CAD ocorre na pasta da skill, como no ZIP instalado.
    import sys
    cad_dir = ROOT / "catalog/engenharia-civil/autocad-assistente/scripts"
    sys.path.insert(0, str(cad_dir))
    try:
        cad_module = module("cad_fluxo_real", "catalog/engenharia-civil/autocad-assistente/scripts/plantas.py")
    finally:
        sys.path.remove(str(cad_dir))
    arch = module("archicad_fluxo", "catalog/engenharia-civil/archicad-assistente/scripts/lancamento.py")
    cfg = json.loads((ROOT / "catalog/engenharia-civil/archicad-assistente/assets/config.exemplo.json").read_text())
    with pytest.raises(ValueError, match="material"):
        arch.gerar(exemplo, cfg)
    cfg["materiais"]["Concreto-exemplo"]["buildingMaterialId"]["guid"] = "00000000-0000-0000-0000-000000000001"
    cfg["materiais"]["Concreto-exemplo"]["slabFavorite"] = "Laje Concreto Teste"
    desenhos = cad_module.gerar(exemplo, tmp_path / "desenhos")
    bim = arch.gerar(exemplo, cfg)
    assert desenhos["sha256_entrada"] == bim["sha256_entrada"] == modelo.digest(exemplo)
    assert len(desenhos["plantas"]) == 2
    assert [op["tool"] for op in bim["operacoes"]] == ["create_elements", "describe_api_command", "execute_write_api_command", "create_elements"]
    assert "4.000 m" in (tmp_path / "desenhos/planta-Pav-1.dxf").read_text(encoding="cp1252")


def test_triagem_dimensionamento_so_em_caso_suportado(exemplo):
    triagem = module("triagem_fluxo", "catalog/engenharia-civil/skyciv-assistente/scripts/triagem_viga.py")
    s3d = modelo.para_skyciv(exemplo)
    manifesto = {"estado": "analisado", "projeto": exemplo["projeto"], "sha256_entrada": modelo.digest(exemplo),
                 "ids": s3d["ids"]}
    selecao = {"id_viga": "V1", "id_skyciv": s3d["ids"]["pecas"]["V1"], "id_combinacao": "EXEMPLO-ELU",
               "eixos_locais_conferidos": True, "eixo_momento": "bmd_z", "eixo_cortante": "sfd_y",
               "sinal_momento": "positivo", "torcao_kNm": 0, "axial_kN": 0, "momento_secundario_kNm": 0,
               "Md_kNm": 12, "Vd_kN": 8, "estacao_m": 2, "fck_MPa": 30, "caa": "II",
               "origem": {"arquivo": "relatorio.pdf", "pagina_ou_tabela": "p. 4", "revisor": "Eng. Exemplo"}}
    out = triagem.preparar(exemplo, manifesto, selecao)
    assert out["comando"][-6:] == ["--Md", "12", "--Vd", "8", "--formato", "json"]
    selecao["torcao_kNm"] = 1
    with pytest.raises(ValueError, match="torção"):
        triagem.preparar(exemplo, manifesto, selecao)
