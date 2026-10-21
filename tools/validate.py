#!/usr/bin/env python3
"""Lint das skills, MCPs e do catálogo modular Engcode.

Uso: python3 tools/validate.py [--strict]
Sai com código 1 se houver erro (ou aviso, com --strict).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
MCPS = ROOT / "mcps"
MANIFEST = ROOT / "engcode" / "catalog.json"
SITE_MANIFEST = ROOT / "website" / "public" / "catalog.json"

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
# Caminhos relativos citados no corpo: `scripts/x.py`, (references/y.md), etc.
REL_PATH_RE = re.compile(r"[`(]((?:scripts|references|assets|templates)/[\w./-]+?)[`)]")
MAX_BODY_LINES = 500
MAX_DESC = 1024


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where: Path | str, msg: str) -> None:
        self.errors.append(f"ERRO  {_rel(where)}: {msg}")

    def warn(self, where: Path | str, msg: str) -> None:
        self.warnings.append(f"AVISO {_rel(where)}: {msg}")


def _rel(p: Path | str) -> str:
    try:
        return str(Path(p).relative_to(ROOT))
    except ValueError:
        return str(p)


def parse_skill_md(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md precisa começar com frontmatter YAML (---)")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("frontmatter sem fechamento (---)")
    meta = yaml.safe_load(text[4:end]) or {}
    body = text[end + 4 :].lstrip("\n")
    return meta, body


def check_skill_md(skill_dir: Path, rep: Report, require_limits: bool = True) -> dict | None:
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        rep.err(skill_dir, "falta SKILL.md")
        return None
    try:
        meta, body = parse_skill_md(md)
    except (ValueError, yaml.YAMLError) as e:
        rep.err(md, str(e))
        return None

    name = meta.get("name")
    desc = meta.get("description")
    if not name:
        rep.err(md, "frontmatter sem 'name'")
    elif name != skill_dir.name:
        rep.err(md, f"name '{name}' difere da pasta '{skill_dir.name}'")
    elif not NAME_RE.match(name) or len(name) > 64:
        rep.err(md, f"name '{name}' deve ser kebab-case com até 64 caracteres")

    if not desc or not isinstance(desc, str):
        rep.err(md, "frontmatter sem 'description'")
    else:
        if len(desc) > MAX_DESC:
            rep.err(md, f"description com {len(desc)} caracteres (máx. {MAX_DESC})")
        if "use quando" not in desc.lower():
            rep.err(md, "description precisa dizer QUANDO usar (inclua 'Use quando …')")

    n_lines = body.count("\n") + 1
    if n_lines > MAX_BODY_LINES:
        rep.err(md, f"corpo com {n_lines} linhas (máx. {MAX_BODY_LINES}); mova detalhes para references/")

    if require_limits and "## Limites e responsabilidade" not in body:
        rep.err(md, "falta a seção '## Limites e responsabilidade'")

    for rel in sorted(set(REL_PATH_RE.findall(body))):
        if not (skill_dir / rel).exists():
            rep.err(md, f"cita '{rel}', que não existe na pasta da skill")

    for py in skill_dir.rglob("*.py"):
        try:
            compile(py.read_text(encoding="utf-8"), str(py), "exec")
        except SyntaxError as e:
            rep.err(py, f"não compila: {e}")

    for bad in skill_dir.rglob("*"):
        if "__pycache__" in bad.parts:
            continue
        if bad.is_file() and re.search(r"/Users/|C:\\\\Users\\\\", bad.read_text(errors="ignore")):
            rep.warn(bad, "contém caminho absoluto de máquina local")
    return meta


def check_catalog(rep: Report, known_mcps: set[str]) -> dict[str, Path]:
    """Retorna {'categoria/skill': caminho}."""
    skills: dict[str, Path] = {}
    names: dict[str, str] = {}
    for cat_dir in sorted(p for p in CATALOG.iterdir() if p.is_dir()):
        for skill_dir in sorted(p for p in cat_dir.iterdir() if p.is_dir()):
            key = f"{cat_dir.name}/{skill_dir.name}"
            skills[key] = skill_dir
            if skill_dir.name in names:
                rep.err(skill_dir, f"nome duplicado com {names[skill_dir.name]} (nomes são globais)")
            names[skill_dir.name] = key

            check_skill_md(skill_dir, rep)

            sy = skill_dir / "skill.yaml"
            if not sy.is_file():
                rep.err(skill_dir, "falta skill.yaml")
                continue
            data = yaml.safe_load(sy.read_text(encoding="utf-8")) or {}
            if not SEMVER_RE.match(str(data.get("version", ""))):
                rep.err(sy, "'version' deve ser semver (ex.: 1.0.0)")
            if data.get("categoria") != cat_dir.name:
                rep.err(sy, f"'categoria' deve ser '{cat_dir.name}'")
            if not data.get("titulo"):
                rep.err(sy, "falta 'titulo' (nome legível da skill, usado no manual)")
            if not data.get("resumo"):
                rep.err(sy, "falta 'resumo' (uma linha, usada no manual)")
            exemplos = data.get("exemplos") or []
            if len(exemplos) < 3:
                rep.err(sy, "inclua pelo menos 3 'exemplos' de pedido (vão para o manual)")
            for m in data.get("mcps") or []:
                if m not in known_mcps:
                    rep.err(sy, f"MCP '{m}' não existe em mcps/")
    return skills


MCP_REQUIRED = ("nome", "titulo", "licenca", "upstream", "versao_fixada", "requisitos", "servidor", "teste")
FERRAMENTAS = {"uv", "node"}
PREPARO = ("copiar_da_skill", "baixar_zip", "extrair_zip", "comando")


def check_mcps(rep: Report) -> set[str]:
    found: set[str] = set()
    for d in sorted(p for p in MCPS.iterdir() if p.is_dir()):
        f = d / "mcp.yaml"
        if not f.is_file():
            rep.err(d, "falta mcp.yaml")
            continue
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for k in MCP_REQUIRED:
            if k not in data:
                rep.err(f, f"falta '{k}'")
        if data.get("nome") != d.name:
            rep.err(f, f"'nome' deve ser '{d.name}'")
        srv = data.get("servidor") or {}
        if "command" not in srv:
            rep.err(f, "servidor.command obrigatório")
        if data.get("upstream") == "interno":
            srv_dir = d / "servidor"
            if not srv_dir.is_dir():
                rep.err(f, "MCP interno precisa da pasta servidor/ com o código")
            for py in srv_dir.rglob("*.py") if srv_dir.is_dir() else []:
                try:
                    compile(py.read_text(encoding="utf-8"), str(py), "exec")
                except SyntaxError as e:
                    rep.err(py, f"não compila: {e}")
            if "{ENGCODE_MCP_DIR}" not in str(data.get("servidor")):
                rep.err(f, "MCP interno deve referenciar o código via {ENGCODE_MCP_DIR}")
        if str(data.get("licenca", "")).upper() in ("", "DESCONHECIDA", "?"):
            rep.err(f, "licença do upstream não verificada — não pode ser vendido")
        for t in (data.get("requisitos") or {}).get("ferramentas") or []:
            if t not in FERRAMENTAS:
                rep.err(f, f"ferramenta '{t}' desconhecida pelo instalador (use {', '.join(sorted(FERRAMENTAS))})")
        for step in data.get("preparo") or []:
            tipo = [k for k in PREPARO if k in step]
            if len(tipo) != 1:
                rep.err(f, f"passo de preparo inválido {step!r} (use um de {', '.join(PREPARO)})")
            elif tipo[0] in ("baixar_zip", "extrair_zip", "copiar_da_skill") and "destino" not in step:
                rep.err(f, f"passo '{tipo[0]}' sem 'destino'")
            elif tipo[0] == "extrair_zip" and "{VERSAO}" in str(step) and not step.get("versoes"):
                rep.err(f, "extrair_zip por versão precisa da lista 'versoes' suportadas")
        found.add(d.name)
    return found


def check_manifest(rep: Report, skills: dict[str, Path], known_mcps: set[str]) -> None:
    try:
        items = json.loads(MANIFEST.read_text(encoding="utf-8"))
        site_items = json.loads(SITE_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        rep.err(MANIFEST, f"catálogo JSON inválido: {exc}")
        return
    if items != site_items:
        rep.err(SITE_MANIFEST, "catálogo do site diverge de engcode/catalog.json")
    ids: set[str] = set()
    for item in items:
        id_ = item.get("id")
        typ = item.get("type")
        if id_ in ids:
            rep.err(MANIFEST, f"ID duplicado: {id_}")
        ids.add(id_)
        if typ == "skill":
            if not any(path.name == id_ for path in skills.values()):
                rep.err(MANIFEST, f"skill ausente: {id_}")
            if not (ROOT / str(item.get("path", "")) / "SKILL.md").is_file():
                rep.err(MANIFEST, f"caminho de skill inválido: {id_}")
            for mcp in item.get("requires", []):
                if mcp not in known_mcps:
                    rep.err(MANIFEST, f"{id_} requer MCP ausente: {mcp}")
        elif typ == "mcp":
            if id_ not in known_mcps:
                rep.err(MANIFEST, f"MCP ausente: {id_}")
        else:
            rep.err(MANIFEST, f"tipo inválido para {id_}: {typ}")
    for path in skills.values():
        if path.name not in ids:
            rep.err(MANIFEST, f"skill não publicada: {path.name}")
    for id_ in known_mcps - ids:
        rep.err(MANIFEST, f"MCP não publicado: {id_}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true", help="avisos também reprovam")
    args = ap.parse_args()

    rep = Report()
    known_mcps = check_mcps(rep)
    skills = check_catalog(rep, known_mcps)
    check_manifest(rep, skills, known_mcps)

    for line in rep.errors + rep.warnings:
        print(line)
    print(f"\n{len(skills)} skills, {len(known_mcps)} MCPs — {len(rep.errors)} erro(s), {len(rep.warnings)} aviso(s)")
    failed = bool(rep.errors) or (args.strict and bool(rep.warnings))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
