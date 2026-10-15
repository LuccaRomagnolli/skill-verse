# Comandos do AutoCAD que o agente precisa conhecer

Para **orientar o usuário** quando a operação não existe no MCP, ou para montar AutoLISP com `(command ...)` (só em modo IPC e com pedido explícito). Alias entre parênteses. No AutoCAD em português os comandos aceitam o nome em inglês com sublinhado: `_LINE`, `_-LAYER`. Em LISP, **sempre** use a forma `_COMANDO` e o hífen para a versão de linha de comando (`_-LAYER`, `_-PLOT`, `_-INSERT`), que não abre caixas de diálogo.

## Configuração do arquivo
| Comando | Para quê |
|---|---|
| `UNITS` (UN) / `INSUNITS` | unidade do desenho (4 mm, 5 cm, 6 m). Confira antes de desenhar ou inserir blocos/xrefs |
| `LIMITS`, `DRAWINGSCALE` | limites e escala de anotação |
| `LTSCALE`, `PSLTSCALE`, `MSLTSCALE` | escala de tipos de linha (tracejado aparecendo contínuo = LTSCALE errado) |
| `DIMSTYLE` (D), `DIMSCALE` | estilo e fator de cota |
| `STYLE` (ST) | estilo de texto (fonte, altura fixa = 0 para permitir altura por texto) |
| `-LAYER` (LA) | criar, ligar, congelar, travar e definir cor/tipo/espessura |
| `LWDISPLAY` | mostrar espessuras de linha |

## Desenho e edição
`LINE` (L), `PLINE` (PL), `RECTANG` (REC), `CIRCLE` (C), `ARC` (A), `OFFSET` (O), `TRIM` (TR), `EXTEND` (EX), `FILLET` (F, raio 0 = cantos vivos), `CHAMFER` (CHA), `MOVE` (M), `COPY` (CO), `ROTATE` (RO), `SCALE` (SC), `MIRROR` (MI), `ARRAY` (AR), `STRETCH` (S), `JOIN` (J), `EXPLODE` (X), `BREAK` (BR), `PEDIT` (PE), `MATCHPROP` (MA), `HATCH` (H), `BOUNDARY` (BO), `REGION` (REG).

## Anotação
`TEXT`/`DTEXT` (DT), `MTEXT` (T), `DIMLINEAR` (DLI), `DIMALIGNED` (DAL), `DIMCONTINUE` (DCO), `DIMBASELINE` (DBA), `DIMANGULAR` (DAN), `DIMRADIUS` (DRA), `MLEADER` (MLD), `TABLE`, `FIELD`. Símbolos em texto: `%%c` diâmetro, `%%d` grau, `%%p` mais ou menos.

## Blocos e referências
`BLOCK` (B), `WBLOCK` (W), `INSERT` (I), `ATTDEF` (ATT), `ATTEDIT`, `BATTMAN`, `ATTSYNC`, `BEDIT` (blocos dinâmicos), `XREF`/`XATTACH`, `XCLIP`, `BIND`, `REFEDIT`, `IMAGEATTACH`, `PDFATTACH`.

## Consulta e limpeza
`LIST` (LI), `DIST` (DI), `AREA` (AA), `MEASUREGEOM` (MEA), `ID`, `QSELECT`, `FILTER`, `PURGE` (PU, `-PURGE` em LISP), `AUDIT`, `RECOVER`, `OVERKILL` (remove linhas sobrepostas), `-WBLOCK *` (regrava limpo), `LAYMRG`/`LAYDEL` (fundir/apagar layers; peça confirmação), `SETBYLAYER`.

## Layout e plotagem
`LAYOUT`, `MVIEW`, `MSPACE` (MS)/`PSPACE` (PS), `VPSCALE`, `PAGESETUP`, `PLOT` (`-PLOT` em LISP), `PUBLISH` (lote), `EXPORTPDF`, `ETRANSMIT` (empacotar com xrefs e fontes).

## Diferenças AutoCAD × AutoCAD LT × macOS
- **LT 2024+** roda AutoLISP (base do modo IPC deste MCP). Versões LT anteriores não rodam.
- **AutoCAD para Mac**: sem AutoLISP de automação externa nem `.NET`. O MCP fica em modo DXF (headless).
- Comandos de verticais (Architecture, MEP, Civil 3D) não existem no LT. Não os sugira sem confirmar o produto.
