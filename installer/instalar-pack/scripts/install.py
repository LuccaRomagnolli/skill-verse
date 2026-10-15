#!/usr/bin/env python3
"""Instalador de packs Skill-Verse para Claude Code e Codex (somente biblioteca padrão).

Subcomandos (rode a partir de qualquer pasta; o pack é localizado pelo caminho deste arquivo
ou por --pack):

  detectar                 JSON com SO, plataformas, uv, softwares detectados e instalação atual
  instalar                 copia o pack, instala skills e registra MCPs escolhidos
  verificar                confere skills e faz handshake real com cada MCP
  manual                   gera MANUAL.md e MANUAL.html personalizados
  desinstalar              remove tudo o que este pack instalou
  atualizar                reinstala com as mesmas escolhas da instalação anterior

Variáveis de ambiente: SKILLVERSE_HOME (padrão ~/SkillVerse), CODEX_HOME (padrão ~/.codex),
CLAUDE_CONFIG_DIR (padrão ~/.claude).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import html
import io
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

MARKER = ".skillverse.json"
MCP_PROTOCOL = "2025-06-18"


# ---------------------------------------------------------------- caminhos

def sv_home() -> Path:
    return Path(os.environ.get("SKILLVERSE_HOME", Path.home() / "SkillVerse"))


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))


def mcp_dir() -> Path:
    return sv_home() / "mcps"


def state_file() -> Path:
    return sv_home() / "estado.json"


def find_claude() -> str | None:
    """CLI do Claude Code: PATH, binário da sessão atual, extensões de IDE ou instalações locais."""
    cands = [os.environ.get("SKILLVERSE_CLAUDE_BIN"), shutil.which("claude"), os.environ.get("CLAUDE_CODE_EXECPATH")]
    exe = "claude.exe" if os.name == "nt" else "claude"
    for ide in (".vscode", ".vscode-insiders", ".cursor", ".windsurf"):
        found = sorted(glob.glob(str(Path.home() / ide / "extensions" / "anthropic.claude-code-*" / "resources"
                                     / "native-binary" / exe)))
        cands += found[::-1]
    cands += [str(Path.home() / ".claude" / "local" / exe), str(Path.home() / ".local" / "bin" / exe)]
    for c in cands:
        if c and Path(c).is_file() and os.access(c, os.X_OK):
            return c
    return None


def find_pack_root(explicit: str | None) -> Path:
    if explicit:
        root = Path(explicit).expanduser().resolve()
    else:
        # instalador/scripts/install.py  ->  raiz do pack
        root = Path(__file__).resolve().parent.parent.parent
    if not (root / "pack.json").is_file():
        sys.exit(f"pack.json não encontrado em {root}. Use --pack <pasta do pack>.")
    return root


def load_pack(root: Path) -> dict:
    return json.loads((root / "pack.json").read_text(encoding="utf-8"))


def os_key() -> str:
    s = platform.system()
    return {"Darwin": "macos", "Windows": "windows"}.get(s, "linux")


# ---------------------------------------------------------------- estado

def load_state() -> dict:
    f = state_file()
    if f.is_file():
        return json.loads(f.read_text(encoding="utf-8"))
    return {"packs": {}}


def save_state(state: dict) -> None:
    sv_home().mkdir(parents=True, exist_ok=True)
    state_file().write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- util

class Log:
    def __init__(self, simular: bool) -> None:
        self.simular = simular
        self.passos: list[str] = []
        self.avisos: list[str] = []

    def passo(self, msg: str) -> None:
        prefix = "[simulação] " if self.simular else ""
        print(f"  • {prefix}{msg}")
        self.passos.append(msg)

    def aviso(self, msg: str) -> None:
        print(f"  ! {msg}")
        self.avisos.append(msg)


def run(cmd: list[str], log: Log, check: bool = True, timeout: int = 600,
        env: dict | None = None) -> subprocess.CompletedProcess | None:
    log.passo("$ " + " ".join(cmd))
    if log.simular:
        return None
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       env={**os.environ, **env} if env else None)
    if check and p.returncode != 0:
        raise RuntimeError(f"comando falhou ({p.returncode}): {' '.join(cmd)}\n{p.stderr.strip() or p.stdout.strip()}")
    return p


def baixar_url(url: str, timeout: int = 120) -> bytes:
    """urllib; se o Python não tiver certificados (python.org no macOS), usa o curl do sistema."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read()
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e) or not shutil.which("curl"):
            raise
        p = subprocess.run(["curl", "-fsSL", "--max-time", str(timeout), url], capture_output=True)
        if p.returncode != 0:
            raise RuntimeError(f"curl falhou ({p.returncode}): {p.stderr.decode(errors='replace')[-300:]}") from e
        return p.stdout


def subst(value, ctx: dict[str, str]):
    if isinstance(value, str):
        for k, v in ctx.items():
            value = value.replace("{" + k + "}", v)
        return value
    if isinstance(value, list):
        return [subst(v, ctx) for v in value]
    if isinstance(value, dict):
        return {k: subst(v, ctx) for k, v in value.items()}
    return value


_PACK_DIR: Path | None = None  # raiz do pack instalado (para MCPs próprios que vêm dentro do pack)


def ctx() -> dict[str, str]:
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    c = {"MCP_DIR": mcp_dir().as_posix(), "SKILLVERSE_HOME": sv_home().as_posix(),
         "APPDATA": Path(appdata).as_posix()}
    if _PACK_DIR:
        c["PACK_DIR"] = _PACK_DIR.as_posix()
    return c


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))


def owned_by(path: Path, pack_id: str) -> bool:
    m = path / MARKER
    if not m.is_file():
        return False
    try:
        return json.loads(m.read_text(encoding="utf-8")).get("pack") == pack_id
    except json.JSONDecodeError:
        return False


# ---------------------------------------------------------------- detectar

# ferramenta declarada em requisitos.ferramentas → executável procurado no PATH
FERRAMENTAS = {"uv": "uv", "node": "npx"}
COMO_INSTALAR = {
    "uv": "rode 'install.py instalar-uv' (com a permissão do usuário)",
    "node": "instale o Node.js LTS (Windows: 'winget install OpenJS.NodeJS.LTS'; ou nodejs.org) e reabra o terminal",
}


def ferramentas_faltando(m: dict) -> list[str]:
    return [f for f in (m.get("requisitos") or {}).get("ferramentas") or []
            if not shutil.which(FERRAMENTAS.get(f, f))]


def detected_paths(m: dict) -> list[str]:
    pats = (m.get("deteccao") or {}).get(os_key(), [])
    return sorted({p for pat in pats for p in glob.glob(pat)})


def detect(pack: dict) -> dict:
    osk = os_key()
    softwares = {}
    for m in pack.get("mcps", []):
        found = detected_paths(m)
        softwares[m["nome"]] = {
            "titulo": m["titulo"],
            "detectado": bool(found),
            "caminhos": found,
            "suporta_este_so": osk in m["requisitos"]["so"],
            "util_sem_software": bool(m.get("util_sem_software")),
            "recomendado": bool(m.get("recomendado")),
            "descricao": m.get("descricao", ""),
            "opcional": m.get("opcional", True),
            "ferramentas_faltando": ferramentas_faltando(m),
        }
    claude = find_claude()
    codex = shutil.which("codex")
    state = load_state()
    return {
        "pack": {"id": pack["id"], "nome": pack["nome"], "version": pack["version"]},
        "so": osk,
        "arquitetura": platform.machine(),
        "python": platform.python_version(),
        "plataformas": {
            "claude_code": {"cli": claude, "pasta": str(claude_home()), "pasta_existe": claude_home().is_dir()},
            "codex": {"cli": codex, "pasta": str(codex_home()), "pasta_existe": codex_home().is_dir()},
        },
        "uv": shutil.which("uv"),
        "node": shutil.which("npx"),
        "softwares": softwares,
        "instalacao_atual": state["packs"].get(pack["id"]),
        "destino": str(sv_home()),
    }


# ---------------------------------------------------------------- skills

def skill_names(pack_root: Path) -> list[str]:
    d = pack_root / "plugin" / "skills"
    return sorted(p.name for p in d.iterdir() if (p / "SKILL.md").is_file())


def install_skills_copy(src_root: Path, dest_dir: Path, pack: dict, log: Log, forcar: bool) -> list[str]:
    instaladas = []
    for name in skill_names(src_root):
        dst = dest_dir / name
        if dst.exists() and not owned_by(dst, pack["id"]) and not forcar:
            log.aviso(f"{dst} já existe e não é deste pack — pulei (use --forcar para sobrescrever)")
            continue
        log.passo(f"skill {name} → {dst}")
        if not log.simular:
            dest_dir.mkdir(parents=True, exist_ok=True)
            copy_tree(src_root / "plugin" / "skills" / name, dst)
            (dst / MARKER).write_text(json.dumps({"pack": pack["id"], "version": pack["version"]}), encoding="utf-8")
        instaladas.append(str(dst))
    return instaladas


def install_claude(installed_root: Path, pack: dict, log: Log, sem_plugin: bool, forcar: bool) -> dict:
    claude = find_claude()
    mkt = pack["marketplace"]
    if claude and not sem_plugin:
        listed = run([claude, "plugin", "marketplace", "list"], log, check=False)
        if listed is not None and mkt in (listed.stdout or ""):
            run([claude, "plugin", "marketplace", "remove", mkt], log, check=False)
        run([claude, "plugin", "marketplace", "add", str(installed_root)], log)
        run([claude, "plugin", "install", f"{pack['id']}@{mkt}"], log)
        return {"modo": "plugin", "plugin": f"{pack['id']}@{mkt}", "skills": skill_names(installed_root)}
    if not claude:
        log.aviso("CLI do Claude Code não encontrada — instalando as skills por cópia em ~/.claude/skills")
    paths = install_skills_copy(installed_root, claude_home() / "skills", pack, log, forcar)
    return {"modo": "copia", "caminhos": paths, "skills": skill_names(installed_root)}


def install_codex(installed_root: Path, pack: dict, log: Log, forcar: bool) -> dict:
    paths = install_skills_copy(installed_root, codex_home() / "skills", pack, log, forcar)
    return {"modo": "copia", "caminhos": paths, "skills": skill_names(installed_root)}


# ---------------------------------------------------------------- MCPs

def resolve_server(m: dict) -> dict:
    srv = subst(dict(m["servidor"]), ctx())
    extra = (srv.pop("por_so", None) or {}).get(os_key(), {})
    env = dict(srv.get("env") or {})
    env.update(extra.get("env") or {})
    command = extra.get("command", srv["command"])
    args = extra.get("args", srv.get("args") or [])
    cmd = shutil.which(command) or command
    return {"command": cmd, "args": list(args), "env": env}


def versoes_detectadas(m: dict, step: dict, log: Log) -> list[str]:
    """Versões do software instalado (ex.: Revit 2025) que o passo suporta."""
    rx = re.compile(step.get("versao_regex", r"(\d{4})"))
    achadas = sorted({mt.group(1) for p in detected_paths(m) if (mt := rx.search(p))})
    suportadas = [str(v) for v in step.get("versoes") or achadas]
    fora = [v for v in achadas if v not in suportadas]
    if fora:
        log.aviso(f"{m['titulo']}: versão {', '.join(fora)} sem suporte nesta conexão (suportadas: "
                  f"{suportadas[0]}–{suportadas[-1]})")
    if not achadas:
        log.aviso(f"{m['titulo']}: software não encontrado nesta máquina — o complemento não foi instalado. "
                  "Instale o programa e rode 'atualizar'.")
    return [v for v in achadas if v in suportadas]


def extrair_mesclando(data: bytes, dest: Path, ignorar: list[str] | None = None) -> list[str]:
    """Extrai o zip DENTRO de dest sem apagar o que já existe lá. Devolve os arquivos gravados."""
    gravados = []
    base = dest.resolve()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            alvo = (dest / info.filename).resolve()
            if base != alvo and base not in alvo.parents:
                raise RuntimeError(f"zip com caminho fora do destino: {info.filename}")
            if info.is_dir() or info.filename in (ignorar or []):
                continue
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_bytes(z.read(info))
            gravados.append(str(alvo))
    return gravados


def prepare_mcp(m: dict, log: Log, pack_root: Path) -> dict:
    """Executa o preparo. Devolve {'arquivos': [...], 'pastas_base': [...]} do que foi extraído fora do MCP_DIR."""
    criados: dict[str, list[str]] = {"arquivos": [], "pastas_base": []}
    for step in subst(m.get("preparo") or [], ctx()):
        if "copiar_do_pack" in step:
            src, dest = pack_root / step["copiar_do_pack"], Path(step["destino"])
            for f in sorted(src.rglob("*")) if src.is_dir() else []:
                alvo = dest / f.relative_to(src)
                if f.is_file() and not alvo.exists():
                    log.passo(f"copiar {f.name} → {alvo}")
                    if not log.simular:
                        alvo.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, alvo)
        elif "baixar_zip" in step:
            dest = Path(step["destino"])
            log.passo(f"baixar {step['baixar_zip']} → {dest}")
            if log.simular:
                continue
            data = baixar_url(step["baixar_zip"])
            with tempfile.TemporaryDirectory() as tmp:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    z.extractall(tmp)
                tops = [p for p in Path(tmp).iterdir() if p.is_dir()]
                src = tops[0] if len(tops) == 1 else Path(tmp)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.move(str(src), str(dest))
        elif "extrair_zip" in step:
            # complemento por versão do software (ex.: add-in do Revit em %APPDATA%/Autodesk/Revit/Addins/<ano>)
            for v in versoes_detectadas(m, step, log):
                url = step["extrair_zip"].replace("{VERSAO}", v)
                dest = Path(step["destino"].replace("{VERSAO}", v))
                log.passo(f"baixar {url} → {dest} (mesclando)")
                if log.simular:
                    continue
                criados["arquivos"] += extrair_mesclando(baixar_url(url), dest, step.get("ignorar"))
                criados["pastas_base"].append(str(dest.resolve()))
        elif "comando" in step:
            cmd = list(step["comando"])
            cmd[0] = shutil.which(cmd[0]) or cmd[0]
            run(cmd, log, timeout=1800, env=step.get("env"))
    return criados


def remover_extraidos(reg: dict, log: Log) -> None:
    """Apaga só os arquivos que o pack extraiu e as pastas que ficaram vazias, sem subir além da pasta base."""
    bases = {Path(b) for b in reg.get("pastas_base", [])}
    for f in reg.get("arquivos", []):
        p = Path(f)
        if p.is_file():
            log.passo(f"remover {p}")
            if log.simular:
                continue
            p.unlink()
            d = p.parent
            while any(b in d.parents for b in bases) and d.is_dir() and not any(d.iterdir()):
                d.rmdir()
                d = d.parent


def toml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)  # string JSON é string básica TOML válida


def codex_block(nome: str, srv: dict) -> str:
    lines = [f"# >>> skillverse:{nome}", f"[mcp_servers.{nome}]",
             f"command = {toml_str(srv['command'])}",
             "args = [" + ", ".join(toml_str(a) for a in srv["args"]) + "]",
             "startup_timeout_sec = 120"]
    if srv["env"]:
        lines.append(f"[mcp_servers.{nome}.env]")
        lines += [f"{k} = {toml_str(v)}" for k, v in srv["env"].items()]
    lines.append(f"# <<< skillverse:{nome}")
    return "\n".join(lines) + "\n"


def strip_codex_block(text: str, nome: str) -> str:
    pat = re.compile(rf"# >>> skillverse:{re.escape(nome)}\n.*?# <<< skillverse:{re.escape(nome)}\n", re.S)
    return pat.sub("", text)


def register_codex_mcp(nome: str, srv: dict, log: Log) -> bool:
    cfg = codex_home() / "config.toml"
    text = cfg.read_text(encoding="utf-8") if cfg.is_file() else ""
    clean = strip_codex_block(text, nome)
    if tomllib and clean.strip():
        try:
            existing = tomllib.loads(clean).get("mcp_servers", {})
        except tomllib.TOMLDecodeError as e:
            log.aviso(f"{cfg} tem TOML inválido ({e}); não registrei o MCP {nome} no Codex")
            return False
        if nome in existing:
            log.aviso(f"já existe um MCP '{nome}' seu em {cfg} — mantive o seu e não registrei o do pack")
            return False
    log.passo(f"MCP {nome} → {cfg}")
    if not log.simular:
        cfg.parent.mkdir(parents=True, exist_ok=True)
        sep = "" if not clean or clean.endswith("\n\n") else ("\n" if clean.endswith("\n") else "\n\n")
        cfg.write_text(clean + sep + codex_block(nome, srv), encoding="utf-8")
    return True


def register_claude_mcp(nome: str, srv: dict, log: Log) -> bool:
    claude = find_claude()
    if not claude:
        log.aviso(f"CLI do Claude Code não encontrada — MCP {nome} não registrado no Claude Code")
        return False
    run([claude, "mcp", "remove", nome, "--scope", "user"], log, check=False)
    cmd = [claude, "mcp", "add", nome, "--scope", "user"]
    for k, v in srv["env"].items():
        cmd += ["-e", f"{k}={v}"]
    cmd += ["--", srv["command"], *srv["args"]]
    run(cmd, log)
    return True


def unregister_codex_mcp(nome: str, log: Log) -> None:
    cfg = codex_home() / "config.toml"
    if cfg.is_file():
        log.passo(f"remover MCP {nome} de {cfg}")
        if not log.simular:
            cfg.write_text(strip_codex_block(cfg.read_text(encoding="utf-8"), nome), encoding="utf-8")


# ---------------------------------------------------------------- MCP handshake

def mcp_handshake(srv: dict, timeout: float = 180.0) -> dict:
    """Inicia o servidor stdio, faz initialize + tools/list e devolve os nomes das tools."""
    env = {**os.environ, **srv["env"]}
    try:
        p = subprocess.Popen([srv["command"], *srv["args"]], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, env=env, bufsize=1)
    except OSError as e:
        return {"ok": False, "erro": f"não iniciou: {e}"}
    q: queue.Queue = queue.Queue()
    threading.Thread(target=lambda: [q.put(l) for l in p.stdout], daemon=True).start()

    def send(msg: dict) -> None:
        p.stdin.write(json.dumps(msg) + "\n")
        p.stdin.flush()

    def wait(id_: int) -> dict | None:
        deadline = _dt.datetime.now() + _dt.timedelta(seconds=timeout)
        while _dt.datetime.now() < deadline:
            try:
                line = q.get(timeout=1)
            except queue.Empty:
                if p.poll() is not None:
                    return None
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == id_:
                return msg
        return None

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": MCP_PROTOCOL, "capabilities": {},
            "clientInfo": {"name": "skillverse-installer", "version": "1"}}})
        init = wait(1)
        if not init or "result" not in init:
            err = p.stderr.read()[-800:] if p.poll() is not None else "sem resposta (tempo esgotado)"
            return {"ok": False, "erro": f"initialize falhou: {err}"}
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tl = wait(2)
        tools = [t["name"] for t in (tl or {}).get("result", {}).get("tools", [])]
        return {"ok": bool(tools), "servidor": init["result"].get("serverInfo", {}), "tools": tools}
    finally:
        p.kill()


# ---------------------------------------------------------------- comandos

def cmd_detectar(args) -> int:
    pack = load_pack(find_pack_root(args.pack))
    print(json.dumps(detect(pack), indent=2, ensure_ascii=False))
    return 0


def parse_list(s: str | None) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def cmd_instalar(args) -> int:
    root = find_pack_root(args.pack)
    pack = load_pack(root)
    log = Log(args.simular)
    plataformas = ["claude", "codex"] if args.plataforma == "ambas" else [args.plataforma]
    mcps_by_name = {m["nome"]: m for m in pack.get("mcps", [])}
    escolhidos = parse_list(args.mcps)
    for n in escolhidos:
        if n not in mcps_by_name:
            sys.exit(f"MCP '{n}' não faz parte deste pack. Disponíveis: {', '.join(mcps_by_name) or 'nenhum'}")
    neste_so = [n for n in escolhidos if os_key() in mcps_by_name[n]["requisitos"]["so"]]
    if any("uv" in ferramentas_faltando(mcps_by_name[n]) for n in neste_so):
        sys.exit("Os MCPs precisam do 'uv'. Rode 'install.py instalar-uv' (com a permissão do usuário) e tente de novo.")

    print(f"Instalando {pack['nome']} v{pack['version']} em: {', '.join(plataformas)}")
    dest = sv_home() / "packs" / pack["id"]
    log.passo(f"copiar pack → {dest}")
    if not log.simular and root.resolve() != dest.resolve():
        copy_tree(root, dest)
    installed_root = dest if not log.simular else root
    global _PACK_DIR
    _PACK_DIR = installed_root

    registro = {"version": pack["version"], "instalado_em": _dt.datetime.now().isoformat(timespec="seconds"),
                "pasta": str(dest), "plataformas": {}, "mcps": {}}
    if "claude" in plataformas:
        registro["plataformas"]["claude"] = install_claude(installed_root, pack, log, args.sem_plugin, args.forcar)
    if "codex" in plataformas:
        registro["plataformas"]["codex"] = install_codex(installed_root, pack, log, args.forcar)

    falhas: dict[str, str] = {}
    for n in escolhidos:
        m = mcps_by_name[n]
        if os_key() not in m["requisitos"]["so"]:
            log.aviso(f"{m['titulo']} não roda em {os_key()} — pulei")
            continue
        faltam = ferramentas_faltando(m)
        if faltam:
            falhas[n] = "falta " + ", ".join(faltam)
            log.aviso(f"{m['titulo']}: falta {', '.join(faltam)} — " + "; ".join(COMO_INSTALAR.get(f, f) for f in faltam))
            continue
        try:
            criados = prepare_mcp(m, log, installed_root)
            srv = resolve_server(m)
            reg = {"servidor": srv, "plataformas": []}
            if criados["arquivos"]:
                reg.update(criados)
            if m.get("dados"):
                reg["dados"] = subst(m["dados"], ctx())
            if "claude" in plataformas and register_claude_mcp(n, srv, log):
                reg["plataformas"].append("claude")
            if "codex" in plataformas and register_codex_mcp(n, srv, log):
                reg["plataformas"].append("codex")
            registro["mcps"][n] = reg
        except Exception as e:  # noqa: BLE001 — falha de um MCP não derruba a instalação
            falhas[n] = f"{type(e).__name__}: {e}"
            log.aviso(f"Falha ao instalar a conexão {m['titulo']}: {falhas[n]}")
    if falhas:
        registro["falhas_mcp"] = falhas

    if not log.simular:
        state = load_state()
        state["packs"][pack["id"]] = registro
        save_state(state)
    print("\nPronto." if not log.simular else "\nSimulação concluída — nada foi alterado.")
    if log.avisos:
        print("Avisos:\n" + "\n".join(f"  - {a}" for a in log.avisos))
    pos = [f"[{mcps_by_name[n]['titulo']}] {s}" for n in escolhidos if n not in falhas
           for s in subst(post_install_steps(mcps_by_name[n]), ctx())]
    if pos:
        print("Passos manuais que o usuário precisa fazer:\n" + "\n".join(f"  - {s}" for s in pos))
    if "claude" in plataformas or "codex" in plataformas:
        print("Reinicie o Claude Code / Codex para carregar as skills novas.")
    if falhas:
        print("Conexões com falha (as skills funcionam; tente de novo com 'atualizar'): " + ", ".join(falhas))
        return 3
    return 0


def post_install_steps(m: dict) -> list[str]:
    pi = m.get("pos_instalacao") or {}
    return list(pi.get("todos", [])) + list(pi.get(os_key(), []))


def cmd_verificar(args) -> int:
    pack = load_pack(find_pack_root(args.pack))
    reg = load_state()["packs"].get(pack["id"])
    if not reg:
        print(json.dumps({"ok": False, "erro": "pack não instalado"}, ensure_ascii=False))
        return 1
    out: dict = {"skills": {}, "mcps": {}}
    claude = find_claude()
    for plat, info in reg["plataformas"].items():
        if info["modo"] == "plugin":
            p = subprocess.run([claude, "plugin", "list"], capture_output=True, text=True) if claude else None
            out["skills"][plat] = {"ok": bool(p and info["plugin"] in p.stdout), "modo": "plugin"}
        else:
            missing = [c for c in info["caminhos"] if not (Path(c) / "SKILL.md").is_file()]
            out["skills"][plat] = {"ok": not missing, "faltando": missing, "modo": "copia"}
    mcps = {m["nome"]: m for m in pack.get("mcps", [])}
    for nome, r in reg["mcps"].items():
        if args.sem_mcp:
            continue
        res = mcp_handshake(r["servidor"], timeout=args.timeout)
        esperada = (mcps.get(nome, {}).get("teste") or {}).get("tool_esperada")
        if res.get("ok") and esperada and esperada not in res["tools"]:
            res = {**res, "ok": False, "erro": f"tool '{esperada}' não encontrada"}
        res["tools"] = len(res.get("tools", []))
        out["mcps"][nome] = res
    out["ok"] = all(v["ok"] for v in out["skills"].values()) and all(v["ok"] for v in out["mcps"].values())
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out["ok"] else 1


# ---------------------------------------------------------------- manual

def render_manual(pack: dict, root: Path, reg: dict, extra: str = "") -> str:
    tpl = (root / "manual.template.md").read_text(encoding="utf-8")
    nomes_plat = {"claude": "Claude Code", "codex": "Codex (ChatGPT)"}
    plats = ", ".join(nomes_plat[p] for p in reg["plataformas"])
    plugin_mode = reg["plataformas"].get("claude", {}).get("modo") == "plugin"

    skills_md = []
    for s in pack["skills"]:
        chamadas = []
        if "claude" in reg["plataformas"]:
            chamadas.append(f"Claude Code `/{pack['id']}:{s['name']}`" if plugin_mode else f"Claude Code `/{s['name']}`")
        if "codex" in reg["plataformas"]:
            chamadas.append(f"Codex `${s['name']}`")
        chamada = " · ".join(chamadas)
        ex = "\n".join(f"   - \"{e}\"" for e in s["exemplos"][:3])
        req = f"\n   - Requer: {', '.join(s['mcps'])}" if s.get("mcps") else ""
        if s.get("mcps") and not set(s["mcps"]) & set(reg["mcps"]):
            req += " (**não instalado** — esta skill funciona só em modo leitura/orientação)"
        skills_md.append(f"### {s['titulo']}\n{s['resumo']}\n\n- Chamada direta: {chamada} (ou só descreva o que quer)\n"
                         f"- Exemplos de pedido:\n{ex}{req}\n")

    mcps = {m["nome"]: m for m in pack.get("mcps", [])}
    mcps_md = []
    for nome in reg["mcps"]:
        m = mcps[nome]
        passos = "\n".join(f"   - {s}" for s in subst(post_install_steps(m), ctx()))
        avisos = "\n".join(f"   - ⚠️ {a}" for a in m.get("avisos", []))
        mcps_md.append(f"### {m['titulo']}\n{m['descricao']}\n\n- Requisito: {m['requisitos']['software']}\n"
                       + (f"- Antes de usar:\n{passos}\n" if passos else "") + (f"- Atenção:\n{avisos}\n" if avisos else ""))
    fluxos_md = []
    for f in pack.get("fluxos", []):
        passos = "\n".join(f"{i}. {p}" for i, p in enumerate(f["passos"], 1))
        fluxos_md.append(f"### {f['titulo']}\n{passos}\n")

    repl = {
        "PACK_NOME": pack["nome"], "VERSAO": pack["version"], "DATA": _dt.date.today().strftime("%d/%m/%Y"),
        "PLATAFORMAS": plats, "PASTA": reg["pasta"],
        "SKILLS": "\n".join(skills_md),
        "MCPS": "\n".join(mcps_md) or "_Nenhum software conectado nesta instalação._",
        "FLUXOS": "\n".join(fluxos_md),
        "PARA_VOCE": extra.strip() + "\n" if extra.strip() else "",
        "PERFIL": perfil_txt(),
    }
    for k, v in repl.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    return tpl


def perfil_txt() -> str:
    f = sv_home() / "perfil.json"
    if not f.is_file():
        return "Município padrão: não informado (o agente pergunta no início de cada projeto)."
    p = json.loads(f.read_text(encoding="utf-8"))
    return (f"Município padrão dos seus projetos: **{p.get('municipio')}/{p.get('uf')}**. Em cada projeto novo o agente "
            "confirma o município da obra e pesquisa as normas locais.")


def md_to_html(md: str, title: str) -> str:
    """Conversor mínimo (títulos, listas, tabelas, código, negrito) — suficiente para o manual."""
    out, in_code, in_list, table = [], False, None, []

    def inline(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"_([^_]+)_", r"<em>\1</em>", s)
        return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)

    def close_list():
        nonlocal in_list
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None

    def flush_table():
        nonlocal table
        if table:
            rows = [r for r in table if not re.match(r"^\|[\s:|-]+\|$", r)]
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in cells[0]) + "</tr></thead><tbody>")
            out.extend("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in cells[1:])
            out.append("</tbody></table>")
            table = []

    for line in md.splitlines():
        if line.startswith("```"):
            close_list(); flush_table()
            out.append("</pre>" if in_code else "<pre>")
            in_code = not in_code
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        if line.startswith("|"):
            close_list(); table.append(line); continue
        flush_table()
        if m := re.match(r"^(#{1,4}) (.*)", line):
            close_list(); n = len(m.group(1)); out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif m := re.match(r"^\s*(?:[-*]|(\d+)\.) (.*)", line):
            kind = "ol" if m.group(1) else "ul"
            if in_list != kind:
                close_list(); out.append(f"<{kind}>"); in_list = kind
            out.append(f"<li>{inline(m.group(2))}</li>")
        elif line.strip() == "---":
            close_list(); out.append("<hr>")
        elif line.strip():
            close_list(); out.append(f"<p>{inline(line)}</p>")
        else:
            close_list()
    close_list(); flush_table()
    css = ("body{font:16px/1.6 system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 16px;color:#1b1b1b;background:#fff}"
           "h1,h2,h3{line-height:1.25}h2{border-bottom:1px solid #ddd;padding-bottom:.3em;margin-top:2em}"
           "code,pre{font-family:ui-monospace,Menlo,monospace;background:#f4f4f2;border-radius:4px}"
           "code{padding:.1em .3em}pre{padding:1em;overflow-x:auto}table{border-collapse:collapse;width:100%}"
           "th,td{border:1px solid #ddd;padding:.4em .6em;text-align:left}"
           "@media (prefers-color-scheme:dark){body{color:#e8e8e6;background:#1a1a19}code,pre{background:#2a2a28}"
           "th,td,h2{border-color:#444}a{color:#8ab4f8}}")
    return (f"<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{html.escape(title)}</title>"
            f"<style>{css}</style></head><body>\n" + "\n".join(out) + "\n</body></html>\n")


def cmd_manual(args) -> int:
    root = find_pack_root(args.pack)
    pack = load_pack(root)
    reg = load_state()["packs"].get(pack["id"])
    if not reg:
        sys.exit("Pack não instalado — rode 'instalar' antes.")
    out_dir = Path(args.saida).expanduser() if args.saida else sv_home() / pack["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    extra = Path(args.extra).read_text(encoding="utf-8") if args.extra else ""
    md = render_manual(pack, root, reg, extra)
    (out_dir / "MANUAL.md").write_text(md, encoding="utf-8")
    (out_dir / "MANUAL.html").write_text(md_to_html(md, f"Manual — {pack['nome']}"), encoding="utf-8")
    print(json.dumps({"md": str(out_dir / "MANUAL.md"), "html": str(out_dir / "MANUAL.html")}, ensure_ascii=False))
    return 0


def cmd_desinstalar(args) -> int:
    pack = load_pack(find_pack_root(args.pack))
    state = load_state()
    reg = state["packs"].get(pack["id"])
    if not reg:
        print("Nada a remover: pack não instalado.")
        return 0
    log = Log(args.simular)
    claude = find_claude()
    for plat, info in reg["plataformas"].items():
        if info["modo"] == "plugin" and claude:
            run([claude, "plugin", "uninstall", info["plugin"]], log, check=False)
            run([claude, "plugin", "marketplace", "remove", pack["marketplace"]], log, check=False)
        for c in info.get("caminhos", []):
            if owned_by(Path(c), pack["id"]):
                log.passo(f"remover {c}")
                if not log.simular:
                    shutil.rmtree(c)
    for nome, r in reg["mcps"].items():
        if "claude" in r["plataformas"] and claude:
            run([claude, "mcp", "remove", nome, "--scope", "user"], log, check=False)
        if "codex" in r["plataformas"]:
            unregister_codex_mcp(nome, log)
        remover_extraidos(r, log)
        if r.get("dados") and Path(r["dados"]).is_dir():
            log.passo(f"remover {r['dados']}")
            if not log.simular:
                shutil.rmtree(r["dados"], ignore_errors=True)
        d = mcp_dir()
        for leftover in d.glob(f"{nome}*") if d.is_dir() else []:
            log.passo(f"remover {leftover}")
            if not log.simular:
                shutil.rmtree(leftover)
    pasta = Path(reg["pasta"])
    if pasta.is_dir():
        log.passo(f"remover {pasta}")
        if not log.simular:
            shutil.rmtree(pasta, ignore_errors=True)
    if not log.simular:
        del state["packs"][pack["id"]]
        save_state(state)
        for d in (mcp_dir(), sv_home() / "packs"):
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
    print("Desinstalado." if not log.simular else "Simulação concluída.")
    print(f"Mantidos (seus arquivos): manual em {sv_home() / pack['id']} e regras personalizáveis em {sv_home()}.")
    return 0


def cmd_atualizar(args) -> int:
    pack = load_pack(find_pack_root(args.pack))
    reg = load_state()["packs"].get(pack["id"])
    if not reg:
        sys.exit("Pack não instalado — use 'instalar'.")
    plats = list(reg["plataformas"])
    args.plataforma = "ambas" if len(plats) == 2 else plats[0]
    args.mcps = ",".join(reg["mcps"])
    args.sem_plugin = reg["plataformas"].get("claude", {}).get("modo") == "copia"
    print(f"Atualizando de v{reg['version']} para v{pack['version']}")
    return cmd_instalar(args)


UFS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
       "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}


def cmd_perfil(args) -> int:
    """Município/UF onde o usuário mais atua — padrão para as fichas de projeto (skill contexto-do-projeto)."""
    f = sv_home() / "perfil.json"
    perfil = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
    if args.municipio or args.uf:
        uf = (args.uf or perfil.get("uf") or "").upper()
        if uf not in UFS:
            sys.exit(f"UF inválida: {uf!r}")
        perfil.update({"municipio": args.municipio or perfil.get("municipio"), "uf": uf})
        if args.atuacao:
            perfil["atuacao"] = args.atuacao
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(perfil, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(perfil, ensure_ascii=False))
    return 0


def cmd_instalar_uv(args) -> int:
    if shutil.which("uv"):
        print("uv já instalado:", shutil.which("uv"))
        return 0
    if os_key() == "windows":
        cmd = ["powershell", "-ExecutionPolicy", "ByPass", "-c", "irm https://astral.sh/uv/install.ps1 | iex"]
    else:
        cmd = ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"]
    print("$ " + " ".join(cmd))
    r = subprocess.run(cmd)
    print("Feche e reabra o terminal (ou o Claude Code/Codex) para o 'uv' entrar no PATH.")
    return r.returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", help="pasta do pack (padrão: a pasta que contém este instalador)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("detectar")
    for name in ("instalar", "atualizar"):
        p = sub.add_parser(name)
        p.add_argument("--simular", action="store_true", help="mostra o que faria, sem alterar nada")
        p.add_argument("--forcar", action="store_true", help="sobrescreve skills de mesmo nome que não são deste pack")
        if name == "instalar":
            p.add_argument("--plataforma", choices=["claude", "codex", "ambas"], required=True)
            p.add_argument("--mcps", default="", help="lista separada por vírgula, ex.: autocad,archicad")
            p.add_argument("--sem-plugin", action="store_true", help="Claude Code: copia skills em vez de usar plugin")
    p = sub.add_parser("verificar")
    p.add_argument("--sem-mcp", action="store_true", help="não inicia os servidores MCP")
    p.add_argument("--timeout", type=float, default=180.0)
    p = sub.add_parser("manual")
    p.add_argument("--saida", help="pasta de saída (padrão ~/SkillVerse/<pack>)")
    p.add_argument("--extra", help="arquivo .md com a seção personalizada 'Para você' (inserida no topo)")
    p = sub.add_parser("desinstalar")
    p.add_argument("--simular", action="store_true")
    sub.add_parser("instalar-uv")
    p = sub.add_parser("perfil")
    p.add_argument("--municipio")
    p.add_argument("--uf")
    p.add_argument("--atuacao", help="uma linha sobre como o usuário trabalha")

    args = ap.parse_args(argv)
    return {
        "detectar": cmd_detectar, "instalar": cmd_instalar, "verificar": cmd_verificar, "manual": cmd_manual,
        "desinstalar": cmd_desinstalar, "atualizar": cmd_atualizar, "instalar-uv": cmd_instalar_uv,
        "perfil": cmd_perfil,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
