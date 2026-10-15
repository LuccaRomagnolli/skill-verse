"""Funções comuns aos scripts do TQS (API Python oficial: pacote `TQS`, wheel TQSPythonInterface).

A API só existe no Windows com o TQS instalado. Tudo aqui importa o TQS de forma preguiçosa e falha com
mensagem clara; a lógica pura (cotas, conferências, conversões) funciona em qualquer sistema e tem testes.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

MODULOS = ["TQSUtil", "TQSGeo", "TQSDwg", "TQSJan", "TQSEag", "TQSBuild", "TQSGrid", "TQSExec", "TQSModel"]
CAA_ROMANO = ["I", "II", "III", "IV"]  # TQSBuild: environmentalClass 0..3


class SemTQS(RuntimeError):
    pass


def importar(*nomes: str):
    """Importa TQS.<nome> e devolve os módulos na ordem pedida."""
    mods = []
    for n in nomes:
        try:
            mods.append(importlib.import_module(f"TQS.{n}"))
        except Exception as e:  # noqa: BLE001 — ImportError, OSError de DLL etc.
            raise SemTQS(
                f"Não consegui importar TQS.{n} ({type(e).__name__}: {e}). Rode 'python scripts/tqs_ambiente.py' "
                "para diagnosticar (Windows + TQS V23 ou mais novo + wheel TQSPythonInterface instalado neste Python)."
            ) from e
    return mods if len(mods) > 1 else mods[0]


def valor(obj, nome: str, padrao=None):
    """Lê atributo da API tolerando diferenças de versão (atributo ou método sem argumentos)."""
    try:
        v = getattr(obj, nome)
    except Exception:  # noqa: BLE001
        return padrao
    if callable(v):
        try:
            v = v()
        except Exception:  # noqa: BLE001
            return padrao
    return v


def constantes(modulo, prefixo: str) -> dict[int, str]:
    """{valor: nome} das constantes do módulo que começam com `prefixo` (ex.: ICL → classes de planta)."""
    out = {}
    for k in dir(modulo):
        if k.startswith(prefixo):
            v = getattr(modulo, k)
            if isinstance(v, int):
                out[v] = k[len(prefixo):]
    return out


def cotas_das_plantas(cota_inicial: float, alturas: list[float], repeticoes: list[int]) -> list[float]:
    """Cota do PRIMEIRO piso de cada planta (m). A altura de uma planta é a diferença para a planta de baixo;
    uma planta repetida r vezes ocupa r pisos de mesma altura."""
    cotas: list[float] = []
    for i, h in enumerate(alturas):
        if i == 0:
            cotas.append(round(cota_inicial, 4))
        else:
            r_ant = max(1, int(repeticoes[i - 1] or 1))
            cotas.append(round(cotas[-1] + (r_ant - 1) * alturas[i - 1] + h, 4))
    return cotas


def fck(classe) -> float | None:
    """'C25' → 25.0; 25 → 25.0; None se não reconhecer."""
    if classe is None:
        return None
    if isinstance(classe, (int, float)):
        return float(classe)
    s = str(classe).strip().upper().lstrip("C")
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def ler_ficha(caminho: str | None) -> dict:
    f = Path(caminho) if caminho else None
    if f and f.is_file():
        return json.loads(f.read_text(encoding="utf-8"))
    return {}


def emitir(dados, saida: str | None = None) -> None:
    txt = json.dumps(dados, indent=1, ensure_ascii=False, default=str)
    if saida:
        Path(saida).write_text(txt, encoding="utf-8")
        print(json.dumps({"saida": saida}, ensure_ascii=False))
    else:
        print(txt)


def falhar(msg: str, codigo: int = 2) -> int:
    print(json.dumps({"ok": False, "erro": msg}, ensure_ascii=False))
    return codigo


def principal(fn):
    """Decorador de main(): converte SemTQS em JSON de erro em vez de traceback."""
    def wrapper(argv=None):
        try:
            return fn(argv)
        except SemTQS as e:
            return falhar(str(e))
    return wrapper


if __name__ == "__main__":
    sys.exit(falhar("módulo auxiliar; use os outros scripts"))
