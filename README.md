# Engcode

Catálogo modular de **skills** e conexões **MCP** para engenharia. O usuário escolhe ferramentas individualmente no site, copia um comando e instala no Claude Code, Codex ou ambos. Cada item é instalado individualmente.

## Instalação individual

O catálogo usa um instalador executado via `npx` a partir da versão pública `engcode-catalog` deste repositório. Exemplo:

```sh
npx --yes --package=github:LuccaRomagnolli/skill-verse#engcode-catalog engcode --skills contexto-do-projeto,planta-arquitetonica --mcps normas-publicas --target claude --scope user
```

Use `--list` para listar IDs, `--target claude|codex|both` e `--scope user|project`. Para escopo `project`, execute o comando na pasta do projeto. O instalador preserva destinos preexistentes e não substitui skills pessoais. MCPs têm requisitos próprios de software e ambiente; o registro no agente não demonstra que o aplicativo está operável. Reinicie o agente e confira a conexão antes de usar.

## Fonte do catálogo

- `catalog/<categoria>/<skill>/`: instruções, scripts, referências e assets das skills.
- `mcps/<nome>/mcp.yaml`: fonte, versão fixada, requisitos e etapas de cada MCP.
- `engcode/catalog.json`: manifesto distribuído ao instalador e ao site.
- `engcode/cli.mjs`: instalador modular sem dependências npm de execução.
- `website/`: catálogo estático, com busca, páginas individuais e lista de instalação.

A fonte atual tem 10 skills e 5 MCPs. Ao alterar uma skill ou MCP, atualize `engcode/catalog.json` e execute `node engcode/sync-site.mjs` para sincronizar a vitrine. Confirme a operação em software real para qualquer promessa de automação CAD/BIM. Textos integrais de normas ABNT não estão incluídos.

## Verificação

```sh
node --check engcode/cli.mjs
node engcode/sync-site.mjs --check
node engcode/cli.mjs --list
node engcode/cli.mjs --skills contexto-do-projeto --target codex --scope project --dry-run
cd website && npm run build
```

O site não inclui checkout. Publicações permanecem privadas durante a validação. Para adicionar uma ferramenta, registre-a no manifesto, sincronize o site e valide o build e a instalação.

## Licença

As skills e o MCP próprio seguem [LICENSE-COMERCIAL.md](LICENSE-COMERCIAL.md). Os MCPs de terceiros têm licenças e autores indicados nos respectivos manifests; seus códigos são baixados dos upstreams na versão fixada, sem incorporação ao repositório.
