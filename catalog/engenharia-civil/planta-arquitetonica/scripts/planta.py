#!/usr/bin/env python3
"""Valida uma planta arquitetônica transcrita e gera cortes DXF e planos BIM.

Não interpreta automaticamente desenhos nem grava no Revit/Archicad. Coordenadas
da planta e alturas precisam ser conferidas antes de executar os planos.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

EPS = 1e-8


def _cad():
    path = Path(__file__).resolve().parents[2] / "autocad-assistente/scripts/detalhe_secao.py"
    spec = importlib.util.spec_from_file_location("skillverse_cad_arquitetura", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def numero(v, campo, positivo=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(f"{campo}: informe número finito")
    if positivo and v <= 0:
        raise ValueError(f"{campo}: deve ser positivo")
    return float(v)


def ponto(v, campo):
    if not isinstance(v, list) or len(v) != 2:
        raise ValueError(f"{campo}: use [x, y]")
    return [numero(v[0], campo), numero(v[1], campo)]


def distancia(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def validar(d):
    if d.get("unidade") != "m":
        raise ValueError("unidade: use m; para PDF/imagem em pixels rode calibrar primeiro")
    projeto = d.get("projeto") or {}
    if not projeto.get("id") or not projeto.get("revisao"):
        raise ValueError("projeto: id e revisao são obrigatórios")
    fonte = d.get("fonte") or {}
    if fonte.get("tipo") not in {"dwg", "dxf", "pdf", "imagem", "manual"}:
        raise ValueError("fonte.tipo: use dwg, dxf, pdf, imagem ou manual")
    if fonte["tipo"] != "manual" and not fonte.get("arquivo"):
        raise ValueError("fonte.arquivo: informe o arquivo de origem")
    if fonte["tipo"] in {"pdf", "imagem"} and not fonte.get("calibracao"):
        raise ValueError("fonte.calibracao: calibre uma medida conhecida antes de gerar")
    niveis = {}
    for n in d.get("niveis") or []:
        ident = n.get("id")
        if not ident or ident in niveis:
            raise ValueError("niveis: id ausente ou repetido")
        cota = numero(n.get("cota_m"), f"nivel {ident}.cota_m")
        altura = numero(n.get("altura_m"), f"nivel {ident}.altura_m", True)
        niveis[ident] = (cota, altura)
    if not niveis:
        raise ValueError("niveis: informe ao menos um")
    paredes = {}
    for p in d.get("paredes") or []:
        ident = p.get("id")
        if not ident or ident in paredes:
            raise ValueError("paredes: id ausente ou repetido")
        if p.get("nivel") not in niveis:
            raise ValueError(f"parede {ident}: nível inexistente")
        a, b = ponto(p.get("de"), f"parede {ident}.de"), ponto(p.get("ate"), f"parede {ident}.ate")
        if distancia(a, b) < EPS:
            raise ValueError(f"parede {ident}: comprimento zero")
        numero(p.get("espessura_m"), f"parede {ident}.espessura_m", True)
        altura = numero(p.get("altura_m", niveis[p["nivel"]][1]), f"parede {ident}.altura_m", True)
        if altura > niveis[p["nivel"]][1] + EPS:
            raise ValueError(f"parede {ident}: altura supera o pavimento")
        paredes[ident] = p
    if not paredes:
        raise ValueError("paredes: informe ao menos uma")
    aberturas = {}
    for a in d.get("aberturas") or []:
        ident = a.get("id")
        if not ident or ident in aberturas:
            raise ValueError("aberturas: id ausente ou repetido")
        if a.get("tipo") not in {"porta", "janela"} or a.get("parede") not in paredes:
            raise ValueError(f"abertura {ident}: tipo ou parede inválidos")
        p = paredes[a["parede"]]
        tam = distancia(p["de"], p["ate"])
        centro = numero(a.get("centro_m"), f"abertura {ident}.centro_m")
        largura = numero(a.get("largura_m"), f"abertura {ident}.largura_m", True)
        altura = numero(a.get("altura_m"), f"abertura {ident}.altura_m", True)
        peitoril = numero(a.get("peitoril_m", 0), f"abertura {ident}.peitoril_m")
        if centro - largura / 2 < -EPS or centro + largura / 2 > tam + EPS:
            raise ValueError(f"abertura {ident}: fora da parede")
        if peitoril < 0 or peitoril + altura > p.get("altura_m", niveis[p["nivel"]][1]) + EPS:
            raise ValueError(f"abertura {ident}: altura fora da parede")
        if a["tipo"] == "porta" and abs(peitoril) > EPS:
            raise ValueError(f"abertura {ident}: porta deve ter peitoril zero")
        for outro in aberturas.values():
            if outro["parede"] == a["parede"] and abs(outro["centro_m"] - centro) < (outro["largura_m"] + largura) / 2 - EPS:
                raise ValueError(f"aberturas {ident}/{outro['id']}: sobrepostas")
        aberturas[ident] = a
    for piso in d.get("pisos") or []:
        if not piso.get("id") or piso.get("nivel") not in niveis:
            raise ValueError("pisos: id ou nível inválido")
        numero(piso.get("espessura_m"), f"piso {piso['id']}.espessura_m", True)
        contorno = piso.get("contorno") or []
        if len(contorno) < 3:
            raise ValueError(f"piso {piso['id']}: contorno com menos de três pontos")
        for pt in contorno:
            ponto(pt, f"piso {piso['id']}.contorno")
    nomes = set()
    for corte in d.get("cortes") or []:
        ident = corte.get("id")
        if not ident or ident in nomes or any(c in ident for c in "/\\"):
            raise ValueError("cortes: id ausente, repetido ou com separador de caminho")
        nomes.add(ident)
        if distancia(ponto(corte.get("de"), f"corte {ident}.de"), ponto(corte.get("ate"), f"corte {ident}.ate")) < EPS:
            raise ValueError(f"corte {ident}: comprimento zero")
    if not nomes:
        raise ValueError("cortes: indique ao menos uma linha de corte")
    return niveis, paredes


def extrair_dxf(path, layer, unidade, projeto, revisao, nivel, cota_m, altura_m, espessura_m, cortes):
    """Extrai LINE/LWPOLYLINE de um layer de eixos de parede de DXF ASCII.

    O resultado é um rascunho sem aberturas/pisos; contornos duplos e blocos
    requerem interpretação humana, não viram paredes automaticamente.
    """
    try:
        linhas = path.read_text(encoding="cp1252").splitlines()
    except UnicodeError as exc:
        raise ValueError("DXF não é texto ASCII/ANSI; exporte DXF ASCII pelo CAD") from exc
    if len(linhas) % 2:
        raise ValueError("DXF com pares de group code incompletos")
    pares = []
    for i in range(0, len(linhas), 2):
        try:
            pares.append((int(linhas[i].strip()), linhas[i + 1].strip()))
        except ValueError as exc:
            raise ValueError("DXF inválido: group code não numérico") from exc
    insunits = None
    for i, (code, value) in enumerate(pares[:-1]):
        if code == 9 and value == "$INSUNITS" and pares[i + 1][0] == 70:
            insunits = int(pares[i + 1][1])
            break
    units = {"mm": (4, .001), "cm": (5, .01), "m": (6, 1.0)}
    if unidade not in units:
        raise ValueError("unidade: use mm, cm ou m")
    if insunits not in (None, 0, units[unidade][0]):
        raise ValueError(f"unidade informada {unidade} diverge de $INSUNITS={insunits}")
    fator = units[unidade][1]
    segmentos = []
    secao = None
    i = 0
    while i < len(pares):
        code, value = pares[i]
        if code == 0 and value == "SECTION" and i + 1 < len(pares) and pares[i + 1][0] == 2:
            secao = pares[i + 1][1]
            i += 2
            continue
        if code == 0 and value == "ENDSEC":
            secao = None
        if secao == "ENTITIES" and code == 0 and value not in {"ENDSEC", "EOF"}:
            j = i + 1
            item = []
            while j < len(pares) and pares[j][0] != 0:
                item.append(pares[j])
                j += 1
            attrs = {k: v for k, v in item}
            if attrs.get(8) == layer:
                if value not in {"LINE", "LWPOLYLINE"}:
                    raise ValueError(f"entidade {value} no layer {layer}: converta/revise no CAD antes de extrair")
                if value == "LINE":
                    if abs(float(attrs.get(30, "0"))) > EPS or abs(float(attrs.get(31, "0"))) > EPS:
                        raise ValueError("LINE 3D no layer de parede; confira projeção da planta")
                    try:
                        x1, y1, x2, y2 = (float(attrs[k]) * fator for k in (10, 20, 11, 21))
                    except (KeyError, ValueError) as exc:
                        raise ValueError("LINE sem coordenadas válidas") from exc
                    segmentos.append(([x1, y1], [x2, y2]))
                else:
                    if abs(float(attrs.get(38, "0"))) > EPS or any(k == 42 and abs(float(v)) > EPS for k, v in item):
                        raise ValueError("LWPOLYLINE elevada/curva no layer de parede; revise no CAD")
                    xs = [float(v) * fator for k, v in item if k == 10]
                    ys = [float(v) * fator for k, v in item if k == 20]
                    if len(xs) != len(ys) or len(xs) < 2:
                        raise ValueError("LWPOLYLINE sem vértices X/Y válidos")
                    pts = list(zip(xs, ys))
                    segmentos.extend((list(a), list(b)) for a, b in zip(pts, pts[1:]))
                    if int(attrs.get(70, "0")) & 1:
                        segmentos.append((list(pts[-1]), list(pts[0])))
            i = j
            continue
        i += 1
    if not segmentos:
        raise ValueError(f"nenhuma LINE/LWPOLYLINE no layer {layer}; confira nome, blocos e xrefs")
    paredes = []
    for n, (a, b) in enumerate(segmentos, 1):
        if distancia(a, b) < EPS:
            raise ValueError(f"segmento {n}: comprimento zero")
        paredes.append({"id": f"PA-{n:03d}", "nivel": nivel, "de": a, "ate": b,
                        "espessura_m": espessura_m, "altura_m": altura_m})
    d = {"projeto": {"id": projeto, "revisao": revisao},
         "fonte": {"tipo": "dxf", "arquivo": str(path), "layer_eixo_paredes": layer,
                    "insunits": insunits, "unidade_confirmada": unidade}, "unidade": "m",
         "niveis": [{"id": nivel, "cota_m": cota_m, "altura_m": altura_m}],
         "paredes": paredes, "aberturas": [], "pisos": [],
         "cortes": [{"id": c[0], "de": [float(c[1]), float(c[2])], "ate": [float(c[3]), float(c[4])]} for c in cortes]}
    if d["cortes"]:
        validar(d)
    return d


def calibrar(d, origem, referencia, distancia_m, y_para_cima=False, controle_px=None, controle_m=None):
    if d.get("unidade") != "px" or (d.get("fonte") or {}).get("tipo") not in {"pdf", "imagem"}:
        raise ValueError("calibrar aceita somente planta PDF/imagem transcrita em px")
    origem, referencia = ponto(origem, "origem"), ponto(referencia, "referencia")
    medida_px = distancia(origem, referencia)
    if medida_px < EPS:
        raise ValueError("referência de calibração tem comprimento zero")
    escala = numero(distancia_m, "distancia_m", True) / medida_px
    ux, uy = (referencia[0] - origem[0]) / medida_px, (referencia[1] - origem[1]) / medida_px
    def conv(pt):
        vx, vy = pt[0] - origem[0], pt[1] - origem[1]
        x = (vx * ux + vy * uy) * escala
        y = (-vx * uy + vy * ux) * escala if y_para_cima else (vx * uy - vy * ux) * escala
        return [round(x, 6), round(y, 6)]
    r = json.loads(json.dumps(d))
    for p in r.get("paredes") or []:
        p["de"], p["ate"] = conv(p["de"]), conv(p["ate"])
    for a in r.get("aberturas") or []:
        if "centro_px" in a:
            a["centro_m"] = round(numero(a.pop("centro_px"), f"abertura {a.get('id')}.centro_px") * escala, 6)
        if "largura_px" in a:
            a["largura_m"] = round(numero(a.pop("largura_px"), f"abertura {a.get('id')}.largura_px", True) * escala, 6)
    for p in r.get("pisos") or []:
        p["contorno"] = [conv(pt) for pt in p["contorno"]]
    for c in r.get("cortes") or []:
        c["de"], c["ate"] = conv(c["de"]), conv(c["ate"])
    r["unidade"] = "m"
    r["fonte"]["calibracao"] = {"origem_px": origem, "referencia_px": referencia,
                                 "distancia_m": distancia_m, "y_para_cima": y_para_cima,
                                 "m_por_px": escala}
    if (controle_px is None) != (controle_m is None):
        raise ValueError("controle: informe quatro coordenadas px e a segunda distância em metros")
    if controle_px is not None:
        a2, b2 = ponto(controle_px[:2], "controle_px.a"), ponto(controle_px[2:], "controle_px.b")
        esperado = numero(controle_m, "controle_m", True)
        observado = distancia(a2, b2) * escala
        desvio = abs(observado - esperado) / esperado
        r["fonte"]["calibracao"]["segunda_medida_conferida"] = {
            "pontos_px": [a2, b2], "esperado_m": esperado,
            "observado_m": round(observado, 6), "desvio_relativo": round(desvio, 6)}
        if desvio > .02:
            raise ValueError(f"segunda medida diverge {desvio:.1%} (> 2%); confira escala/traçado")
    validar(r)
    return r


def cruzamento(a, b, c, d):
    """Parâmetros t/u da interseção entre os segmentos a-b e c-d."""
    rx, ry = b[0] - a[0], b[1] - a[1]
    sx, sy = d[0] - c[0], d[1] - c[1]
    den = rx * sy - ry * sx
    if abs(den) < EPS:
        return None
    qx, qy = c[0] - a[0], c[1] - a[1]
    t, u = (qx * sy - qy * sx) / den, (qx * ry - qy * rx) / den
    if -EPS <= t <= 1 + EPS and -EPS <= u <= 1 + EPS:
        return t, u, abs(den) / (distancia(a, b) * distancia(c, d))
    return None


def _dentro(pt, pol):
    x, y = pt
    inside = False
    for a, b in zip(pol, pol[1:] + pol[:1]):
        if (a[1] > y) != (b[1] > y):
            cross_x = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x < cross_x:
                inside = not inside
    return inside


def _faixas_piso(a, b, pol):
    ts = [0.0, 1.0]
    for c, d in zip(pol, pol[1:] + pol[:1]):
        hit = cruzamento(a, b, c, d)
        if hit:
            ts.append(max(0.0, min(1.0, hit[0])))
    ts.sort()
    n = distancia(a, b)
    out = []
    for lo, hi in zip(ts, ts[1:]):
        if hi - lo < EPS:
            continue
        mid = (lo + hi) / 2
        if _dentro([a[0] + mid * (b[0] - a[0]), a[1] + mid * (b[1] - a[1])], pol):
            out.append((lo * n, hi * n))
    return out


def corte(d, linha, niveis, paredes):
    a, b = linha["de"], linha["ate"]
    compr = distancia(a, b)
    ent = []
    avisos = []
    def rect(x1, z1, x2, z2, layer):
        if x2 - x1 > EPS and z2 - z1 > EPS:
            ent.append({"t": "rect", "layer": layer, "p": [round(x1, 6), round(z1, 6), round(x2, 6), round(z2, 6)]})
    for n, (cota, _) in niveis.items():
        ent.append({"t": "line", "layer": "ARQ-NIVEL", "p": [0, cota, compr, cota]})
        ent.append({"t": "text", "layer": "ARQ-TEXTO", "p": [compr + .2, cota], "s": f"{n} {cota:+.2f} m", "h": .12})
    for p in paredes.values():
        hit = cruzamento(a, b, p["de"], p["ate"])
        if not hit:
            continue
        t, u, seno = hit
        if seno < .05:
            avisos.append(f"parede {p['id']}: corte quase paralelo; confira a espessura projetada")
        x = t * compr
        largura = min(p["espessura_m"] / max(seno, .05), 2 * p["espessura_m"])
        z, altura = niveis[p["nivel"]][0], p.get("altura_m", niveis[p["nivel"]][1])
        abertura = next((op for op in d.get("aberturas") or [] if op["parede"] == p["id"] and
                         abs(u * distancia(p["de"], p["ate"]) - op["centro_m"]) <= op["largura_m"] / 2 + EPS), None)
        if abertura:
            peitoril = abertura.get("peitoril_m", 0)
            rect(x - largura / 2, z, x + largura / 2, z + peitoril, "ARQ-PAREDE")
            rect(x - largura / 2, z + peitoril + abertura["altura_m"], x + largura / 2, z + altura, "ARQ-PAREDE")
            ent.append({"t": "text", "layer": "ARQ-TEXTO", "p": [x + largura / 2 + .05, z + peitoril + abertura["altura_m"] / 2],
                        "s": abertura["id"], "h": .1})
        else:
            rect(x - largura / 2, z, x + largura / 2, z + altura, "ARQ-PAREDE")
        ent.append({"t": "text", "layer": "ARQ-TEXTO", "p": [x - largura / 2, z + altura + .12], "s": p["id"], "h": .1})
    for piso in d.get("pisos") or []:
        z = niveis[piso["nivel"]][0]
        for x1, x2 in _faixas_piso(a, b, piso["contorno"]):
            rect(x1, z - piso["espessura_m"], x2, z, "ARQ-PISO")
    ent.append({"t": "text", "layer": "ARQ-TEXTO", "p": [0, max(c + h for c, h in niveis.values()) + .35],
                "s": f"CORTE {linha['id']} - REV {d['projeto']['revisao']}", "h": .18})
    if not any(e["layer"] in {"ARQ-PAREDE", "ARQ-PISO"} for e in ent):
        avisos.append("linha de corte não intercepta parede nem piso")
    return {"nome": linha["id"], "entidades": ent}, avisos


def revit(d, niveis):
    ops = [{"tool": "create_level", "args": {"data": [{"name": n, "elevation": c * 1000}
             for n, (c, _) in niveis.items()]}, "remover_niveis_existentes": True}]
    paredes = []
    for p in d["paredes"]:
        z, alt = niveis[p["nivel"]]
        paredes.append({"id_origem": p["id"], "category": "OST_Walls", "locationLine": {
            "p0": {"x": p["de"][0] * 1000, "y": p["de"][1] * 1000, "z": z * 1000},
            "p1": {"x": p["ate"][0] * 1000, "y": p["ate"][1] * 1000, "z": z * 1000}},
            "thickness": p["espessura_m"] * 1000, "height": p.get("altura_m", alt) * 1000,
            "baseLevel": z * 1000, "baseOffset": 0})
    ops.append({"tool": "create_line_based_element", "args": {"data": paredes},
                "salvar_ids_com": "id_origem", "antes_de_executar": "retire id_origem; confira tipo de parede e origem"})
    if d.get("pisos"):
        pisos = []
        for p in d["pisos"]:
            z = niveis[p["nivel"]][0] * 1000
            vs = p["contorno"]
            pisos.append({"id_origem": p["id"], "name": p["id"], "category": "OST_Floors", "thickness": p["espessura_m"] * 1000,
                         "baseLevel": z, "baseOffset": 0, "boundary": {"outerLoop": [{"p0": {"x": x * 1000, "y": y * 1000, "z": z},
                         "p1": {"x": xx * 1000, "y": yy * 1000, "z": z}}
                         for (x, y), (xx, yy) in zip(vs, vs[1:] + vs[:1])]}})
        ops.append({"tool": "create_surface_based_element", "args": {"data": pisos},
                    "salvar_ids_com": "id_origem", "antes_de_executar": "retire id_origem; confira tipo e espessura"})
    if d.get("aberturas"):
        ops.append({"tool": "get_available_family_types", "args": {"categoryList": ["OST_Doors", "OST_Windows"]}})
        ops.append({"tool": "create_point_based_element", "deps": ["ids das paredes", "typeId da família"],
                    "args": {"data": [{"id_origem": a["id"], "name": a["id"],
                        "typeId": "$tipo:" + a["id"], "hostWallId": "$parede:" + a["parede"],
                        "locationPoint": {"x": (p["de"][0] + (p["ate"][0] - p["de"][0]) * a["centro_m"] / distancia(p["de"], p["ate"])) * 1000,
                                          "y": (p["de"][1] + (p["ate"][1] - p["de"][1]) * a["centro_m"] / distancia(p["de"], p["ate"])) * 1000,
                                          "z": (niveis[p["nivel"]][0] + a.get("peitoril_m", 0)) * 1000},
                        "width": a["largura_m"] * 1000, "height": a["altura_m"] * 1000,
                        "baseLevel": niveis[p["nivel"]][0] * 1000, "baseOffset": a.get("peitoril_m", 0) * 1000}
                        for a in d["aberturas"] for p in d["paredes"] if p["id"] == a["parede"]]},
                    "antes_de_executar": "resolva typeId e hostWallId; retire id_origem; confira orientação e peitoril"})
    return ops


def archicad(d, niveis):
    ops = [{"tool": "list_instances"}, {"tool": "execute_read_api_command", "args": {"name": "GetStories", "params": {}}},
           {"tool": "describe_api_command", "args": {"name": "CreateWalls"}}]
    items = [{"id_origem": p["id"], "begCoordinate": {"x": p["de"][0], "y": p["de"][1]},
              "endCoordinate": {"x": p["ate"][0], "y": p["ate"][1]}, "floorIndex": "$pavimento:" + p["nivel"],
              "zCoordinate": 0, "height": p.get("altura_m", niveis[p["nivel"]][1]), "thickness": p["espessura_m"],
              "favoriteName": "$favorito:parede"} for p in d["paredes"]]
    ops.append({"tool": "execute_write_api_command", "args": {"name": "CreateWalls", "params": {"wallsData": items}, "confirm": False},
                "executar_apos_confirmacao": {"confirm": True},
                "antes_de_executar": "resolva floorIndex/favorito, retire id_origem e grave GUIDs das paredes"})
    if d.get("pisos"):
        ops.append({"tool": "describe_api_command", "args": {"name": "CreateSlabs"}})
        ops.append({"tool": "execute_write_api_command", "args": {"name": "CreateSlabs", "params": {"slabsData": [
            {"id_origem": p["id"], "favoriteName": "$favorito:piso-basic", "level": niveis[p["nivel"]][0],
             "floorIndex": "$pavimento:" + p["nivel"], "thickness": p["espessura_m"],
             "referencePlaneLocation": "Top", "polygonCoordinates": [{"x": x, "y": y} for x, y in p["contorno"]]}
            for p in d["pisos"]]}, "confirm": False}, "executar_apos_confirmacao": {"confirm": True},
            "antes_de_executar": "use favorito Basic; resolva floorIndex, retire id_origem; confira espessura após criar"})
    for kind in ("porta", "janela"):
        group = [a for a in d.get("aberturas") or [] if a["tipo"] == kind]
        if not group:
            continue
        command = "CreateDoors" if kind == "porta" else "CreateWindows"
        ops.append({"tool": "describe_api_command", "args": {"name": command}})
        ops.append({"tool": "execute_write_api_command", "args": {"name": command,
            "params": {"doorsData" if kind == "porta" else "windowsData": [
                {"id_origem": a["id"], "ownerWallId": {"guid": "$parede:" + a["parede"]},
                 "centerOffset": a["centro_m"] - distancia(p["de"], p["ate"]) / 2, "sillHeight": a.get("peitoril_m", 0),
                 "width": a["largura_m"], "height": a["altura_m"],
                 "favoriteName": "$favorito:" + kind} for a in group for p in d["paredes"] if p["id"] == a["parede"]]}, "confirm": False},
            "executar_apos_confirmacao": {"confirm": True},
            "antes_de_executar": "resolva GUID/favorito; retire id_origem; confira posição, lado, biblioteca e abertura real"})
    return ops


def gerar(d, pasta, origem_dir=None):
    niveis, paredes = validar(d)
    pasta.mkdir(parents=True, exist_ok=True)
    cad = _cad()
    layers = [("ARQ-PAREDE", 1), ("ARQ-PISO", 2), ("ARQ-NIVEL", 8), ("ARQ-TEXTO", 7)]
    saidas = []
    avisos = []
    for linha in d["cortes"]:
        g, warning = corte(d, linha, niveis, paredes)
        file = pasta / ("corte-" + "".join(c if c.isalnum() or c in "-_" else "-" for c in linha["id"]) + ".dxf")
        file.write_text(cad.para_dxf([g], layers, 6), encoding="cp1252", errors="replace")
        saidas.append({"corte": linha["id"], "dxf": str(file)})
        avisos += [f"{linha['id']}: {w}" for w in warning]
    fonte_nome = d["fonte"].get("arquivo")
    fonte_path = Path(fonte_nome) if fonte_nome else None
    if fonte_path is not None and not fonte_path.is_absolute() and origem_dir is not None:
        fonte_path = origem_dir / fonte_path
    sha = hashlib.sha256(fonte_path.read_bytes()).hexdigest() if fonte_path is not None and fonte_path.is_file() else None
    if fonte_nome and sha is None:
        avisos.append("arquivo de origem não encontrado; SHA-256 da fonte pendente")
    if d["fonte"]["tipo"] in {"pdf", "imagem"} and not d["fonte"]["calibracao"].get("segunda_medida_conferida"):
        avisos.append("segunda medida independente da calibração ainda não registrada")
    digest = hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    planos = {"projeto": d["projeto"], "sha256_modelo": digest, "revit": revit(d, niveis), "archicad": archicad(d, niveis),
              "estado": "prévia; não executar sem conferir planta, famílias/favoritos, níveis e lote"}
    (pasta / "planos-bim.json").write_text(json.dumps(planos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifesto = {"projeto": d["projeto"], "fonte": d["fonte"], "sha256_fonte": sha,
                 "sha256_modelo": digest, "cortes": saidas, "planos_bim": str(pasta / "planos-bim.json"),
                 "avisos": avisos, "estado": "geometria de apoio; revisar cortes no CAD e elementos no BIM"}
    (pasta / "manifesto-arquitetura.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifesto


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="comando", required=True)
    cal = sub.add_parser("calibrar", help="converter pontos transcritos de PDF/imagem de px para m")
    cal.add_argument("entrada", type=Path)
    cal.add_argument("--origem-px", nargs=2, type=float, required=True)
    cal.add_argument("--referencia-px", nargs=2, type=float, required=True)
    cal.add_argument("--distancia-m", type=float, required=True)
    cal.add_argument("--y-para-cima", action="store_true")
    cal.add_argument("--controle-px", nargs=4, type=float)
    cal.add_argument("--controle-distancia-m", type=float)
    cal.add_argument("--saida", type=Path, required=True)
    ext = sub.add_parser("extrair-dxf", help="extrair eixos de parede de um layer DXF ASCII")
    ext.add_argument("entrada", type=Path)
    ext.add_argument("--layer", required=True)
    ext.add_argument("--unidade", choices=("mm", "cm", "m"), required=True)
    ext.add_argument("--projeto", required=True)
    ext.add_argument("--revisao", required=True)
    ext.add_argument("--nivel", required=True)
    ext.add_argument("--cota-m", type=float, required=True)
    ext.add_argument("--altura-m", type=float, required=True)
    ext.add_argument("--espessura-m", type=float, required=True)
    ext.add_argument("--corte", nargs=5, action="append", default=[], metavar=("ID", "X1", "Y1", "X2", "Y2"))
    ext.add_argument("--saida", type=Path, required=True)
    for name in ("validar", "gerar"):
        p = sub.add_parser(name)
        p.add_argument("entrada", type=Path)
        if name == "gerar":
            p.add_argument("--saida", type=Path, required=True)
    args = ap.parse_args()
    if args.comando == "extrair-dxf":
        result = extrair_dxf(args.entrada, args.layer, args.unidade, args.projeto, args.revisao,
                            args.nivel, args.cota_m, args.altura_m, args.espessura_m, args.corte)
        args.saida.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"saida": str(args.saida), "paredes": len(result["paredes"]),
                          "cortes": len(result["cortes"]), "pendencia": "conferir paredes e informar aberturas/pisos"}, ensure_ascii=False))
        return
    d = json.loads(args.entrada.read_text(encoding="utf-8"))
    if args.comando == "calibrar":
        result = calibrar(d, args.origem_px, args.referencia_px, args.distancia_m,
                         args.y_para_cima, args.controle_px, args.controle_distancia_m)
        args.saida.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"saida": str(args.saida)}, ensure_ascii=False))
    elif args.comando == "validar":
        validar(d)
        print(json.dumps({"estado": "válido", "paredes": len(d["paredes"]), "cortes": len(d["cortes"])}, ensure_ascii=False))
    else:
        print(json.dumps(gerar(d, args.saida, args.entrada.parent), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
