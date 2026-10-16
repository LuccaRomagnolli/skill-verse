#!/usr/bin/env python3
"""Valida e resume um mapa de ações por zona, sem converter cargas concentradas em distribuídas.

Entrada JSON: projeto, zonas[id, pavimento, elemento, uso_especifico, acoes[]].
Cada ação: id, natureza, forma, valor, unidade, origem[tipo, documento, item, data].
O mapa é inventário de ações características; não é análise estrutural nem dimensionamento.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

UNIDADES = {"distribuida": "kN/m²", "linear": "kN/m", "concentrada": "kN"}
NATUREZAS = {"permanente", "variavel"}
ORIGENS = {"norma", "fabricante", "medicao", "levantamento", "hipotese"}
USOS_GENERICOS = {"residencial", "comercial", "misto", "industrial", "outro"}
CHECAGENS = {"concentrada", "paredes_divisorias", "cobertura", "garagem", "equipamentos", "construcao"}


def compilar(dados: dict) -> dict:
    if not isinstance(dados, dict) or not str(dados.get("projeto", "")).strip():
        raise ValueError("informe o nome do projeto")
    zonas = dados.get("zonas")
    if not isinstance(zonas, list) or not zonas:
        raise ValueError("informe ao menos uma zona/elemento")
    vistos, saida, pendencias = set(), [], []
    for zona in zonas:
        zid = str(zona.get("id", "")).strip()
        if not zid or zid in vistos:
            raise ValueError("cada zona exige id único")
        vistos.add(zid)
        for campo in ("pavimento", "elemento", "uso_especifico"):
            if not str(zona.get(campo, "")).strip():
                raise ValueError(f"zona {zid}: falta {campo}; não inferir pelo uso geral do projeto")
        if zona["uso_especifico"].strip().lower() in USOS_GENERICOS:
            raise ValueError(f"zona {zid}: uso genérico; identifique o ambiente (ex.: varanda residencial)")
        checagens = zona.get("checagens")
        if not isinstance(checagens, dict) or set(checagens) != CHECAGENS:
            raise ValueError(f"zona {zid}: registre checagens de {', '.join(sorted(CHECAGENS))}")
        for nome, item in checagens.items():
            if not isinstance(item, dict) or item.get("estado") not in {"verificada", "nao_se_aplica", "pendente"} or not str(item.get("justificativa", "")).strip():
                raise ValueError(f"zona {zid}: checagem {nome} exige estado e justificativa")
            if item["estado"] == "pendente":
                pendencias.append(f"{zid}: {nome} — {item['justificativa']}")
        acoes = zona.get("acoes")
        if not isinstance(acoes, list) or not acoes:
            raise ValueError(f"zona {zid}: registre ações ou pendência; mapa incompleto")
        area = zona.get("area_m2")
        if any(a.get("forma") == "distribuida" for a in acoes) and (
                isinstance(area, bool) or not isinstance(area, (int, float)) or not math.isfinite(area) or area <= 0):
            raise ValueError(f"zona {zid}: ação distribuída exige area_m2 positiva e conferida")
        ids, totais = set(), {"permanente_kN_m2": 0.0, "variavel_kN_m2": 0.0}
        for acao in acoes:
            aid = str(acao.get("id", "")).strip()
            if not aid or aid in ids:
                raise ValueError(f"zona {zid}: cada ação exige id único")
            ids.add(aid)
            forma, natureza = acao.get("forma"), acao.get("natureza")
            if forma not in UNIDADES or natureza not in NATUREZAS:
                raise ValueError(f"zona {zid}, ação {aid}: forma ou natureza inválida")
            if acao.get("unidade") != UNIDADES[forma]:
                raise ValueError(f"zona {zid}, ação {aid}: unidade deve ser {UNIDADES[forma]}")
            valor = acao.get("valor")
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor <= 0:
                raise ValueError(f"zona {zid}, ação {aid}: valor positivo finito obrigatório")
            if forma == "linear" and (not isinstance(acao.get("extensao_m"), (int, float)) or
                                     not math.isfinite(acao["extensao_m"]) or acao["extensao_m"] <= 0):
                raise ValueError(f"zona {zid}, ação {aid}: carga linear exige extensao_m positiva")
            if forma == "concentrada" and not str(acao.get("posicao", "")).strip():
                raise ValueError(f"zona {zid}, ação {aid}: carga concentrada exige posição no elemento")
            origem = acao.get("origem") or {}
            if origem.get("tipo") not in ORIGENS or any(not str(origem.get(c, "")).strip() for c in ("documento", "item", "data")):
                raise ValueError(f"zona {zid}, ação {aid}: origem exige tipo, documento, item e data")
            if forma == "distribuida":
                totais[f"{natureza}_kN_m2"] += valor
        if checagens["concentrada"]["estado"] == "verificada" and not any(
                a["forma"] == "concentrada" for a in acoes):
            raise ValueError(f"zona {zid}: carga concentrada marcada verificada sem ação concentrada registrada")
        saida.append({"id": zid, "pavimento": zona["pavimento"], "elemento": zona["elemento"],
                      "uso_especifico": zona["uso_especifico"], "area_m2": area, "checagens": checagens,
                      "acoes": acoes, "totais_distribuidos": totais,
                      "observacao": "Cargas lineares e concentradas exigem casos e efeitos próprios; não foram diluídas na área."})
    return {"projeto": dados["projeto"], "norma_base": "ABNT NBR 6120:2019 (versão corrigida 12.11.2019)",
            "status_normativo": "incompleto" if pendencias else "inventario-para-revisao-do-responsavel-tecnico",
            "pendencias": pendencias, "zonas": saida}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--entrada", type=Path, required=True)
    ap.add_argument("--saida", type=Path, help="arquivo JSON; sem esta opção escreve em stdout")
    a = ap.parse_args(argv)
    try:
        resultado = compilar(json.loads(a.entrada.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        ap.error(str(exc))
    conteudo = json.dumps(resultado, indent=2, ensure_ascii=False) + "\n"
    if a.saida:
        a.saida.write_text(conteudo, encoding="utf-8")
    else:
        print(conteudo, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
