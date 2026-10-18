---
name: archicad-assistente
description: Lê, modela e audita projetos no Archicad 29 ou 30 via MCP e Tapir. Use quando o usuário escolher Archicad como destino BIM, pedir inspeção ou edição do PLN, exportação IFC ou issues BCF.
---

# Assistente Archicad

O MCP `archicad` 0.8.0 em modo `full` expõe leitura, auditoria e criação de elementos; algumas operações dependem do Tapir. Leia [references/conexao.md](references/conexao.md) ao diagnosticar a conexão, múltiplas instâncias ou o Public MCP do Archicad 30.

## Conexão e preparação

1. Leia `projeto-contexto.json` e confira a revisão e a origem das informações a usar. Inicie com `list_instances`; selecione a porta do PLN certo e confirme `project_open`, `tapir_available`, versão e build. Salve uma cópia do PLN antes de alterações. Não faça o primeiro teste em projeto de cliente ou Teamwork.
2. Use `GetStories` para mapear níveis e cotas reais. Consulte atributos, materiais e favoritos do template aberto; para lajes simples, confira se o favorito é **Basic** e corresponde à espessura e ao material pretendidos.
3. Planeje as operações a partir dos dados conferidos do projeto. Registre a porta, a revisão, os IDs de origem, pavimentos e materiais reais antes de enviar qualquer criação ao aplicativo.

## Modelar

1. Apresente quantidade, níveis, dimensões, material, porta e revisão por lote. `create_elements` com `dry_run=true` e `execute_write_api_command` com `confirm=false` mostram o payload sem gravar. Confira o comando com `describe_api_command` e resolva qualquer erro antes da execução.
2. Após confirmação para o lote no PLN salvo, repita com `dry_run=false` ou `confirm=true`. Crie pilares, depois vigas, depois lajes. O retorno `elements` deve conter um GUID por ID esperado; pare em erro parcial, grave o mapeamento ID → GUID e não repita o lote inteiro às cegas.
3. Execute `GetDetailsOfElements` para todos os GUIDs criados e compare tipo, pavimento, dimensões, material e contorno com os dados de origem. O ensaio no Archicad 30 mostrou que uma laje criada com favorito Composite pode ignorar a espessura pedida. Se houver divergência, mostre a correção proposta, confirme e releia o elemento.
4. Inspecione no 3D e nas plantas: contagens por tipo, piso, posição, largura/altura/espessura, material e vínculos visuais. Registre PLN, GUIDs, revisão, resultado do verificador e pendências em `projeto-contexto.json`.

## Auditoria e troca IFC

Use as regras em `assets/regras/entrega-br.yaml`, descritas em `references/regras.md`, adaptando classificação e layers ao escritório. `list_rules` confirma carga. Execute `get_model_summary`, `audit_delivery_readiness` e `verify_ifc_export_readiness`. **Não aceite o score agregado quando `element_count=0`, houver `skipped=true` ou alguma regra falhar**: salve as respostas em um JSON e use `scripts/validar_auditoria.py`. Destaque falhas, crie issues e exporte BCF somente após conferir a lista e o destino. Para IFC, inspecione coordenadas, unidades, classes, nomes, pavimentos e quantitativos no arquivo reaberto. O teste AC30 preservou 4 `IFCCOLUMN`, 4 `IFCBEAM` e 1 `IFCSLAB` no arquivo, mas o tradutor padrão de reabertura trouxe as oito barras como `Object`; trate a correspondência semântica do tradutor como requisito explícito. Se o projeto for Teamwork, reserve os elementos necessários antes de gravar. O upstream [documenta as ferramentas e limites](https://github.com/alesdev88/Archicad-MCP/blob/v0.8.0/README.md).

## Limites e responsabilidade

Criação de geometria BIM não transfere automaticamente critérios de projeto ou verificações técnicas para o Archicad. Paredes, portas, janelas e pisos da planta arquitetônica seguem o plano gerado por `planta-arquitetonica`, com propriedades resolvidas no PLN aberto. A auditoria não prova conformidade normativa nem detecta todos os clashes. Mudanças no PLN exigem confirmação e cópia salva; resultados e IFC precisam de revisão técnica independente.
