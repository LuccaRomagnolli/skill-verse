# Skill-Verse

Banco de skills para agentes de IA (Claude Code e Codex), organizado por categoria, de onde saem **packs por nicho** vendidos como download. O comprador baixa o .zip, abre a pasta no agente e diz **"instale este pack"**. O agente instala as skills, conecta os softwares que ele usa (via MCP), testa tudo e gera um manual personalizado.

## Packs

| Pack | Versão | Skills | Conexões |
|---|---|---|---|
| Engenharia Civil | 1.3.0 (candidato) | 12 skills: ficha persistente, normas locais, cálculo e documentação, AutoCAD, Revit, SOLIDWORKS, TQS e ArchiCAD | 5 MCPs opcionais: normas-publicas, AutoCAD, Revit, SOLIDWORKS, ArchiCAD; TQS via API Python |
| Professores | — | (próximo) | — |

## Estrutura
```
catalog/<categoria>/<skill>/   fonte única de cada skill (SKILL.md + skill.yaml + scripts/ + references/ + assets/)
catalog/_comum/                skills usadas por mais de um pack
mcps/<nome>/mcp.yaml           como baixar/registrar cada MCP (terceiros: versão fixada; próprio: upstream interno + servidor/)
packs/<pack>/                  pack.yaml (composição), manual.template.md, CHANGELOG.md
installer/instalar-pack/       skill + install.py (stdlib) que vão dentro de todo pack
installer/bundle/              COMECE-AQUI, INSTALAR, CLAUDE.md/AGENTS.md do zip
tools/validate.py · build.py   lint do catálogo e geração do .zip
tests/                         pytest (cálculos, instalador, build) + evals/gatilhos.yaml
```

## Fluxo de trabalho
```bash
pip install -r requirements-dev.txt
python3 tools/validate.py                  # lint (frontmatter, "Use quando", limites, scripts, packs, MCPs)
python3 -m pytest -q                       # testes
python3 tools/build.py engenharia-civil    # → dist/skillverse-engenharia-civil-v1.3.0.zip
```
Regras de autoria em [CLAUDE.md](CLAUDE.md).

## Como o pack instala
- **Claude Code**: o pack é um marketplace local com um plugin. O instalador copia o pack para `~/SkillVerse/packs/<pack>`, roda `claude plugin marketplace add` + `claude plugin install` e registra os MCPs com `claude mcp add --scope user`. A CLI é achada no PATH, na sessão atual (`CLAUDE_CODE_EXECPATH`) ou nas extensões do VS Code/Cursor.
- **Codex**: copia as skills para `~/.codex/skills/` e adiciona os MCPs ao `~/.codex/config.toml` entre marcadores `# >>> skillverse:<nome>`, sem tocar no que é do usuário.
- **MCPs**: baixados do upstream na versão fixada (nunca embutidos), só para os softwares compatíveis escolhidos pelo usuário. `verificar` distingue servidor iniciado de leitura do aplicativo; AutoCAD headless é identificado como geração DXF, não como AutoCAD operável.
- `desinstalar` remove componentes registrados do pack; preserva manuais, regras personalizadas, documentos locais e arquivos do usuário. Cada skill copiada leva um marcador `.skillverse.json`.

O ZIP 1.3.0 é **candidato**, não liberação técnica para clientes. A referência declarada é NBR 6118:2026, mas os cálculos herdados de 2023 ainda exigem auditoria com o texto-base licenciado e a Emenda 1. Também faltam testes de ponta a ponta nos programas reais para cada integração. Veja as pendências no [changelog](packs/engenharia-civil/CHANGELOG.md).

## Novo pack
1. Escreva as skills em `catalog/<categoria>/` seguindo o CLAUDE.md (reaproveite `_comum/`).
2. Crie `packs/<id>/pack.yaml`, `manual.template.md` e `CHANGELOG.md` (copie do pack de engenharia).
3. `validate` → `pytest` → `build` → teste de ponta a ponta em HOME isolado (ver CLAUDE.md).

## Licença
Conteúdo proprietário, ver [LICENSE-COMERCIAL.md](LICENSE-COMERCIAL.md). Os MCPs de terceiros têm licença MIT e pertencem aos seus autores.
