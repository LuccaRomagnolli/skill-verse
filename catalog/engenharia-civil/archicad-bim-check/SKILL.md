---
name: archicad-bim-check
description: Audita o modelo BIM aberto no ArchiCAD 29 via MCP — prontidão de entrega e de exportação IFC (classificação de elementos, numeração de ambientes, propriedades IFC como LoadBearing/IsExternal, padrão de layers), destaca os elementos com falha no ArchiCAD, cria issues e exporta BCF para compatibilização com estrutura e instalações. Use quando o usuário pedir "auditar o modelo", "checar o modelo", "pronto para IFC?", "compatibilização", "BCF", "issues", "elementos sem classificação", "QA do ArchiCAD" ou mencionar ArchiCAD/BIM.
---

# Auditoria BIM no ArchiCAD

O MCP `archicad` conversa com o ArchiCAD 29 **aberto com o projeto**. O add-on Tapir habilita IFC, issues, destaque de elementos e BCF. Sem ele, essas ferramentas degradam (avise o usuário).

> ⚠️ **Peça para salvar o projeto antes da auditoria.** A leitura de propriedades pode travar o ArchiCAD 29 (falha do próprio ArchiCAD). Não rode auditoria sem esse "ok".

## Fluxo
1. **Contexto**: `get_project_info` (versão, pavimentos, Tapir) e `get_model_summary` (contagem por tipo). Em modelos grandes, não use `include_layer_story`.
2. **Regras**: `list_rules`. Confira se as regras de `~/SkillVerse/archicad-regras/` carregaram sem erro (formato em `references/regras.md`). Se o sistema de classificação do escritório não for "ARCHICAD Classification", ajuste o YAML (use `search_definitions` para achar o nome exato) e peça para reiniciar o agente.
3. **Auditoria**: `audit_delivery_readiness` com `ruleset`:
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

## Perguntas típicas
- "Quantas portas tem no 2º pavimento?" → `find_elements` com `element_types: [Door]` e comparação `story`.
- "Quais paredes são estruturais?" → `find_elements` com a propriedade IFC/usuário correspondente (ache o endereço com `search_definitions`).
- Integração com a estrutura: depois do IFC aprovado, use a skill `concreto-armado-nbr6118` para as peças e a `quantitativos-sinapi` para os volumes.

## Limites e responsabilidade
- A auditoria verifica **dados** do modelo (preenchimento, classificação, nomenclatura). Ela não verifica geometria, interferências físicas (clash) nem conformidade com código de obras.
- Alterações no modelo são feitas em nome do usuário: sempre com confirmação e com o projeto salvo.
- Requisitos: ArchiCAD 29 aberto; Tapir recomendado. Outras versões do ArchiCAD não são suportadas por este MCP.
