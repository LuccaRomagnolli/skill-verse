#!/usr/bin/env python3
"""Confere GUIDs e geometria criada pelo Archicad contra o plano de lançamento."""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

GUID = re.compile(r"^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")


def _conteudo(d: object) -> object:
    if not isinstance(d, dict):
        return d
    for chave in ("structuredContent", "data", "result"):
        if isinstance(d.get(chave), dict):
            interno = _conteudo(d[chave])
            if isinstance(interno, dict) and "detailsOfElements" in interno:
                return interno
    return d


def _mapa(d: dict) -> dict[str, str]:
    if all(isinstance(v, str) for v in d.values()):
        return d
    saida: dict[str, str] = {}
    for grupo in ("pilares", "vigas", "lajes"):
        parte = d.get(grupo) or {}
        if not isinstance(parte, dict):
            raise ValueError(f"mapeamento.{grupo}: use objeto ID -> GUID")
        saida.update(parte)
    return saida


def _pontos(pontos: object) -> list[tuple[float, float]] | None:
    if not isinstance(pontos, list):
        return None
    r = [(float(p["x"]), float(p["y"])) for p in pontos if isinstance(p, dict) and "x" in p and "y" in p]
    if len(r) > 1 and r[0] == r[-1]:
        r.pop()
    return r


def _igual(esperado: object, real: object, tolerancia: float) -> bool:
    if isinstance(esperado, bool) or isinstance(real, bool):
        return esperado == real
    if isinstance(esperado, (int, float)) and isinstance(real, (int, float)):
        return math.isclose(float(esperado), float(real), abs_tol=tolerancia, rel_tol=0)
    if isinstance(esperado, str) and isinstance(real, str):
        return esperado.casefold() == real.casefold()
    return esperado == real


def avaliar(plano: dict, mapeamento: dict, detalhes: dict, tolerancia: float = 1e-5) -> dict:
    verificacao = plano.get("verificacao_pos_criacao") or {}
    esperado = verificacao.get("esperado") or []
    ids = verificacao.get("ids_na_ordem") or []
    mapa = _mapa(mapeamento)
    corpo = _conteudo(detalhes)
    reais = corpo.get("detailsOfElements") if isinstance(corpo, dict) else None
    falhas: list[dict] = []
    if not esperado or ids != [e.get("id") for e in esperado]:
        falhas.append({"id": None, "campo": "plano", "esperado": "lista coerente", "real": "ausente/incoerente"})
    if not isinstance(reais, list) or len(reais) != len(ids):
        falhas.append({"id": None, "campo": "detailsOfElements", "esperado": len(ids),
                       "real": len(reais) if isinstance(reais, list) else None})
        reais = reais if isinstance(reais, list) else []
    guids = []
    for ident in ids:
        guid = mapa.get(ident)
        if not isinstance(guid, str) or not GUID.fullmatch(guid):
            falhas.append({"id": ident, "campo": "guid", "esperado": "UUID retornado pelo lote", "real": guid})
        else:
            guids.append(guid.casefold())
    if len(guids) != len(set(guids)):
        falhas.append({"id": None, "campo": "guid", "esperado": "GUIDs únicos", "real": "duplicados"})

    def comparar(ident: str, campo: str, exp: object, real: object) -> None:
        if campo.endswith("polygonOutline"):
            ok = _pontos(exp) == _pontos(real)
        else:
            ok = _igual(exp, real, tolerancia)
        if not ok:
            falhas.append({"id": ident, "campo": campo, "esperado": exp, "real": real})

    for exp, real in zip(esperado, reais):
        ident = exp["id"]
        comparar(ident, "type", exp["tipo"], real.get("type"))
        comparar(ident, "floorIndex", exp["floorIndex"], real.get("floorIndex"))
        rd = real.get("details") or {}
        for campo, valor in exp["detalhes"].items():
            if isinstance(valor, dict) and campo != "buildingMaterialId":
                for subcampo, subvalor in valor.items():
                    comparar(ident, f"details.{campo}.{subcampo}", subvalor, (rd.get(campo) or {}).get(subcampo))
            elif campo == "buildingMaterialId":
                comparar(ident, "details.buildingMaterialId.guid", valor.get("guid"),
                         (rd.get(campo) or {}).get("guid"))
            else:
                comparar(ident, f"details.{campo}", valor, rd.get(campo))
    return {"aprovado": not falhas, "elementos_esperados": len(ids), "elementos_lidos": len(reais),
            "ids": ids, "falhas": falhas}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plano", type=Path)
    ap.add_argument("mapeamento", type=Path)
    ap.add_argument("detalhes", type=Path)
    ap.add_argument("--tolerancia-m", type=float, default=1e-5)
    ap.add_argument("--saida", type=Path)
    a = ap.parse_args()
    r = avaliar(*(json.loads(p.read_text(encoding="utf-8")) for p in (a.plano, a.mapeamento, a.detalhes)),
                tolerancia=a.tolerancia_m)
    texto = json.dumps(r, ensure_ascii=False, indent=2) + "\n"
    if a.saida:
        a.saida.write_text(texto, encoding="utf-8")
    print(texto, end="")
    raise SystemExit(0 if r["aprovado"] else 2)


if __name__ == "__main__":
    main()
