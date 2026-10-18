#!/usr/bin/env python3
"""Interpreta evidências do Archicad MCP sem aceitar passes vazios ou regras ignoradas."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def avaliar(d: dict) -> dict:
    def conteudo(valor: object) -> dict:
        if not isinstance(valor, dict):
            return {}
        for chave in ("structuredContent", "data"):
            if isinstance(valor.get(chave), dict):
                return valor[chave]
        return valor

    bloqueios: list[str] = []
    instancias = conteudo(d.get("instancias") or d.get("list_instances")).get("instances") or []
    port = d.get("port")
    if port is None and len(instancias) == 1:
        port = instancias[0].get("port")
    instancia = next((x for x in instancias if x.get("port") == port), None)
    if instancia is None:
        bloqueios.append("instância/porta do Archicad não identificada")
    else:
        if not instancia.get("project_open"):
            bloqueios.append("nenhum projeto aberto na instância escolhida")
        if not instancia.get("tapir_available"):
            bloqueios.append("Tapir ausente: criação, pavimentos e verificações IFC/BCF incompletos")

    resumo = conteudo(d.get("resumo") or d.get("get_model_summary"))
    if not isinstance(resumo.get("element_count"), int) or resumo.get("element_count", 0) <= 0:
        bloqueios.append("modelo vazio ou contagem de elementos indisponível")

    ignoradas: list[dict] = []
    falhas: list[dict] = []
    for nome, chave in (("auditoria", "audit_delivery_readiness"), ("ifc", "verify_ifc_export_readiness")):
        conjunto = conteudo(d.get(nome) or d.get(chave))
        if not isinstance(conjunto, dict):
            bloqueios.append(f"resultado '{nome}' ausente")
            continue
        resultados = conjunto.get("results")
        if not isinstance(resultados, list) or not resultados:
            bloqueios.append(f"resultado '{nome}' sem regras executadas")
            continue
        ignoradas.extend({"conjunto": nome, **r} for r in resultados if r.get("skipped"))
        falhas.extend({"conjunto": nome, **r} for r in resultados if not r.get("pass") and not r.get("skipped"))
        if conjunto.get("pass") is not True:
            bloqueios.append(f"resultado '{nome}' não passou")
    if ignoradas:
        bloqueios.append(f"{len(ignoradas)} regra(s) ignorada(s); score/pass agregado não comprova prontidão")
    if falhas:
        bloqueios.append(f"{len(falhas)} regra(s) falharam")

    return {
        "pronto_para_entrega": not bloqueios,
        "port": port,
        "element_count": resumo.get("element_count"),
        "bloqueios": bloqueios,
        "regras_ignoradas": ignoradas,
        "falhas": falhas,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("evidencia", type=Path, help="JSON com instancias, resumo, auditoria e ifc")
    ap.add_argument("--saida", type=Path)
    args = ap.parse_args()
    resultado = avaliar(json.loads(args.evidencia.read_text(encoding="utf-8")))
    texto = json.dumps(resultado, ensure_ascii=False, indent=2) + "\n"
    if args.saida:
        args.saida.write_text(texto, encoding="utf-8")
    print(texto, end="")


if __name__ == "__main__":
    main()
