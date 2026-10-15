---
name: quantitativos-sinapi
description: Levanta quantitativos de obra (concreto, fôrmas, aço por bitola, alvenaria com desconto de vãos) a partir dos elementos da estrutura e monta orçamento com composições SINAPI lidas da planilha oficial da Caixa (.xlsx ou .csv), com BDI e exportação para Excel. Use quando o usuário pedir "quantitativo", "levantamento de materiais", "quanto de concreto/aço/fôrma", "orçamento", "SINAPI", "composição de custo", "BDI" ou "planilha orçamentária".
---

# Quantitativos e orçamento SINAPI

Scripts em `scripts/` (stdlib). Rode a partir da pasta desta skill.

## 1. Quantitativos
1. Monte `elementos.json` no formato de `assets/elementos.exemplo.json`. Fontes: as dimensões que o usuário passar, os resultados das skills de cálculo (seções, vãos, barras sugeridas) ou a leitura do projeto. Unidades em **metros**; bitolas em mm; comprimento de barra já com ganchos/transpasse.
2. Rode:
   ```bash
   python3 scripts/quantitativos.py elementos.json --perda-aco 10 --vaos total
   python3 scripts/quantitativos.py elementos.json --formato csv > quantitativos.csv
   ```
3. Mostre a tabela, explique os critérios (`references/criterios-medicao.md`) e **confira as taxas** (aço kg/m³ e fôrma m²/m³) contra os indicadores da referência.

## 2. Orçamento SINAPI
1. Peça ao usuário a planilha SINAPI (UF, mês, desonerado ou não). A UF da obra está em `projeto-contexto.json` quando a ficha da skill `contexto-do-projeto` existir e o caminho do arquivo. Sem planilha, **não informe preços**: códigos e custos mudam todo mês.
2. Se o leitor não achar o cabeçalho: `python3 scripts/sinapi.py colunas --arquivo X.xlsx` e, se precisar, `--aba "<nome>"`.
3. Para cada serviço do quantitativo, busque e **confirme a composição com o usuário** (descrição e unidade compatíveis):
   ```bash
   python3 scripts/sinapi.py buscar --arquivo SINAPI.xlsx --termo "concreto fck 25 bomba"
   ```
4. Monte `itens.json` (`[{"item": "1.1", "codigo": "...", "quantidade": 5.09}]`), peça o BDI e rode:
   ```bash
   python3 scripts/sinapi.py orcar --arquivo SINAPI.xlsx --itens itens.json --bdi 25 --saida orcamento.csv
   ```
5. **Critério de medição**: com o MCP `normas-publicas` conectado, confirme no caderno técnico da composição: `buscar_catalogo` (fonte `sinapi`, ex.: "alvenaria") → `baixar_documentos` → `buscar_normas` ("critério de medição vãos"). Cite o caderno e a página no orçamento.
6. Entregue a tabela, o total e o CSV (abre no Excel com `;`). Anote UF, mês de referência, desoneração e BDI no cabeçalho do orçamento.

## Limites e responsabilidade
- O quantitativo é geométrico e depende dos dados de entrada: não substitui o levantamento sobre o projeto executivo.
- Critérios de medição variam por composição. O Caderno Técnico do SINAPI prevalece sobre os padrões do script (consulte-o pelo MCP `normas-publicas` quando disponível).
- Preços e BDI de obra pública seguem regras próprias (Decreto 7.983/2013 e orientações do TCU). Avise quando o usuário estiver orçando obra pública.
- O orçamento é estimativa técnica de responsabilidade do profissional que o assina.
