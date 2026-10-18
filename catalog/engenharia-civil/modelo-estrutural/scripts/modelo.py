#!/usr/bin/env python3
"""Modelo estrutural versionado -> SkyCiv S3D e entrada BIM legada.

Geometria em m, seções em m, forças em kN, pressões em kPa, E em MPa.
O arquivo exige ações e vínculos explícitos; não infere cargas de desenhos.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

UNIDADES = {"comprimento": "m", "secao": "m", "forca": "kN", "momento": "kN.m",
            "pressao": "kPa", "modulo": "MPa", "densidade": "kg/m3"}
FONTES = ("documento", "item", "data")


def numero(v, nome, positivo=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or (positivo and v <= 0):
        raise ValueError(f"{nome}: número {'positivo ' if positivo else ''}finito obrigatório")
    return float(v)


def texto(v, nome):
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{nome}: texto obrigatório")
    return v.strip()


def fonte(v, nome):
    if not isinstance(v, dict) or any(not str(v.get(k, "")).strip() for k in FONTES):
        raise ValueError(f"{nome}: documento, item e data são obrigatórios")


def colecao(d, nome):
    x = d.get(nome, [])
    if not isinstance(x, list):
        raise ValueError(f"{nome}: lista obrigatória")
    ids = [texto(e.get("id"), f"{nome}.id") for e in x if isinstance(e, dict)]
    if len(ids) != len(x) or len(ids) != len(set(ids)):
        raise ValueError(f"{nome}: objetos com IDs únicos obrigatórios")
    return x


def validar(d: dict) -> dict:
    if not isinstance(d, dict) or d.get("schema_version") != 1:
        raise ValueError("schema_version deve ser 1")
    if d.get("unidades") != UNIDADES:
        raise ValueError("unidades devem corresponder ao esquema v1; sem conversão implícita")
    projeto = d.get("projeto")
    if not isinstance(projeto, dict):
        raise ValueError("projeto: objeto obrigatório")
    texto(projeto.get("id"), "projeto.id")
    texto(projeto.get("revisao"), "projeto.revisao")
    if d.get("eixo_vertical") != "Z":
        raise ValueError("eixo_vertical deve ser Z")
    if d.get("mapa_acoes") is not None:
        caminho_mapa = texto(d["mapa_acoes"], "mapa_acoes")
        if Path(caminho_mapa).is_absolute() or ".." in Path(caminho_mapa).parts:
            raise ValueError("mapa_acoes deve ser caminho relativo à pasta do modelo")
    niveis = colecao(d, "niveis")
    materiais = colecao(d, "materiais")
    pilares, vigas, lajes = (colecao(d, k) for k in ("pilares", "vigas", "lajes"))
    apoios, acoes, combinacoes = (colecao(d, k) for k in ("apoios", "acoes", "combinacoes"))
    if not niveis or not materiais or not apoios or not combinacoes or not (pilares or vigas or lajes):
        raise ValueError("modelo requer níveis, materiais, peças, apoios e combinações")
    niveis_por_id = {x["id"]: numero(x.get("cota_m"), f"nível {x['id']}.cota_m") for x in niveis}
    if len(set(niveis_por_id.values())) != len(niveis_por_id):
        raise ValueError("níveis com cotas coincidentes")
    eixos = d.get("eixos", {"x": [], "y": []})
    if not isinstance(eixos, dict) or set(eixos) - {"x", "y"}:
        raise ValueError("eixos: objeto com listas x/y obrigatório")
    for direcao in ("x", "y"):
        lista = eixos.get(direcao, [])
        if not isinstance(lista, list):
            raise ValueError(f"eixos.{direcao}: lista obrigatória")
        nomes = []
        for eixo in lista:
            if not isinstance(eixo, dict):
                raise ValueError(f"eixos.{direcao}: objeto obrigatório")
            nomes.append(texto(eixo.get("nome"), f"eixos.{direcao}.nome"))
            numero(eixo.get("pos_m"), f"eixos.{direcao}.pos_m")
        if len(nomes) != len(set(nomes)):
            raise ValueError(f"eixos.{direcao}: nomes duplicados")
    mats = {x["id"] for x in materiais}
    for m in materiais:
        if m.get("classe") not in {"concrete", "steel", "wood", "other"}:
            raise ValueError(f"material {m['id']}: classe inválida")
        numero(m.get("E_MPa"), f"material {m['id']}.E_MPa", True)
        numero(m.get("densidade_kg_m3"), f"material {m['id']}.densidade_kg_m3", True)
        nu = numero(m.get("nu"), f"material {m['id']}.nu")
        if not 0 <= nu < .5:
            raise ValueError(f"material {m['id']}: nu fora de [0,0.5)")
    elementos = {}
    for tipo, itens in (("pilar", pilares), ("viga", vigas), ("laje", lajes)):
        for e in itens:
            eid = e["id"]
            if eid in elementos:
                raise ValueError(f"ID de peça duplicado: {eid}")
            elementos[eid] = tipo
            if e.get("material") not in mats:
                raise ValueError(f"{eid}: material inexistente")
            if tipo == "pilar":
                for k in ("x_m", "y_m", "b_m", "h_m"):
                    numero(e.get(k), f"{eid}.{k}", k in {"b_m", "h_m"})
                if e.get("base") not in niveis_por_id or e.get("topo") not in niveis_por_id or niveis_por_id[e["topo"]] <= niveis_por_id[e["base"]]:
                    raise ValueError(f"{eid}: base/topo inválidos")
            elif tipo == "viga":
                if e.get("nivel") not in niveis_por_id:
                    raise ValueError(f"{eid}: nível inexistente")
                for k in ("b_m", "h_m"):
                    numero(e.get(k), f"{eid}.{k}", True)
                for k in ("de", "ate"):
                    if not isinstance(e.get(k), list) or len(e[k]) != 2:
                        raise ValueError(f"{eid}.{k}: par [x,y] obrigatório")
                    for v in e[k]:
                        numero(v, f"{eid}.{k}")
                if e["de"] == e["ate"]:
                    raise ValueError(f"{eid}: comprimento zero")
            else:
                if e.get("nivel") not in niveis_por_id:
                    raise ValueError(f"{eid}: nível inexistente")
                numero(e.get("espessura_m"), f"{eid}.espessura_m", True)
                contorno = e.get("contorno")
                if not isinstance(contorno, list) or len(contorno) not in (3, 4):
                    raise ValueError(f"{eid}: placa requer 3 ou 4 vértices; divida polígonos maiores")
                for p in contorno:
                    if not isinstance(p, list) or len(p) != 2:
                        raise ValueError(f"{eid}: vértice deve ser [x,y]")
                    for v in p:
                        numero(v, f"{eid}.contorno")
                area = sum(contorno[i][0] * contorno[(i + 1) % len(contorno)][1] - contorno[(i + 1) % len(contorno)][0] * contorno[i][1] for i in range(len(contorno))) / 2
                if area <= 0:
                    raise ValueError(f"{eid}: contorno deve ter área positiva e sentido anti-horário")
                cruzamentos = []
                for i in range(len(contorno)):
                    a, b, c = (contorno[j % len(contorno)] for j in (i, i + 1, i + 2))
                    cruzamentos.append((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]))
                if any(v <= 1e-9 for v in cruzamentos):
                    raise ValueError(f"{eid}: placa deve ser convexa, sem vértices repetidos ou colineares")
            if tipo != "laje":
                for k in ("fixity_A", "fixity_B"):
                    if not isinstance(e.get(k), str) or len(e[k]) != 6 or any(c not in "FR" for c in e[k]):
                        raise ValueError(f"{eid}.{k}: seis caracteres F/R obrigatórios")
                numero(e.get("rot_graus", 0), f"{eid}.rot_graus")
    pontos_apoio = set()
    for a in apoios:
        if not isinstance(a.get("ponto"), list) or len(a["ponto"]) != 3:
            raise ValueError(f"apoio {a['id']}: ponto [x,y,z] obrigatório")
        for v in a["ponto"]:
            numero(v, f"apoio {a['id']}.ponto")
        ponto = tuple(round(float(v), 6) for v in a["ponto"])
        if ponto in pontos_apoio:
            raise ValueError(f"apoio {a['id']}: ponto duplicado")
        pontos_apoio.add(ponto)
        if not isinstance(a.get("restricao"), str) or len(a["restricao"]) != 6 or any(c not in "FR" for c in a["restricao"]):
            raise ValueError(f"apoio {a['id']}: restricao exige seis caracteres F/R")
    grupos = {"SW1"} if d.get("peso_proprio") is True else set()
    for a in acoes:
        if a.get("alvo") not in elementos:
            raise ValueError(f"ação {a['id']}: alvo inexistente")
        if (a.get("tipo"), elementos[a["alvo"]]) not in {("distribuida", "viga"), ("distribuida", "pilar"), ("pressao", "laje"), ("pontual", "viga"), ("pontual", "pilar")}:
            raise ValueError(f"ação {a['id']}: tipo incompatível com a peça")
        texto(a.get("grupo"), f"ação {a['id']}.grupo")
        grupos.add(a["grupo"])
        if a["grupo"] == "SW1":
            raise ValueError("SW1 é reservado ao peso próprio")
        numero(a.get("valor"), f"ação {a['id']}.valor")
        if a.get("direcao") not in {"X", "Y", "Z"}:
            raise ValueError(f"ação {a['id']}: direção global X/Y/Z obrigatória")
        if a["tipo"] == "pontual":
            pos = numero(a.get("posicao_pct"), f"ação {a['id']}.posicao_pct")
            if not 0 <= pos <= 100:
                raise ValueError(f"ação {a['id']}: posição fora de 0..100")
        fonte(a.get("origem"), f"ação {a['id']}.origem")
        if a.get("mapa_ref") is not None:
            texto(a["mapa_ref"], f"ação {a['id']}.mapa_ref")
    for c in combinacoes:
        if c.get("criterio") not in {"strength", "serviceability"}:
            raise ValueError(f"combinação {c['id']}: critério inválido")
        fatores = c.get("fatores")
        if not isinstance(fatores, dict) or not fatores or set(fatores) - grupos:
            raise ValueError(f"combinação {c['id']}: fatores vazios ou grupos inexistentes")
        for g, v in fatores.items():
            numero(v, f"combinação {c['id']}.{g}")
        fonte(c.get("origem"), f"combinação {c['id']}.origem")
        if c.get("perfil") is not None:
            texto(c["perfil"], f"combinação {c['id']}.perfil")
    if type(d.get("peso_proprio")) is not bool:
        raise ValueError("peso_proprio deve ser true ou false")
    return {"pecas": len(elementos), "apoios": len(apoios), "acoes": len(acoes), "combinacoes": len(combinacoes), "grupos": sorted(grupos)}


def digest(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def conferir_mapa(d: dict, mapa: dict) -> dict:
    """Confere rastreabilidade de cada ação explícita contra o inventário característico."""
    validar(d)
    if not isinstance(mapa, dict) or not isinstance(mapa.get("zonas"), list):
        raise ValueError("mapa de ações inválido")
    refs = {}
    for zona in mapa["zonas"]:
        for acao in zona.get("acoes", []):
            refs[f"{zona['id']}/{acao['id']}"] = acao
    for a in d["acoes"]:
        ref = texto(a.get("mapa_ref"), f"ação {a['id']}.mapa_ref")
        if ref not in refs:
            raise ValueError(f"ação {a['id']}: mapa_ref inexistente")
        item = refs[ref]
        forma = {"pressao": ("distribuida", "kN/m²"), "distribuida": ("linear", "kN/m"),
                 "pontual": ("concentrada", "kN")}[a["tipo"]]
        valor_mapa = item.get("valor")
        if ((item.get("forma"), item.get("unidade")) != forma or
                isinstance(valor_mapa, bool) or not isinstance(valor_mapa, (int, float)) or
                not math.isclose(abs(a["valor"]), valor_mapa, rel_tol=1e-8)):
            raise ValueError(f"ação {a['id']}: forma, unidade ou módulo diverge do mapa")
        if any(a["origem"].get(k) != item.get("origem", {}).get(k) for k in FONTES):
            raise ValueError(f"ação {a['id']}: fonte diverge do mapa")
    return {"acoes_conferidas": len(d["acoes"]), "referencias": sorted(a["mapa_ref"] for a in d["acoes"])}


def para_skyciv(d: dict) -> dict:
    validar(d)
    cotas = {n["id"]: n["cota_m"] for n in d["niveis"]}
    nos, barras, placas, secoes = {}, {}, {}, {}
    ids, posicoes, sec_ids = {"nos": {}, "pecas": {}, "placas": {}}, {}, {}
    mat_ids = {m["id"]: i for i, m in enumerate(d["materiais"], 1)}

    def no(x, y, z):
        chave = tuple(round(float(v), 6) for v in (x, y, z))
        if chave not in posicoes:
            nid = len(nos) + 1
            posicoes[chave] = nid
            nos[str(nid)] = {"x": chave[0], "y": chave[1], "z": chave[2]}
        return posicoes[chave]

    def barra(e, a, b):
        sec = (e["material"], e["b_m"], e["h_m"])
        if sec not in sec_ids:
            sid = len(secoes) + 1
            sec_ids[sec] = sid
            secoes[str(sid)] = {"material_id": mat_ids[e["material"]], "info": {"shape": "rectangle", "dimensions": {"b": e["b_m"] * 1000, "h": e["h_m"] * 1000}}}
        mid = len(barras) + 1
        barras[str(mid)] = {"node_A": no(*a), "node_B": no(*b), "section_id": sec_ids[sec],
                            "fixity_A": e["fixity_A"], "fixity_B": e["fixity_B"], "rotation_angle": e.get("rot_graus", 0)}
        ids["pecas"][e["id"]] = mid

    for p in d.get("pilares", []):
        barra(p, (p["x_m"], p["y_m"], cotas[p["base"]]), (p["x_m"], p["y_m"], cotas[p["topo"]]))
    for v in d.get("vigas", []):
        barra(v, (*v["de"], cotas[v["nivel"]]), (*v["ate"], cotas[v["nivel"]]))
    for l in d.get("lajes", []):
        pid = len(placas) + 1
        placas[str(pid)] = {"nodes": [no(x, y, cotas[l["nivel"]]) for x, y in l["contorno"]],
                            "thickness": l["espessura_m"] * 1000, "material_id": mat_ids[l["material"]]}
        ids["placas"][l["id"]] = pid
    apoios = {}
    for i, a in enumerate(d["apoios"], 1):
        key = tuple(round(float(v), 6) for v in a["ponto"])
        if key not in posicoes:
            raise ValueError(f"apoio {a['id']}: ponto sem nó estrutural")
        apoios[str(i)] = {"node": posicoes[key], "restraint_code": a["restricao"]}
    cargas = {"distributed_loads": {}, "point_loads": {}, "pressures": {}}
    for a in d["acoes"]:
        direcao = a["direcao"].lower()
        if a["tipo"] == "pressao":
            item = {"plate_id": ids["placas"][a["alvo"]], "axes": "global", "load_group": a["grupo"]}
            item.update({f"{k}_mag": a["valor"] if k == direcao else 0 for k in "xyz"})
            chave = "pressures"
        elif a["tipo"] == "distribuida":
            item = {"member": ids["pecas"][a["alvo"]], "axes": "global", "load_group": a["grupo"],
                    "position_A": 0, "position_B": 100}
            item.update({f"{k}_mag_{p}": a["valor"] if k == direcao else 0 for k in "xyz" for p in "AB"})
            chave = "distributed_loads"
        else:
            item = {"type": "m", "member": ids["pecas"][a["alvo"]], "position": a["posicao_pct"], "load_group": a["grupo"]}
            item.update({f"{k}_mag": a["valor"] if k == direcao else 0 for k in "xyz"})
            chave = "point_loads"
        cargas[chave][str(len(cargas[chave]) + 1)] = item
    model = {"settings": {"vertical_axis": "Z", "units": {"length": "m", "section_length": "mm", "material_strength": "mpa", "density": "kg/m3", "force": "kn", "moment": "kn-m", "pressure": "kpa", "mass": "kg", "translation": "mm", "stress": "mpa"}},
             "nodes": nos, "members": barras, "plates": placas, "sections": secoes,
             "materials": {str(mat_ids[m["id"]]): {"name": m["id"], "class": m["classe"], "density": m["densidade_kg_m3"], "elasticity_modulus": m["E_MPa"], "poissons_ratio": m["nu"]} for m in d["materiais"]},
             "supports": apoios, **cargas,
             "self_weight": {"direction": "Z", "factor": -1, "LG": "SW1"} if d["peso_proprio"] else {},
             "load_combinations": {str(i): {"name": c["id"], "criteria": c["criterio"], **c["fatores"]} for i, c in enumerate(d["combinacoes"], 1)}}
    ids["nos"] = {str(k): v for k, v in posicoes.items()}
    return {"modelo": model, "ids": ids, "projeto": d["projeto"], "sha256_entrada": digest(d),
            "mapa_acoes": d.get("mapa_acoes")}


def para_revit(d: dict) -> dict:
    validar(d)
    return {"niveis": [{"nome": n["id"], "cota_m": n["cota_m"]} for n in d["niveis"]],
            "eixos": d.get("eixos", {"x": [], "y": []}),
            "pilares": [{"nome": p["id"], "x_m": p["x_m"], "y_m": p["y_m"], "b_cm": p["b_m"] * 100, "h_cm": p["h_m"] * 100, "base": p["base"], "topo": p["topo"]} for p in d.get("pilares", [])],
            "vigas": [{"nome": v["id"], "de": v["de"], "ate": v["ate"], "b_cm": v["b_m"] * 100, "h_cm": v["h_m"] * 100, "nivel": v["nivel"]} for v in d.get("vigas", [])],
            "lajes": [{"nome": l["id"], "contorno": l["contorno"], "h_cm": l["espessura_m"] * 100, "nivel": l["nivel"]} for l in d.get("lajes", [])]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("acao", choices=["validar", "skyciv", "revit"])
    p.add_argument("modelo", type=Path)
    p.add_argument("--saida", type=Path)
    p.add_argument("--mapa", type=Path, help="mapa-acoes.json para conferir mapa_ref, unidade, valor e origem")
    a = p.parse_args()
    d = json.loads(a.modelo.read_text(encoding="utf-8"))
    out = validar(d) if a.acao == "validar" else para_skyciv(d) if a.acao == "skyciv" else para_revit(d)
    if a.mapa:
        conf = conferir_mapa(d, json.loads(a.mapa.read_text(encoding="utf-8")))
        if a.acao == "validar":
            out["mapa"] = conf
    s = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    if a.saida:
        a.saida.write_text(s, encoding="utf-8")
    else:
        print(s, end="")


if __name__ == "__main__":
    main()
