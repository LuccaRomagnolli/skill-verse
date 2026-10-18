#!/usr/bin/env python3
"""Prepara a entrada limitada de viga.py a partir de esforços conferidos no relatório SkyCiv.

Os valores são transcritos pelo responsável; não interpreta automaticamente eixos locais
ou diagramas de uma resposta SkyCiv sem ensaio real de referência.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path


def _modelo():
    f = Path(__file__).resolve().parents[2] / "modelo-estrutural/scripts/modelo.py"
    spec = importlib.util.spec_from_file_location("skillverse_triagem_modelo", f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def numero(v, nome, minimo=0):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < minimo:
        raise ValueError(f"{nome}: número finito >= {minimo} obrigatório")
    return float(v)


def preparar(modelo: dict, manifesto: dict, selecao: dict) -> dict:
    m = _modelo()
    m.validar(modelo)
    if manifesto.get("estado") != "analisado" or manifesto.get("sha256_entrada") != m.digest(modelo):
        raise ValueError("modelo/revisão não coincide com análise concluída")
    if manifesto.get("projeto") != modelo["projeto"]:
        raise ValueError("identidade do projeto divergente")
    v = next((x for x in modelo.get("vigas", []) if x["id"] == selecao.get("id_viga")), None)
    c = next((x for x in modelo["combinacoes"] if x["id"] == selecao.get("id_combinacao")), None)
    if not v or not c or c["criterio"] != "strength":
        raise ValueError("selecione viga e combinação ELU explícitas no modelo")
    if (selecao.get("eixos_locais_conferidos") is not True or selecao.get("eixo_momento") != "bmd_z" or
            selecao.get("eixo_cortante") != "sfd_y" or selecao.get("sinal_momento") != "positivo" or
            v.get("rot_graus", 0) != 0):
        raise ValueError("eixos locais/rotação ou sinal fora do caso uniaxial positivo suportado")
    if any(abs(numero(selecao.get(k), k, -math.inf)) > 1e-9 for k in ("torcao_kNm", "axial_kN", "momento_secundario_kNm")):
        raise ValueError("torção, axial ou flexão biaxial exigem revisão fora da rotina viga.py")
    md = numero(selecao.get("Md_kNm"), "Md_kNm", 1e-9)
    vd = numero(selecao.get("Vd_kN"), "Vd_kN")
    estacao = numero(selecao.get("estacao_m"), "estacao_m")
    comprimento = math.dist(v["de"], v["ate"])
    if estacao > comprimento:
        raise ValueError("estação fora da viga")
    if selecao.get("id_skyciv") != manifesto.get("ids", {}).get("pecas", {}).get(v["id"]):
        raise ValueError("ID SkyCiv não corresponde à viga")
    origem = selecao.get("origem")
    if not isinstance(origem, dict) or not all(str(origem.get(k, "")).strip() for k in ("arquivo", "pagina_ou_tabela", "revisor")):
        raise ValueError("registre arquivo, página/tabela e revisor da leitura de esforços")
    fck = numero(selecao.get("fck_MPa"), "fck_MPa", 1e-9)
    caa = selecao.get("caa")
    if caa not in {"I", "II", "III", "IV"}:
        raise ValueError("CAA explícita obrigatória")
    script = Path(__file__).resolve().parents[2] / "concreto-armado-nbr6118/scripts/viga.py"
    args = ["python3", str(script), "--b", f"{v['b_m'] * 100:g}", "--h", f"{v['h_m'] * 100:g}",
            "--fck", f"{fck:g}", "--caa", caa, "--Md", f"{md:g}", "--Vd", f"{vd:g}", "--formato", "json"]
    return {"estado": "entrada-para-revisao", "projeto": modelo["projeto"], "sha256_entrada": m.digest(modelo),
            "viga": v["id"], "id_skyciv": selecao["id_skyciv"], "combinacao": c["id"],
            "estacao_m": estacao, "origem": origem, "comando": args,
            "pendencias": ["Confirmar envoltória e demais seções/combinações", "Conferir altura útil, detalhamento e premissas normativas no exemplar licenciado", "Revisão técnica independente"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("modelo", type=Path)
    p.add_argument("manifesto", type=Path)
    p.add_argument("selecao", type=Path)
    p.add_argument("--saida", type=Path, required=True)
    a = p.parse_args()
    out = preparar(*(json.loads(f.read_text(encoding="utf-8")) for f in (a.modelo, a.manifesto, a.selecao)))
    a.saida.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"estado": out["estado"], "saida": str(a.saida)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
