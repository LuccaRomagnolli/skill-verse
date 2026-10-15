# Ferramentas do MCP `solidworks` (HarrierPigeon/Solidworks-MCP-Server v0.4.0)

Todas com prefixo `solidworks_`. **Milímetros e graus** (o servidor converte para metros/radianos da API COM). Cada objeto criado ganha um ID estável (`feat:…`, `sketch:…`, `entity:…`, `ref:…`) por documento.

## Esboço (sketch)
`create_sketch` (`plane`: Front/Top/Right ou plano de referência; ou face por `faceX/faceY/faceZ`; devolve `sketchFrame` com origem e eixos do esboço no espaço do modelo) · `exit_sketch` · `sketch_rectangle` (centro + `width/height`, cantos `x1..y2`, ou relativo à última forma) · `sketch_circle` · `sketch_profile` (contorno encadeado inteiro numa chamada: `startX/startY`, `segments` LINE/TANGENT_ARC/ARC, `close`, `cornerFillets`) · `sketch_line` · `sketch_centerline` (eixo de revolução/espelho) · `sketch_arc` · `sketch_spline` · `sketch_ellipse` · `sketch_polygon` · `sketch_slot` (furo oblongo) · `sketch_point` · `sketch_text` · `sketch_fillet` (arredonda canto existente com tangência exata) · `sketch_offset` (paredes, contorno interno) · `sketch_dimension` (cota que **dirige** a geometria) · `set_dimension_value` · `sketch_constraint` (horizontal, vertical, coincidente, tangente, igual…) · `sketch_toggle_construction` · `get_last_shape_info`.

**Esboço em face**: os eixos do esboço podem estar espelhados ou girados em relação ao modelo, e a origem do esboço é a projeção da origem do modelo na face (não o centro da face). Use `sketchFrame` e `faceCenter` devolvidos para converter coordenadas.

## Sólidos
`new_part` · `create_extrusion` (`depth`, `reverse`, `endCondition` BLIND/THROUGH_ALL, `merge`) · `create_cut_extrusion` · `revolve` / `cut_revolve` (exige linha de centro) · `sweep` / `cut_sweep` (perfil + caminho) · `loft` / `cut_loft` · `boundary_boss` / `boundary_cut` · `combine_bodies` (ADD/SUBTRACT/COMMON) · `intersect`.

## Operações aplicadas
`fillet` (raio; de preferência por `feature`, sem coordenadas) · `chamfer` · `shell` (faces a remover por coordenada) · `draft` · `rib` (nervura a partir de esboço aberto) · `wrap`.

## Padrões, furos e referência
`linear_pattern` · `circular_pattern` · `mirror` · `hole_wizard` (escareado, rebaixado, roscado; pode abrir diálogo em algumas versões) · `thread` (rosca cosmética) · `ref_plane` · `ref_axis` · `ref_point` · `coordinate_system`.

## Consulta e verificação
`get_body_info` (caixa envolvente, contagem de faces/arestas) · `get_faces` / `get_edges` / `get_face_edges` / `get_vertices` (pontos de amostra **garantidos** sobre a geometria, para usar em seleção) · `find_face` (por orientação +X/−Z/ANGLED, feature, tipo, ranking de área) · `look_at_model` (**captura com rótulos de faces**, para ver o que foi construído) · `get_state` · `get_entity` · `get_sketch_entities`.

## Parâmetros, configurações e equações
`list_parameters` (nomes tipo `D1@Sketch1`) · `set_parameter` · `add_configuration` / `switch_configuration` / `list_configurations` · `set_config_parameter` · `add_equation` / `list_equations` / `delete_equation`.

## Material e massa
`set_material` (nome exato da biblioteca: `ASTM A36 Steel`, `Plain Carbon Steel`, `AISI 304`, `6061 Alloy`…; sem material a densidade é 1000 kg/m³) · `get_mass_properties` (kg, volume, área, centro de massa, inércias; opcional relativo a um sistema de coordenadas).

## Árvore de projeto
`get_feature_tree` · `rename_feature` (**renomeie logo após criar**: "Chapa de base", "Furos chumbadores") · `create_feature_folder` · `move_to_folder` (limitação conhecida no SOLIDWORKS 2025) · `list_features` · `suppress_feature` · `delete_feature`.

## Montagens
`new_assembly` · `insert_component` (peça salva; a caixa envolvente é centrada no ponto de inserção) · `add_mate` (COINCIDENT, CONCENTRIC, PERPENDICULAR, PARALLEL, TANGENT, DISTANCE, ANGLE, LOCK, GEAR; por planos de componente ou por coordenadas) · `edit_mate` · `list_components` · `list_mates` · `check_interference` (volumes em mm³) · `suppress_component` · `get_assembly_mass_properties`.

## Documentos e troca de arquivos
`save_document` (nome sem pasta → `workspace` do servidor; caminho absoluto → usado como está; extensão `.STEP/.STP/.IGS/.X_T/.SAT/.STL/.3MF` **exporta**) · `open_document` · `import_file` (STEP/IGES/Parasolid/ACIS/STL como corpo "burro") · `recognize_features` (FeatureWorks: recupera a árvore paramétrica) · `activate_document` · `close_document` (**sem salvar**) · `capture_views` (PNGs das vistas padrão) · `list_documents`.

## Lote
`solidworks_batch`: até 25 chamadas **independentes** numa requisição (ex.: várias entidades de esboço). Resultados de uma chamada não podem ser usados por outra do mesmo lote. Não coloque `look_at_model` em lote.

## O que NÃO existe
Desenho 2D (folha com vistas e cotas), exportação DXF/DWG/PDF, chapa metálica (sheet metal), soldagem (weldments), simulação. Para folha de desenho e DXF, use as macros de `api-vba.md` (o usuário executa no SOLIDWORKS).
