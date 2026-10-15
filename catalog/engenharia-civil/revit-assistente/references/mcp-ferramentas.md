# Ferramentas do MCP `revit` (mcp-servers-for-revit v1.0.0)

Arquitetura: servidor Node (stdio) ↔ TCP `localhost:8080` ↔ add-in C# dentro do Revit. Cada chamada abre a conexão, executa e fecha. Se o serviço não estiver ligado no Revit (botão **Revit MCP Switch**), toda ferramenta falha com "connect to revit client failed".

**Unidades nas ferramentas: milímetros e graus.** O add-in converte para pés (÷ 304,8). "Nível" (`baseLevel`) nas ferramentas de criação é a **cota do nível em mm**, e não o id: o add-in procura o nível mais próximo dessa cota.

## Leitura (seguras, sem confirmação)
| Ferramenta | Parâmetros | Uso |
|---|---|---|
| `say_hello` | — | testa a conexão (mostra um diálogo no Revit) |
| `get_current_view_info` | — | vista ativa: tipo, nome, escala, nível |
| `get_current_view_elements` | `modelCategoryList?`, `annotationCategoryList?`, `includeHidden?`, `limit?` | elementos da vista ativa (`OST_Walls`, `OST_StructuralColumns`, `OST_Dimensions`…) |
| `get_selected_elements` | `limit?` | o que o usuário selecionou, para "esse pilar aqui" |
| `get_available_family_types` | `categoryList?`, `familyNameFilter?`, `limit?` | tipos carregados e seus **ids** (necessários para criar) |
| `ai_element_filter` | `data: {filterCategory?, filterElementType?, filterFamilySymbolId?, includeTypes, includeInstances, filterVisibleInCurrentView?, boundingBoxMin/Max? (mm), maxElements? (≤50)}` | busca no projeto inteiro, com parâmetros dos elementos |
| `analyze_model_statistics` | `includeDetailedTypes?` | contagem por categoria/família/tipo, vistas, folhas |
| `get_material_quantities` | `categoryFilters?`, `selectedElementsOnly?` | área e volume por material, para orçamento |
| `export_room_data` | `includeUnplacedRooms?`, `includeNotEnclosedRooms?` | ambientes com área, perímetro, volume, nível |

## Criação e edição (descreva o que vai criar e confirme lotes grandes)
| Ferramenta | Parâmetros principais |
|---|---|
| `create_level` | `data: [{name, elevation (mm), createFloorPlan?, createCeilingPlan?, …}]` |
| `create_grid` | `xCount, xSpacing, yCount, ySpacing` (mm), rótulos iniciais, `xNamingStyle/yNamingStyle` (`alphabetic`/`numeric`), extensões, posições iniciais. **Só espaçamento uniforme.** Eixos irregulares: C# gerado por `scripts/lancamento.py` |
| `create_point_based_element` | `data: [{name, typeId, locationPoint{x,y,z}, width, depth?, height, baseLevel, baseOffset, rotation?, hostWallId?, facingFlipped?}]`. Pilares (o topo é o nível mais próximo de `baseLevel + height`), portas, janelas, mobiliário |
| `create_line_based_element` | `data: [{category, typeId?, locationLine{p0,p1}, thickness, height, baseLevel, baseOffset}]`. Paredes (`OST_Walls`; sem `typeId` cria tipo pela espessura), vigas (`OST_StructuralFraming`; **precisa** de `typeId` com a seção), dutos |
| `create_surface_based_element` | `data: [{name, category (OST_Floors/OST_Ceilings/OST_Roofs), typeId?, boundary{outerLoop:[{p0,p1}…≥3]}, thickness, baseLevel, baseOffset}]`. Sem `typeId`, cria tipo de piso com a espessura |
| `create_structural_framing_system` | `levelName, xMin, xMax, yMin, yMax, spacing` (mm), `directionEdge`, `justify`, `beamTypeName?`, `elevation?`. Grade de vigas secundárias (BeamSystem), ex.: barrotes e terças metálicas |
| `create_room` | `data: [{name, number?, location{x,y,z}, levelId?, …}]`. Ponto dentro de paredes fechadas |
| `create_dimensions` | `dimensions: [{startPoint, endPoint, linePoint?, elementIds?, dimensionType?, dimensionStyleId?, viewId?}]` (mm) |
| `tag_all_walls` / `tag_all_rooms` | `useLeader?`, `tagTypeId?`, (`roomIds?`) na vista ativa |
| `color_elements` | `categoryName, parameterName, useGradient?, customColors?`. Mapa de cores por parâmetro na vista (ótimo para revisar seções, materiais, fck) |
| `operate_element` | `data: {elementIds, action}`. Ações: `Select`, `SelectionBox`, `Highlight`, `SetColor` (`colorValue`), `SetTransparency`, `Hide`, `TempHide`, `Isolate`, `Unhide`, `ResetIsolate`, `Delete` |
| `delete_element` | `elementIds: ["…"]` (**sempre com confirmação**) |

## Código e dados
| Ferramenta | Uso |
|---|---|
| `send_code_to_revit` | `code` (C#) + `parameters?`. Roda dentro de uma transação já aberta. Ver `revit-api-csharp.md`. **Mostre o código e peça "sim" antes.** |
| `store_project_data` / `store_room_data` / `query_stored_data` | banco SQLite local do servidor, para guardar metadados entre sessões. Pouco útil, já que a ficha do projeto (`contexto-do-projeto`) cumpre esse papel |

## Padrões de uso
- Antes de criar: `get_available_family_types` da categoria → escolha o `typeId`. Ids mudam entre projetos, então nunca reaproveite de outra sessão.
- Depois de criar: leia os **avisos** do retorno ("Requested typeId … not found. Defaulted to …" significa que o elemento saiu com o tipo errado) e confira com `ai_element_filter` ou `get_current_view_elements`.
- Para mostrar o resultado, `operate_element` `Select`/`Highlight` nos ids criados.
- Lotes: as ferramentas aceitam listas. Um lote por categoria e por nível.
