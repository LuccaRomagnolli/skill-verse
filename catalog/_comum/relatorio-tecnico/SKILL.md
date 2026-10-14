---
name: relatorio-tecnico
description: Redige e formata documentos técnicos de engenharia — relatório técnico, laudo de vistoria/perícia (NBR 13752), parecer técnico e relatório de inspeção predial (NBR 16747) — com estrutura normativa, tabela de constatações, fotos numeradas com legenda, e entrega em Word (.docx editável) e HTML pronto para PDF. Use quando o usuário pedir "laudo", "relatório técnico", "parecer técnico", "inspeção predial", "relatório de vistoria", "relatório fotográfico" ou quiser transformar anotações e fotos de campo em documento.
---

# Relatórios e laudos técnicos

## Fluxo
1. **Tipo de documento**: identifique (relatório, laudo, parecer, inspeção predial) e use a estrutura de `references/modelos.md`. Se não estiver claro, pergunte qual o objetivo e quem vai ler (cliente, juiz, condomínio, prefeitura).
2. **Coleta**: peça o que faltar, de uma vez — identificação (solicitante, endereço, data), anotações de campo, medições, fotos (caminhos dos arquivos) e o responsável técnico. Não invente medições, datas, registros profissionais ou números de ART: deixe `[preencher]`.
3. **Redação**: escreva o `.md` (cabeçalho de metadados + seções; partida em `assets/laudo.exemplo.md`).
   - Uma linha de constatação por anomalia, com local inequívoco e medida.
   - Fotos: `![legenda descritiva](fotos/arquivo.jpg)`, caminho relativo ao `.md`. Cite as figuras no texto.
   - Causas como prováveis, salvo quando houver ensaio. Separe fato, análise e conclusão.
   - `---` sozinho numa linha força quebra de página.
4. **Gerar**:
   ```bash
   python3 scripts/gerar_relatorio.py caminho/laudo.md --saida caminho/saida/
   ```
   Saídas: `.docx` (edição final no Word/Google Docs, fotos embutidas) e `.html` (abrir no navegador → Imprimir → PDF A4).
5. **Revisão**: liste os `[preencher]` pendentes e as afirmações que dependem de confirmação do responsável.

Se o laudo for de estrutura de concreto e o usuário quiser verificar uma peça, use a skill `concreto-armado-nbr6118` e cite o resultado no documento.

## Limites e responsabilidade
- O documento é redigido a partir das informações fornecidas pelo usuário. A vistoria, as medições e as conclusões técnicas são do profissional que assina.
- Laudos e pareceres exigem profissional habilitado e ART/RRT. Perícia judicial segue também o CPC e as orientações do juízo.
- Não emita conclusão sobre segurança estrutural sem dados que a sustentem. Nesses casos, recomende investigação complementar (ensaios, projeto, monitoramento).
