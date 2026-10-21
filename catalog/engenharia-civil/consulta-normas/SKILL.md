---
name: consulta-normas
description: Consulta NRs, documentos DNIT, cadernos SINAPI e documentos públicos locais pelo MCP normas-publicas, citando item, página, link e vigência para orientar projeto, obra ou medição. Use quando pedirem exigências normativas, canteiro, segurança, especificações DNIT ou critérios SINAPI; para NBR, consulte apenas metadados e a cópia licenciada do usuário.
---

# Consulta a normas e boas práticas

O MCP `normas-publicas` mantém um índice local (SQLite) com documentos **públicos**, baixados das fontes oficiais: NRs do MTE, DNIT/IPR e SINAPI/Caixa. Ferramentas: `buscar_normas`, `buscar_catalogo`, `baixar_documentos`, `ler_pagina`, `localizar_item`, `atualizar_catalogo`, `status`.

**Normas ABNT não estão no índice** (protegidas por direito autoral). Nunca invente nem "reconstrua" texto de NBR. Para NBR, use as sínteses em `references/` das skills de cálculo, com o número do item, e diga que o texto oficial está na norma.

## Fluxo de consulta
0. **Ficha do projeto**: se existir `projeto-contexto.json`, use `contexto-do-projeto` → `resumo` para ler uso, porte, local, fontes e pendências. Sem ficha, pergunte o município/UF e o uso antes de declarar aplicabilidade. Confirme `status` do índice e a data do documento antes da busca; uma NR pode ter portaria posterior ao PDF indexado.
1. **Assunto → fonte**: use `references/mapa-de-fontes.md` para saber onde procurar.
2. **Buscar no texto**: `buscar_normas` com termos técnicos (substantivos, sem frases). Ex.: `"guarda-corpo travessão rodapé"`, `"escavação talude 1,25"`, `"critério medição alvenaria vãos"`.
3. **Sem resultado bom?** `buscar_normas` já sugere documentos do catálogo ainda não baixados → `baixar_documentos` com os ids pertinentes (no máximo 10; diga ao usuário o que vai baixar) → repita a busca.
4. **Texto exato**: `localizar_item` ou `ler_pagina`; confira título, data, item e página no documento recuperado. Cite só o trecho curto necessário, seguido do link oficial. Se o item não existir ou a versão for duvidosa, registre a questão como pendência; não reconstrua o texto.
5. **Responder**: exigência em linguagem direta + documento/edição + item + página + URL oficial + data de acesso. Para NR, ressalve quando houver portaria recente ainda não incorporada ao PDF; confirme a vigência no MTE/DOU.

## Do requisito ao projeto (boas práticas)
Quando o usuário estiver **projetando ou planejando** (não só perguntando), converta as exigências em entregáveis:
- **Checklist** em tabela: `Requisito | Fonte (item) | Como atender no projeto/obra | Responsável | OK?`.
- **Canteiro (NR-18)**: áreas de vivência dimensionadas pelo efetivo, proteção de periferia, aberturas no piso, escadas e rampas, instalações elétricas provisórias (NR-10), sinalização, plano de movimentação de cargas. Se o AutoCAD estiver conectado, ofereça desenhar o layout com a skill `autocad-assistente`.
- **Orçamento**: o critério de medição vem do caderno técnico SINAPI da composição. Use junto com a skill `quantitativos-sinapi`.
- **Rodovias/pavimentos**: ES (execução e controle) + EM (material) + ME (ensaios), com a frequência de ensaios para o plano de controle tecnológico.
- Sempre diferencie **obrigação normativa** (tem item) de **boa prática** (recomendação de manual/guia ou experiência). Escreva "boa prática" quando não houver item que obrigue.
- No projeto em andamento, registre a fonte e cada requisito efetivamente aplicável na ficha com `contexto.py fonte` e `requisito`; registre incertezas com `pendencia` e o checklist produzido com `artefato`. Leia `contexto-do-projeto/references/continuidade.md` quando for salvar a etapa.

## Normas locais (município/estado)
Código de obras, plano diretor, ITs do Corpo de Bombeiros e normas de concessionárias são pesquisados na internet pela skill `contexto-do-projeto`, a partir do município da obra. Documentos públicos encontrados entram no índice com `importar_documento_publico(url, titulo, esfera)` e passam a ser consultados aqui com `buscar_normas(fonte='local')`. O servidor recusa sites de cópias e exemplares de NBR.

## Manutenção do índice
- `status`: o que está indexado e quando o catálogo foi atualizado. Antes de confiar em item decisivo, confira se há publicação mais recente na fonte oficial; `atualizar_catalogo` refaz o índice quando necessário.
- Documento comprovadamente público que o usuário obteve de fonte oficial (por exemplo, lei municipal, IT ou manual público), via `importar_documento_publico`. Não use esse fluxo para exemplares de NBR, mesmo quando o acesso individual for gratuito: direitos de distribuição e indexação não se presumem.
- Documento digitalizado sem texto (`sem_texto`): avise que a busca não alcança o conteúdo e passe o link.

## Limites e responsabilidade
- O índice reproduz documentos públicos como publicados nos sites oficiais. A versão legal das NRs é a do Diário Oficial da União, e portarias recentes podem ainda não estar consolidadas no PDF.
- Normas estaduais e municipais só estarão no índice se forem importadas de fonte oficial para aquela obra. Normas ABNT não são distribuídas pelo MCPcad; uma cópia licenciada fornecida pelo usuário não vira conteúdo distribuível.
- A interpretação e aplicação da norma ao caso concreto cabe ao profissional habilitado (engenheiro de segurança, responsável técnico da obra).
