# MCPcad — regras do repositório

Catálogo modular de skills e conexões MCP para engenharia. Cada ferramenta pode ser selecionada e instalada individualmente em Claude Code, Codex ou ambos. O site é uma vitrine estática, sem checkout ativo.

## Mapa
- `catalog/<categoria>/<skill>/`: fonte das skills. `_comum/` contém ferramentas de uso geral.
- `mcps/<nome>/mcp.yaml`: origem, versão, requisitos e passos de cada conexão. MCP interno tem código em `servidor/`.
- `mcpcad/catalog.json`: manifesto dos itens distribuídos; `mcpcad/cli.mjs`: instalador via `npx`.
- `website/`: site estático; `website/public/catalog.json` é sincronizado a partir do manifesto.
- `tools/validate.py`: valida skills, MCPs e manifesto. `tests/`: testes de scripts técnicos.

## Regras de autoria
1. Cada skill tem `SKILL.md` e `skill.yaml`. `name` no frontmatter corresponde à pasta, em kebab-case, até 64 caracteres.
2. `description` diz o que faz e quando usar, incluindo gatilhos em português. O corpo tem até 500 linhas; detalhes vão em `references/` e código em `scripts/`.
3. Cálculo numérico técnico usa script verificável, com teste. Toda skill técnica inclui `## Limites e responsabilidade`.
4. Referências a arquivos dentro da skill usam caminhos relativos. Não incluir chaves, dados pessoais ou caminhos absolutos da máquina do autor.
5. Citar normas brasileiras por número e edição. Não copiar nem distribuir texto protegido de normas ABNT. Para fontes públicas, registrar URL, data de acesso e vigência.
6. MCP de terceiros tem origem, licença e versão fixada; confirmar versão publicada no upstream. Não declarar integração CAD/BIM pronta sem teste no software real.
7. Ao incluir ferramenta nova, registrar no manifesto, sincronizar o site, adicionar página ao build estático e validar instalação individual.

## Verificação
```bash
pip install -r requirements-dev.txt
python3 tools/validate.py --strict
python3 -m pytest -q
node mcpcad/sync-site.mjs --check
node --check mcpcad/cli.mjs
node website/build.mjs
node mcpcad/cli.mjs --list
```

Teste instalação em HOME temporário e com projeto descartável antes de publicar um comando novo. O instalador preserva destinos existentes; não usar o HOME pessoal no teste.
