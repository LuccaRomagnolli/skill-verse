---
name: solidworks-assistente
description: Opera o SOLIDWORKS pelo chat via MCP para peças e montagens de engenharia civil, como chapas de base com furos para chumbadores, chapas de ligação, perfis W/U/Ue/L/tubos, insertos metálicos, enrijecedores, guarda-corpos, suportes, fôrmas e gabaritos. Esboça com cotas e relações, extruda, fura, arredonda, cria padrões, configura variações e equações, monta com posicionamentos, verifica interferência, calcula massa e peso de aço para orçamento, captura vistas e exporta STEP. Gera macro VBA para folha de desenho, PDF e DXF de corte. Use quando o usuário mencionar SOLIDWORKS, SLDPRT, SLDASM, peça metálica, chapa de base, ligação metálica, perfil, STEP, ou disser "modela essa chapa", "quanto pesa essa peça", "monta essa ligação", "tem interferência?", "exporta em STEP" ou "gera o DXF para corte".
---

# Assistente SOLIDWORKS

MCP `solidworks` (ferramentas `solidworks_*`, todas em **mm e graus**). O catálogo completo, com o que **não** existe (desenho 2D, DXF, chapa metálica, soldagem), está em `references/mcp-ferramentas.md`.

## 1. Antes de modelar
0. Retome `projeto-contexto.json` com `contexto-do-projeto` → `resumo`; obtenha revisão, cálculo que definiu a peça, material e pendências. Sem origem verificável, trate as dimensões como hipótese para estudo, não como ligação dimensionada.
1. O SOLIDWORKS precisa estar **aberto** no Windows. `solidworks_list_documents` testa a conexão e mostra o que está aberto. Falha de conexão = SOLIDWORKS fechado ou ainda carregando.
2. Junte os dados de entrada com o usuário: dimensões, furação, material, perfil pela designação do catálogo (ex.: "W200 × 22,5"). **Não invente medidas** de perfis nem de furação de ligação. Confirme com o catálogo/projeto do usuário (`references/estruturas-metalicas.md`).
3. Defina onde salvar: pasta do projeto do usuário (caminho absoluto). Sem caminho, o arquivo vai para a pasta `workspace` do servidor.
4. Antes das chamadas, apresente plano de lotes: documento ativo, sketch/plano, dimensões em mm, features, material, arquivos de saída e critérios de conferência. Salve uma cópia antes de modificar peça existente. Após cada lote, releia features/corpos; não prossiga se aparecer feature falha ou referência perdida.

## 2. Perfis e chapas (com peso calculado)
Use `scripts/perfis.py`. Ele gera as chamadas do MCP **e** a área, a massa por metro e o peso, para conferir depois com o SOLIDWORKS:
```bash
python3 scripts/perfis.py chapa --b 300 --h 300 --t 16 --furos "-110,-110,22;110,-110,22;110,110,22;-110,110,22" --nome "Chapa de base P1" --ops chapa.json
python3 scripts/perfis.py I --d 200 --bf 100 --tw 5.6 --tf 8.5 --comprimento 6000 --nome "Viga W200"
python3 scripts/perfis.py Ue --d 150 --bf 60 --c 20 --t 2.65 --comprimento 6000
```
Execute as `ops` em ordem: cada item é `{tool, args}`. Troque `"$ultima_extrusao"` pelo nome que `solidworks_create_extrusion` devolveu. No fim, compare `massa_kg` do script com `solidworks_get_mass_properties`: diferença acima de 1% indica geometria ou material errados.

## 3. Peça genérica
Siga o roteiro de `references/boas-praticas-modelagem.md`:
1. `new_part` → `create_sketch` no plano certo (Top = planta).
2. Perfil com `sketch_profile` (contorno inteiro numa chamada) ou retângulos/círculos. Cote o que o fabricante mede (`sketch_dimension` com `value`). Use `solidworks_batch` para várias entidades independentes.
3. `create_extrusion` / `create_cut_extrusion` / `revolve`. Acabamento com `fillet`/`chamfer` por `feature`.
4. `rename_feature` logo após cada operação. `set_material` (ex.: `ASTM A36 Steel`).
5. Verificação: `get_body_info`, `look_at_model` (mostre a imagem ao usuário), `get_mass_properties`.
6. `save_document` com caminho absoluto. Para outro software, `save_document` com `.STEP`.
7. Reabra ou inspecione o arquivo exportado, compare dimensões e massa calculada com a fonte, e registre SLDPRT/SLDASM/STEP na ficha (`contexto.py artefato`). Se a massa, material, interferência ou aprovação da ligação não estiverem conferidos, registre `pendencia` com responsável.

Para selecionar faces/arestas, use **sempre** pontos devolvidos por `get_faces`/`get_edges`/`find_face`, nunca coordenadas estimadas: a seleção depende da câmera.

## 4. Variações e alterações
- "E se a chapa for de 19 mm?": `list_parameters` → `set_parameter` (reconstrói). Não refaça a peça.
- Família de peças (chapas 250/300/350): `add_configuration` + `set_config_parameter`. Relações fixas (furos a 40 mm da borda): `add_equation`.
- Remover algo: `suppress_feature` antes de `delete_feature`.

## 5. Montagens e interferência
`save_document` de cada peça → `new_assembly` → `insert_component` → `add_mate` (prefira planos de componente) → `check_interference` → `get_assembly_mass_properties`. Interferência diferente de zero numa ligação aparafusada é quase sempre furo ou chapa fora de posição: mostre com `look_at_model` e corrija pela cota.

## 6. Folha de desenho, PDF e DXF de corte
Não há ferramenta no MCP. Gere a macro de `references/api-vba.md` (3 vistas no **1º diedro** + PDF + DXF, DXF de face para corte, lista de peças em CSV), explique o que ela faz e oriente o usuário a executá-la (`Ferramentas → Macro`). O DXF pode receber carimbo e prancha com a skill `autocad-assistente`.

## 7. Peso → orçamento e outros softwares
- Peso total e área de pintura (`get_mass_properties`) → skill `quantitativos-sinapi` (estrutura metálica em kg, pintura em m²). Some e converta por script, nunca de cabeça.
- STEP → Revit (família genérica) ou compatibilização com o modelo estrutural (skills `revit-assistente`, `tqs-assistente`).
- Cargas na peça (reação de apoio, vento) vêm do cálculo: skill `cargas-combinacoes`.

## Limites e responsabilidade
- O SOLIDWORKS **não dimensiona** a peça pela NBR 8800:2024 (corrigida em 2025) nem pela NBR 14762 (confirme a edição vigente no Catálogo ABNT): o modelo materializa a geometria definida pelo engenheiro. Espessuras, furos, soldas e parafusos são decisão do projetista, que assina como responsável técnico.
- Pesos calculados com cantos vivos são aproximados. Para orçamento de perfis laminados, prefira a massa nominal do catálogo do fabricante.
- Macros VBA são executadas pelo usuário. Explique o que cada uma faz antes. `close_document` descarta alterações não salvas: confirme antes.
- Requer Windows com SOLIDWORKS 2022+ aberto e ativado. Sem ele, nenhuma ferramenta funciona.
