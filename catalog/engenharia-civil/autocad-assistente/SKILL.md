---
name: autocad-assistente
description: Opera o AutoCAD/AutoCAD LT pelo chat via MCP. Cria e organiza layers no padrão de projeto, desenha e edita entidades, cotas, textos, blocos e atributos, detalha seções de vigas e pilares a partir do cálculo, monta pranchas A0–A4 com carimbo e escala, limpa a planta de arquitetura para lançar no TQS/Revit, inspeciona DWG/DXF recebidos, plota PDF e roda AutoLISP com confirmação. Sem AutoCAD (ou no macOS), gera DXF. Use quando o usuário pedir para "desenhar no AutoCAD", "detalhar a seção", "criar layers", "gerar DXF", "montar a prancha", "carimbo", "plotar em PDF", "limpar a planta da arquitetura", "base para o TQS", "quantos pilares tem nesse DWG", "LISP", "escala do desenho", "planta de fôrma" ou mencionar AutoCAD, CAD, DWG ou DXF.
---

# Assistente AutoCAD

Ferramentas do MCP `autocad`: `system`, `drawing`, `layer`, `entity`, `annotation`, `block`, `view` (e `pid`, raramente útil). Cada uma recebe `operation` + parâmetros. A tabela completa, com o que cada operação aceita e o que só funciona com o AutoCAD aberto, está em `references/mcp-operacoes.md`.

## 1. Antes de qualquer coisa
1. `system` → `status`. Veja o `backend`:
   - `file_ipc`: AutoCAD/LT 2024+ aberto no Windows. Tudo disponível.
   - `ezdxf`: modo sem AutoCAD (macOS/Linux ou AutoCAD fechado). O desenho fica em memória, só lê **DXF** (não DWG) e grava com `drawing` → `save_as_dxf` `{path}`. `offset`, `fillet`, `chamfer`, `plot_pdf` e `execute_lisp` não funcionam.
   - Erro de conexão no Windows: peça para abrir o AutoCAD e carregar o `mcp_dispatch.lsp` (APPLOAD; caminho no manual do pack). Depois `system` → `init`.
2. Desenho existente: `drawing` → `info` e `get_variables` `{names:["INSUNITS","LTSCALE","DIMSCALE"]}`. Confirme a **unidade** medindo algo conhecido (porta ≈ 0,80 m). Desenho novo: padrão **cm** e layers de `references/padrao-layers.md`, a menos que o escritório tenha padrão próprio (pergunte uma vez).
3. Trabalhe numa **cópia** quando for limpar ou alterar muito um arquivo recebido.

## 2. Detalhe de seção (viga ou pilar)
O script `scripts/detalhe_secao.py` calcula a geometria (cobrimento, estribo, posição das barras, cotas, textos) e gera:
- `--ops arquivo.json`: lista de chamadas do MCP em ordem. Execute cada item chamando a ferramenta `tool` com os demais campos como parâmetros. Onde aparecer `"entity_id": "$anterior"`, use o `handle` devolvido pela operação anterior (a polilinha da barra que recebe a hachura).
- `--dxf arquivo.dxf`: desenho pronto (R12). Útil sem AutoCAD, para enviar a terceiros ou para abrir com `drawing` → `open`.

```bash
python3 scripts/detalhe_secao.py --b 15 --h 45 --c 3 --inf 3x12.5 --sup 2x8 --estribo 5 --s 13 --nome V1 --ops V1.json --dxf V1.dxf
python3 scripts/detalhe_secao.py --b 20 --h 50 --c 3 --pilar 3 --phi 20 --estribo 5 --s 20 --nome P1 --origem 40 0 --ops P1.json
```
Use os dados da skill `concreto-armado-nbr6118` (barras e estribos sugeridos). Rodando na pasta do projeto, o script pega o **cobrimento pela classe de agressividade da ficha** (`projeto-contexto.json`, skill `contexto-do-projeto`). `--c` sobrescreve. Várias seções no mesmo desenho: desloque cada uma com `--origem x y` (ex.: 40 cm entre seções).

Depois de executar as operações: `view` → `zoom_extents` e `view` → `get_screenshot` para mostrar o resultado ao usuário. Salve com `drawing` → `save` (AutoCAD) ou `save_as_dxf`.

## 3. Pranchas, carimbo e escala
Nunca calcule escala, tamanho de folha ou altura de texto de cabeça. Use `scripts/prancha.py`:
```bash
python3 scripts/prancha.py --cabe 18.5 12.0 --unidade m      # sugere formato e escala para um desenho de 18,5 × 12 m
python3 scripts/prancha.py --formato A1 --escala 50 --unidade cm --obra "<obra>" --local "<cidade/UF>" \
    --conteudo "Planta de fôrmas" --rt "<RT>" --registro "<CREA/CAU>" --art "<nº>" --folha 01/03 --ops A1.json --dxf A1.dxf
```
O JSON de saída traz a moldura, a área livre e as **alturas de texto já convertidas** (`alturas_texto`). Use-as em `create_text`. O roteiro completo (prancha no modelo × layout com viewport, PDF, checklist de entrega) está em `references/plotagem-e-pranchas.md`. Convenções de folha, linhas, cotas e concreto, com as normas citadas por número: `references/padroes-desenho-abnt.md`.

**Pranchas para aprovação**: prefeituras costumam ter padrão próprio (formato, carimbo, quadro de áreas, escalas). Com a ficha do projeto, procure esse padrão com a skill `contexto-do-projeto` (consulta: `padrão de apresentação de projetos <município>`), registre a fonte e siga-o. Ele prevalece sobre o padrão genérico. Preencha o carimbo com os dados da ficha e do responsável técnico informados pelo usuário. **Nunca invente** registro profissional nem número de ART.

## 4. Base de arquitetura para o cálculo (TQS, Revit)
Roteiro em `references/base-para-calculo.md`: diagnóstico de layers/unidade, proposta de limpeza (com confirmação), congelar o que não é estrutural, levar o cruzamento de eixos para 0,0 e salvar `BASE-ESTRUTURA-<pavimento>.dxf`, um por pavimento.

## 5. Ler e auditar um DWG/DXF recebido
- `drawing` → `info`, `layer` → `list`, `entity` → `count` por layer e `block` → `list`. Resuma o que há no arquivo.
- Contagens e comprimentos em lote (ex.: quantos blocos `PIL*`, comprimento total de um layer): receitas em `references/autolisp.md` (IPC). No modo DXF, `entity` → `list` por layer e some com um script Python a partir da saída. Nada de soma de cabeça.
- Quantitativos e orçamento a partir dessas medidas: skill `quantitativos-sinapi`.

## 6. Pedidos comuns
- **Layers**: `layer` → `create` `{name, color, linetype?}` para cada linha de `references/padrao-layers.md`; depois `set_current`.
- **Contorno de peça**: `entity` → `create_rectangle` `x1,y1,x2,y2` ou `create_polyline` `points` + `data: {closed: true}`.
- **Cotas**: `annotation` → `create_dimension_linear` `{x1,y1,x2,y2,dim_x,dim_y}`.
- **Textos**: `annotation` → `create_text` `{x,y,text,height,layer}`. Para ⌀, use `%%c`.
- **Blocos com atributos** (carimbo, etiqueta de pilar): `block` → `define` com `ATTDEF`, depois `insert_with_attributes`. Para editar, `update_attribute`.
- **Edição**: `entity` → `move`/`copy`/`rotate`/`mirror`/`array` pelo handle. Antes de apagar ou mover muitas entidades, **descreva o que vai fazer e peça confirmação**. No IPC existe `drawing` → `undo`.
- **Comando que o MCP não tem**: explique o comando ao usuário (`references/comandos-essenciais.md`) ou, com pedido explícito, rode AutoLISP (`references/autolisp.md`).

## 7. Layout de canteiro
Para desenhar canteiro de obras (áreas de vivência, acessos, central de armação/fôrmas, baias, proteção de periferia), levante antes as exigências com a skill `consulta-normas` (NR-18, NR-24, NR-10) e anote o item da norma em cada elemento do desenho (layer `EST-TEXTO`).

## 8. Integração com as outras skills
- Cálculo → desenho: `concreto-armado-nbr6118` (armaduras) → seção §2 → prancha §3 → `memorial-de-calculo`.
- Revit: DWG vinculado e exportação de vistas (skill `revit-assistente`). TQS: base §4 e plantas DXF exportadas pelo TQS (skill `tqs-assistente`). SolidWorks: peças metálicas exportadas em STEP/DXF (skill `solidworks-assistente`).

## Limites e responsabilidade
- Gera desenhos de apoio (seções, pranchas, layers, elementos simples, limpeza de base). Não substitui o detalhamento completo (armação longitudinal com comprimentos, ancoragens, dobras, tabela de aço) nem a revisão do projetista. O responsável técnico assina e responde pelo projeto.
- `system` → `execute_lisp` executa código arbitrário no AutoCAD: só use com pedido explícito do usuário, mostre o código antes e envolva em `UNDO`.
- Padrões de prancha e de desenho seguem as normas citadas por número e o padrão da prefeitura. Confirme a edição vigente. Nenhum texto de norma ABNT é reproduzido.
- No modo headless, salve o DXF em pasta do usuário e diga o caminho; nada fica salvo automaticamente.
