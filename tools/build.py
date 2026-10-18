#!/usr/bin/env python3
"""Monta o .zip vendável de um pack.

Uso: python3 tools/build.py <pack-id> [--sem-validar] [--manter-pasta]
Saída: dist/skillverse-<pack>-v<versão>.zip (e dist/build/<mesmo nome>/ com --manter-pasta)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import ROOT, CATALOG, MCPS, PACKS, INSTALLER, parse_skill_md  # noqa: E402

DIST = ROOT / "dist"
BUNDLE = INSTALLER / "bundle"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "skill.yaml")


def load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def resolve(pack_id: str) -> tuple[dict, dict[str, Path]]:
    pdir = PACKS / pack_id
    pk = load_yaml(pdir / "pack.yaml")
    skills, sources = [], {}
    for key in pk["skills"]:
        sdir = CATALOG / key
        meta, _ = parse_skill_md(sdir / "SKILL.md")
        sy = load_yaml(sdir / "skill.yaml")
        skills.append({"name": meta["name"], "titulo": sy["titulo"], "resumo": sy["resumo"],
                       "exemplos": sy["exemplos"], "mcps": sy.get("mcps") or [], "version": sy["version"]})
        sources[meta["name"]] = sdir
    mcps = []
    for entry in pk.get("mcps") or []:
        m = load_yaml(MCPS / entry["nome"] / "mcp.yaml")
        m["opcional"] = entry.get("opcional", True)
        mcps.append(m)
    pack = {
        "id": pk["id"], "nome": pk["nome"], "version": pk["version"], "publico": pk["publico"],
        "descricao": pk["descricao"], "marketplace": f"skillverse-{pk['id']}",
        "skills": skills, "mcps": mcps, "fluxos": pk.get("fluxos") or [],
    }
    return pack, sources


def render(text: str, pack: dict) -> str:
    lista = "\n".join(f"- **{s['titulo']}** — {s['resumo']}" for s in pack["skills"])
    softwares = "\n".join(f"- {m['titulo']} ({m['requisitos']['software']})" for m in pack["mcps"]) or "- nenhum"
    for k, v in {"PACK_NOME": pack["nome"], "PACK_ID": pack["id"], "VERSAO": pack["version"],
                 "LISTA_SKILLS": lista, "LISTA_SOFTWARES": softwares, "PUBLICO": pack["publico"]}.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def build(pack_id: str, keep: bool) -> Path:
    pack, sources = resolve(pack_id)
    name = f"skillverse-{pack['id']}-v{pack['version']}"
    stage = DIST / "build" / name
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    # Plugin (Claude Code) + pasta de skills (Codex usa a mesma)
    plugin = stage / "plugin"
    for sname, sdir in sources.items():
        shutil.copytree(sdir, plugin / "skills" / sname, ignore=IGNORE)
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": pack["id"], "displayName": pack["nome"], "version": pack["version"],
        "description": pack["descricao"], "author": {"name": "Skill-Verse"},
        "license": "LicenseRef-SkillVerse-Comercial", "keywords": ["skillverse", pack["id"]],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (stage / ".claude-plugin").mkdir()
    (stage / ".claude-plugin" / "marketplace.json").write_text(json.dumps({
        "name": pack["marketplace"], "description": f"Skill-Verse — {pack['nome']}",
        "owner": {"name": "Skill-Verse"},
        "plugins": [{"name": pack["id"], "source": "./plugin", "description": pack["descricao"]}],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # MCPs próprios (código em mcps/<nome>/servidor/)
    for m in pack["mcps"]:
        srv_dir = MCPS / m["nome"] / "servidor"
        if srv_dir.is_dir():
            shutil.copytree(srv_dir, stage / "mcps" / m["nome"], ignore=IGNORE)

    # Instalador
    shutil.copytree(INSTALLER / "instalar-pack", stage / "instalador", ignore=IGNORE)

    # Metadados e textos
    (stage / "pack.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    pdir = PACKS / pack_id
    shutil.copy2(pdir / "manual.template.md", stage / "manual.template.md")
    shutil.copy2(pdir / "CHANGELOG.md", stage / "CHANGELOG.md")
    for evidencia in sorted(pdir.glob("VALIDACAO-*.md")):
        shutil.copy2(evidencia, stage / evidencia.name)
    shutil.copy2(ROOT / "LICENSE-COMERCIAL.md", stage / "LICENCA.md")
    for f in sorted(BUNDLE.iterdir()):
        (stage / f.name).write_text(render(f.read_text(encoding="utf-8"), pack), encoding="utf-8")

    claude = shutil.which("claude") or os.environ.get("CLAUDE_CODE_EXECPATH")
    if claude:
        for alvo in (stage, stage / "plugin"):
            r = subprocess.run([claude, "plugin", "validate", "--strict", str(alvo)], capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stdout.strip() or r.stderr.strip())
                sys.exit("claude plugin validate falhou")
        print("✔ claude plugin validate (marketplace + plugin)")
    else:
        print("! CLI do Claude Code não encontrada — pulei 'claude plugin validate'")

    DIST.mkdir(exist_ok=True)
    out = DIST / f"{name}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(stage.rglob("*")):
            if p.is_file():
                info = zipfile.ZipInfo(str(Path(name) / p.relative_to(stage)), date_time=(2026, 1, 1, 0, 0, 0))
                info.external_attr = (0o755 if p.suffix == ".py" else 0o644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, p.read_bytes())
    if not keep:
        shutil.rmtree(stage)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pack")
    ap.add_argument("--sem-validar", action="store_true")
    ap.add_argument("--manter-pasta", action="store_true")
    a = ap.parse_args()
    if not (PACKS / a.pack / "pack.yaml").is_file():
        sys.exit(f"pack '{a.pack}' não existe em packs/")
    if not a.sem_validar:
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "validate.py")])
        if r.returncode != 0:
            sys.exit("validação falhou — corrija antes de gerar o pack")
    out = build(a.pack, a.manter_pasta)
    print(f"\n✔ {out.relative_to(ROOT)} ({out.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
