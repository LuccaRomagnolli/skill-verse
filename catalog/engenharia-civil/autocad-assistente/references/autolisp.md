# AutoLISP pelo `system` → `execute_lisp`

Só em modo **IPC** (AutoCAD aberto no Windows com `mcp_dispatch.lsp` carregado) e **só com pedido explícito do usuário**. Antes de executar: mostre o código, explique em uma frase o que ele altera e peça "sim". Prefira as operações nativas do MCP. Use LISP para o que elas não cobrem: seleção por filtro, edição em lote, variáveis de sistema, comandos de linha.

## Esqueleto seguro
```lisp
(progn
  (command "_.UNDO" "_BEGIN")              ; tudo vira um único desfazer
  (setq ss (ssget "_X" '((0 . "LINE") (8 . "ARQ-PAREDE"))))   ; filtro: tipo + layer
  (setq n 0)
  (if ss
    (repeat (sslength ss)
      (setq e (ssname ss n) d (entget e))
      ;; ... alterar d com subst/entmod ...
      (setq n (1+ n))))
  (command "_.UNDO" "_END")
  (princ (strcat "\nAlteradas: " (itoa n)))
  (princ))
```
- `ssget "_X"` varre o desenho todo sem interação. Nunca use `ssget` sem `"_X"`, porque fica esperando clique.
- Filtros DXF úteis: `(0 . "LWPOLYLINE")` tipo, `(8 . "EST-*")` layer com curinga, `(62 . 1)` cor, `(2 . "PILAR")` nome de bloco, `(-4 . "<OR") … (-4 . "OR>")` lógica.
- Edição: `(entmod (subst (cons 8 "NOVO") (assoc 8 d) d))` troca o layer. `(entupd e)` atualiza a tela.
- Comandos: `(command "_.-LAYER" "_M" "EST-FORMA" "_C" "7" "" "")`. Termine o comando com `""` (Enter) e use a forma com hífen.
- Variáveis: `(getvar "INSUNITS")`, `(setvar "DIMSCALE" 50)`. Para restaurar depois, guarde o valor antigo.

## Receitas
**Contar blocos por nome** (pilares/estacas de um projeto recebido):
```lisp
(progn (setq ss (ssget "_X" '((0 . "INSERT") (2 . "PIL*"))))
  (princ (if ss (sslength ss) 0)) (princ))
```

**Somar comprimento de polilinhas de um layer** (ex.: perímetro de fôrma, comprimento de vigas):
```lisp
(progn (vl-load-com) (setq tot 0.0 ss (ssget "_X" '((0 . "LWPOLYLINE,LINE") (8 . "EST-FORMA"))) i 0)
  (if ss (repeat (sslength ss)
    (setq o (vlax-ename->vla-object (ssname ss i)) tot (+ tot (vlax-curve-getDistAtParam o (vlax-curve-getEndParam o))) i (1+ i))))
  (princ (rtos tot 2 2)) (princ))
```
O resultado sai na unidade do desenho. Converter e somar com regra de medição é trabalho da skill `quantitativos-sinapi`.

**Mudar a escala de anotação em lote**: `(setvar "DIMSCALE" 50) (command "_.-DIMSTYLE" "_A" (ssget "_X" '((0 . "DIMENSION"))) "")`.

**Plotar um layout em PDF** (lote): prefira `drawing` → `plot_pdf`. Por LISP: `(command "_.-PLOT" "_Y" "Layout1" "DWG To PDF.pc3" "ISO full bleed A1 (841.00 x 594.00 MM)" "_M" "_L" "_N" "_E" "1:1" "_C" "_Y" "acad.ctb" "_Y" "_N" "_N" "_N" "C:/saida/prancha.pdf" "_N" "_Y")`. A sequência de respostas muda entre versões. Rode antes uma vez interativamente com `-PLOT` para confirmar.

## Nunca
- `(command "_.ERASE" (ssget "_X") "")` ou qualquer apagamento global sem confirmação e sem `UNDO`.
- Gravar arquivos fora da pasta do projeto, mexer em `acad.lsp`/`acaddoc.lsp` do usuário ou carregar `.fas`/`.vlx` de terceiros.
- Loops com `(command ...)` em milhares de entidades: use `entmod`, que é muito mais rápido.
