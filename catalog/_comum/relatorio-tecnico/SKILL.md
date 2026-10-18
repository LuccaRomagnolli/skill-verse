---
name: relatorio-tecnico
description: Organiza evidências de vistoria e redige relatório, laudo, parecer ou inspeção predial com fotos, constatações, fontes e pendências, gerando DOCX e HTML. Use quando pedirem laudo, parecer, relatório técnico ou transformação de anotações e fotos de campo em documento.
---

# Relatórios e laudos técnicos

## Fluxo
Se houver `projeto-contexto.json`, comece com `contexto-do-projeto` → `resumo`: confira endereço, município/UF, revisão, fontes oficiais e pendências. Em trabalho isolado, confirme esses dados diretamente com o usuário.
1. **Tipo de documento**: identifique (relatório, laudo, parecer, inspeção predial) e use a estrutura de `references/modelos.md`. Se não estiver claro, pergunte qual o objetivo e quem vai ler (cliente, juiz, condomínio, prefeitura).
2. **Coleta**: peça o que faltar, de uma vez — identificação (solicitante, endereço, data), anotações de campo, medições com unidade e método, fotos (caminhos dos arquivos) e responsável técnico. Identifique quem observou cada fato e quando. Não invente medições, datas, registros profissionais ou números de ART: deixe `[preencher]`.
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
5. **Revisão**: liste os `[preencher]` pendentes, verifique se cada foto corresponde ao local descrito e se cada conclusão é sustentada por evidência. Separe fato observado, hipótese causal e recomendação; opinião não vira constatação medida.
6. **Continuidade**: registre `.md`, `.docx` e `.html` com `contexto.py artefato --tipo relatorio --estado em-revisao` quando houver ficha; registre lacunas de vistoria e ensaios com `pendencia`. Só marque `revisado` após o profissional conferir e assumir as conclusões.

Quando o documento tratar de segurança do trabalho, canteiro, trabalho em altura, espaço confinado ou de critérios de obras rodoviárias, e o MCP `normas-publicas` estiver conectado, fundamente as constatações com a skill `consulta-normas`: cite o item literal da NR/DNIT e a página. Isso dá força técnica ao laudo.

Se existir `projeto-contexto.json` (skill `contexto-do-projeto`), use o município/UF e a legislação local registrada na identificação e na fundamentação do documento.

Se o laudo exigir verificação de uma peça, registre a necessidade de cálculo e parecer do profissional responsável; cite somente resultados fornecidos e revisados.

## Limites e responsabilidade
- O documento é redigido a partir das informações fornecidas pelo usuário. A vistoria, as medições e as conclusões técnicas são do profissional que assina.
- Laudos e pareceres exigem profissional habilitado e ART/RRT. Perícia judicial segue também o CPC e as orientações do juízo.
- Não emita conclusão sobre segurança estrutural sem dados que a sustentem. Nesses casos, recomende investigação complementar (ensaios, projeto, monitoramento).
