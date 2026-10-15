# Operações do MCP `autocad` (puran-water/autocad-mcp v3.1, commit fixado 95476a3)

Cada ferramenta recebe `operation` e os parâmetros abaixo. Coordenadas em **unidades do desenho** (o MCP não converte nada; combine a unidade com o usuário). Quase todas aceitam `include_screenshot: true`, que anexa uma captura depois da operação. Isso é útil para conferir sem uma chamada a mais.

Legenda: **[IPC]** só com o AutoCAD aberto no Windows (`file_ipc`); no modo `ezdxf` devolve erro.

## system
| operation | parâmetros | uso |
|---|---|---|
| `status` / `get_backend` | — | backend (`file_ipc` ou `ezdxf`), versão, se há documento, contagem de entidades, `capabilities` |
| `health` | — | ping rápido |
| `runtime` | — | plataforma, Python, pasta, `AUTOCAD_MCP_BACKEND` (diagnóstico) |
| `init` | — | recria a conexão (use após abrir o AutoCAD ou recarregar o LISP) |
| `execute_lisp` **[IPC]** | `data.code` | AutoLISP arbitrário. **Só com pedido explícito e mostrando o código antes.** |

## drawing
| operation | parâmetros | observação |
|---|---|---|
| `create` | `data.name?` | desenho novo vazio |
| `open` | `data.path` | abre DWG/DXF (no `ezdxf`, só DXF) |
| `info` | — | extents, nº de entidades, layers e blocos |
| `save` | `data.path?` | QSAVE ou salva no caminho |
| `save_as_dxf` | `data.path` | exporta DXF (no `ezdxf` é **a** forma de gravar) |
| `plot_pdf` **[IPC]** | `data.path` | plota em PDF com a configuração de plotagem atual |
| `purge` | — | remove itens não usados |
| `get_variables` | `data.names: [...]` | lê variáveis de sistema (ex.: `INSUNITS`, `LUNITS`, `DIMSCALE`, `LTSCALE`, `CLAYER`) |
| `undo` / `redo` | — | desfazer/refazer (IPC) |

## entity
Criação (`layer?` opcional em todas; sem ele vai para o layer corrente):
| operation | parâmetros |
|---|---|
| `create_line` | `x1,y1,x2,y2` |
| `create_rectangle` | `x1,y1,x2,y2` (cantos opostos) |
| `create_polyline` | `points: [[x,y],…]`, `data.closed?` |
| `create_circle` | `data: {cx, cy, radius}` |
| `create_arc` | `data: {cx, cy, radius, start_angle, end_angle}` (graus, anti-horário) |
| `create_ellipse` | `data: {cx, cy, major_x, major_y, ratio}` (`major_*` = vetor do semieixo maior) |
| `create_mtext` | `data: {x, y, width, text, height?}` |
| `create_hatch` | `entity_id` (contorno fechado), `data.pattern?` (`ANSI31`, `SOLID`, `AR-CONC`…) |

Leitura: `list` (`layer?`), `count` (`layer?`), `get` (`entity_id`). O `entity_id` é o **handle** devolvido na criação ou pelo `list`.

Modificação: `copy`/`move` (`entity_id`, `data:{dx,dy}`), `rotate` (`data:{cx,cy,angle}`), `scale` (`data:{cx,cy,factor}`), `mirror` (`entity_id`, `x1,y1,x2,y2` = eixo), `array` (`data:{rows,cols,row_dist,col_dist}`), `erase` (`entity_id`), `offset` **[IPC]** (`data:{distance}`), `fillet` **[IPC]** (`data:{id1,id2,radius}`), `chamfer` **[IPC]** (`data:{id1,id2,dist1,dist2}`).

## layer
`list` · `create` (`data:{name, color?, linetype?}`; cor como nome ou número ACI) · `set_current` · `set_properties` (`data:{name, color?, linetype?, lineweight?}`) · `freeze`/`thaw` · `lock`/`unlock`.

## block
`list` · `insert` (`data:{name, x, y, scale?, rotation?}`) · `insert_with_attributes` (`data:{…, attributes:{TAG: valor}}`) · `get_attributes` (`data.entity_id`) · `update_attribute` (`data:{entity_id, tag, value}`) · `define` (`data:{name, entities:[{type:"LINE",x1,y1,x2,y2} | {type:"CIRCLE",cx,cy,radius} | {type:"ATTDEF",tag,x,y,height}]}`).

## annotation
| operation | `data` |
|---|---|
| `create_text` | `x, y, text, height?, rotation?, layer?` |
| `create_dimension_linear` | `x1,y1,x2,y2` (pontos medidos), `dim_x,dim_y` (posição da linha de cota) |
| `create_dimension_aligned` | `x1,y1,x2,y2, offset` |
| `create_dimension_angular` | `cx,cy` (vértice), `x1,y1,x2,y2` |
| `create_dimension_radius` | `cx,cy,radius, angle` |
| `create_leader` | `points:[[x,y],…], text` |

A cota usa o estilo de cota corrente. Para a altura do texto na prancha, ajuste antes `DIMSCALE` (via LISP, com pedido do usuário) ou use o fator de `scripts/prancha.py`.

## view
`zoom_extents` · `zoom_window` (`x1,y1,x2,y2`) · `get_screenshot` (PNG). No `ezdxf` a captura é uma renderização do DXF em memória, que serve para conferir a geometria.

## pid
Símbolos de P&ID (biblioteca CTO). Raramente útil em edificações. Use só se o usuário pedir fluxograma de processo (ex.: ETE, casa de bombas).

## Regras práticas
- Muitas entidades: crie em sequência e só no fim faça `zoom_extents` + `get_screenshot`.
- Guarde os handles devolvidos: hachura, cota associada e edição posterior dependem deles.
- `ezdxf` não lê DWG. Se o usuário só tem DWG e está sem AutoCAD, peça para exportar DXF ou use o modo IPC.
- Antes de `erase`, `move` em lote, `purge` ou `execute_lisp`: descreva o efeito e peça confirmação.
