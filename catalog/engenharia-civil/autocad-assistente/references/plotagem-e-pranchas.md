# Pranchas e plotagem

## Duas estratégias
1. **Prancha no espaço do modelo (pelo MCP)**: o MCP não cria layouts nem viewports. Então a folha é desenhada no modelo, **ampliada pela escala**, em volta do desenho. É o que `scripts/prancha.py` faz:
   ```bash
   python3 scripts/prancha.py --cabe 18.5 12.0 --unidade m            # 1) qual formato/escala cabe
   python3 scripts/prancha.py --formato A1 --escala 50 --unidade cm \
       --obra "<obra>" --local "<município/UF>" --conteudo "Planta de fôrmas – Térreo" \
       --rt "<nome>" --registro "<CREA/CAU>" --art "<nº>" --folha 01/04 --ops prancha.json
   ```
   Execute o `prancha.json` como no detalhe de seção: cada item é uma chamada à ferramenta `tool` com os demais campos. Depois **mova o desenho** para dentro de `area_livre_acima_do_carimbo` (`entity` → `move`) ou gere a prancha com a origem já posicionada. O script informa `fator_unidades_por_mm_papel`: por exemplo, numa prancha em metros a 1:50, plote `1 mm = 0,05 unidade de desenho` (`1=0.05` no `-PLOT`).
2. **Layout com viewport (AutoCAD completo, pelo usuário ou LISP)**: o caminho "certo" para várias vistas com escalas diferentes. O agente orienta: `LAYOUT` → `PAGESETUP` (formato ISO, `DWG To PDF.pc3`, tabela `.ctb`) → `MVIEW` → `VPSCALE`/barra de escala → travar viewport. Inserir a folha gerada por `prancha.py` com `--escala 1 --unidade mm` no layout (papel em mm).

## Plotar em PDF
- Com AutoCAD (IPC): `drawing` → `plot_pdf` `{path}` usa a configuração atual da folha. Confira antes no `PAGESETUP` do usuário (formato, `.ctb`, área = layout ou janela).
- No AutoCAD para Mac 2027, o teste real usou `-PLOT` com configuração detalhada: `Model`, `AutoCAD PDF (General Documentation).pc3`, `ISO full bleed A3 (420.00 x 297.00 MM)`, milímetros, paisagem, área `Extents`, escala `1=0.05` para DXF em metros a 1:50, centralizado e `monochrome.ctb`. Confira o PDF A3 antes da entrega. Mídia A3 padrão pode cortar a linha de limite do papel; escolha mídia sem margem para PDF ou ajuste a moldura à área imprimível do dispositivo.
- Sem AutoCAD: entregue o DXF. O usuário plota no programa dele, ou num visualizador gratuito como o DWG TrueView.
- Monocromático: tabela `monochrome.ctb` com espessura por cor (ver `padrao-layers.md`). Colorido para aprovação só se a prefeitura pedir.

## Checklist antes de entregar
- [ ] Unidade e escala conferidas (medir uma cota conhecida).
- [ ] Textos legíveis no papel (≥ 2,5 mm), sem sobreposição com cotas.
- [ ] Carimbo completo: obra, local, conteúdo, escala, data, folha, RT, registro, ART/RRT, revisão.
- [ ] Layers de trabalho congelados ou apagados (com confirmação). `PURGE` feito.
- [ ] Padrão de apresentação da prefeitura atendido (quadro de áreas, selo, formato), com a fonte registrada pela skill `contexto-do-projeto`.
- [ ] Xrefs e imagens embutidos ou entregues junto (`ETRANSMIT`).

## Dobra
Pranchas maiores que A4 são dobradas até o formato A4, com a legenda visível na frente e a faixa de encadernação à esquerda. Oriente o usuário. O agente não executa a dobra.
