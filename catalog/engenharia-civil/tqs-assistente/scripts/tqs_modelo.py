#!/usr/bin/env python3
"""Modelo estrutural do TQS (módulo TQSModel): listar pilares, vigas e lajes por planta e converter para o
formato de lançamento da skill revit-assistente.

  listar     --edificio NOME [--saida modelo.json]        lê o modelo (só leitura; não salva nada)
  para-revit --modelo modelo.json --edificio-json ed.json  gera lancamento.json para revit-assistente
             [--saida lancamento.json]                     (ed.json = saída de tqs_edificio.py ler)

Coordenadas do Modelador em cm; o lançamento do Revit usa m (posições) e cm (seções).
Limitações da conversão (avisadas no resultado): lajes não têm contorno exposto pela API (use o IFC do TQS para
o modelo completo); plantas repetidas geram só o primeiro piso; pilares não retangulares são listados mas não
convertidos; posição por canto de inserção é aproximada quando não há poligonal da seção.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tqs_comum import emitir, falhar, importar, principal, valor  # noqa: E402


def ident(obj, attr: str) -> dict:
    i = valor(obj, attr)
    return {"numero": valor(i, "objectNumber"), "titulo": valor(i, "objectTitle") or ""}


def poligono(pol) -> list[list[float]]:
    n = int(valor(pol, "NumPts", 0) or 0)
    pts = []
    for k in range(n):
        try:
            x, y = pol.GetPt(k)
            pts.append([float(x), float(y)])
        except Exception:  # noqa: BLE001
            break
    return pts


def centroide(pts: list[list[float]]) -> tuple[float, float] | None:
    if len(pts) < 3:
        return None
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        c = x1 * y2 - x2 * y1
        a += c
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
    if abs(a) < 1e-12:
        return None
    return cx / (3 * a), cy / (3 * a)


def ler_pilar(TQSModel, sec) -> dict:
    geo = valor(sec, "columnGeometry")
    tipos = {getattr(TQSModel, k): k.replace("COLUMNTYPE_", "") for k in dir(TQSModel) if k.startswith("COLUMNTYPE_")}
    col = valor(sec, "column")
    ins = valor(sec, "columnInsertion")
    return {**ident(col, "columnIdent"),
            "tipo_secao": tipos.get(valor(geo, "sectionType"), valor(geo, "sectionType")),
            "b1_cm": valor(geo, "sectionB1"), "h1_cm": valor(geo, "sectionH1"),
            "angulo_graus": valor(geo, "sectionAngle", 0.0),
            "insercao_cm": [valor(sec, "insertionX"), valor(sec, "insertionY")],
            "insercao_por": "canto" if valor(ins, "insertionType") == 1 else "centro",
            "poligono_cm": poligono(valor(sec, "sectionPolig"))}


def ler_viga(beam) -> dict:
    n = int(valor(beam, "NumNodes", 0) or 0)
    nos, trechos = [], []
    for k in range(n):
        no = beam.GetBeamNode(k)
        nos.append([valor(no, "nodeX"), valor(no, "nodeY")])
    for k in range(max(0, n - 1)):
        g = beam.GetSegmentBeamGeometry(k)
        trechos.append({"de": k, "ate": k + 1, "b_cm": valor(g, "width"), "h_cm": valor(g, "depth")})
    return {**ident(beam, "beamIdent"), "nos_cm": nos, "trechos": trechos}


def ler_laje(slab) -> dict:
    g = valor(slab, "slabGeometry")
    return {**ident(slab, "slabIdent"), "h_cm": valor(g, "thickness"), "angulo_principal": valor(slab, "mainAngle")}


def listar(TQSBuild, TQSModel, nome: str) -> dict:
    b = TQSBuild.Building()
    entrar = getattr(b, "RootFolder", None) or b.file.RootFolder
    if entrar(nome) != 0:
        raise FileNotFoundError(f"edifício '{nome}' não existe na árvore do TQS")
    model = TQSModel.Model()
    if model.file.OpenModel() != 0:
        raise FileNotFoundError(f"não abri o modelo estrutural de '{nome}'")
    plantas = []
    try:
        fl = model.floors
        for i in range(1, int(fl.GetNumFloors()) + 1):
            nome_pl = fl.GetFloorName(i)
            floor = fl.GetFloor(nome_pl)
            it = floor.iterator
            dados = {"indice": i, "nome": str(nome_pl).strip(), "pilares": [], "vigas": [], "lajes": [], "erros": []}
            for tipo, chave, fn in ((TQSModel.TYPE_SECPIL, "pilares", lambda o: ler_pilar(TQSModel, o)),
                                    (TQSModel.TYPE_VIGAS, "vigas", ler_viga),
                                    (TQSModel.TYPE_LAJES, "lajes", ler_laje)):
                for k in range(int(it.GetNumObjects(tipo))):
                    o = it.GetObject(tipo, k)
                    if o is None:
                        continue
                    try:
                        dados[chave].append(fn(o))
                    except Exception as e:  # noqa: BLE001
                        dados["erros"].append(f"{chave}[{k}]: {type(e).__name__}: {e}")
            plantas.append(dados)
    finally:
        try:
            model.file.Close()
        except Exception:  # noqa: BLE001
            pass
    return {"edificio": nome, "plantas": plantas}


# ------------------------------------------------------------------ conversão (lógica pura, testada)

def nome_peca(prefixo: str, d: dict) -> str:
    return d.get("titulo") or f"{prefixo}{d.get('numero')}"


def para_revit(modelo: dict, edificio: dict) -> dict:
    info = {p["nome"].strip(): p for p in edificio.get("plantas", [])}
    avisos, niveis, pilares, vigas = [], [], [], []
    ordem = [p["nome"].strip() for p in modelo.get("plantas", [])]
    for nome in ordem:
        if nome not in info:
            avisos.append(f"planta '{nome}' do modelo não está nos dados do edifício: sem cota")
            continue
        niveis.append({"nome": nome, "cota_m": info[nome]["cota_m"]})
        if (info[nome].get("repeticoes") or 1) > 1:
            avisos.append(f"planta '{nome}' repete {info[nome]['repeticoes']}×: só o primeiro piso foi gerado")
    cotas = {n["nome"]: n["cota_m"] for n in niveis}
    for i, pl in enumerate(modelo.get("plantas", [])):
        nome = pl["nome"].strip()
        if nome not in cotas:
            continue
        abaixo = ordem[i - 1] if i > 0 else None
        for p in pl.get("pilares", []):
            if abaixo is None or abaixo not in cotas:
                continue  # planta mais baixa: os pilares nascem aqui
            if p.get("tipo_secao") not in ("R", None) or not p.get("b1_cm") or not p.get("h1_cm"):
                avisos.append(f"{nome_peca('P', p)} em '{nome}': seção {p.get('tipo_secao')} não convertida")
                continue
            c = centroide(p.get("poligono_cm") or [])
            if c is None:
                c = tuple(p["insercao_cm"])
                if p.get("insercao_por") == "canto":
                    avisos.append(f"{nome_peca('P', p)} em '{nome}': inserção por canto, posição aproximada")
            pilares.append({"nome": nome_peca("P", p), "x_m": round(c[0] / 100, 4), "y_m": round(c[1] / 100, 4),
                            "b_cm": p["b1_cm"], "h_cm": p["h1_cm"], "rot_graus": p.get("angulo_graus") or 0,
                            "base": abaixo, "topo": nome})
        for v in pl.get("vigas", []):
            nos = v.get("nos_cm") or []
            for t in v.get("trechos", []):
                a, b = nos[t["de"]], nos[t["ate"]]
                if not t.get("b_cm") or not t.get("h_cm") or a == b:
                    continue
                vigas.append({"nome": nome_peca("V", v), "de": [a[0] / 100, a[1] / 100], "ate": [b[0] / 100, b[1] / 100],
                              "b_cm": t["b_cm"], "h_cm": t["h_cm"], "nivel": nome})
        if pl.get("lajes"):
            avisos.append(f"'{nome}': {len(pl['lajes'])} laje(s) não convertidas (contorno não exposto pela API); "
                          "use o IFC do TQS ou desenhe no Revit")
    return {"niveis": niveis, "eixos": {}, "pilares": pilares, "vigas": vigas, "lajes": [], "avisos": avisos,
            "origem": f"TQS: {modelo.get('edificio')}"}


@principal
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("acao", choices=["listar", "para-revit"])
    ap.add_argument("--edificio")
    ap.add_argument("--modelo", help="para-revit: JSON de 'listar'")
    ap.add_argument("--edificio-json", help="para-revit: JSON de 'tqs_edificio.py ler'")
    ap.add_argument("--saida")
    a = ap.parse_args(argv)
    if a.acao == "para-revit":
        if not (a.modelo and a.edificio_json):
            ap.error("para-revit: informe --modelo e --edificio-json")
        ler = lambda f: json.loads(Path(f).read_text(encoding="utf-8"))  # noqa: E731
        emitir(para_revit(ler(a.modelo), ler(a.edificio_json)), a.saida)
        return 0
    if not a.edificio:
        ap.error("listar: informe --edificio")
    TQSBuild, TQSModel = importar("TQSBuild", "TQSModel")
    try:
        emitir(listar(TQSBuild, TQSModel, a.edificio), a.saida)
    except FileNotFoundError as e:
        return falhar(str(e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
