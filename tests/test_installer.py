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
    for f in ("COMECE-AQUI.txt", "INSTALAR.md", "MANUAL-COMPLETO.md", "CLAUDE.md", "AGENTS.md", "LICENCA.md", "pack.json",
              ".claude-plugin/marketplace.json", "plugin/.claude-plugin/plugin.json", "instalador/SKILL.md"):
        assert (pacote / f).is_file(), f
    pack = json.loads((pacote / "pack.json").read_text(encoding="utf-8"))
    names = {s["name"] for s in pack["skills"]}
    assert len(pack["skills"]) == len(names)
    assert "planta-arquitetonica" in names
    assert (pacote / "plugin/skills/planta-arquitetonica/scripts/planta.py").is_file()
    assert (pacote / "mcps/normas-publicas/server.py").is_file()   # código do MCP próprio vai no zip
    assert (pacote / "mcps/skyciv/server.py").is_file()
    assert (pacote / "VALIDACAO-AUTOCAD-MAC-2027.md").is_file()
    assert (pacote / "VALIDACAO-ARCHICAD-30-MAC.md").is_file()
    assert not list(pacote.rglob("*.db")) and not list(pacote.rglob("pdf/*.pdf"))  # documentos não vão
    mk = json.loads((pacote / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    assert mk["plugins"][0]["name"] == json.loads((pacote / "plugin/.claude-plugin/plugin.json").read_text())["name"]
    assert not list(pacote.rglob("skill.yaml")), "metadados internos não devem ir no zip"
    assert "{{" not in (pacote / "INSTALAR.md").read_text(encoding="utf-8")
    completo = (pacote / "MANUAL-COMPLETO.md").read_text(encoding="utf-8")
    assert "Versão 1.5.1" in completo and "{{" not in completo
    assert "Fluxo 1 — planta baixa" in completo and "Fluxo 2 — estrutura" in completo


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
    assert "Seu primeiro projeto guiado" in md and "NBR 6118:2026" in md
    assert "MANUAL-COMPLETO.html" in md
    assert "<table>" in (home / "SkillVerse/engenharia-civil/MANUAL.html").read_text(encoding="utf-8")
    completo_md = (home / "SkillVerse/engenharia-civil/MANUAL-COMPLETO.md").read_text(encoding="utf-8")
    completo_html = (home / "SkillVerse/engenharia-civil/MANUAL-COMPLETO.html").read_text(encoding="utf-8")
    assert completo_md == (pacote / "MANUAL-COMPLETO.md").read_text(encoding="utf-8")
    assert "<table>" in completo_html and "Fluxo 1" in completo_html

    r = cli(pacote, "desinstalar")
    assert r.returncode == 0
    assert not (skills / "concreto-armado-nbr6118").exists()
    assert not (home / "SkillVerse/packs").exists()


def test_ciclo_ambas_plataformas_com_atualizacao(pacote, home):
    r = cli(pacote, "instalar", "--plataforma", "ambas", "--sem-plugin")
    assert r.returncode == 0, r.stderr
    for pasta in (home / ".claude/skills", home / ".codex/skills"):
        assert (pasta / "contexto-do-projeto/SKILL.md").is_file()
    r = cli(pacote, "verificar", "--sem-mcp")
    assert r.returncode == 0 and json.loads(r.stdout)["ok"]
    r = cli(pacote, "atualizar")
    assert r.returncode == 0, r.stderr
    r = cli(pacote, "verificar", "--sem-mcp")
    assert r.returncode == 0 and json.loads(r.stdout)["ok"]
    r = cli(pacote, "desinstalar")
    assert r.returncode == 0, r.stderr
    for pasta in (home / ".claude/skills", home / ".codex/skills"):
        assert not (pasta / "contexto-do-projeto").exists()


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


def _zip(arquivos: dict[str, bytes]) -> bytes:
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for nome, dados in arquivos.items():
            z.writestr(nome, dados)
    return buf.getvalue()


REVIT = {"nome": "revit", "titulo": "Revit", "requisitos": {"so": ["windows"], "ferramentas": ["node"]},
         "deteccao": {"windows": ["C:/Program Files/Autodesk/Revit 20*"]},
         "preparo": [{"extrair_zip": "https://x/addin-Revit{VERSAO}.zip", "destino": "{APPDATA}/Addins/{VERSAO}",
                      "versao_regex": r"Revit (\d{4})", "versoes": ["2024", "2025", "2026"],
                      "ignorar": ["duplicado.addin"]}],
         "servidor": {"command": "npx", "args": ["-y", "pkg@1.0.0"], "env": {},
                      "por_so": {"windows": {"command": "cmd", "args": ["/c", "npx", "-y", "pkg@1.0.0"]}}}}


def test_extrair_zip_por_versao_mescla_e_desinstala_so_o_que_e_do_pack(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setattr(install, "os_key", lambda: "windows")
    monkeypatch.setattr(install.glob, "glob", lambda pat: ["C:/Program Files/Autodesk/Revit 2025",
                                                           "C:/Program Files/Autodesk/Revit 2027"])
    urls = []
    monkeypatch.setattr(install, "baixar_url", lambda url: urls.append(url) or _zip(
        {"plugin.addin": b"<x/>", "duplicado.addin": b"<x/>", "plugin/a.dll": b"1", "plugin/sub/b.dll": b"2"}))
    addins = tmp_path / "Roaming/Addins/2025"
    addins.mkdir(parents=True)
    (addins / "outro-addin.addin").write_text("do usuário")

    log = install.Log(simular=False)
    criados = install.prepare_mcp(REVIT, log, tmp_path)
    assert urls == ["https://x/addin-Revit2025.zip"]                  # 2027 sem suporte não é baixado
    assert any("2027" in a for a in log.avisos)
    assert (addins / "plugin/sub/b.dll").is_file() and not (addins / "duplicado.addin").exists()
    assert (addins / "outro-addin.addin").read_text() == "do usuário"  # mescla, não apaga

    install.remover_extraidos(criados, log)
    assert not (addins / "plugin").exists() and not (addins / "plugin.addin").exists()
    assert (addins / "outro-addin.addin").is_file() and addins.is_dir()


def test_extrair_zip_recusa_caminho_fora_do_destino(tmp_path):
    with pytest.raises(RuntimeError, match="fora do destino"):
        install.extrair_mesclando(_zip({"../fora.txt": b"x"}), tmp_path / "dest")


def test_revit_nao_sobrescreve_arquivo_alheio_e_preserva_alteracao_do_usuario(tmp_path):
    dest = tmp_path / "Addins/2025"
    dest.mkdir(parents=True)
    (dest / "plugin.addin").write_bytes(b"do usuario")
    with pytest.raises(RuntimeError, match="preexistente"):
        install.extrair_mesclando(_zip({"plugin.addin": b"do pack", "plugin/a.dll": b"1"}), dest)
    assert (dest / "plugin.addin").read_bytes() == b"do usuario"
    assert not (dest / "plugin/a.dll").exists()  # preflight evita instalação parcial

    (dest / "plugin.addin").unlink()
    arquivos = install.extrair_mesclando(_zip({"plugin.addin": b"do pack"}), dest)
    reg = {"arquivos": arquivos, "pastas_base": [str(dest)],
           "hashes": {arquivos[0]: install.sha256_arquivo(dest / "plugin.addin")}}
    (dest / "plugin.addin").write_bytes(b"alterado depois")
    log = install.Log(simular=False)
    install.remover_extraidos(reg, log)
    assert (dest / "plugin.addin").read_bytes() == b"alterado depois"
    assert any("mantido" in x for x in log.avisos)


def test_revit_preflight_todas_as_versoes_antes_de_escrever(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setattr(install, "os_key", lambda: "windows")
    monkeypatch.setattr(install.glob, "glob", lambda pat: ["C:/Program Files/Autodesk/Revit 2024",
                                                            "C:/Program Files/Autodesk/Revit 2025"])
    monkeypatch.setattr(install, "baixar_url", lambda url: _zip({"plugin.addin": b"do pack"}))
    ocupado = tmp_path / "Roaming/Addins/2025/plugin.addin"
    ocupado.parent.mkdir(parents=True)
    ocupado.write_bytes(b"do usuario")
    with pytest.raises(RuntimeError, match="preexistente"):
        install.prepare_mcp(REVIT, install.Log(simular=False), tmp_path)
    assert not (tmp_path / "Roaming/Addins/2024/plugin.addin").exists()
    assert ocupado.read_bytes() == b"do usuario"


def test_mcp_zip_nao_remove_pasta_preexistente_sem_registro(tmp_path):
    dest = tmp_path / "mcp"
    dest.mkdir()
    (dest / "meu.txt").write_text("meu", encoding="utf-8")
    m = {"preparo": [{"baixar_zip": "https://example.org/mcp.zip", "destino": str(dest)}]}
    with pytest.raises(RuntimeError, match="preexistente"):
        install.prepare_mcp(m, install.Log(simular=False), tmp_path)
    assert (dest / "meu.txt").read_text(encoding="utf-8") == "meu"


def test_verificacao_mcp_distingue_handshake_de_aplicativo(tmp_path):
    servidor = tmp_path / "mcp_falso.py"
    servidor.write_text("""import json, sys
for line in sys.stdin:
    msg = json.loads(line)
    if 'id' not in msg:
        continue
    if msg['method'] == 'initialize':
        result = {'serverInfo': {'name': 'falso', 'version': '1'}, 'protocolVersion': '2025-06-18', 'capabilities': {}}
    elif msg['method'] == 'tools/list':
        result = {'tools': [{'name': 'estado', 'description': 'read', 'inputSchema': {'type': 'object'}}]}
    else:
        result = {'isError': True, 'content': [{'type': 'text', 'text': 'software fechado'}]}
    print(json.dumps({'jsonrpc': '2.0', 'id': msg['id'], 'result': result}), flush=True)
""", encoding="utf-8")
    resultado = install.mcp_handshake({"command": sys.executable, "args": [str(servidor)], "env": {}},
                                      timeout=3, probe={"name": "estado", "arguments": {}})
    assert resultado["ok"] is True and resultado["tools"] == ["estado"]
    assert resultado["aplicativo"]["ok"] is False


def test_sem_software_detectado_nao_baixa(tmp_path, monkeypatch):
    monkeypatch.setattr(install, "os_key", lambda: "windows")
    monkeypatch.setattr(install.glob, "glob", lambda pat: [])
    monkeypatch.setattr(install, "baixar_url", lambda url: pytest.fail("não devia baixar"))
    log = install.Log(simular=False)
    assert install.prepare_mcp(REVIT, log, tmp_path)["arquivos"] == []
    assert any("não encontrado" in a for a in log.avisos)


def test_servidor_por_so_troca_comando_e_ferramentas(monkeypatch):
    monkeypatch.setattr(install, "os_key", lambda: "windows")
    monkeypatch.setattr(install.shutil, "which", lambda n: None)
    srv = install.resolve_server(REVIT)
    assert srv["command"] == "cmd" and srv["args"][:2] == ["/c", "npx"]
    assert install.ferramentas_faltando(REVIT) == ["node"]
    monkeypatch.setattr(install.shutil, "which", lambda n: "/usr/bin/npx" if n == "npx" else None)
    assert install.ferramentas_faltando(REVIT) == []
