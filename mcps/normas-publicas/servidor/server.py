#!/usr/bin/env python3
"""Servidor MCP "normas-publicas": consulta NRs, normas/manuais DNIT e cadernos SINAPI indexados localmente.

Executado pelo Claude Code/Codex via:
  uv run --no-project --with "mcp[cli]>=1.2,<2" --with "pypdf>=4" python server.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import normas  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

INSTRUCOES = """Índice local de documentos técnicos PÚBLICOS brasileiros:
- NRs (Normas Regulamentadoras do MTE): segurança e saúde no trabalho, canteiro de obras (NR-18),
  trabalho em altura (NR-35), eletricidade (NR-10), máquinas (NR-12), espaço confinado (NR-33)…
  e manuais/guias oficiais de aplicação.
- DNIT/IPR: especificações de serviço (ES), materiais (EM), métodos de ensaio (ME), procedimentos
  (PRO) e manuais de obras rodoviárias, pavimentação, drenagem e obras de arte.
- SINAPI/Caixa: cadernos técnicos de composições (critérios de medição, especificações, produtividade)
  e metodologia.
- Documentos públicos locais que o agente importou (fonte 'local'): código de obras, plano diretor,
  ITs do Corpo de Bombeiros, normas de concessionárias.
Normas ABNT (NBR) NÃO estão aqui: são protegidas por direito autoral. Nunca invente texto de NBR e nunca
use cópias de NBR encontradas na internet.

Como usar: 1) buscar_normas pelo assunto; 2) se vier vazio, buscar_catalogo e baixar_documentos;
3) ler_pagina / localizar_item para o texto exato. Sempre cite documento, item e página, e avise que o
texto das NRs não substitui o publicado no DOU."""

mcp = FastMCP("normas-publicas", instructions=INSTRUCOES)


@mcp.tool()
def buscar_normas(consulta: str, fonte: str | None = None, limite: int = 8) -> dict:
    """Busca no TEXTO dos documentos já baixados. fonte: 'nr', 'dnit', 'sinapi' ou 'usuario'.

    Retorna trechos com documento, página e link para citação. Use termos técnicos
    (ex.: "guarda-corpo travessão altura", "sub-base solo cimento", "critério de medição alvenaria").
    """
    res = normas.buscar(consulta, fonte, max(1, min(limite, 20)))
    saida: dict = {"resultados": res}
    if len(res) < 3:
        sug = normas.buscar_catalogo(consulta, fonte, 8)
        nao_baixados = [s for s in sug if not s["baixado"]]
        if nao_baixados:
            saida["sugestao"] = ("Há documentos no catálogo ainda não baixados que podem tratar do assunto. "
                                 "Chame baixar_documentos com os ids relevantes e repita a busca.")
            saida["catalogo"] = nao_baixados
    return saida


@mcp.tool()
def buscar_catalogo(consulta: str, fonte: str | None = None, limite: int = 20) -> list[dict]:
    """Busca pelo TÍTULO/código no catálogo completo (inclusive documentos ainda não baixados).

    Ex.: "NR-18", "concreto", "drenagem", "alvenaria", "DNIT 031". O campo 'baixado' indica se já
    está indexado para busca de texto.
    """
    return normas.buscar_catalogo(consulta, fonte, max(1, min(limite, 50)))


@mcp.tool()
def baixar_documentos(ids: list[str]) -> dict:
    """Baixa da fonte oficial e indexa até 10 documentos do catálogo (ids de buscar_catalogo)."""
    log: list[str] = []
    res = normas.baixar(ids[:10], log=log.append)
    return {"resultado": res, "log": log, "ignorados": ids[10:]}


@mcp.tool()
def ler_pagina(doc_id: str, pagina: int, quantidade: int = 1) -> dict:
    """Texto integral de 1 a 5 páginas de um documento baixado, com o aviso de fonte."""
    return normas.ler(doc_id, pagina, quantidade)


@mcp.tool()
def localizar_item(doc_id: str, item: str) -> dict:
    """Texto de um item numerado (ex.: doc_id 'nr-18', item '18.13.1') até o item seguinte."""
    return normas.localizar_item(doc_id, item)


@mcp.tool()
def importar_documento_publico(url: str, titulo: str, esfera: str = "municipal") -> dict:
    """Baixa e indexa um documento PÚBLICO encontrado na web: código de obras, plano diretor, lei de uso do solo,
    Instrução Técnica do Corpo de Bombeiros, norma de concessionária (PDF ou página HTML).

    esfera: 'municipal', 'estadual', 'federal' ou 'concessionaria'. Prefira sempre o site oficial (.gov.br,
    .leg.br, prefeitura, câmara, diário oficial, Corpo de Bombeiros). Sites de cópias e exemplares de NBR
    vendidos pela ABNT são recusados. Depois use buscar_normas(fonte='local').
    """
    return normas.importar_url(url, titulo, esfera, log=lambda m: None)


@mcp.tool()
def atualizar_catalogo(fontes: list[str] | None = None) -> dict:
    """Atualiza a lista de documentos nas fontes oficiais (nr, dnit, sinapi). Leva ~1 minuto.

    Documentos que mudaram de versão voltam a 'não baixado' para serem reindexados.
    """
    log: list[str] = []
    res = normas.atualizar_catalogo(fontes, log=log.append)
    return {"resultado": res, "log": log}


@mcp.tool()
def status() -> dict:
    """Quantos documentos há no catálogo e no índice, por fonte, e quando foram atualizados."""
    return normas.status()


if __name__ == "__main__":
    mcp.run()
