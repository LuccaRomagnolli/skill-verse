---
name: quantitativos-sinapi
description: Mede concreto, fôrmas, aço e alvenaria a partir de projeto rastreável e monta orçamento com composições SINAPI da Caixa, UF, mês, regime e BDI. Use quando pedirem quantitativos, orçamento, SINAPI, custo de obra ou planilha orçamentária.
---

# Quantitativos e orçamento SINAPI

Scripts em `scripts/` (stdlib). Rode a partir da pasta desta skill.

Retome pela ficha (`contexto-do-projeto` → `resumo`): UF da obra, revisão dos desenhos/modelos, decisões de medição e pendências. Antes de medir, confirme se o modelo cobre todos os pavimentos e se houve mudanças após o último cálculo.

## 1. Quantitativos
1. Monte `elementos.json` no formato de `assets/elementos.exemplo.json`. Anote a origem de cada elemento: planta/revisão, modelo BIM, medida do usuário ou resultado de cálculo. Unidades em **metros**; bitolas em mm; comprimento de barra já com ganchos/transpasse. Armadura sugerida pelo script de concreto não equivale a tabela de aço executiva; sem detalhamento, marque a quantidade de aço como estimativa.
2. Rode:
   ```bash
   python3 scripts/quantitativos.py elementos.json --perda-aco 10 --vaos total
   python3 scripts/quantitativos.py elementos.json --formato csv > quantitativos.csv
   ```
3. Mostre a tabela, explique os critérios (`references/criterios-medicao.md`) e **confira as taxas** (aço kg/m³ e fôrma m²/m³) contra os indicadores da referência. Registre divergências, sobreposições ou elementos ausentes como pendência.

## 2. Orçamento SINAPI
1. Use a planilha oficial SINAPI da Caixa do **mês, UF e regime de encargos** definidos para a obra. Desde 2025, a Caixa reúne relatórios mensais em arquivos ZIP nacionais com planilhas XLSX; localize a aba e a UF corretas antes de orçar. Sem arquivo e referência comprovados, **não informe preços**: códigos e custos mudam todo mês.
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
6. Entregue a tabela, o total e o CSV (abre no Excel com `;`). Anote UF, mês de referência, desoneração, BDI, versão da base e critérios de medição. Compare unidade da composição com a medida; composição incompatível não recebe preço por aproximação.
7. Registre `elementos.json`, quantitativos e orçamento com `contexto.py artefato --estado em-revisao`, e registre no contexto a composição escolhida e o critério quando afetarem a medição. Na retomada, reorçe apenas após checar revisão do projeto e mês da base.

## Limites e responsabilidade
- O quantitativo é geométrico e depende dos dados de entrada: não substitui o levantamento sobre o projeto executivo.
- Critérios de medição variam por composição. O Caderno Técnico do SINAPI prevalece sobre os padrões do script (consulte-o pelo MCP `normas-publicas` quando disponível).
- Preços e BDI de obra pública seguem regras próprias (Decreto 7.983/2013 e orientações do TCU). Avise quando o usuário estiver orçando obra pública.
- O orçamento é estimativa técnica de responsabilidade do profissional que o assina.
