# Site Engcode

Catálogo estático de skills e MCPs para engenharia. A interface foi organizada como uma biblioteca: navegação por área e tipo, cartões compactos, páginas individuais e lista de seleção que gera comandos de instalação para Claude Code e Codex. Não existe checkout, banco de pedidos nem pack no fluxo do usuário.

A fonte do catálogo é `../engcode/catalog.json`. Rode `node ../engcode/sync-site.mjs` após alterar itens. `npm run build` cria `dist/` com a página inicial, índices de skills/MCPs, páginas por área e página individual de cada ferramenta. O build valida a presença dos arquivos públicos e mantém os dados sincronizados.

A publicação usa Sites com o `project_id` em `.openai/hosting.json`, como site estático. O acesso permanece privado enquanto as ferramentas de engenharia são validadas. O comando copiado usa a branch pública `engcode-catalog` como origem do instalador.

Verificação local:

```sh
node ../engcode/sync-site.mjs --check
npm run build
python3 -m http.server 8787 --directory dist
```

A revisão técnica dos resultados e a conexão efetiva com CAD/BIM devem ser feitas no software correspondente.
