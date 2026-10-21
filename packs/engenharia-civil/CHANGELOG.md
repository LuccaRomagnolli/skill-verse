# Changelog — Pack Engenharia Civil

## 1.7.0 — 2026-10-18 (candidato)

- Nova skill `cotacao-materiais` 1.0.0: importa a planilha de quantitativos, orienta a pesquisa de preços de fornecedores na web e gera XLSX com o melhor custo-benefício por item (empresa, produto, embalagem, quantidade a comprar, frete, total estimado e link), comparativo de ofertas, resumo por fornecedor e pedidos de cotação para itens sem preço público.
- Pack passa a 10 skills.

### Validação pendente

- Ensaiar a pesquisa com uma planilha real em pelo menos duas cidades e conferir preços, fretes e links na data da pesquisa.
- Abrir a planilha gerada no Excel e no LibreOffice e conferir fórmulas, formatos de moeda e links.

## 1.6.0 — 2026-10-18 (candidato)

- Pack reduzido a 9 skills e 5 MCPs opcionais. Permanecem contexto de projeto, planta arquitetônica, quantitativos SINAPI, AutoCAD, Revit, SOLIDWORKS, Archicad, consulta a normas públicas e relatório técnico.
- Manual, fluxos, testes e vitrine atualizados para a composição vigente. O histórico das versões anteriores permanece no Git.
- Para instalações anteriores, atualize pelo novo ZIP e confira se componentes que saíram do pack foram removidos do ambiente.

### Validação pendente

- Conferir cortes e planos BIM com uma planta real e validar os lotes no Revit e Archicad com arquivos de teste.
- Validar o MCP AutoCAD em Windows; o teste anterior no macOS cobriu abertura e medição de DXF e geração de DWG/PDF no aplicativo, sem comprovar controle pelo MCP.
- Conferir templates, categorias e tradução IFC no fluxo Archicad; o ensaio anterior com licença Education cobriu operações limitadas em cópia PLN.
- Validar a instalação, atualização e remoção no ambiente final do cliente antes de anunciar prontidão comercial.
