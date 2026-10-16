#!/usr/bin/env python3
"""Ficha de contexto do projeto (município, UF, uso, ambiente) + registro das fontes normativas encontradas.

A ficha fica na pasta do projeto (projeto-contexto.json + projeto-contexto.md) e é lida pelas outras skills.
O perfil do usuário (município/UF onde mais atua) fica em $SKILLVERSE_HOME/perfil.json e serve de padrão.

  python3 contexto.py iniciar --pasta . --projeto "Residência Silva" --municipio "Brasília" --uf DF \
        --uso residencial-unifamiliar --pavimentos 2 --area 280 --ambiente urbano
  python3 contexto.py fonte --pasta . --esfera municipal --tipo "Código de Obras" \
        --titulo "Lei nº ... — Código de Obras" --url https://... --vigente sim --checklist c1
  python3 contexto.py nao-aplica --pasta . --checklist c5 --motivo "residência unifamiliar isenta no estado"
  python3 contexto.py pendencia --pasta . --texto "Confirmar com a concessionária o padrão de entrada"
  python3 contexto.py mostrar --pasta .
  python3 contexto.py perfil --municipio "Brasília" --uf DF        # grava o padrão do usuário
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

UFS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
       "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}
USOS = ["residencial-unifamiliar", "residencial-multifamiliar", "comercial", "servicos", "industrial",
        "institucional", "saude", "educacional", "misto", "infraestrutura"]
ESFERAS = ["municipal", "estadual", "federal", "concessionaria", "conselho", "abnt", "outra"]

# NBR 6118:2023, Tabela 6.1 — classe de agressividade ambiental por tipo de ambiente (síntese)
CAA = {
    "rural": ("I", "fraca"), "submersa": ("I", "fraca"),
    "urbano": ("II", "moderada"),
    "marinho": ("III", "forte"), "industrial": ("III", "forte"),
    "industrial-agressivo": ("IV", "muito forte"), "respingos-de-mare": ("IV", "muito forte"),
}

# O que pesquisar em todo projeto de edificação (a skill transforma em buscas concretas)
CHECKLIST_BASE = [
    ("municipal", "Código de Obras e Edificações vigente"),
    ("municipal", "Plano Diretor e Lei de Uso e Ocupação do Solo (zoneamento, afastamentos, gabarito, taxa de ocupação, coeficiente de aproveitamento, permeabilidade)"),
    ("municipal", "Procedimento e documentos para aprovação de projeto / alvará de construção"),
    ("municipal", "Legislação de acessibilidade e calçadas"),
    ("estadual", "Corpo de Bombeiros: regulamento de segurança contra incêndio e Instruções/Normas Técnicas aplicáveis ao uso"),
    ("concessionaria", "Energia: norma de fornecimento / padrão de entrada da distribuidora local"),
    ("concessionaria", "Água e esgoto: norma técnica de ligação da concessionária local"),
    ("conselho", "CREA-UF / CONFEA: ART (tipo, atividades) e atribuições profissionais"),
    ("abnt", "Edição vigente das NBR usadas no projeto (consulta ao ABNT Catálogo, só metadados)"),
]
EXTRAS_POR_USO = {
    "residencial-multifamiliar": [("municipal", "Exigências de vagas de garagem, áreas comuns e lixo"),
                                  ("estadual", "Exigências do Corpo de Bombeiros para edificação multifamiliar (altura/área)")],
    "saude": [("estadual", "Vigilância sanitária estadual/municipal e RDC ANVISA 50/2002 (estabelecimentos assistenciais de saúde)")],
    "educacional": [("estadual", "Normas da secretaria de educação para edificações escolares")],
    "industrial": [("estadual", "Licenciamento ambiental estadual"), ("federal", "NRs aplicáveis à atividade industrial")],
    "comercial": [("municipal", "Licença de funcionamento / habite-se para uso comercial")],
    "infraestrutura": [("federal", "DNIT (obras rodoviárias federais) ou DER estadual"), ("estadual", "Licenciamento ambiental")],
}


def sv_home() -> Path:
    return Path(os.environ.get("SKILLVERSE_HOME", Path.home() / "SkillVerse"))


def ler_perfil() -> dict:
    f = sv_home() / "perfil.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}


def arq(pasta: str) -> Path:
    return Path(pasta).expanduser().resolve() / "projeto-contexto.json"


def carregar(pasta: str) -> dict:
    f = arq(pasta)
    if not f.is_file():
        sys.exit(f"Ficha não encontrada em {f.parent}. Rode 'iniciar' primeiro.")
    ficha = json.loads(f.read_text(encoding="utf-8"))
    for chave, prefixo in (("fontes", "f"), ("pendencias", "p")):
        itens = ficha.setdefault(chave, [])
        for item in itens:
            if not item.get("id"):
                item["id"] = proximo_id(itens, prefixo)
    return ficha


def salvar(pasta: str, ficha: dict) -> None:
    f = arq(pasta)
    ficha["atualizado_em"] = dt.date.today().isoformat()
    for destino, conteudo in ((f, json.dumps(ficha, indent=2, ensure_ascii=False) + "\n"),
                              (f.with_suffix(".md"), render(ficha))):
        temporario = destino.with_name(destino.name + ".tmp")
        temporario.write_text(conteudo, encoding="utf-8")
        temporario.replace(destino)


def proximo_id(itens: list[dict], prefixo: str) -> str:
    usados = {str(x.get("id", "")) for x in itens}
    n = 1
    while f"{prefixo}{n}" in usados:
        n += 1
    return f"{prefixo}{n}"


def pendencias_abertas(ficha: dict) -> list[dict]:
    return [p for p in ficha.get("pendencias", []) if not p.get("resolvida")]


def checklist_faltante(ficha: dict) -> list[dict]:
    atendidos = {x.get("checklist") for x in ficha.get("fontes", [])
                 if x.get("vigente") == "sim" and x.get("url")}
    return [c for c in ficha.get("checklist", []) if c["id"] not in atendidos and not c.get("nao_aplica")]


def render(f: dict) -> str:
    caa = f.get("caa") or {}
    linhas = [f"# Contexto do projeto — {f.get('projeto') or 'sem nome'}", "",
              f"Atualizado em {f.get('atualizado_em', '')}. Ficha usada pelas skills do pack: mantenha-a atualizada.", "",
              "| Parâmetro | Valor |", "|---|---|",
              f"| Município / UF | {f['municipio']} / {f['uf']} |",
              f"| Uso | {f.get('uso') or '—'} |",
              f"| Pavimentos | {f.get('pavimentos') or '—'} |",
              f"| Área construída (m²) | {f.get('area') or '—'} |",
              f"| Ambiente | {f.get('ambiente') or '—'} |",
              f"| Classe de agressividade sugerida (NBR 6118:2023, Tab. 6.1) | "
              + (f"CAA {caa['classe']} ({caa['agressividade']}) — confirmar com o projetista" if caa else "—") + " |",
              "", "## Fontes normativas encontradas", ""]
    fontes = f.get("fontes", [])
    if fontes:
        linhas += ["| ID | Esfera | Tipo | Documento | Vigência confirmada | Link | Acesso |", "|---|---|---|---|---|---|---|"]
        for x in fontes:
            vig = {"sim": "sim", "nao": "não", None: "a confirmar"}.get(x.get("vigente"), "a confirmar")
            linhas.append(f"| {x.get('id') or '—'} | {x['esfera']} | {x['tipo']} | {x['titulo']} | {vig} | {x.get('url') or '—'} | {x['acessado_em']} |")
    else:
        linhas.append("_Nenhuma fonte registrada ainda._")
    requisitos = f.get("requisitos", [])
    if requisitos:
        linhas += ["", "## Exigências verificadas", "", "| Critério | Valor | Fonte / item | Impacto |", "|---|---|---|---|"]
        linhas += [f"| {x['criterio']} | {x.get('valor') or '—'} {x.get('unidade') or ''} | "
                   f"{x['fonte_id']} / {x['item']} | {x.get('impacto') or '—'} |" for x in requisitos]
    decisoes = f.get("decisoes", [])
    if decisoes:
        linhas += ["", "## Decisões e hipóteses", ""]
        linhas += [f"- `{x['id']}` {x['assunto']}: {x['decisao']} "
                   f"(origem: {x['origem']}; {x['registrado_em']})" for x in decisoes]
    artefatos = f.get("artefatos", [])
    if artefatos:
        linhas += ["", "## Artefatos", "", "| Tipo | Caminho | Revisão | Estado |", "|---|---|---|---|"]
        linhas += [f"| {x['tipo']} | {x['caminho']} | {x.get('revisao') or '—'} | {x['estado']} |"
                   for x in artefatos]
    atp = f.get("atp") or {}
    linhas += ["", "## Avaliação técnica do projeto — NBR 6118:2026, 5.3", "",
              f"Classe de consequência: {atp.get('classe') or 'a definir pelo responsável técnico'}; "
              f"situação: {atp.get('situacao') or 'pendente'}."]
    if atp.get("fundamento"):
        linhas.append(f"Fundamento: {atp['fundamento']}.")
    if atp.get("documento"):
        linhas.append(f"Documento: {atp['documento']}.")
    pend = pendencias_abertas(f)
    faltando = checklist_faltante(f)
    linhas += ["", "## Ainda a pesquisar / confirmar", ""]
    linhas += [f"- [ ] `{c['id']}` ({c['esfera']}) {c['item']}" for c in faltando] or ["- (checklist completo)"]
    linhas += [f"- [ ] `{p.get('id') or '?'}` {p['texto']}" for p in pend]
    return "\n".join(linhas) + "\n"


def cmd_iniciar(a) -> int:
    perfil = ler_perfil()
    municipio = a.municipio or perfil.get("municipio")
    uf = (a.uf or perfil.get("uf") or "").upper()
    if not municipio or uf not in UFS:
        sys.exit("Informe --municipio e --uf válidos (ou grave um perfil com 'perfil').")
    f = arq(a.pasta)
    if f.is_file() and not a.forcar:
        sys.exit(f"Já existe {f}. Use 'mostrar' ou --forcar para recomeçar.")
    caa = None
    if a.ambiente:
        cl, ag = CAA[a.ambiente]
        caa = {"classe": cl, "agressividade": ag, "ambiente": a.ambiente}
    checklist = [{"id": f"c{n}", "esfera": e, "item": i}
                 for n, (e, i) in enumerate(CHECKLIST_BASE + EXTRAS_POR_USO.get(a.uso or "", []), 1)]
    ficha = {"projeto": a.projeto, "municipio": municipio, "uf": uf, "uso": a.uso, "pavimentos": a.pavimentos,
             "area": a.area, "ambiente": a.ambiente, "caa": caa, "fontes": [], "requisitos": [],
             "decisoes": [], "artefatos": [], "atp": {"situacao": "pendente"}, "pendencias": [], "checklist": checklist,
             "criado_em": dt.date.today().isoformat()}
    salvar(a.pasta, ficha)
    print(json.dumps({"ficha": str(f), "municipio": municipio, "uf": uf, "caa": caa,
                      "pesquisar": [f"{c['id']} ({c['esfera']}) {c['item']}" for c in checklist]}, indent=2, ensure_ascii=False))
    return 0


def cmd_fonte(a) -> int:
    ficha = carregar(a.pasta)
    if a.vigente == "sim" and not a.url:
        sys.exit("fonte com vigência confirmada exige URL oficial")
    if a.checklist and a.checklist not in {c["id"] for c in ficha["checklist"]}:
        sys.exit(f"item de checklist '{a.checklist}' não existe")
    anteriores = [x for x in ficha["fontes"] if x["titulo"] == a.titulo and x["esfera"] == a.esfera]
    item = {"id": (anteriores[0].get("id") if anteriores else None) or proximo_id(ficha["fontes"], "f"),
            "checklist": a.checklist, "esfera": a.esfera, "tipo": a.tipo, "titulo": a.titulo,
            "numero": a.numero, "ano": a.ano, "url": a.url, "vigente": a.vigente,
            "observacao": a.obs, "acessado_em": dt.date.today().isoformat()}
    ficha["fontes"] = [x for x in ficha["fontes"] if not (x["titulo"] == a.titulo and x["esfera"] == a.esfera)] + [item]
    salvar(a.pasta, ficha)
    print(json.dumps({"fonte_id": item["id"], "total": len(ficha["fontes"])}, ensure_ascii=False))
    return 0


def cmd_pendencia(a) -> int:
    ficha = carregar(a.pasta)
    pendencias = ficha.setdefault("pendencias", [])
    item = {"id": proximo_id(pendencias, "p"), "texto": a.texto, "resolvida": False,
            "responsavel": a.responsavel, "registrado_em": dt.date.today().isoformat()}
    pendencias.append(item)
    salvar(a.pasta, ficha)
    print(json.dumps(item, ensure_ascii=False))
    return 0


def cmd_resolver_pendencia(a) -> int:
    ficha = carregar(a.pasta)
    for item in ficha.get("pendencias", []):
        if item.get("id") == a.id:
            item.update({"resolvida": True, "solucao": a.solucao, "resolvida_em": dt.date.today().isoformat()})
            salvar(a.pasta, ficha)
            return 0
    sys.exit(f"pendência '{a.id}' não encontrada; use 'resumo' para listar IDs")


def cmd_requisito(a) -> int:
    ficha = carregar(a.pasta)
    fontes = ficha.get("fontes", [])
    fonte = next((x for x in fontes if x.get("id") == a.fonte), None)
    if fonte is None or fonte.get("vigente") != "sim" or not fonte.get("url"):
        sys.exit("requisito exige fonte oficial registrada com URL e vigência confirmada")
    itens = ficha.setdefault("requisitos", [])
    item = {"id": proximo_id(itens, "r"), "fonte_id": a.fonte, "item": a.item,
            "criterio": a.criterio, "valor": a.valor, "unidade": a.unidade,
            "impacto": a.impacto, "registrado_em": dt.date.today().isoformat()}
    itens.append(item)
    salvar(a.pasta, ficha)
    print(json.dumps(item, ensure_ascii=False))
    return 0


def cmd_decisao(a) -> int:
    ficha = carregar(a.pasta)
    itens = ficha.setdefault("decisoes", [])
    item = {"id": proximo_id(itens, "d"), "assunto": a.assunto, "decisao": a.decisao,
            "origem": a.origem, "fonte_id": a.fonte, "registrado_em": dt.date.today().isoformat()}
    if a.fonte and a.fonte not in {x.get("id") for x in ficha.get("fontes", [])}:
        sys.exit(f"fonte '{a.fonte}' não encontrada")
    itens.append(item)
    salvar(a.pasta, ficha)
    print(json.dumps(item, ensure_ascii=False))
    return 0


def cmd_artefato(a) -> int:
    ficha = carregar(a.pasta)
    base = arq(a.pasta).parent
    caminho = Path(a.caminho)
    alvo = (base / caminho).resolve()
    if alvo != base and base not in alvo.parents:
        sys.exit("artefato deve estar dentro da pasta do projeto")
    if not alvo.is_file():
        sys.exit(f"artefato não encontrado: {alvo}")
    relativo = alvo.relative_to(base).as_posix()
    itens = ficha.setdefault("artefatos", [])
    item = {"tipo": a.tipo, "caminho": relativo, "revisao": a.revisao, "estado": a.estado,
            "registrado_em": dt.date.today().isoformat()}
    ficha["artefatos"] = [x for x in itens if x.get("caminho") != relativo] + [item]
    salvar(a.pasta, ficha)
    print(json.dumps(item, ensure_ascii=False))
    return 0


def cmd_atp(a) -> int:
    """Registra decisão profissional; não infere CC só pelo uso/pavimentos da ficha."""
    ficha = carregar(a.pasta)
    if a.situacao == "dispensada" and a.classe == "CC3":
        sys.exit("a Emenda 1 não prevê dispensa da ATP para CC3")
    if a.situacao in {"dispensada", "parecer-recebido"} and not a.documento:
        sys.exit("decisão final de ATP exige documento formal na pasta da obra")
    if a.situacao == "parecer-recebido" and not a.avaliador:
        sys.exit("parecer de ATP exige identificação do avaliador independente")
    relativo = None
    if a.documento:
        base = arq(a.pasta).parent
        alvo = (base / a.documento).resolve()
        if base not in alvo.parents or not alvo.is_file():
            sys.exit("documento da ATP deve existir dentro da pasta do projeto")
        relativo = alvo.relative_to(base).as_posix()
    ficha["atp"] = {"classe": a.classe, "situacao": a.situacao, "fundamento": a.fundamento,
                    "avaliador": a.avaliador, "documento": relativo, "registrado_em": dt.date.today().isoformat()}
    salvar(a.pasta, ficha)
    print(json.dumps(ficha["atp"], ensure_ascii=False))
    return 0


def cmd_resumo(a) -> int:
    ficha = carregar(a.pasta)
    dados = {"projeto": ficha.get("projeto"), "municipio": ficha.get("municipio"), "uf": ficha.get("uf"),
             "uso": ficha.get("uso"), "caa": ficha.get("caa"), "fontes": ficha.get("fontes", []),
             "requisitos": ficha.get("requisitos", []), "decisoes": ficha.get("decisoes", []),
             "artefatos": ficha.get("artefatos", []), "atp": ficha.get("atp") or {"situacao": "pendente"},
             "pendencias": pendencias_abertas(ficha),
             "checklist_faltante": checklist_faltante(ficha), "atualizado_em": ficha.get("atualizado_em")}
    print(json.dumps(dados, indent=2, ensure_ascii=False))
    return 0


def cmd_nao_aplica(a) -> int:
    ficha = carregar(a.pasta)
    if a.fonte and a.fonte not in {x.get("id") for x in ficha.get("fontes", [])}:
        sys.exit(f"fonte '{a.fonte}' não encontrada")
    for c in ficha["checklist"]:
        if c["id"] == a.checklist:
            c["nao_aplica"] = a.motivo
            c["fonte_id"] = a.fonte
            salvar(a.pasta, ficha)
            return 0
    sys.exit(f"item '{a.checklist}' não existe")


def cmd_mostrar(a) -> int:
    ficha = carregar(a.pasta)
    print(json.dumps(ficha, indent=2, ensure_ascii=False) if a.json else render(ficha))
    return 0


def cmd_perfil(a) -> int:
    f = sv_home() / "perfil.json"
    perfil = ler_perfil()
    if a.municipio or a.uf:
        uf = (a.uf or perfil.get("uf") or "").upper()
        if uf not in UFS:
            sys.exit("UF inválida")
        perfil.update({"municipio": a.municipio or perfil.get("municipio"), "uf": uf})
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(perfil, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(perfil, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("iniciar")
    p.add_argument("--pasta", default=".")
    p.add_argument("--projeto")
    p.add_argument("--municipio")
    p.add_argument("--uf")
    p.add_argument("--uso", choices=USOS)
    p.add_argument("--pavimentos", type=int)
    p.add_argument("--area", type=float)
    p.add_argument("--ambiente", choices=list(CAA))
    p.add_argument("--forcar", action="store_true")
    p = sub.add_parser("fonte")
    p.add_argument("--pasta", default=".")
    p.add_argument("--esfera", choices=ESFERAS, required=True)
    p.add_argument("--tipo", required=True, help="ex.: Código de Obras, IT do Corpo de Bombeiros, NBR")
    p.add_argument("--titulo", required=True)
    p.add_argument("--numero")
    p.add_argument("--ano")
    p.add_argument("--url")
    p.add_argument("--vigente", choices=["sim", "nao"])
    p.add_argument("--obs")
    p.add_argument("--checklist", help="id do item do checklist que esta fonte atende (ex.: c1)")
    p = sub.add_parser("requisito")
    p.add_argument("--pasta", default=".")
    p.add_argument("--fonte", required=True, help="ID devolvido pelo comando fonte (ex.: f1)")
    p.add_argument("--item", required=True, help="artigo ou item da fonte")
    p.add_argument("--criterio", required=True)
    p.add_argument("--valor")
    p.add_argument("--unidade")
    p.add_argument("--impacto")
    p = sub.add_parser("decisao")
    p.add_argument("--pasta", default=".")
    p.add_argument("--assunto", required=True)
    p.add_argument("--decisao", required=True)
    p.add_argument("--origem", required=True, choices=["usuario", "projetista", "fonte-oficial", "hipotese"])
    p.add_argument("--fonte", help="ID da fonte que fundamenta a decisão")
    p = sub.add_parser("artefato")
    p.add_argument("--pasta", default=".")
    p.add_argument("--tipo", required=True)
    p.add_argument("--caminho", required=True, help="arquivo dentro da pasta do projeto")
    p.add_argument("--revisao", default="0")
    p.add_argument("--estado", choices=["rascunho", "em-revisao", "revisado"], default="rascunho")
    p = sub.add_parser("atp")
    p.add_argument("--pasta", default=".")
    p.add_argument("--classe", choices=["CC1", "CC2", "CC3"], required=True)
    p.add_argument("--situacao", choices=["pendente", "em-andamento", "parecer-recebido", "dispensada"], required=True)
    p.add_argument("--fundamento", required=True, help="critérios da classificação e da decisão, informados pelo projetista")
    p.add_argument("--avaliador", help="profissional independente, quando houver ATP")
    p.add_argument("--documento", help="parecer ou decisão formal dentro da pasta da obra")
    p = sub.add_parser("nao-aplica")
    p.add_argument("--pasta", default=".")
    p.add_argument("--checklist", required=True)
    p.add_argument("--motivo", required=True)
    p.add_argument("--fonte", help="ID da fonte oficial que fundamenta a dispensa")
    p = sub.add_parser("pendencia")
    p.add_argument("--pasta", default=".")
    p.add_argument("--texto", required=True)
    p.add_argument("--responsavel")
    p = sub.add_parser("resolver-pendencia")
    p.add_argument("--pasta", default=".")
    p.add_argument("--id", required=True)
    p.add_argument("--solucao", required=True)
    p = sub.add_parser("resumo")
    p.add_argument("--pasta", default=".")
    p = sub.add_parser("mostrar")
    p.add_argument("--pasta", default=".")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("perfil")
    p.add_argument("--municipio")
    p.add_argument("--uf")
    a = ap.parse_args(argv)
    return {"iniciar": cmd_iniciar, "fonte": cmd_fonte, "pendencia": cmd_pendencia, "mostrar": cmd_mostrar,
            "requisito": cmd_requisito, "decisao": cmd_decisao, "artefato": cmd_artefato, "atp": cmd_atp,
            "resolver-pendencia": cmd_resolver_pendencia, "resumo": cmd_resumo, "nao-aplica": cmd_nao_aplica,
            "perfil": cmd_perfil}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
