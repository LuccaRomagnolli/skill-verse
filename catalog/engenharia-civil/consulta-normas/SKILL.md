---
name: consulta-normas
description: Consulta documentos técnicos públicos brasileiros num índice local via MCP — Normas Regulamentadoras (NR-18 canteiro de obras, NR-35 trabalho em altura, NR-10, NR-12, NR-33 e outras) com seus manuais oficiais, normas e manuais do DNIT e cadernos técnicos do SINAPI — e cita item, página e fonte; transforma as exigências em checklist de projeto, de canteiro ou de medição. Use quando o usuário perguntar "o que a NR diz", "exigência da norma", "segurança do trabalho na obra", "canteiro", "guarda-corpo", "andaime", "trabalho em altura", "critério de medição", "caderno técnico SINAPI", "norma do DNIT", "especificação de serviço" ou pedir boas práticas normativas para projetar ou executar.
---

# Consulta a normas e boas práticas

O MCP `normas-publicas` mantém um índice local (SQLite) com documentos **públicos**, baixados das fontes oficiais: NRs do MTE, DNIT/IPR e SINAPI/Caixa. Ferramentas: `buscar_normas`, `buscar_catalogo`, `baixar_documentos`, `ler_pagina`, `localizar_item`, `atualizar_catalogo`, `status`.

**Normas ABNT não estão no índice** (protegidas por direito autoral). Nunca invente nem "reconstrua" texto de NBR. Para NBR, use as sínteses em `references/` das skills de cálculo, com o número do item, e diga que o texto oficial está na norma.

## Fluxo de consulta
0. **Ficha do projeto**: se existir `projeto-contexto.json` (skill `contexto-do-projeto`), use uso, pavimentos, área e município para filtrar o que se aplica (ex.: exigências da NR-18 que dependem do porte da obra; documentos `fonte='local'` daquele município). Fontes encontradas aqui que valem para o projeto devem ser registradas na ficha com `contexto.py fonte`.
1. **Assunto → fonte**: use `references/mapa-de-fontes.md` para saber onde procurar.
2. **Buscar no texto**: `buscar_normas` com termos técnicos (substantivos, sem frases). Ex.: `"guarda-corpo travessão rodapé"`, `"escavação talude 1,25"`, `"critério medição alvenaria vãos"`.
3. **Sem resultado bom?** `buscar_normas` já sugere documentos do catálogo ainda não baixados → `baixar_documentos` com os ids pertinentes (no máximo 10; diga ao usuário o que vai baixar) → repita a busca.
4. **Texto exato**: `localizar_item` (`nr-18`, `18.13.1`) ou `ler_pagina`. Cite **literalmente** o trecho que fundamenta a resposta.
5. **Responder**: exigência em linguagem direta + citação no formato `NR-18 (2026), item 18.13.1, p. 42` + link oficial. Para NR, acrescente: "texto conforme publicação no gov.br; o oficial é o do DOU".

## Do requisito ao projeto (boas práticas)
Quando o usuário estiver **projetando ou planejando** (não só perguntando), converta as exigências em entregáveis:
- **Checklist** em tabela: `Requisito | Fonte (item) | Como atender no projeto/obra | Responsável | OK?`.
- **Canteiro (NR-18)**: áreas de vivência dimensionadas pelo efetivo, proteção de periferia, aberturas no piso, escadas e rampas, instalações elétricas provisórias (NR-10), sinalização, plano de movimentação de cargas. Se o AutoCAD estiver conectado, ofereça desenhar o layout com a skill `autocad-assistente`.
- **Orçamento**: o critério de medição vem do caderno técnico SINAPI da composição. Use junto com a skill `quantitativos-sinapi`.
- **Rodovias/pavimentos**: ES (execução e controle) + EM (material) + ME (ensaios), com a frequência de ensaios para o plano de controle tecnológico.
- Sempre diferencie **obrigação normativa** (tem item) de **boa prática** (recomendação de manual/guia ou experiência). Escreva "boa prática" quando não houver item que obrigue.

## Normas locais (município/estado)
Código de obras, plano diretor, ITs do Corpo de Bombeiros e normas de concessionárias são pesquisados na internet pela skill `contexto-do-projeto`, a partir do município da obra. Documentos públicos encontrados entram no índice com `importar_documento_publico(url, titulo, esfera)` e passam a ser consultados aqui com `buscar_normas(fonte='local')`. O servidor recusa sites de cópias e exemplares de NBR.

## Manutenção do índice
- `status`: o que está indexado e quando o catálogo foi atualizado. Se faz mais de 3 meses, sugira `atualizar_catalogo` (NRs mudam várias vezes por ano; versões novas são reindexadas).
- Documento que o usuário obteve legitimamente e é público (ex.: NBR 9050 gratuita), via terminal:
  `uv run --with pypdf python <pasta do pack>/mcps/normas-publicas/normas.py importar arquivo.pdf --titulo "NBR 9050:2020"`.
- Documento digitalizado sem texto (`sem_texto`): avise que a busca não alcança o conteúdo e passe o link.

## Limites e responsabilidade
- O índice reproduz documentos públicos como publicados nos sites oficiais. A versão legal das NRs é a do Diário Oficial da União, e portarias recentes podem ainda não estar consolidadas no PDF.
- Normas estaduais e municipais (Corpo de Bombeiros, código de obras) e normas ABNT não estão incluídas: diga isso quando forem relevantes ao caso.
- A interpretação e aplicação da norma ao caso concreto cabe ao profissional habilitado (engenheiro de segurança, responsável técnico da obra).
