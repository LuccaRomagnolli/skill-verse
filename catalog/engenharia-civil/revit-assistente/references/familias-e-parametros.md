# Famílias, tipos e parâmetros

## Conceitos que o agente precisa usar certo
- **Família** (ex.: "Pilar de concreto - Retangular") → **tipos** (`P 20x50`) → **instâncias** (cada P1, P2 no modelo).
- **Parâmetro de tipo** muda todas as instâncias do tipo (seção b × h). **Parâmetro de instância** muda só aquela (níveis, deslocamentos, Marca, Comentários).
- Famílias **de sistema** (paredes, pisos/lajes, telhados) não são carregáveis: os tipos são duplicados dentro do projeto. Famílias **carregáveis** (pilares, vigas, fundações, portas) vêm de `.rfa`.
- Seção de pilar/viga = parâmetros de tipo, geralmente `b` e `h` nas famílias de concreto (o nome varia com o idioma: "Largura", "Altura", "Profundidade", "Width", "Depth"). O `lancamento.py` tenta esses nomes e avisa se não achar.

## Criar o tipo que falta
1. `get_available_family_types` com `categoryList: ["OST_StructuralColumns"]`: se o tipo com a seção já existe, use o id.
2. Se não existe, use o `tipos_csharp` do `lancamento.py`, que duplica uma família retangular e ajusta b/h.
3. Sem nenhuma família retangular de concreto carregada: peça ao usuário para carregar (`Inserir → Carregar família`, pasta Estrutural → Pilares/Framing → Concreto). O MCP não carrega `.rfa`, e o C# só deve fazer isso com o caminho informado pelo usuário (`document.LoadFamily(caminho)`).

## Parâmetros úteis (BuiltInParameter, independentes de idioma)
| Parâmetro | Uso |
|---|---|
| `ALL_MODEL_MARK` | Marca (P1, V1) |
| `ALL_MODEL_INSTANCE_COMMENTS` | Comentários |
| `STRUCTURAL_MATERIAL_PARAM` | material estrutural (classe do concreto) |
| `HOST_VOLUME_COMPUTED` / `HOST_AREA_COMPUTED` | volume / área calculados |
| `FAMILY_BASE_LEVEL_PARAM`, `FAMILY_TOP_LEVEL_PARAM` | níveis de base/topo de pilar |
| `FAMILY_BASE_LEVEL_OFFSET_PARAM`, `FAMILY_TOP_LEVEL_OFFSET_PARAM` | deslocamentos de pilar |
| `STRUCTURAL_BEAM_END0_ELEVATION`, `STRUCTURAL_BEAM_END1_ELEVATION` | cotas das extremidades da viga |
| `INSTANCE_LENGTH_PARAM` / `STRUCTURAL_FRAME_CUT_LENGTH` | comprimento da viga |
| `FLOOR_ATTR_THICKNESS_PARAM` | espessura da laje (tipo) |

## Classificação e dados BIM
- Classificação da informação da construção: **NBR 15965** (sistema de classificação; tabelas por partes). Use o campo de classificação do template do escritório (ou um parâmetro compartilhado) e preencha só com código que o usuário confirmar. Não invente código de tabela.
- Contratações públicas: a Estratégia BIM BR (Decreto nº 11.888/2024) e o edital definem o nível de informação e o formato de entrega (geralmente IFC). Pesquise o edital/caderno do órgão com `contexto-do-projeto` e registre a fonte.
- Parâmetros compartilhados: arquivo `.txt` do escritório. Não crie um arquivo novo por conta própria. Pergunte qual usar.
