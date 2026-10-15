# Boas práticas de modelagem (o que separa um modelo útil de um "boneco")

## Intenção de projeto
1. **Origem e planos com significado**: origem no centro da chapa de base, no eixo do pilar ou na face de apoio. Planos Front/Top/Right alinhados com os eixos da obra (X e Y da planta, Z vertical = plano Top como planta).
2. **Esboços totalmente definidos**: toda geometria com cota (`sketch_dimension` com `value`) ou relação (`sketch_constraint`). Esboço subdefinido "escorrega" quando um valor muda. Confira o status em `get_state`.
3. **Cotas que dirigem**: dimensione o que o fabricante mede (furação a partir das bordas ou do centro, espessura, comprimento), e não coordenadas arbitrárias.
4. **Parametrize o que muda**: variações (chapas 250/300/350, comprimentos) com `add_configuration` + `set_config_parameter`. Relações entre medidas com `add_equation` (ex.: furos a 40 mm da borda).
5. **Nomeie tudo**: `rename_feature` logo após criar ("Chapa 300x300x16", "Furos ⌀22 chumbadores", "Enrijecedor"). Agrupe com `create_feature_folder`.

## Fluxo de cada peça
1. `new_part` → `create_sketch` (plano certo) → perfil (`sketch_profile` ou retângulo/círculo) → cotas/relações → `create_extrusion`.
2. Furos: círculos no mesmo esboço da chapa (saem vazados na extrusão) ou `hole_wizard`/`create_cut_extrusion` depois.
3. Acabamento: `fillet`/`chamfer` por **feature** (sem coordenadas, independe da câmera).
4. `set_material` → `get_mass_properties` → compare com o peso calculado por `scripts/perfis.py`.
5. `look_at_model` (verifique visualmente) → `save_document` com caminho na pasta do projeto.

## Seleção por coordenadas (armadilha)
A seleção usa a **vista atual da câmera**: geometria escondida atrás de outra não é selecionável, e faces vistas de perfil podem "roubar" a seleção. Prefira opções por `feature` e use pontos devolvidos por `get_faces`/`get_edges`/`find_face`, nunca coordenadas estimadas.

## Montagens
- Salve cada peça antes de inserir (`save_document`). O primeiro componente fica fixo.
- Posicione com `add_mate` por planos (`{"plane":"Front","component":"comp:chapa-1"}`), mais robusto que faces por coordenada.
- Feche com `check_interference`: interferência ≠ 0 em ligação aparafusada geralmente é furo ou chapa mal posicionada.
- Peso total da montagem: `get_assembly_mass_properties`.

## Corrigir em vez de refazer
`list_parameters` → `set_parameter` muda uma cota e reconstrói. `suppress_feature` antes de `delete_feature` (reversível). Peça importada de STEP sem histórico: `recognize_features` para recuperar a árvore.
