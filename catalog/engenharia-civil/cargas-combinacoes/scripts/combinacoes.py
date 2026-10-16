#!/usr/bin/env python3
"""Envoltórias auxiliares ELU normal/ELS de efeitos lineares; perfil normativo explícito.

Ação: nome:tipo:valor[:grupo]. Valores são efeitos característicos assinados na
mesma seção e unidade. Grupos são alternativas mutuamente exclusivas.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys

PSI = {
    "residencial": (0.5, 0.4, 0.3), "comercial": (0.7, 0.6, 0.4),
    "biblioteca": (0.8, 0.7, 0.6), "cobertura": (0.8, 0.7, 0.6),
    "vento": (0.6, 0.3, 0.0), "temperatura": (0.6, 0.5, 0.3),
}
PERMANENTES = {"permanente", "retracao"}
PERFIS = {
    "concreto-6118": {
        "norma": "ABNT NBR 6118:2023 + Emenda 1:2026, Tabelas 11.1/11.2; ABNT NBR 8681:2025, 5.1.3",
        "gamma_g": (1.4, 1.0), "gamma_q": 1.4, "gamma_vento": 1.4, "gamma_temp": 1.2,
    },
    "geral-8681": {
        "norma": "ABNT NBR 8681:2025, 5.1.3, Tabelas 2/4/6 (permanentes agrupadas, variáveis separadas)",
        "gamma_g": (1.35, 1.0), "gamma_q": 1.5, "gamma_vento": 1.4, "gamma_temp": 1.2,
    },
}


def parse(s: str) -> dict:
    parts = s.split(":")
    if len(parts) not in (3, 4):
        raise argparse.ArgumentTypeError(f"ação inválida '{s}' — use nome:tipo:valor[:grupo]")
    nome, tipo = parts[0].strip(), parts[1].strip().lower()
    if not nome or tipo not in PSI and tipo not in PERMANENTES:
        raise argparse.ArgumentTypeError(f"nome ou tipo inválido na ação '{s}'")
    try:
        valor = float(parts[2].replace(",", "."))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"valor inválido na ação '{s}'") from exc
    if not math.isfinite(valor):
        raise argparse.ArgumentTypeError("efeito deve ser finito")
    grupo = parts[3].strip() if len(parts) == 4 else nome
    if not grupo:
        raise argparse.ArgumentTypeError("grupo vazio")
    return {"nome": nome, "tipo": tipo, "valor": valor, "grupo": grupo}


def combinar(acoes: list[dict], perfil: str = "concreto-6118", gamma_g=None) -> dict:
    if gamma_g is not None:
        raise ValueError("--gamma-g isolado não define combinação especial; use somente ELU normal")
    if perfil not in PERFIS:
        raise ValueError(f"perfil desconhecido: {perfil}")
    if not acoes:
        raise ValueError("informe ao menos uma ação")
    nomes = [a["nome"] for a in acoes]
    if len(nomes) != len(set(nomes)):
        raise ValueError("nomes de ações devem ser únicos")
    if perfil == "concreto-6118" and any(a["tipo"] == "cobertura" for a in acoes):
        raise ValueError("fator de cobertura não consta da Tabela 11.2 da NBR 6118:2023; confirme no projeto")
    cfg = PERFIS[perfil]
    perm = [a for a in acoes if a["tipo"] in PERMANENTES]
    var = [a for a in acoes if a["tipo"] in PSI]
    grupos: dict[str, list[dict]] = {}
    for v in var:
        grupos.setdefault(v["grupo"], []).append(v)
    escolhas = [[None, *g] for g in grupos.values()]
    out = {"ELU": [], "ELS_quase_permanente": [], "ELS_frequente": [], "ELS_rara": []}

    def permanente_elu(sinal: int) -> tuple[float, str]:
        diretas = [p for p in perm if p["tipo"] == "permanente"]
        indiretas = [p for p in perm if p["tipo"] == "retracao"]
        termos, valor = [], 0.0
        if perfil == "geral-8681":  # Tabela 2: todas as diretas agrupadas
            soma = sum(p["valor"] for p in diretas)
            if diretas:
                gamma = cfg["gamma_g"][0 if soma * sinal > 0 else 1]
                valor += gamma * soma
                termos.append(f"{gamma:g}·(" + " + ".join(p["nome"] for p in diretas) + ")")
        else:
            for p in diretas:
                gamma = cfg["gamma_g"][0 if p["valor"] * sinal > 0 else 1]
                valor += gamma * p["valor"]
                termos.append(f"{gamma:g}·{p['nome']}")
        for p in indiretas:
            gamma = 1.2 if p["valor"] * sinal > 0 else 0.0
            valor += gamma * p["valor"]
            termos.append(f"{gamma:g}·{p['nome']}")
        return valor, " + ".join(termos) or "0"

    def gamma_variavel(tipo: str) -> float:
        return cfg["gamma_vento"] if tipo == "vento" else (cfg["gamma_temp"] if tipo == "temperatura" else cfg["gamma_q"])

    sum_g = sum(p["valor"] for p in perm)
    for combo in itertools.product(*escolhas):
        ativos = [c for c in combo if c is not None]
        if not ativos:
            continue
        for principal in ativos:
            sec = [c for c in ativos if c is not principal]
            for sinal in (1, -1):
                if principal["valor"] * sinal <= 0:
                    continue  # variáveis favoráveis não entram no ELU
                adversas = [c for c in sec if c["valor"] * sinal > 0]
                g_val, g_txt = permanente_elu(sinal)
                termos = [(principal, 1.0), *[(c, PSI[c["tipo"]][0]) for c in adversas]]
                val = g_val + sum(gamma_variavel(c["tipo"]) * psi * c["valor"] for c, psi in termos)
                txt = g_txt + " + " + " + ".join(
                    f"{gamma_variavel(c['tipo']):g}·{psi:g}·{c['nome']}" for c, psi in termos)
                out["ELU"].append({"principal": principal["nome"], "sentido": "max" if sinal == 1 else "min",
                                   "valor": val, "expressao": txt})
            out["ELS_frequente"].append({"principal": principal["nome"],
                                         "valor": sum_g + PSI[principal["tipo"]][1] * principal["valor"]
                                         + sum(PSI[c["tipo"]][2] * c["valor"] for c in sec)})
            out["ELS_rara"].append({"principal": principal["nome"],
                                    "valor": sum_g + principal["valor"]
                                    + sum(PSI[c["tipo"]][1] * c["valor"] for c in sec)})
        out["ELS_quase_permanente"].append({"acoes": [c["nome"] for c in ativos],
                                            "valor": sum_g + sum(PSI[c["tipo"]][2] * c["valor"] for c in ativos)})
    for sinal in (1, -1):
        g_val, g_txt = permanente_elu(sinal)
        out["ELU"].append({"principal": "-", "sentido": "max" if sinal == 1 else "min",
                           "valor": g_val, "expressao": g_txt})
    if not var:
        for chave in ("ELS_quase_permanente", "ELS_frequente", "ELS_rara"):
            out[chave].append({"acoes": [], "valor": sum_g})
    for chave, lista in out.items():
        seen, uniq = set(), []
        for item in lista:
            key = (round(item["valor"], 9), item.get("principal"), item.get("sentido"), tuple(item.get("acoes", [])))
            if key not in seen:
                seen.add(key)
                uniq.append(item)
        out[chave] = uniq
    resumo = {k: {"max": max(i["valor"] for i in v), "min": min(i["valor"] for i in v)} for k, v in out.items() if v}
    return {"norma_base_calculo": cfg["norma"], "perfil": perfil,
            "status_normativo": "parametros-tabelados-conferidos-aplicabilidade-e-erratas-pendentes",
            "limites": ["somente combinações normais de efeitos lineares na mesma seção e unidade",
                        "não cobre combinações especiais, construção, excepcionais, fadiga ou estabilidade como corpo rígido",
                        "compatibilização NBR 8681:2025 x NBR 6118:2023/Em1:2026 exige decisão documentada do projetista",
                        "não comprova ações, concomitância, resistência nem dimensionamento"],
            "combinacoes": out, "envoltoria": resumo}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--acao", action="append", type=parse, required=True)
    ap.add_argument("--perfil", choices=list(PERFIS), required=True,
                    help="concreto-6118 ou geral-8681; escolha registrada pelo responsável técnico")
    ap.add_argument("--gamma-g", nargs=2, help=argparse.SUPPRESS)  # erro explícito para chamadas antigas
    ap.add_argument("--formato", choices=["md", "json"], default="md")
    a = ap.parse_args(argv)
    try:
        r = combinar(a.acao, a.perfil, a.gamma_g)
    except ValueError as exc:
        ap.error(str(exc))
    if a.formato == "json":
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0
    print(f"### Combinações de ações — {a.perfil}\n\n| Combinação | Principal | Expressão | Valor |\n|---|---|---|---:|")
    for item in sorted(r["combinacoes"]["ELU"], key=lambda i: -i["valor"]):
        print(f"| ELU normal | {item['principal']} | {item['expressao']} | {item['valor']:.2f} |")
    for k in ("ELS_rara", "ELS_frequente", "ELS_quase_permanente"):
        for item in r["combinacoes"][k]:
            quem = item.get("principal") or ", ".join(item.get("acoes", [])) or "-"
            print(f"| {k.replace('_', ' ')} | {quem} | — | {item['valor']:.2f} |")
    print("\n**Envoltória**\n")
    for k, v in r["envoltoria"].items():
        print(f"- {k.replace('_', ' ')}: máx {v['max']:.2f} · mín {v['min']:.2f}")
    print("\n_Cálculo auxiliar. Confira aplicabilidade, edição e casos excluídos antes de uso em projeto._")
    return 0


if __name__ == "__main__":
    sys.exit(main())
