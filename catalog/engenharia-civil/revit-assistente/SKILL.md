---
name: revit-assistente
description: Opera o Autodesk Revit pelo chat via MCP. Lê a vista, a seleção e os elementos do modelo; cria níveis, eixos, pilares, vigas, lajes, paredes, ambientes, cotas e tags; lança a estrutura a partir do cálculo (seções de pilares e vigas, espessuras de lajes) com os tipos certos; extrai quantitativos de concreto por nível e material para orçamento; colore e isola elementos para revisão; exporta IFC para o calculista e roda C# da Revit API com confirmação. Use quando o usuário mencionar Revit, RVT, família, tipo, nível, modelo BIM estrutural ou disser "lança a estrutura no Revit", "modela esses pilares", "cria os níveis e eixos", "quantos m³ de concreto tem no modelo", "pinta as vigas por seção", "exporta o IFC para o TQS", "cria uma tabela de pilares" ou "faz isso na Revit API".
---

# Assistente Revit

MCP `revit` (mcp-servers-for-revit). As ferramentas recebem **milímetros e graus**, e o "nível" nas criações é a **cota do nível em mm**. Tabela completa com parâmetros: `references/mcp-ferramentas.md`.

## 1. Antes de qualquer coisa
0. Leia `contexto-do-projeto` → `resumo` se houver ficha. Identifique decisões, arquivos e pendências; se não houver, inicie uma. Peça origem do modelo, revisão, planta/eixos e resultados de cálculo. Marque dados assumidos como hipótese.
1. `get_current_view_info`. Se falhar com erro de conexão, peça ao usuário: Revit aberto **com o projeto**, faixa Suplementos → "Revit MCP Plugin" → **Revit MCP Switch** (ligar). Primeira vez: **Settings** → marcar todos os comandos → salvar. Outros sintomas: `references/solucao-de-problemas.md`.
2. Entenda o modelo antes de criar: `analyze_model_statistics` (o que existe) e níveis existentes (receita "Listar níveis" em `references/revit-api-csharp.md`, ou `ai_element_filter` com `filterCategory: "OST_Levels"`).
3. Confirme com o usuário: **critério de nível** (topo da laje estrutural × piso acabado), unidade do projeto e se há padrão de nomes do escritório.
4. Antes de alterar o RVT, descreva o lote (categoria, níveis, quantidade esperada, tipos, unidades e arquivo de destino), salve uma cópia ou ponto de recuperação e confirme operações destrutivas. Releia estatísticas, vista e IDs após cada lote; compare criado × esperado e examine avisos.

## 2. Lançar a estrutura a partir do cálculo
Quando houver `modelo-estrutural.json`, confira que sua revisão e SHA-256 coincidem com o manifesto SkyCiv e gere a entrada legada sem alterar projetos antigos:
```bash
python3 ../modelo-estrutural/scripts/modelo.py revit modelo-estrutural.json --saida lancamento.json
```
Registre o hash e os IDs das peças de entrada para comparar com os `elementId` reais após a criação. A geometria BIM não transfere apoios, cargas ou critérios de análise.

Fonte dos dados: skill `concreto-armado-nbr6118` (seções) e a planta (posições). Monte o JSON no formato de `assets/lancamento.exemplo.json` (posições em m, seções em cm) e gere as chamadas:
```bash
python3 scripts/lancamento.py lancamento.json --saida lancamento-ops.json
```
O resultado traz:
- `tipos_csharp`: C# que garante um tipo por seção (`P 20x50`, `V 15x45`) duplicando uma família retangular do projeto. **Mostre, peça "sim"** e rode com `send_code_to_revit`. Ele devolve `{tipos: {nome: id}, avisos}`.
- `ops`: chamadas em ordem (`create_level` → eixos → pilares → vigas → lajes). Substitua cada `"$tipo:<nome>"` pelo id devolvido. Eixos irregulares vêm como C# (`requer_confirmacao: true`). Antes de `create_level`, retire da lista os níveis que já existem.
- `avisos`: níveis não declarados, pilar com topo abaixo da base, viga de comprimento zero. Resolva antes de executar.

Depois de cada lote: leia os avisos do retorno do MCP ("Defaulted to…" = tipo errado), selecione os ids criados (`operate_element` `Select`) e confira em 3D. Para gravar a Marca (P1, V1…) com os ids devolvidos: `python3 scripts/lancamento.py --marcar ids.json --saida marcas.json` → `send_code_to_revit` com `marcas_csharp`.
Salve o RVT pelo Revit e registre na ficha o caminho, revisão, IDs/quantidades criadas e pendências (ex.: tipo substituído, eixo incerto, interferência ou modelo analítico não conferido). Não declare concluído só porque o lote retornou sucesso.

Fluxo completo de modelagem (vínculos, níveis, fundações, unir geometrias, modelo analítico): `references/modelagem-estrutural.md`. Tipos, parâmetros e classificação: `references/familias-e-parametros.md`.

## 3. Consultar e revisar o modelo
- "Esse pilar aqui": `get_selected_elements`.
- Busca: `ai_element_filter` (categoria, tipo, caixa em mm, até 50 por chamada) e `get_current_view_elements`.
- Revisão visual: `color_elements` por `Tipo`/`Material`/`Marca` (ex.: seções diferentes destacadas), `operate_element` `Isolate`/`Highlight`/`ResetIsolate`.
- Ambientes: `export_room_data` (áreas para quadro de áreas e cargas por uso na skill `cargas-combinacoes`).

## 4. Quantitativos para orçamento
1. Visão rápida: `get_material_quantities` com `categoryFilters` estruturais.
2. Por peça/nível: receita "Volume de concreto por nível" (`references/revit-api-csharp.md`). Mostre o código e rode com confirmação. O retorno vem em **ft³**.
3. Converta com `python3 scripts/revit_unidades.py <valor> ft3 m3` (ou em lote no script de quantitativos). **Nunca converta nem some de cabeça.**
4. Orce com a skill `quantitativos-sinapi`.

## 5. Anotar e documentar
- Cotas: `create_dimensions` (pontos em mm ou `elementIds`). Tags: `tag_all_walls`, `tag_all_rooms` na vista ativa.
- Tabelas (quadro de pilares, de lajes): receita de `ViewSchedule` em `revit-api-csharp.md`.
- Pranchas finais em CAD: exportar DWG pelo Revit e montar com `autocad-assistente`, se o escritório trabalhar assim.

## 6. IFC e outros softwares
IFC para o calculista/TQS, vínculo do IFC do TQS, troca com ArchiCAD, AutoCAD e SolidWorks: `references/ifc-interoperabilidade.md`. A exportação pelo agente é a receita "Exportar IFC" (pasta informada pelo usuário).

## 7. Código C# (Revit API)
Para o que não tem ferramenta própria (níveis, materiais, schedules, unir geometrias, IFC, parâmetros): `send_code_to_revit`. Regras do template (variável `document`, `return` obrigatório, sem `Transaction` própria, unidades em pés) e receitas: `references/revit-api-csharp.md`. **Sempre mostre o código e peça "sim"**. Para alterações em massa, rode antes uma versão que só conta o que seria afetado.

## Limites e responsabilidade
- O modelo gerado é de **apoio** (geometria e quantitativos). Dimensionamento e detalhamento oficiais vêm do cálculo estrutural (skill `concreto-armado-nbr6118`, TQS etc.) e da revisão do engenheiro, que assina como responsável técnico.
- Resultados do modelo analítico do Revit não substituem o software de cálculo.
- `send_code_to_revit` e `delete_element` alteram o projeto: só com confirmação explícita. Recomende salvar (ou trabalhar numa cópia) antes de lotes grandes, já que o desfazer do Revit cobre a transação inteira.
- Quantitativos dependem da modelagem (uniões, sobreposições). Informe o critério usado e confira com o critério de medição do SINAPI.
- Requer Windows com Revit 2020–2026 e o add-in instalado pelo pack. Sem o Revit aberto, nenhuma ferramenta funciona.
- A exportação IFC deve ser reaberta/inspecionada no destino; geometria, classes, unidades, coordenadas e quantitativos requerem conferência técnica independente.
