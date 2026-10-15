#!/usr/bin/env python3
"""Processamento global e tarefas do Gerenciador TQS (módulo TQSExec), para um ou vários edifícios.

Por padrão só MOSTRA o plano (simulação). Executa com --executar, depois do "sim" do usuário. O TQS abre o
Gerenciador, processa e fecha; pode levar de minutos a horas.

Presets do processamento global (TaskGlobalProc):
  esforcos  modelos de grelha e pórtico + análise e transferência de esforços (sem desenhos)
  completo  esforcos + desenho de formas, lajes (esforços e desenho), vigas e pilares (dimensionamento,
            detalhamento e desenho), fundações e escadas
Ajuste fino com --param nome=valor (nomes da TaskGlobalProc: floorPlan, floorDraw, slabs, beams, columnsData,
columns, columnsReport, gridModel, gridDraw, gridExtr, gridAnalysis, gridBeamsTrnsf, gridSlabsTrnsf,
gridNonLinear, frameModel, frameAnalysis, frameBeamsTrnsf, frameColumnsTrnsf, foundations, stairs, fire,
precastPhases).

Exemplos:
  python scripts/tqs_processar.py --edificios "Residencial X" --preset completo --tabela-ferros
  python scripts/tqs_processar.py --edificios "Ed-C25,Ed-C30" --preset esforcos --executar
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tqs_comum import emitir, importar, principal  # noqa: E402

PARAMS = ["floorPlan", "floorDraw", "slabs", "beams", "columnsData", "columns", "columnsReport", "gridModel",
          "gridDraw", "gridExtr", "gridAnalysis", "gridBeamsTrnsf", "gridSlabsTrnsf", "gridNonLinear", "frameModel",
          "frameAnalysis", "frameBeamsTrnsf", "frameColumnsTrnsf", "foundations", "stairs", "fire", "precastPhases"]
PRESETS = {
    # valores-padrão da TaskGlobalProc: extrai e processa plantas, esforços de vigas, grelha e pórtico completos
    "esforcos": {},
    "completo": {"floorDraw": 1, "slabs": 2, "beams": 3, "columns": 2, "foundations": 1, "stairs": 1},
}


def montar_plano(edificios: list[str], preset: str, extras: dict, tabela_ferros: bool, planta_cargas: bool) -> list[dict]:
    params = {**PRESETS[preset], **extras}
    desconhecidos = set(params) - set(PARAMS)
    if desconhecidos:
        raise ValueError(f"parâmetros desconhecidos: {', '.join(sorted(desconhecidos))}")
    plano = []
    for ed in edificios:
        plano.append({"tarefa": "TaskFolder", "args": [ed, "FOLDER_FRAMES"]})
        plano.append({"tarefa": "TaskGlobalProc", "kwargs": params})
        if planta_cargas:
            plano.append({"tarefa": "TaskLoadsReport"})
        if tabela_ferros:
            plano.append({"tarefa": "TaskRebarSchedule"})
    return plano


def executar(TQSExec, plano: list[dict]) -> float:
    job = TQSExec.Job()
    for t in plano:
        if t["tarefa"] == "TaskFolder":
            ed, pasta = t["args"]
            job.EnterTask(TQSExec.TaskFolder(ed, getattr(TQSExec.TaskFolder, pasta)))
        else:
            job.EnterTask(getattr(TQSExec, t["tarefa"])(**t.get("kwargs", {})))
    t0 = time.time()
    job.Execute()
    return round(time.time() - t0, 1)


def parse_param(s: str) -> tuple[str, int]:
    k, v = s.split("=", 1)
    return k.strip(), int(v)


@principal
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--edificios", required=True, help="nomes separados por vírgula")
    ap.add_argument("--preset", choices=list(PRESETS), default="esforcos")
    ap.add_argument("--param", action="append", default=[], type=parse_param, help="ajuste: nome=valor")
    ap.add_argument("--tabela-ferros", action="store_true", help="tabela única de ferros na pasta GERAIS")
    ap.add_argument("--planta-cargas", action="store_true", help="planta de cargas (últimas combinações)")
    ap.add_argument("--executar", action="store_true", help="executa de fato (padrão: só mostra o plano)")
    ap.add_argument("--saida")
    a = ap.parse_args(argv)
    eds = [e.strip() for e in a.edificios.split(",") if e.strip()]
    try:
        plano = montar_plano(eds, a.preset, dict(a.param), a.tabela_ferros, a.planta_cargas)
    except ValueError as e:
        ap.error(str(e))
    if not a.executar:
        emitir({"simulacao": True, "edificios": eds, "plano": plano,
                "aviso": "Feche o edifício no TQS antes de executar. Rode de novo com --executar após o 'sim'."}, a.saida)
        return 0
    TQSExec = importar("TQSExec")
    seg = executar(TQSExec, plano)
    emitir({"ok": True, "edificios": eds, "duracao_s": seg,
            "proximo_passo": "abra o edifício no TQS e revise os avisos/erros do processamento (relatórios do "
                             "Gerenciador) antes de usar qualquer resultado"}, a.saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
