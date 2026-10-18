#!/usr/bin/env python3
"""MCP local do Skill-Verse para análise estrutural na SkyCiv API v3."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import client  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("skyciv", instructions="Análise estrutural linear de modelos explícitos. Valide localmente, mostre a revisão e obtenha confirmação antes de usar créditos SkyCiv. Os resultados não atestam conformidade NBR.")


@mcp.tool()
def skyciv_status() -> dict:
    """Diagnóstico local, sem chamada cobrada: presença das credenciais e versão da integração."""
    ok = bool(os.environ.get("SKYCIV_USERNAME") and os.environ.get("SKYCIV_API_KEY"))
    return {"connected": False, "credenciais_configuradas": ok, "api": "v3", "modo": "analise-linear",
            "aviso": "Diagnóstico local; conexão e saldo só se comprovam com chamada real"}


@mcp.tool()
def skyciv_validar_modelo(caminho_modelo: str) -> dict:
    """Valida arquivo estrutural JSON e mostra tamanho/hash antes de transmitir dados."""
    try:
        _, d, s = client.preparar(caminho_modelo)
        m = client._modelo_module()
        return {"ok": True, "projeto": s["projeto"], "sha256_entrada": s["sha256_entrada"],
                "resumo": m.validar(d), "nos": len(s["modelo"]["nodes"]), "barras": len(s["modelo"]["members"]),
                "placas": len(s["modelo"]["plates"]), "aviso": "Conectividade e premissas dependem de revisão técnica"}
    except (OSError, ValueError, RuntimeError) as exc:
        return {"ok": False, "erro": str(exc)}


@mcp.tool()
def skyciv_analisar(caminho_modelo: str, confirmar_envio: bool = False, gerar_relatorio: bool = True) -> dict:
    """Envia a revisão à SkyCiv para análise linear, com confirmação explícita e consumo de créditos.

    Não repita após resposta incerta sem consultar a atividade da conta SkyCiv. Grava entrada,
    resposta, resultados, IDs e PDF quando disponível na pasta resultados/ do projeto.
    """
    try:
        return client.analisar(caminho_modelo, confirmar_envio, gerar_relatorio)
    except (OSError, ValueError, RuntimeError) as exc:
        return {"ok": False, "erro": str(exc)}


@mcp.tool()
def skyciv_resultados(caminho_manifesto: str) -> dict:
    """Lê manifesto e aponta resultados locais de uma análise já concluída; não usa créditos."""
    try:
        p = Path(caminho_manifesto).expanduser().resolve(strict=True)
        if p.name != "manifesto.json":
            raise ValueError("informe manifesto.json de uma análise SkyCiv")
        import json
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("estado") != "analisado":
            raise ValueError("análise não concluída")
        return {"ok": True, "projeto": d["projeto"], "sha256_entrada": d["sha256_entrada"],
                "sha256_mapa": d.get("sha256_mapa"),
                "resultados": d["resultados"], "relatorio": d.get("relatorio"), "creditos": d.get("creditos"),
                "ids": d.get("ids"), "revisao_tecnica": d.get("revisao_tecnica")}
    except (OSError, ValueError, KeyError) as exc:
        return {"ok": False, "erro": str(exc)}


if __name__ == "__main__":
    mcp.run()
