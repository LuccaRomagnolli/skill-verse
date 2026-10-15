#!/usr/bin/env python3
"""Diagnóstico do ambiente para automatizar o TQS por Python (rode SEMPRE antes dos outros scripts).

Verifica: sistema, versão e arquitetura (32/64 bits) do Python, instalação do TQS (pasta TQSW), wheel
TQSPythonInterface, quais módulos TQS.* importam, versão da interface e a pasta raiz dos edifícios.
Com --introspectar, lista as classes, métodos e constantes REALMENTE disponíveis na versão instalada,
para o agente usar os nomes certos (a API muda entre versões do TQS).

Uso:
  python scripts/tqs_ambiente.py
  python scripts/tqs_ambiente.py --introspectar TQSModel --saida api-tqsmodel.json
"""
from __future__ import annotations

import argparse
import glob
import importlib
import inspect
import os
import platform
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tqs_comum import MODULOS, emitir  # noqa: E402

PASTAS_TQSW = ["C:/TQSW", "D:/TQSW", "E:/TQSW"]


def achar_tqsw() -> list[str]:
    cands = [os.environ.get("TQSW", "")] + PASTAS_TQSW + glob.glob("C:/Program Files*/TQS*/TQSW")
    return [c for c in dict.fromkeys(cands) if c and Path(c).is_dir()]


def achar_wheels(tqsw: list[str]) -> list[str]:
    return sorted({w for t in tqsw for w in glob.glob(f"{t}/EXEC/Python/TQSPythonInterface-*.whl")})


def testar_modulos() -> dict:
    res = {}
    for m in MODULOS:
        try:
            importlib.import_module(f"TQS.{m}")
            res[m] = "ok"
        except Exception as e:  # noqa: BLE001
            res[m] = f"{type(e).__name__}: {e}"[:200]
    return res


def versao_interface() -> str | None:
    try:
        from importlib.metadata import version
        return version("TQSPythonInterface")
    except Exception:  # noqa: BLE001
        return None


def diagnostico() -> dict:
    so = platform.system()
    bits = struct.calcsize("P") * 8
    d = {"so": so, "python": platform.python_version(), "bits": bits, "executavel": sys.executable}
    recs = []
    if so != "Windows":
        d["modulos"] = {}
        recs.append("A API Python do TQS só funciona no Windows com o TQS instalado. Aqui dá para preparar "
                    "scripts e conferir JSONs exportados, mas não para ler ou processar edifícios.")
        d["recomendacoes"] = recs
        return d
    tqsw = achar_tqsw()
    wheels = achar_wheels(tqsw)
    mods = testar_modulos()
    d.update({"tqsw": tqsw, "wheels": wheels, "modulos": mods, "interface": versao_interface()})
    if not tqsw:
        recs.append("Pasta TQSW não encontrada em C:/, D:/ ou E:/. Pergunte ao usuário onde o TQS está instalado "
                    "e defina a variável de ambiente TQSW com esse caminho.")
    if all(v != "ok" for v in mods.values()):
        if wheels:
            recs.append(f'Instale a interface neste Python: "{sys.executable}" -m pip install "{wheels[-1]}" '
                        "(peça permissão ao usuário).")
        erros = " ".join(mods.values())
        if "DLL" in erros or "%1" in erros or "WinError 193" in erros:
            outro = "32" if bits == 64 else "64"
            recs.append(f"Erro de DLL: a arquitetura do Python ({bits} bits) não bate com a do TQS. A documentação "
                        f"do TQS pede Python 32 bits (o TQSModel do V25 é 64 bits). Tente um Python {outro} bits "
                        f"(ex.: 'py -3-{outro}').")
    elif mods.get("TQSModel") != "ok":
        recs.append("TQSModel indisponível nesta versão/arquitetura: leitura de pilares/vigas/lajes não funciona; "
                    "TQSBuild (dados do edifício) e TQSExec (processamento) podem funcionar.")
    if mods.get("TQSBuild") == "ok":
        try:
            from TQS import TQSBuild
            d["raiz_edificios"] = TQSBuild.BuildingRoot()
            d["contexto_atual"] = TQSBuild.BuildingContext()
        except Exception as e:  # noqa: BLE001
            d["raiz_edificios"] = f"erro: {e}"
    d["recomendacoes"] = recs or ["Ambiente pronto."]
    return d


def introspectar(nome: str) -> dict:
    mod = importlib.import_module(f"TQS.{nome}")
    out = {"modulo": nome, "constantes": {}, "funcoes": [], "classes": {}}
    for k in sorted(dir(mod)):
        if k.startswith("_"):
            continue
        v = getattr(mod, k)
        if inspect.isclass(v):
            out["classes"][k] = sorted(m for m in dir(v) if not m.startswith("_"))
        elif callable(v):
            out["funcoes"].append(k)
        elif isinstance(v, (int, float, str)) and k.isupper():
            out["constantes"][k] = v
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--introspectar", choices=MODULOS, help="lista a API real de um módulo instalado")
    ap.add_argument("--saida")
    a = ap.parse_args(argv)
    if a.introspectar:
        try:
            emitir(introspectar(a.introspectar), a.saida)
        except Exception as e:  # noqa: BLE001
            emitir({"ok": False, "erro": f"{type(e).__name__}: {e}"}, a.saida)
            return 2
        return 0
    emitir(diagnostico(), a.saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
