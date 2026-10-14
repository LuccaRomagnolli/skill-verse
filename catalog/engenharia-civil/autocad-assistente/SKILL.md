---
name: autocad-assistente
description: Desenha no AutoCAD LT pelo chat via MCP (criar layers no padrão de projeto estrutural, desenhar retângulos, polilinhas, cotas, textos e blocos, detalhar seções de vigas e pilares a partir do resultado do cálculo) e gera arquivo DXF quando o AutoCAD não estiver disponível. Use quando o usuário pedir para "desenhar no AutoCAD", "detalhar a seção", "criar layers", "gerar DXF", "mandar para o CAD", "planta de fôrma" ou mencionar AutoCAD/CAD/DWG.
---

# Assistente AutoCAD (estrutural)

Ferramentas do MCP `autocad`: `system`, `drawing`, `layer`, `entity`, `annotation`, `block`, `view`. Cada uma recebe `operation` + parâmetros.

## Antes de desenhar
1. `system` → `status`. Veja o `backend`:
   - `file_ipc`: AutoCAD LT aberto (Windows). Tudo disponível.
   - `ezdxf`: modo headless (macOS/Linux ou AutoCAD fechado). O desenho fica em memória e é salvo como DXF com `drawing` → `save_as_dxf` `{path}`. `offset`, `fillet`, `chamfer`, `plot_pdf` e `zoom` não funcionam.
   - Erro de conexão no Windows: peça para abrir o AutoCAD e carregar o `mcp_dispatch.lsp` (APPLOAD). O caminho está no manual do pack.
2. Confirme **unidade** (padrão: cm) e se o usuário tem padrão de layers próprio. Senão, use `references/padrao-layers.md`.

## Detalhe de seção (viga ou pilar)
O script `scripts/detalhe_secao.py` calcula a geometria (cobrimento, estribo, posição das barras, cotas, textos) e gera:
- `--ops arquivo.json`: lista de chamadas do MCP em ordem. Execute cada item chamando a ferramenta `tool` com os demais campos como parâmetros. Onde aparecer `"entity_id": "$anterior"`, use o `handle` devolvido pela operação anterior (a polilinha da barra que recebe a hachura).
- `--dxf arquivo.dxf`: desenho pronto (R12). Útil sem AutoCAD, para enviar a terceiros ou para abrir com `drawing` → `open`.

```bash
python3 scripts/detalhe_secao.py --b 15 --h 45 --c 3 --inf 3x12.5 --sup 2x8 --estribo 5 --s 13 --nome V1 --ops V1.json --dxf V1.dxf
python3 scripts/detalhe_secao.py --b 20 --h 50 --c 3 --pilar 3 --phi 20 --estribo 5 --s 20 --nome P1 --origem 40 0 --ops P1.json
```
Use os dados da skill `concreto-armado-nbr6118` (barras e estribos sugeridos, cobrimento da CAA). Várias seções no mesmo desenho: desloque cada uma com `--origem x y` (ex.: 40 cm entre seções).

Depois de executar as operações: `view` → `zoom_extents` (se disponível) e `view` → `get_screenshot` para mostrar o resultado ao usuário. Salve com `drawing` → `save` (AutoCAD) ou `save_as_dxf`.

## Outros pedidos comuns
- **Criar layers**: `layer` → `create` `{name, color, linetype?}` para cada linha da tabela de referência; depois `set_current`.
- **Contorno de peça**: `entity` → `create_rectangle` `x1,y1,x2,y2` ou `create_polyline` `points` + `data: {closed: true}`.
- **Cotas**: `annotation` → `create_dimension_linear` `{x1,y1,x2,y2,dim_x,dim_y}`.
- **Textos**: `annotation` → `create_text` `{x,y,text,height,layer}`. Para ⌀, no AutoCAD use `%%c`.
- **Inspecionar desenho existente**: `drawing` → `info`; `entity` → `list` `{layer}`.
- Antes de apagar ou mover muitas entidades, **descreva o que vai fazer e peça confirmação**. Em `file_ipc` existe `drawing` → `undo`.

## Layout de canteiro
Para desenhar canteiro de obras (áreas de vivência, acessos, central de armação/fôrmas, baias, proteção de periferia), levante antes as exigências com a skill `consulta-normas` (NR-18, NR-24, NR-10) e anote o item da norma em cada elemento do desenho (layer `EST-TEXTO`).

## Limites e responsabilidade
- Gera desenhos de apoio (seções, layers, elementos simples). Não substitui o detalhamento completo (armação longitudinal com comprimentos, ancoragens, dobras, tabela de aço) nem a revisão do projetista.
- `system` → `execute_lisp` executa código arbitrário no AutoCAD: só use com pedido explícito do usuário e mostre o código antes.
- No modo headless, salve o DXF em pasta do usuário e diga o caminho; nada fica salvo automaticamente.
