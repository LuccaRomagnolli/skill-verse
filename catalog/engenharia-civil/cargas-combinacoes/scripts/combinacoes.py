#!/usr/bin/env python3
"""Combinações de ações — ELU normal e ELS (NBR 8681:2003 / NBR 6118:2023, Tabelas 11.1 e 11.2).

Cada ação: nome:tipo:valor[:grupo]. O valor é o EFEITO característico (kN, kN·m, kN/m…), com sinal.
Ações do mesmo `grupo` são mutuamente exclusivas (ex.: vento 0° e vento 90°).

Tipos:
  permanente            γg = 1,4 desfavorável / 1,0 favorável
  retracao              γε = 1,2 / 0 (permanente indireta)
  residencial           ψ0 0,5  ψ1 0,4  ψ2 0,3
  comercial             ψ0 0,7  ψ1 0,6  ψ2 0,4   (escritórios, lojas, edifícios públicos)
  biblioteca            ψ0 0,8  ψ1 0,7  ψ2 0,6   (bibliotecas, arquivos, oficinas, garagens)
  vento                 ψ0 0,6  ψ1 0,3  ψ2 0,0
  temperatura           ψ0 0,6  ψ1 0,5  ψ2 0,3   (γ = 1,2)

Exemplo:
  python3 combinacoes.py --acao G:permanente:120 --acao Q:comercial:45 \
      --acao W0:vento:30:vento --acao W90:vento:-25:vento
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys

PSI = {"residencial": (0.5, 0.4, 0.3), "comercial": (0.7, 0.6, 0.4), "biblioteca": (0.8, 0.7, 0.6),
       "vento": (0.6, 0.3, 0.0), "temperatura": (0.6, 0.5, 0.3)}
GAMMA_Q = {"temperatura": 1.2}
PERMANENTES = {"permanente": (1.4, 1.0), "retracao": (1.2, 0.0)}


def parse(s: str) -> dict:
    parts = s.split(":")
    if len(parts) not in (3, 4):
        raise argparse.ArgumentTypeError(f"ação inválida '{s}' — use nome:tipo:valor[:grupo]")
    nome, tipo, valor = parts[0], parts[1].lower(), float(parts[2].replace(",", "."))
    if tipo not in PSI and tipo not in PERMANENTES:
        raise argparse.ArgumentTypeError(f"tipo '{tipo}' desconhecido")
    return {"nome": nome, "tipo": tipo, "valor": valor, "grupo": parts[3] if len(parts) == 4 else nome}


def combinar(acoes: list[dict], gamma_g: tuple[float, float] | None = None) -> dict:
    perm = [a for a in acoes if a["tipo"] in PERMANENTES]
    var = [a for a in acoes if a["tipo"] in PSI]
    grupos: dict[str, list[dict]] = {}
    for v in var:
        grupos.setdefault(v["grupo"], []).append(v)
    # cada grupo: ausente ou uma das ações do grupo
    escolhas = [[None, *g] for g in grupos.values()]
    out = {"ELU": [], "ELS_quase_permanente": [], "ELS_frequente": [], "ELS_rara": []}

    def perm_elu(sinal: int) -> tuple[float, str]:
        """γ desfavorável/favorável por ação conforme o sentido que se quer maximizar."""
        tot, termos = 0.0, []
        for p in perm:
            gd, gf = gamma_g if (gamma_g and p["tipo"] == "permanente") else PERMANENTES[p["tipo"]]
            g = gd if p["valor"] * sinal > 0 else gf
            tot += g * p["valor"]
            termos.append(f"{g:g}·{p['nome']}")
        return tot, " + ".join(termos)

    sum_g = sum(p["valor"] for p in perm)
    for combo in itertools.product(*escolhas):
        ativos = [c for c in combo if c is not None]
        if not ativos:
            continue
        for principal in ativos:
            sec = [c for c in ativos if c is not principal]
            gq = GAMMA_Q.get(principal["tipo"], 1.4)
            q = principal["valor"] + sum(PSI[c["tipo"]][0] * c["valor"] for c in sec)
            for sinal in (1, -1):  # maximiza (+1) e minimiza (−1) o efeito
                g_tot, g_txt = perm_elu(sinal)
                val = g_tot + gq * q
                txt = f"{g_txt} + {gq:g}·({principal['nome']}" + "".join(
                    f" + {PSI[c['tipo']][0]:g}·{c['nome']}" for c in sec) + ")"
                out["ELU"].append({"principal": principal["nome"], "valor": val, "expressao": txt})
            # ELS
            out["ELS_frequente"].append({"principal": principal["nome"],
                                         "valor": sum_g + PSI[principal["tipo"]][1] * principal["valor"]
                                         + sum(PSI[c["tipo"]][2] * c["valor"] for c in sec)})
            out["ELS_rara"].append({"principal": principal["nome"],
                                    "valor": sum_g + principal["valor"] + sum(PSI[c["tipo"]][1] * c["valor"] for c in sec)})
        out["ELS_quase_permanente"].append({"acoes": [c["nome"] for c in ativos],
                                            "valor": sum_g + sum(PSI[c["tipo"]][2] * c["valor"] for c in ativos)})
    if not var:
        for sinal in (1, -1):
            g_tot, g_txt = perm_elu(sinal)
            out["ELU"].append({"principal": "-", "valor": g_tot, "expressao": g_txt})
        out["ELS_quase_permanente"].append({"acoes": [], "valor": sum_g})
    # remove duplicadas e resume
    for k, lst in out.items():
        seen, uniq = set(), []
        for item in lst:
            key = round(item["valor"], 6), item.get("expressao", str(item.get("acoes", item.get("principal"))))
            if key not in seen:
                seen.add(key)
                uniq.append(item)
        out[k] = uniq
    resumo = {k: {"max": max(i["valor"] for i in v), "min": min(i["valor"] for i in v)} for k, v in out.items() if v}
    return {"combinacoes": out, "envoltoria": resumo}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--acao", action="append", type=parse, required=True)
    ap.add_argument("--gamma-g", type=float, nargs=2, metavar=("DESF", "FAV"),
                    help="sobrescreve γg (ex.: 1.3 1.0 para combinação especial/construção)")
    ap.add_argument("--formato", choices=["md", "json"], default="md")
    a = ap.parse_args(argv)
    r = combinar(a.acao, tuple(a.gamma_g) if a.gamma_g else None)
    if a.formato == "json":
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0
    print("### Combinações de ações\n\n| Combinação | Ação principal | Expressão | Valor |\n|---|---|---|---|")
    for item in sorted(r["combinacoes"]["ELU"], key=lambda i: -i["valor"]):
        print(f"| ELU normal | {item['principal']} | {item['expressao']} | {item['valor']:.2f} |")
    for k in ("ELS_rara", "ELS_frequente", "ELS_quase_permanente"):
        for item in r["combinacoes"][k]:
            quem = item.get("principal") or ", ".join(item.get("acoes", [])) or "-"
            print(f"| {k.replace('_', ' ')} | {quem} | — | {item['valor']:.2f} |")
    print("\n**Envoltória**\n")
    for k, v in r["envoltoria"].items():
        print(f"- {k.replace('_', ' ')}: máx {v['max']:.2f} · mín {v['min']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
