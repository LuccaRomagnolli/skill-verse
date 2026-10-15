---
name: memorial-de-calculo
description: Gera o memorial de cálculo estrutural em Word (.docx editável), HTML pronto para imprimir em PDF e Markdown, a partir dos resultados JSON das skills de cálculo (concreto armado, vento, combinações), com identificação da obra, normas, materiais, ações, métodos, memória passo a passo de cada elemento e assinatura. Use quando o usuário pedir "memorial de cálculo", "memorial descritivo do cálculo", "documentar o cálculo", "relatório do dimensionamento", "anexar à ART" ou quiser juntar os resultados num documento.
---

# Memorial de cálculo

O script `scripts/gerar_memorial.py` (stdlib) monta o documento. Você coleta os dados da obra, organiza os resultados e revisa o texto final.

## Passo a passo
1. **Resultados**: cada elemento deve estar em `resultados/<NOME>.json`, gerado pelos scripts com `--formato json`. Nomeie pelo identificador do projeto (`L1.json`, `V3.json`, `P12.json`, `vento.json`, `combinacoes.json`). Se o usuário calculou algo na conversa sem salvar, rode de novo com `--formato json > resultados/<NOME>.json`.
2. **Dados da obra**: copie `assets/projeto.exemplo.json` para a pasta de trabalho como `projeto.json` e preencha com o usuário: obra, endereço, proprietário, responsável técnico, registro (CREA/CAU), ART, revisão, materiais, ações (texto) e considerações. Campos vazios são omitidos. **Não invente** nº de registro ou de ART: deixe vazio se ele não informar.
3. **Gerar** (com `--contexto` quando existir a ficha da skill `contexto-do-projeto`: entram município/UF, classe de agressividade e a legislação local consultada, com links):
   ```bash
   python3 scripts/gerar_memorial.py --projeto projeto.json --resultados resultados/ --saida memorial/ --contexto projeto-contexto.json
   ```
4. **Revisar com o usuário**: liste os elementos incluídos e os **alertas** que apareceram (seção "Observações" de cada elemento). Alerta não resolvido (flecha acima do limite, armadura dupla etc.) deve ser resolvido ou justificado no campo `consideracoes` antes de entregar.
5. **Entregar**: `MEMORIAL.docx` (editável no Word/Google Docs), `MEMORIAL.html` (abrir no navegador → Imprimir → Salvar como PDF, A4) e `MEMORIAL.md`.

Ordem no documento: ações (vento, combinações) → lajes → vigas → pilares, em ordem natural (L2 antes de L10).

## Personalização
- `metodos`, `acoes`, `consideracoes`, `normas_extras` em `projeto.json` substituem ou complementam os textos padrão.
- Logo, carimbo e layout próprios do escritório: edite o .docx gerado (o script produz estilos "Title", "Heading 1/2" para facilitar).

## Limites e responsabilidade
- O memorial reproduz o que os scripts calcularam. Ele não substitui as plantas de forma e armação nem a revisão do responsável técnico.
- Assinatura e ART são do engenheiro responsável. Nunca preencha dados profissionais que o usuário não forneceu.
