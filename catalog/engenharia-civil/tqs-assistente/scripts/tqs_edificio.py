#!/usr/bin/env python3
"""Dados do edifício TQS (módulo TQSBuild): ler, conferir com a NBR 6118 e aplicar alterações numa cópia.

  ler       --edificio NOME [--saida f.json]   pisos/plantas (nome, classe, altura, repetição, cota), materiais,
                                               cobrimentos, modelo estrutural e coeficientes dos carregamentos
  conferir  --edificio NOME | --json f.json    CAA × fck mínimo (NBR 6118:2023, Tab. 7.1) e cobrimentos mínimos
            [--contexto projeto-contexto.json]  (Tab. 7.2), comparando com a ficha do projeto, se houver
  aplicar   --edificio NOME --dados alt.json --salvar-como NOVO   grava alterações num edifício NOVO (cópia).
            Com --sobrescrever no lugar de --salvar-como, altera o original (só com "sim" do usuário).

alt.json: {"materials": {"beamConcreteStrength": "C30"}, "covers": {"beamCover": 3.0}, "project": {...}, "model": {...}}
Unidades do TQS: cotas e alturas de piso em m; cobrimentos em cm; cargas em tf (1 tf = 9,80665 kN).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tqs_comum import (CAA_ROMANO, constantes, cotas_das_plantas, emitir, falhar, fck, importar,  # noqa: E402
                       ler_ficha, principal, valor)

PROJECT = ["projectTitle", "clientTitle", "projectAddress", "projectNumber", "projectDescription", "structureType",
           "concreteCode", "masonryCode", "codeStrictUse", "floorHeight", "country"]
MODEL = ["structuralModel", "expansionJoints", "secondOrderEfect", "structuralDynamicsAnalysis",
         "soilStructureInteraction", "incrementalAnalysis"]
MATERIALS = ["environmentalClass", "dryClimate", "qualityControl", "beamConcreteStrength", "columnConcreteStrength",
             "foundationConcreteStrength", "columnConcreteVariantions"]
COVERS = ["beamCover", "columnCover", "foundationCover", "foundationSecCover", "slabLowerCover", "slabUpperCover",
          "slabSecLowerCover", "slabSecUpperCover", "prestressedSlabLowerCover", "prestressedSlabUpperCover",
          "beamAndSlabSoilCover", "columnSoilCover"]
EDITAVEIS = {"project": PROJECT, "model": MODEL, "materials": MATERIALS, "covers": COVERS}
PREFIXOS = ["PP", "PERM", "ACID", "VENT", "DESA", "EMPU", "TEMP", "RETR", "ADIC"]
CAMPOS_CARGA = ["titulo", "ipermacid", "ivigtrans", "ireduzida", "imulaxi", "gamaf", "igamafd", "gamafd",
                "psi0", "psi1", "psi2", "ipavimento", "numcasos", "istat"]

# NBR 6118:2023 — síntese numérica das tabelas (concreto armado)
FCK_MIN = {"I": 20, "II": 25, "III": 30, "IV": 40}                      # Tab. 7.1, classe mínima
COB_MIN_CM = {                                                          # Tab. 7.2, cobrimento nominal (Δc = 10 mm)
    "laje": {"I": 2.0, "II": 2.5, "III": 3.5, "IV": 4.5},
    "viga_pilar": {"I": 2.5, "II": 3.0, "III": 4.0, "IV": 5.0},
    "solo": {"I": 3.0, "II": 3.0, "III": 4.0, "IV": 5.0},
}
GRUPO_COBRIMENTO = {"slabLowerCover": "laje", "slabUpperCover": "laje", "beamCover": "viga_pilar",
                    "columnCover": "viga_pilar", "foundationCover": "solo", "beamAndSlabSoilCover": "solo",
                    "columnSoilCover": "solo"}


# ------------------------------------------------------------------ leitura

def abrir(TQSBuild, nome: str):
    b = TQSBuild.Building()
    if b.file.Open(nome) != 0:
        raise FileNotFoundError(f"edifício '{nome}' não encontrado/aberto pelo TQS")
    return b


def ler(TQSBuild, b) -> dict:
    out = {sec: {k: valor(getattr(b, sec), k) for k in campos} for sec, campos in EDITAVEIS.items()}
    caa = out["materials"].get("environmentalClass")
    if isinstance(caa, int) and 0 <= caa <= 3:
        out["materials"]["caa"] = CAA_ROMANO[caa]
    classes = constantes(TQSBuild, "ICL")
    fp = b.floorsplan
    n = int(valor(fp, "floorsPlanNumber", 0) or 0)
    plantas = []
    for i in range(n):
        plantas.append({"indice": i, "nome": fp.GetName(i), "titulo": fp.GetTitle(i),
                        "classe": classes.get(fp.GetClass(i), fp.GetClass(i)),
                        "altura_m": fp.GetFloorHeight(i), "repeticoes": fp.GetRepetition(i)})
    cotas = cotas_das_plantas(float(out["project"].get("floorHeight") or 0.0),
                              [float(p["altura_m"] or 0) for p in plantas], [p["repeticoes"] for p in plantas])
    for p, c in zip(plantas, cotas):
        p["cota_m"] = c
    out["plantas"] = plantas
    cargas = {}
    for pre in PREFIXOS:
        const = getattr(TQSBuild, "PREFIXO" + pre, None)
        if const is None:
            continue
        try:
            r = b.loads.GetLoad(const)
            r = r if isinstance(r, (list, tuple)) else [r]
            cargas[pre] = dict(zip(CAMPOS_CARGA, r))
        except Exception as e:  # noqa: BLE001
            cargas[pre] = {"erro": str(e)}
    out["carregamentos"] = cargas
    return out


# ------------------------------------------------------------------ conferência (lógica pura)

def conferir(dados: dict, ficha: dict | None = None) -> dict:
    mat, cov = dados.get("materials", {}), dados.get("covers", {})
    itens = []
    caa = mat.get("caa")
    if caa is None and isinstance(mat.get("environmentalClass"), int):
        caa = CAA_ROMANO[mat["environmentalClass"]]
    caa_ficha = ((ficha or {}).get("caa") or {}).get("classe")
    if caa_ficha and caa and caa_ficha != caa:
        itens.append({"item": "CAA", "status": "ALERTA",
                      "msg": f"TQS em CAA {caa}, ficha do projeto em CAA {caa_ficha}. Confirme qual vale."})
    caa_ref = caa_ficha or caa
    if not caa_ref:
        return {"caa": None, "itens": [{"item": "CAA", "status": "PENDENTE", "msg": "CAA não definida"}]}
    minimo = FCK_MIN[caa_ref]
    for campo, rot in (("beamConcreteStrength", "vigas/lajes"), ("columnConcreteStrength", "pilares"),
                       ("foundationConcreteStrength", "fundações")):
        f = fck(mat.get(campo))
        if f is None:
            itens.append({"item": f"fck {rot}", "status": "PENDENTE", "msg": f"valor não lido: {mat.get(campo)!r}"})
        else:
            ok = f >= minimo
            itens.append({"item": f"fck {rot}", "status": "OK" if ok else "ALERTA",
                          "msg": f"C{f:g} {'≥' if ok else '<'} C{minimo} (mínimo para CAA {caa_ref}, NBR 6118:2023 Tab. 7.1)"})
    reducao = 0.5 if mat.get("qualityControl") == 1 else 0.0  # Δc = 5 mm com controle rigoroso de execução
    for campo, grupo in GRUPO_COBRIMENTO.items():
        v = cov.get(campo)
        if not isinstance(v, (int, float)) or v <= 0:
            continue
        req = round(COB_MIN_CM[grupo][caa_ref] - reducao, 2)
        ok = v + 1e-9 >= req
        itens.append({"item": f"cobrimento {campo}", "status": "OK" if ok else "ALERTA",
                      "msg": f"{v:g} cm {'≥' if ok else '<'} {req:g} cm (CAA {caa_ref}, NBR 6118:2023 Tab. 7.2"
                             + (", Δc = 5 mm" if reducao else "") + ")"})
    norma = dados.get("project", {}).get("concreteCode")
    return {"caa": caa_ref, "norma_concreto_tqs": norma, "itens": itens,
            "resumo": {s: sum(1 for i in itens if i["status"] == s) for s in ("OK", "ALERTA", "PENDENTE")}}


# ------------------------------------------------------------------ aplicação

def aplicar(b, alteracoes: dict) -> list[dict]:
    feitas = []
    for sec, campos in alteracoes.items():
        if sec not in EDITAVEIS:
            raise ValueError(f"seção '{sec}' não editável (use {', '.join(EDITAVEIS)})")
        obj = getattr(b, sec)
        for k, v in campos.items():
            if k not in EDITAVEIS[sec]:
                raise ValueError(f"campo '{sec}.{k}' fora da lista permitida")
            antes = valor(obj, k)
            setattr(obj, k, v)
            feitas.append({"campo": f"{sec}.{k}", "antes": antes, "depois": v})
    return feitas


@principal
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("acao", choices=["ler", "conferir", "aplicar"])
    ap.add_argument("--edificio")
    ap.add_argument("--json", help="conferir: usa um JSON salvo por 'ler' (funciona fora do Windows)")
    ap.add_argument("--contexto", default="projeto-contexto.json")
    ap.add_argument("--dados", help="aplicar: JSON com as alterações")
    ap.add_argument("--salvar-como", help="aplicar: nome do edifício NOVO (cópia)")
    ap.add_argument("--sobrescrever", action="store_true", help="aplicar: grava no original")
    ap.add_argument("--saida")
    a = ap.parse_args(argv)

    if a.acao == "conferir" and a.json:
        emitir(conferir(json.loads(Path(a.json).read_text(encoding="utf-8")), ler_ficha(a.contexto)), a.saida)
        return 0
    if not a.edificio:
        ap.error("informe --edificio")
    TQSBuild = importar("TQSBuild")
    try:
        b = abrir(TQSBuild, a.edificio)
    except FileNotFoundError as e:
        return falhar(str(e))
    if a.acao == "ler":
        emitir({"edificio": a.edificio, **ler(TQSBuild, b)}, a.saida)
    elif a.acao == "conferir":
        emitir(conferir(ler(TQSBuild, b), ler_ficha(a.contexto)), a.saida)
    else:
        if not a.dados or not (a.salvar_como or a.sobrescrever):
            ap.error("aplicar: informe --dados e --salvar-como NOVO (ou --sobrescrever)")
        feitas = aplicar(b, json.loads(Path(a.dados).read_text(encoding="utf-8")))
        b.file.SuppressMessages(1)
        st = b.file.SaveAs(a.salvar_como) if a.salvar_como else b.file.Save()
        if st != 0:
            return falhar(f"o TQS não gravou o edifício (código {st})")
        emitir({"ok": True, "gravado_em": a.salvar_como or a.edificio, "alteracoes": feitas,
                "proximo_passo": "abra o edifício no TQS e confira no Editor de Dados do Edifício antes de processar"},
               a.saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
