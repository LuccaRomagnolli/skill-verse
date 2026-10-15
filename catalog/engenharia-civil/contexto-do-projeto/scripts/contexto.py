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
    return json.loads(f.read_text(encoding="utf-8"))


def salvar(pasta: str, ficha: dict) -> None:
    f = arq(pasta)
    ficha["atualizado_em"] = dt.date.today().isoformat()
    f.write_text(json.dumps(ficha, indent=2, ensure_ascii=False), encoding="utf-8")
    f.with_suffix(".md").write_text(render(ficha), encoding="utf-8")


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
        linhas += ["| Esfera | Tipo | Documento | Vigência confirmada | Link | Acesso |", "|---|---|---|---|---|---|"]
        for x in fontes:
            vig = {"sim": "sim", "nao": "não", None: "a confirmar"}.get(x.get("vigente"), "a confirmar")
            linhas.append(f"| {x['esfera']} | {x['tipo']} | {x['titulo']} | {vig} | {x.get('url') or '—'} | {x['acessado_em']} |")
    else:
        linhas.append("_Nenhuma fonte registrada ainda._")
    pend = [p for p in f.get("pendencias", []) if not p.get("resolvida")]
    atendidos = {x.get("checklist") for x in fontes}
    faltando = [c for c in f.get("checklist", []) if c["id"] not in atendidos and not c.get("nao_aplica")]
    linhas += ["", "## Ainda a pesquisar / confirmar", ""]
    linhas += [f"- [ ] `{c['id']}` ({c['esfera']}) {c['item']}" for c in faltando] or ["- (checklist completo)"]
    linhas += [f"- [ ] {p['texto']}" for p in pend]
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
             "area": a.area, "ambiente": a.ambiente, "caa": caa, "fontes": [], "pendencias": [], "checklist": checklist,
             "criado_em": dt.date.today().isoformat()}
    salvar(a.pasta, ficha)
    print(json.dumps({"ficha": str(f), "municipio": municipio, "uf": uf, "caa": caa,
                      "pesquisar": [f"{c['id']} ({c['esfera']}) {c['item']}" for c in checklist]}, indent=2, ensure_ascii=False))
    return 0


def cmd_fonte(a) -> int:
    ficha = carregar(a.pasta)
    if a.checklist and a.checklist not in {c["id"] for c in ficha["checklist"]}:
        sys.exit(f"item de checklist '{a.checklist}' não existe")
    item = {"checklist": a.checklist, "esfera": a.esfera, "tipo": a.tipo, "titulo": a.titulo, "numero": a.numero, "ano": a.ano, "url": a.url,
            "vigente": a.vigente, "observacao": a.obs, "acessado_em": dt.date.today().isoformat()}
    ficha["fontes"] = [x for x in ficha["fontes"] if not (x["titulo"] == a.titulo and x["esfera"] == a.esfera)] + [item]
    salvar(a.pasta, ficha)
    print(f"Fonte registrada ({len(ficha['fontes'])} no total).")
    return 0


def cmd_pendencia(a) -> int:
    ficha = carregar(a.pasta)
    ficha["pendencias"].append({"texto": a.texto, "resolvida": False})
    salvar(a.pasta, ficha)
    return 0


def cmd_nao_aplica(a) -> int:
    ficha = carregar(a.pasta)
    for c in ficha["checklist"]:
        if c["id"] == a.checklist:
            c["nao_aplica"] = a.motivo
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
    p = sub.add_parser("nao-aplica")
    p.add_argument("--pasta", default=".")
    p.add_argument("--checklist", required=True)
    p.add_argument("--motivo", required=True)
    p = sub.add_parser("pendencia")
    p.add_argument("--pasta", default=".")
    p.add_argument("--texto", required=True)
    p = sub.add_parser("mostrar")
    p.add_argument("--pasta", default=".")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("perfil")
    p.add_argument("--municipio")
    p.add_argument("--uf")
    a = ap.parse_args(argv)
    return {"iniciar": cmd_iniciar, "fonte": cmd_fonte, "pendencia": cmd_pendencia, "mostrar": cmd_mostrar,
            "nao-aplica": cmd_nao_aplica,
            "perfil": cmd_perfil}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
