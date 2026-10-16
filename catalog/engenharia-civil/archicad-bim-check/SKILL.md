---
name: archicad-bim-check
description: Audita o modelo BIM aberto no ArchiCAD 29 via MCP — prontidão de entrega e de exportação IFC (classificação de elementos, numeração de ambientes, propriedades IFC como LoadBearing/IsExternal, padrão de layers), destaca os elementos com falha no ArchiCAD, cria issues e exporta BCF para compatibilização com estrutura e instalações. Use quando o usuário pedir "auditar o modelo", "checar o modelo", "pronto para IFC?", "compatibilização", "BCF", "issues", "elementos sem classificação", "QA do ArchiCAD" ou mencionar ArchiCAD/BIM.
---

# Auditoria BIM no ArchiCAD

O MCP `archicad` conversa com o ArchiCAD 29 **aberto com o projeto**. O add-on Tapir habilita IFC, issues, destaque de elementos e BCF. Sem ele, essas ferramentas degradam (avise o usuário).

> ⚠️ **Peça para salvar o projeto antes da auditoria.** A leitura de propriedades pode travar o ArchiCAD 29 (falha do próprio ArchiCAD). Não rode auditoria sem esse "ok".

Antes da conexão, leia `contexto-do-projeto` → `resumo` quando existir. Identifique revisão do modelo, município, fontes e pendências. Sem ficha, proponha iniciar uma. A conexão só é operável se `get_project_info` retornar o projeto aberto; servidor MCP iniciado isoladamente não basta.

## Fluxo
1. **Contexto**: `get_project_info` (versão, pavimentos, Tapir) e `get_model_summary` (contagem por tipo). Em modelos grandes, não use `include_layer_story`. Anote contagens e arquivo/revisão de entrada.
2. **Regras**: `list_rules`. Confira se as regras de `~/SkillVerse/archicad-regras/` carregaram sem erro (formato em `references/regras.md`). Se o sistema de classificação do escritório não for "ARCHICAD Classification", ajuste o YAML (use `search_definitions` para achar o nome exato) e peça para reiniciar o agente.
3. **Plano e auditoria**: escolha regras, escopo, pavimentos, limite por lote e destino do relatório antes de executar. Rode `audit_delivery_readiness` com `ruleset`:
   - `entrega`: prancha/aprovação (ambientes numerados, classificação).
   - `ifc`: exportação para o calculista e projetistas (ou `verify_ifc_export_readiness`).
   - `padrao`: padrão interno de layers.
   - sem `ruleset`: tudo.
4. **Relatório ao usuário**: veredito, nota, e uma tabela **regra → quantidade de falhas → o que fazer no ArchiCAD** (ex.: "Classificação: selecione as paredes → Configurações → Classificação e Propriedades"). Erros (`error`) primeiro.
5. **Ação**, com confirmação do usuário a cada passo:
   - `highlight_failures` `{rule_id}`: destaca no ArchiCAD.
   - `create_issues_from_failures` `{rule_id}`: cria issue com os elementos anexados.
   - `export_issues_bcf` `{bcf_path}`: exporta tudo em BCF (sobrescreve o arquivo; confirme o caminho).
6. **Correção automática** (opcional): `set_element_data`/`edit_classifications` alteram o modelo. Só com pedido explícito, num conjunto pequeno de elementos, depois de mostrar exatamente o que vai mudar. Sugira salvar uma cópia antes.
7. **Inspeção e registro**: depois de cada lote, releia a amostra dos elementos alterados e rode novamente as regras afetadas. Salve o PLN/PLA no ArchiCAD, confirme o BCF exportado por leitura/importação e registre relatório, modelo e BCF na ficha com `contexto.py artefato`. Falha de propriedade, regra indisponível, clash não verificado ou exigência municipal sem fonte vira `pendencia` com responsável.

## Conformidade com a legislação local
Com a ficha do projeto (`projeto-contexto.json`, skill `contexto-do-projeto`), confira o modelo contra exigências **numéricas** do código de obras e do zoneamento do município:
1. Levante os valores na fonte registrada na ficha (ou no índice `normas-publicas`, `buscar_normas(fonte='local')`): área mínima e dimensão mínima por compartimento, pé-direito, iluminação/ventilação, taxa de ocupação, permeabilidade. Anote o artigo de cada valor.
2. Verifique com `find_elements` (ex.: zonas cujo nome contém "Dormit" e com área `less` que o mínimo; valores em m e m²). Use `search_definitions` para achar o endereço exato da propriedade de área/altura no template do usuário.
3. Relate em tabela `Exigência | Artigo | Elementos fora | Ação`. Com confirmação do usuário, crie issues com `create_issue` + `attach_elements_to_issue` e exporte BCF.
4. Valor que não foi encontrado em fonte oficial **não vira verificação**: entra como pendência na ficha.

## Perguntas típicas
- "Quantas portas tem no 2º pavimento?" → `find_elements` com `element_types: [Door]` e comparação `story`.
- "Quais paredes são estruturais?" → `find_elements` com a propriedade IFC/usuário correspondente (ache o endereço com `search_definitions`).
- Integração com a estrutura: depois do IFC aprovado, use a skill `concreto-armado-nbr6118` para as peças e a `quantitativos-sinapi` para os volumes.

## Limites e responsabilidade
- A auditoria verifica **dados** do modelo (preenchimento, classificação, nomenclatura) e, quando houver ficha do projeto, os parâmetros numéricos da legislação local que foram levantados em fonte oficial. Não substitui a análise da prefeitura nem verifica interferências físicas (clash).
- Alterações no modelo são feitas em nome do usuário: sempre com confirmação e com o projeto salvo.
- Requisitos: ArchiCAD 29 aberto; Tapir recomendado. Outras versões do ArchiCAD não são suportadas por este MCP.
