"""Testes do build e do instalador (Codex, sem rede; Claude Code fica para o teste manual de ponta a ponta)."""
import json
import os
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "installer/instalar-pack/scripts"))
import install  # noqa: E402


@pytest.fixture(scope="module")
def pacote(tmp_path_factory):
    subprocess.run([sys.executable, str(ROOT / "tools/build.py"), "engenharia-civil", "--sem-validar"],
                   check=True, capture_output=True, env={**os.environ, "PATH": "/usr/bin:/bin", "CLAUDE_CODE_EXECPATH": ""})
    zips = sorted((ROOT / "dist").glob("skillverse-engenharia-civil-v*.zip"))
    dest = tmp_path_factory.mktemp("dl")
    with zipfile.ZipFile(zips[-1]) as z:
        z.extractall(dest)
    return next(dest.iterdir())


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SKILLVERSE_HOME", str(tmp_path / "SkillVerse"))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / ".claude"))
    return tmp_path


def cli(pacote, *args):
    env = {**os.environ, "PATH": "/usr/bin:/bin", "CLAUDE_CODE_EXECPATH": "", "SKILLVERSE_CLAUDE_BIN": ""}
    return subprocess.run([sys.executable, str(pacote / "instalador/scripts/install.py"), *args],
                          capture_output=True, text=True, env=env)


def test_estrutura_do_zip(pacote):
    for f in ("COMECE-AQUI.txt", "INSTALAR.md", "CLAUDE.md", "AGENTS.md", "LICENCA.md", "pack.json",
              ".claude-plugin/marketplace.json", "plugin/.claude-plugin/plugin.json", "instalador/SKILL.md"):
        assert (pacote / f).is_file(), f
    pack = json.loads((pacote / "pack.json").read_text(encoding="utf-8"))
    assert len(pack["skills"]) == 8
    assert (pacote / "mcps/normas-publicas/server.py").is_file()   # código do MCP próprio vai no zip
    assert not list(pacote.rglob("*.db")) and not list(pacote.rglob("pdf/*.pdf"))  # documentos não vão
    mk = json.loads((pacote / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    assert mk["plugins"][0]["name"] == json.loads((pacote / "plugin/.claude-plugin/plugin.json").read_text())["name"]
    assert not list(pacote.rglob("skill.yaml")), "metadados internos não devem ir no zip"
    assert "{{" not in (pacote / "INSTALAR.md").read_text(encoding="utf-8")


def test_ciclo_codex(pacote, home):
    r = cli(pacote, "instalar", "--plataforma", "codex")
    assert r.returncode == 0, r.stderr
    skills = home / ".codex/skills"
    assert (skills / "concreto-armado-nbr6118/SKILL.md").is_file()
    assert json.loads((skills / "concreto-armado-nbr6118/.skillverse.json").read_text())["pack"] == "engenharia-civil"
    assert (home / "SkillVerse/packs/engenharia-civil/pack.json").is_file()

    r = cli(pacote, "verificar", "--sem-mcp")
    assert r.returncode == 0 and json.loads(r.stdout)["ok"]

    r = cli(pacote, "manual")
    assert r.returncode == 0, r.stderr
    md = (home / "SkillVerse/engenharia-civil/MANUAL.md").read_text(encoding="utf-8")
    assert "Codex `$concreto-armado-nbr6118`" in md and "{{" not in md
    assert "<table>" in (home / "SkillVerse/engenharia-civil/MANUAL.html").read_text(encoding="utf-8")

    r = cli(pacote, "desinstalar")
    assert r.returncode == 0
    assert not (skills / "concreto-armado-nbr6118").exists()
    assert not (home / "SkillVerse/packs").exists()


def test_nao_sobrescreve_skill_alheia(pacote, home):
    alheia = home / ".codex/skills/relatorio-tecnico"
    alheia.mkdir(parents=True)
    (alheia / "SKILL.md").write_text("minha skill")
    r = cli(pacote, "instalar", "--plataforma", "codex")
    assert "não é deste pack" in r.stdout
    assert (alheia / "SKILL.md").read_text() == "minha skill"
    cli(pacote, "desinstalar")
    assert (alheia / "SKILL.md").read_text() == "minha skill"


def test_toml_codex_preserva_usuario(home):
    cfg = home / ".codex/config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text('model = "gpt-5"\n\n[mcp_servers.meu]\ncommand = "x"\n')
    log = install.Log(simular=False)
    srv = {"command": "/usr/bin/uv", "args": ["run", "a b"], "env": {"K": "v\"1"}}
    assert install.register_codex_mcp("autocad", srv, log)
    assert install.register_codex_mcp("autocad", srv, log)  # idempotente
    data = tomllib.loads(cfg.read_text())
    assert data["model"] == "gpt-5" and data["mcp_servers"]["meu"]["command"] == "x"
    assert data["mcp_servers"]["autocad"]["args"] == ["run", "a b"]
    assert data["mcp_servers"]["autocad"]["env"]["K"] == 'v"1'
    assert cfg.read_text().count("skillverse:autocad") == 2
    assert not install.register_codex_mcp("meu", srv, log)  # não pisa no MCP do usuário
    install.unregister_codex_mcp("autocad", log)
    assert "autocad" not in tomllib.loads(cfg.read_text())["mcp_servers"]


def test_simulacao_nao_altera_nada(pacote, home):
    r = cli(pacote, "instalar", "--plataforma", "codex", "--simular")
    assert r.returncode == 0
    assert not (home / ".codex").exists() and not (home / "SkillVerse").exists()


def test_md_to_html_tabela_e_listas():
    h = install.md_to_html("# T\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n- x\n- y\n", "t")
    assert "<th>a</th>" in h and "<td>2</td>" in h and "<li>y</li>" in h


def test_download_cai_para_curl_sem_certificados(monkeypatch):
    import urllib.error

    def falha(*a, **k):
        raise urllib.error.URLError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
    chamadas = []

    class P:
        returncode, stdout, stderr = 0, b"PK-conteudo", b""
    monkeypatch.setattr(install.urllib.request, "urlopen", falha)
    monkeypatch.setattr(install.shutil, "which", lambda n: "/usr/bin/curl" if n == "curl" else None)
    monkeypatch.setattr(install.subprocess, "run", lambda cmd, **k: chamadas.append(cmd) or P())
    assert install.baixar_url("https://exemplo/x.zip") == b"PK-conteudo"
    assert chamadas[0][0] == "curl"
