#!/usr/bin/env python3
"""Lint do catálogo de skills, dos MCPs e dos packs.

Uso: python3 tools/validate.py [--strict]
Sai com código 1 se houver erro (ou aviso, com --strict).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
MCPS = ROOT / "mcps"
PACKS = ROOT / "packs"
INSTALLER = ROOT / "installer"

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
        if str(data.get("licenca", "")).upper() in ("", "DESCONHECIDA", "?"):
            rep.err(f, "licença do upstream não verificada — não pode ser vendido")
        found.add(d.name)
    return found


PACK_REQUIRED = ("id", "nome", "version", "publico", "descricao", "skills")


def check_packs(rep: Report, skills: dict[str, Path], known_mcps: set[str]) -> None:
    for d in sorted(p for p in PACKS.iterdir() if p.is_dir()):
        f = d / "pack.yaml"
        if not f.is_file():
            rep.err(d, "falta pack.yaml")
            continue
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for k in PACK_REQUIRED:
            if k not in data:
                rep.err(f, f"falta '{k}'")
        if data.get("id") != d.name:
            rep.err(f, f"'id' deve ser '{d.name}'")
        if not SEMVER_RE.match(str(data.get("version", ""))):
            rep.err(f, "'version' deve ser semver")
        for s in data.get("skills") or []:
            if s not in skills:
                rep.err(f, f"skill '{s}' não existe em catalog/")
        for m in data.get("mcps") or []:
            if m.get("nome") not in known_mcps:
                rep.err(f, f"MCP '{m.get('nome')}' não existe em mcps/")
        # MCPs exigidos pelas skills precisam estar no pack
        pack_mcps = {m.get("nome") for m in data.get("mcps") or []}
        for s in data.get("skills") or []:
            sy = skills.get(s, Path()) / "skill.yaml"
            if sy.is_file():
                need = set((yaml.safe_load(sy.read_text(encoding="utf-8")) or {}).get("mcps") or [])
                for m in need - pack_mcps:
                    rep.err(f, f"skill '{s}' precisa do MCP '{m}', que não está no pack")
        for req in ("manual.template.md", "CHANGELOG.md"):
            if not (d / req).is_file():
                rep.err(d, f"falta {req}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true", help="avisos também reprovam")
    args = ap.parse_args()

    rep = Report()
    known_mcps = check_mcps(rep)
    skills = check_catalog(rep, known_mcps)
    check_packs(rep, skills, known_mcps)
    check_skill_md(INSTALLER / "instalar-pack", rep, require_limits=False)

    for line in rep.errors + rep.warnings:
        print(line)
    print(f"\n{len(skills)} skills, {len(known_mcps)} MCPs — {len(rep.errors)} erro(s), {len(rep.warnings)} aviso(s)")
    failed = bool(rep.errors) or (args.strict and bool(rep.warnings))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
