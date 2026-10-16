---
name: memorial-de-calculo
description: Reúne resultados rastreáveis de concreto, vento e combinações em memorial estrutural DOCX, HTML e Markdown, com hipóteses, fontes e pendências de revisão. Use quando pedirem memorial de cálculo, documentação de dimensionamento ou anexo técnico do projeto.
---

# Memorial de cálculo

O script `scripts/gerar_memorial.py` (stdlib) monta o documento. Você coleta os dados da obra, organiza os resultados e revisa o texto final. Antes, rode `contexto-do-projeto` → `resumo` e confira município, revisão, decisões, fontes, resultados disponíveis e pendências. Não misture elementos de revisões diferentes da estrutura.

## Passo a passo
1. **Resultados**: cada elemento deve estar em `resultados/<NOME>.json`, gerado pelos scripts com `--formato json`. Nomeie pelo identificador do projeto (`L1.json`, `V3.json`, `P12.json`, `vento.json`, `combinacoes.json`). Se o usuário calculou algo na conversa sem salvar, rode de novo com os dados confirmados. Confira entrada, unidade, `status_normativo`, alertas e revisão de cada JSON; resultado sem procedência vira pendência.
2. **Dados da obra**: copie `assets/projeto.exemplo.json` para a pasta de trabalho como `projeto.json` e preencha com o usuário: obra, endereço, proprietário, responsável técnico, registro (CREA/CAU), ART, revisão, materiais, ações (texto) e considerações. Campos vazios são omitidos. **Não invente** nº de registro ou de ART: deixe vazio se ele não informar.
3. **Gerar** (com `--contexto` quando existir a ficha da skill `contexto-do-projeto`: entram município/UF, classe de agressividade e a legislação local consultada, com links):
   ```bash
   python3 scripts/gerar_memorial.py --projeto projeto.json --resultados resultados/ --saida memorial/ --contexto projeto-contexto.json
   ```
4. **Revisar com o usuário**: liste os elementos incluídos e os **alertas** que apareceram (seção "Observações" de cada elemento). Diferencie correção comprovada de justificativa do projetista. O memorial lista a NBR 6118:2026 como referência de revisão, mas os resultados ainda vêm de critérios implementados em 2023; mantenha visível a pendência de confronto integral. Verifique com o responsável a aplicabilidade da avaliação técnica independente do item 5.3 e registre o parecer quando houver.
5. **Entregar**: `MEMORIAL.docx` (editável no Word/Google Docs), `MEMORIAL.html` (abrir no navegador → Imprimir → Salvar como PDF, A4) e `MEMORIAL.md`.
6. **Persistir**: registre os três arquivos com `contexto.py artefato --tipo memorial --estado em-revisao` e as verificações ainda abertas com `pendencia`. Só marque `revisado` após conferência do profissional habilitado; na próxima sessão, releia o resumo e a revisão antes de regenerar.

Ordem no documento: ações (vento, combinações) → lajes → vigas → pilares, em ordem natural (L2 antes de L10).

## Personalização
- `metodos`, `acoes`, `consideracoes`, `normas_extras` em `projeto.json` substituem ou complementam os textos padrão.
- Logo, carimbo e layout próprios do escritório: edite o .docx gerado (o script produz estilos "Title", "Heading 1/2" para facilitar).

## Limites e responsabilidade
- O memorial reproduz o que os scripts calcularam. Ele não substitui as plantas de forma e armação nem a revisão do responsável técnico.
- Não inclua a emenda ou o texto integral de normas ABNT no memorial. Cite número, edição, item e resultado da verificação feita com exemplar licenciado.
- Assinatura e ART são do engenheiro responsável. Nunca preencha dados profissionais que o usuário não forneceu.
