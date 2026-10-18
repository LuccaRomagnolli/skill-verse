---
name: archicad-assistente
description: Modela e audita estruturas no Archicad 29 ou 30 via MCP e Tapir, usando o modelo estrutural versionado. Use quando o usuário escolher Archicad como destino BIM, pedir criação de pilares, vigas ou lajes, inspeção do PLN, exportação IFC ou issues BCF.
---

# Assistente Archicad

O MCP `archicad` 0.8.0 em modo `full` expõe `create_elements` para pilares/lajes, e o gateway Tapir `CreateBeams` para vigas. Tapir é obrigatório para criação, pavimentos, IFC e issues. O arquivo de entrada é o mesmo da skill `modelo-estrutural` e deve corresponder à revisão analisada na SkyCiv. Leia [references/conexao.md](references/conexao.md) ao diagnosticar a conexão, múltiplas instâncias ou o Public MCP do Archicad 30.

## Conexão e preparação

1. Leia `projeto-contexto.json` e o manifesto da análise SkyCiv. Confira `sha256_entrada` e revisão. Inicie com `list_instances`; selecione a porta do PLN certo e confirme `project_open`, `tapir_available`, versão e build. Salve uma cópia do PLN antes de auditorias ou alterações. Não faça o primeiro teste em projeto de cliente ou Teamwork.
2. Use `execute_read_api_command` com `name: GetStories` para mapear cada nível e cota do modelo ao `floorIndex` real. Use `list_attributes` com `BuildingMaterial` e selecione o GUID do material do template. Consulte `GetFavoritesByType` para a laje e escolha um favorito **Basic** cujo material corresponda ao GUID configurado. Preencha um arquivo como `assets/config.exemplo.json`; substitua todos os valores de exemplo e confira no programa.
3. Grave a porta escolhida em `archicad-config.json` quando houver mais de uma instância. Gere o plano: `python3 scripts/lancamento.py modelo-estrutural.json --config archicad-config.json --saida archicad-ops.json`. O script recusa porta, pavimento ou material sem correspondência. Ele não roda o Archicad.

## Modelar

1. Leia as operações e apresente ao usuário quantidade, níveis, seções, material, porta e revisão por lote. `create_elements` com `dry_run=true` e `execute_write_api_command` com `confirm=false` mostram o payload sem gravar. Confira com `describe_api_command CreateBeams` e resolva qualquer erro antes da execução.
2. Após confirmação para o lote no PLN salvo, repita com `dry_run=false` ou `confirm=true`. Crie pilares, depois vigas, depois lajes. O retorno `elements` deve conter um GUID por ID esperado; pare em erro parcial, grave o mapeamento ID → GUID e não repita o lote inteiro às cegas.
3. Execute `GetDetailsOfElements` para os GUIDs na ordem de `verificacao_pos_criacao.ids_na_ordem`. Salve a resposta e rode `python3 scripts/verificar_lancamento.py archicad-ops.json mapeamento.json detalhes.json`. O ensaio no Archicad 30 mostrou que uma laje criada a partir do padrão Composite manteve 30 cm mesmo quando o payload pediu 15 cm. Exija `structureType=Basic`, espessura, material, contorno e nível corretos. Se divergirem, monte `ModifySlabs` com o GUID e os valores de `correcao_lajes_se_divergirem`, mostre a alteração e peça nova confirmação.
4. Inspecione no 3D e nas plantas: contagens por tipo, piso, posição, largura/altura/espessura, material e vínculos visuais. Registre PLN, GUIDs, revisão, resultado do verificador e pendências em `projeto-contexto.json`.

## Auditoria e troca IFC

Use as regras em `assets/regras/entrega-br.yaml`, descritas em `references/regras.md`, adaptando classificação e layers ao escritório. `list_rules` confirma carga. Execute `get_model_summary`, `audit_delivery_readiness` e `verify_ifc_export_readiness`. **Não aceite o score agregado quando `element_count=0`, houver `skipped=true` ou alguma regra falhar**: salve as respostas em um JSON e use `scripts/validar_auditoria.py`. Destaque falhas, crie issues e exporte BCF somente após conferir a lista e o destino. Para IFC, inspecione coordenadas, unidades, classes, nomes, pavimentos e quantitativos no arquivo reaberto. O teste AC30 preservou 4 `IFCCOLUMN`, 4 `IFCBEAM` e 1 `IFCSLAB` no arquivo, mas o tradutor padrão de reabertura trouxe as oito barras como `Object`; trate a correspondência semântica do tradutor como requisito explícito. Se o projeto for Teamwork, reserve os elementos necessários antes de gravar. O upstream [documenta as ferramentas e limites](https://github.com/alesdev88/Archicad-MCP/blob/v0.8.0/README.md).

## Limites e responsabilidade

Criação de geometria BIM não transfere automaticamente cargas, apoios, armadura ou cálculo para o Archicad. O conversor desta skill lança pilares, vigas e lajes; paredes, portas, janelas, ambientes, anotações e composição de plantas arquitetônicas exigem um fluxo Archicad separado. O modelo gerado é de apoio, sem detalhamento executivo. A auditoria não prova conformidade normativa nem detecta todos os clashes. Mudanças no PLN exigem confirmação e cópia salva; resultados e IFC precisam de revisão técnica independente.
