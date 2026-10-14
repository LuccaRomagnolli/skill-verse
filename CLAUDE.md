# Skill-Verse — regras do repositório

Banco de skills (formato aberto Agent Skills) organizado por categoria. Packs por nicho são montados a partir dele e vendidos como .zip (Hotmart/Kiwify). O comprador instala no **Claude Code** ou no **Codex**.

## Mapa
- `catalog/<categoria>/<skill>/` — **fonte única** de cada skill. `_comum/` = skills usadas por mais de um pack.
- `mcps/<nome>/mcp.yaml` — como instalar/registrar um MCP de terceiros (origem upstream fixada, licença, requisitos).
- `packs/<pack>/pack.yaml` — o que entra em cada pack + `manual.template.md`.
- `installer/` — skill `instalar-pack` + `install.py` (stdlib pura). Vai dentro de todo pack.
- `tools/validate.py` — lint do catálogo. `tools/build.py <pack>` — gera `dist/*.zip`.
- `tests/` — pytest dos scripts de cálculo e do instalador; `tests/evals/<skill>.yaml` — gatilhos.

## Regras de autoria de skill
1. Pasta `catalog/<categoria>/<nome>/` com `SKILL.md` + `skill.yaml`. `name` no frontmatter = nome da pasta, kebab-case, ≤ 64 caracteres.
2. `description` (≤ 1024 caracteres) diz **o que faz + quando usar + gatilhos em PT-BR** ("Use quando…"). Sem isso a skill não dispara.
3. Corpo do SKILL.md < 500 linhas. Tabelas, normas e detalhes vão em `references/`; código em `scripts/`.
4. **Cálculo numérico nunca é feito "de cabeça" pelo modelo**: sempre por script em `scripts/` (Python 3.10+, stdlib; numpy só se indispensável), com teste em `tests/`.
5. Toda skill técnica tem a seção `## Limites e responsabilidade`.
6. Scripts referenciados no SKILL.md com caminho relativo à pasta da skill (`scripts/x.py`); o agente resolve a partir da pasta da skill.
7. Nada de dados pessoais, chaves ou caminhos absolutos da máquina do autor.
8. Português do Brasil, normas ABNT citadas por número e ano.

## Comandos
```bash
pip install -r requirements-dev.txt
python3 tools/validate.py                 # lint de todo o catálogo e packs
python3 -m pytest -q                      # testes
python3 tools/build.py engenharia-civil   # dist/skillverse-engenharia-civil-vX.Y.Z.zip
```

## Versionamento
- Cada skill tem `version` em `skill.yaml`; cada pack tem `version` em `pack.yaml` (semver). Mudou skill → sobe a versão do pack e registra no `CHANGELOG.md` do pack.

## Teste de ponta a ponta (antes de cada release)
Nunca teste no HOME real. Use um HOME isolado:
```bash
T=$(mktemp -d); mkdir -p $T/home $T/dl && unzip -q dist/skillverse-<pack>-v<versão>.zip -d $T/dl
export HOME=$T/home CLAUDE_CONFIG_DIR=$T/home/.claude UV_CACHE_DIR=~/.cache/uv
export SKILLVERSE_CLAUDE_BIN=<caminho da CLI claude>   # dentro do Claude Code: $CLAUDE_CODE_EXECPATH
cd $T/dl/skillverse-*/instalador
python3 scripts/install.py instalar --plataforma ambas --mcps <lista>
python3 scripts/install.py verificar      # handshake real com cada MCP
python3 scripts/install.py manual
python3 scripts/install.py desinstalar    # deve deixar plugin, MCPs e skills limpos
```
Confira também `claude plugin list` e `claude mcp list` com o mesmo `CLAUDE_CONFIG_DIR`.
MCP de terceiros: só fixe versões **publicadas** no upstream (commit no GitHub remoto ou versão no PyPI).
