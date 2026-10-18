---
name: archicad-assistente
description: Modela e audita estruturas no Archicad 29 via MCP e Tapir, usando o modelo estrutural versionado. Use quando o usuário escolher Archicad como destino BIM, pedir criação de pilares, vigas ou lajes, inspeção do PLN, exportação IFC ou issues BCF.
---

# Assistente Archicad

O MCP `archicad` em modo `full` expõe `create_elements` para pilares/lajes, e o gateway Tapir `CreateBeams` para vigas. Tapir é obrigatório para criação e IFC/issues. O arquivo de entrada é o mesmo da skill `modelo-estrutural` e deve corresponder à revisão analisada na SkyCiv.

## Conexão e preparação

1. Leia `projeto-contexto.json` e o manifesto da análise SkyCiv. Confira `sha256_entrada` e revisão. Inicie com `list_instances` e `get_project_info`; identifique o PLN aberto e Tapir. Salve uma cópia do PLN **antes de ler propriedades**: a leitura de propriedades pode encerrar o Archicad 29, conforme o aviso do upstream.
2. Use `execute_read_api_command` com `name: GetStories` para mapear cada nível e cota do modelo ao `floorIndex` real. Use `list_attributes` com `BuildingMaterial` e selecione o GUID do material do template. Para laje, escolha um favorito existente que tenha esse material. Preencha um arquivo como `assets/config.exemplo.json`; substitua todos os valores de exemplo e confira no programa.
3. Gere o plano: `python3 scripts/lancamento.py modelo-estrutural.json --config archicad-config.json --saida archicad-ops.json`. O script recusa pavimento ou material sem correspondência. Ele não roda o Archicad.

## Modelar

1. Leia as operações e apresente ao usuário quantidade, níveis, seções e material por lote. `create_elements` com `dry_run=true` e `execute_write_api_command` com `confirm=false` mostram o payload sem gravar. Confira com `describe_api_command CreateBeams` e resolva qualquer erro antes da execução.
2. Após confirmação para o lote no PLN salvo, repita com `dry_run=false` ou `confirm=true`. Crie pilares, depois vigas, depois lajes. O retorno `elements` deve conter um GUID por ID esperado; pare em erro parcial, grave o mapeamento ID → GUID e não repita o lote inteiro às cegas.
3. Inspecione no 3D e nas plantas: contagens por tipo, piso, posição, largura/altura/espessura, material e vínculos visuais. Use `find_elements` e `get_element_data` apenas após o salvamento por causa da falha conhecida de leitura de propriedades. Registre PLN, GUIDs, revisão e pendências em `projeto-contexto.json`.

## Auditoria e troca IFC

Use as regras em `assets/regras/entrega-br.yaml`, descritas em `references/regras.md`, adaptando classificação e layers ao escritório. `list_rules` confirma carga. `audit_delivery_readiness` e `verify_ifc_export_readiness` verificam dados/classificação; destaque falhas, crie issues e exporte BCF somente após conferir a lista e o destino. Para IFC, inspecione coordenadas, unidades, classes, nomes, pavimentos e quantitativos no arquivo reaberto. Se o projeto for Teamwork, reserve os elementos necessários antes de gravar. O upstream [documenta as ferramentas e o aviso de travamento](https://github.com/alesdev88/Archicad-MCP/blob/v0.7.1/README.md).

## Limites e responsabilidade

Criação de geometria BIM não transfere automaticamente cargas, apoios, armadura ou cálculo para o Archicad. O modelo gerado é de apoio, sem detalhamento executivo. A auditoria não prova conformidade normativa nem detecta todos os clashes. Mudanças no PLN exigem confirmação e cópia salva; resultados e IFC precisam de revisão técnica independente.
