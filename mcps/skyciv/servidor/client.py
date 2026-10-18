"""Cliente SkyCiv v3. Sem import do MCP para permitir testes isolados."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

API_URL = "https://api.skyciv.com/v3"


def _modelo_module():
    p = Path(__file__).resolve()
    roots = [p.parents[3], p.parents[2]]  # repositório e ZIP instalado
    for root in roots:
        candidate = root / "catalog/engenharia-civil/modelo-estrutural/scripts/modelo.py"
        if not candidate.is_file():
            candidate = root / "plugin/skills/modelo-estrutural/scripts/modelo.py"
        if candidate.is_file():
            spec = importlib.util.spec_from_file_location("skillverse_modelo_estrutural", candidate)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise RuntimeError("modelo-estrutural não encontrado no pack")


def _json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def preparar(caminho: str) -> tuple[Path, dict, dict]:
    p = Path(caminho).expanduser().resolve(strict=True)
    if p.suffix.lower() != ".json":
        raise ValueError("modelo deve ser JSON")
    d = json.loads(p.read_text(encoding="utf-8"))
    m = _modelo_module()
    s3d = m.para_skyciv(d)
    if d.get("mapa_acoes"):
        mapa_path = p.parent / d["mapa_acoes"]
        mapa = json.loads(mapa_path.read_text(encoding="utf-8"))
        s3d["conferencia_mapa"] = m.conferir_mapa(d, mapa)
        s3d["sha256_mapa"] = m.digest(mapa)
    elif d["acoes"]:
        raise ValueError("informe mapa_acoes e mapa_ref em cada ação antes do envio")
    return p, d, s3d


def credenciais() -> tuple[str, str]:
    user = os.environ.get("SKYCIV_USERNAME", "").strip()
    key = os.environ.get("SKYCIV_API_KEY", "").strip()
    if not user or not key:
        raise ValueError("configure SKYCIV_USERNAME e SKYCIV_API_KEY no ambiente do cliente MCP")
    return user, key


def plano_requisicao(s3d: dict, user: str, key: str, gerar_relatorio: bool) -> dict:
    funcs = [
        {"function": "S3D.session.start", "arguments": {"keep_open": False}},
        {"function": "S3D.model.set", "arguments": {"s3d_model": s3d["modelo"]}},
    ]
    if s3d["modelo"]["plates"]:
        funcs.append({"function": "S3D.model.mesh", "arguments": {"method": "frontal_quads", "granularity": 2}})
    funcs.extend([
        {"function": "S3D.model.solve", "arguments": {"analysis_type": "linear", "repair_model": False}},
        {"function": "S3D.results.get", "arguments": {"format": "json", "include_nodal_displacements": True,
            "result_filter": ["reactions", "member_forces", "member_peak_results", "member_displacements", "plate_forces", "plate_displacements"]}},
    ])
    if gerar_relatorio:
        funcs.append({"function": "S3D.results.getAnalysisReport", "arguments": {
            "job_name": f"{s3d['projeto']['id']}-{s3d['projeto']['revisao']}", "file_type": "pdf",
            "load_combinations": "all", "sections": {"title_page": True, "job_setup": True,
                "nodal_reactions": True, "nodal_displacements": True, "member_forces": True,
                "member_displacements": True, "plate_element_forces": True, "plate_displacements": True}}})
    return {"auth": {"username": user, "key": key}, "options": {"validate_input": True, "response_data_only": False,
            "return_base64_image_on_error": False}, "functions": funcs}


def enviar(payload: dict) -> dict:
    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            body = response.read(50_000_001)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("resposta da SkyCiv incerta; a análise pode ter consumido crédito. Consulte a atividade da conta antes de tentar novamente") from exc
    if len(body) > 50_000_000:
        raise RuntimeError("resposta da SkyCiv excede 50 MB; consulte a atividade da conta antes de repetir")
    try:
        parsed = json.loads(body)
    except ValueError as exc:
        raise RuntimeError("resposta SkyCiv inválida; consulte a atividade da conta antes de repetir") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("resposta SkyCiv inesperada; consulte a atividade da conta antes de repetir")
    return parsed


def limpar(obj, segredos=()):
    if isinstance(obj, dict):
        return {k: limpar(v, segredos) for k, v in obj.items() if k.lower() not in {"auth", "key", "api_key", "session_id", "last_session_id"}}
    if isinstance(obj, list):
        return [limpar(v, segredos) for v in obj]
    if isinstance(obj, str):
        for segredo in segredos:
            if segredo:
                obj = obj.replace(segredo, "[REDACTED]")
    return obj


def conferir_resposta(res: dict, nomes: list[str]) -> list[dict]:
    if not isinstance(res, dict) or not isinstance(res.get("response"), dict):
        raise ValueError("envelope de resposta SkyCiv inválido")
    funcoes = res.get("functions")
    if not isinstance(funcoes, list) or len(funcoes) != len(nomes):
        raise ValueError("resposta SkyCiv sem resultado individual de cada função")
    for i, (f, esperado) in enumerate(zip(funcoes, nomes)):
        item = f.get("response", f) if isinstance(f, dict) else {}
        if not isinstance(item, dict) or item.get("function", esperado) != esperado or item.get("status") != 0:
            raise ValueError(f"SkyCiv {esperado} falhou na etapa {i + 1}; confira resposta.json")
    if res["response"].get("status") != 0:
        raise ValueError("SkyCiv informou falha; confira resposta.json")
    return [f.get("response", f) for f in funcoes]


def baixar_relatorio(url: str, destino: Path) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "solver.skyciv.com" or not parsed.path.startswith("/temp/"):
        raise ValueError("URL do relatório fora do domínio SkyCiv esperado")
    with urllib.request.urlopen(url, timeout=60) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != "solver.skyciv.com":
            raise ValueError("redirecionamento do relatório fora do domínio SkyCiv")
        pdf = response.read(20_000_001)
    if len(pdf) > 20_000_000 or not pdf.startswith(b"%PDF-"):
        raise ValueError("relatório não é PDF válido ou excede 20 MB")
    destino.write_bytes(pdf)
    return str(destino)


def analisar(caminho: str, confirmar_envio: bool = False, gerar_relatorio: bool = True) -> dict:
    p, _, s3d = preparar(caminho)
    if not confirmar_envio:
        return {"ok": False, "requer_confirmacao": True, "projeto": s3d["projeto"],
                "sha256_entrada": s3d["sha256_entrada"], "pecas": len(s3d["ids"]["pecas"]) + len(s3d["ids"]["placas"]),
                "aviso": "Enviar modelo à SkyCiv usa a conta do cliente e pode consumir crédito. Confirme o modelo e a revisão antes de repetir com confirmar_envio=true."}
    user, key = credenciais()
    payload = plano_requisicao(s3d, user, key, gerar_relatorio)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    nome = re.sub(r"[^A-Za-z0-9_-]+", "-", s3d["projeto"]["id"] + "-" + s3d["projeto"]["revisao"])[:80]
    pasta = p.parent / "resultados" / f"skyciv-{nome}-{stamp}"
    pasta.mkdir(parents=True, exist_ok=False)
    _json(pasta / "modelo-s3d.json", s3d)
    try:
        resposta = enviar(payload)
    except RuntimeError as exc:
        _json(pasta / "falha.json", {"estado": "incerto", "mensagem": str(exc), "sha256_entrada": s3d["sha256_entrada"]})
        return {"ok": False, "estado": "incerto", "pasta": str(pasta), "aviso": str(exc)}
    limpa = limpar(resposta, (user, key))
    _json(pasta / "resposta.json", limpa)
    nomes = [f["function"] for f in payload["functions"]]
    aviso_relatorio = None
    try:
        funcoes = conferir_resposta(resposta, nomes)
    except ValueError as exc:
        try:
            if not gerar_relatorio:
                raise exc
            base = {"response": {"status": 0}, "functions": resposta["functions"][:-1]}
            funcoes = conferir_resposta(base, nomes[:-1]) + [{}]
            aviso_relatorio = "Relatório SkyCiv falhou; análise e resultados foram preservados. Confira resposta.json"
        except (ValueError, KeyError, TypeError):
            _json(pasta / "falha.json", {"estado": "falha_api", "mensagem": str(exc), "sha256_entrada": s3d["sha256_entrada"]})
            cabecalho = resposta.get("response")
            return {"ok": False, "estado": "falha_api", "pasta": str(pasta), "aviso": str(exc),
                    "creditos": cabecalho.get("monthly_api_credits") if isinstance(cabecalho, dict) else None}
    idx = nomes.index("S3D.results.get")
    resultados = limpar(funcoes[idx].get("data"), (user, key))
    if not isinstance(resultados, dict):
        _json(pasta / "falha.json", {"estado": "falha_api", "mensagem": "resultados vazios ou inválidos", "sha256_entrada": s3d["sha256_entrada"]})
        return {"ok": False, "estado": "falha_api", "pasta": str(pasta), "aviso": "resultados vazios ou inválidos"}
    _json(pasta / "resultados.json", resultados)
    relatorio = None
    if gerar_relatorio and aviso_relatorio is None:
        dados_relatorio = funcoes[nomes.index("S3D.results.getAnalysisReport")].get("data")
        link = dados_relatorio.get("download_link") if isinstance(dados_relatorio, dict) else None
        if link:
            try:
                relatorio = baixar_relatorio(link, pasta / "relatorio.pdf")
            except (ValueError, urllib.error.URLError, TimeoutError) as exc:
                aviso_relatorio = f"PDF não baixado: {exc}; o link permanece em resposta.json"
        else:
            aviso_relatorio = "SkyCiv não devolveu link do relatório"
    manifesto = {"estado": "analisado", "projeto": s3d["projeto"], "sha256_entrada": s3d["sha256_entrada"],
                 "sha256_mapa": s3d.get("sha256_mapa"), "conferencia_mapa": s3d.get("conferencia_mapa"),
                 "analise": "linear", "ids": s3d["ids"], "creditos": resposta["response"].get("monthly_api_credits"),
                 "resultados": str(pasta / "resultados.json"), "relatorio": relatorio, "aviso_relatorio": aviso_relatorio,
                 "revisao_tecnica": "pendente"}
    _json(pasta / "manifesto.json", manifesto)
    return {"ok": True, "manifesto": str(pasta / "manifesto.json"), "pasta": str(pasta),
            "creditos": manifesto["creditos"], "relatorio": relatorio, "aviso_relatorio": aviso_relatorio,
            "revisao_tecnica": "pendente"}
