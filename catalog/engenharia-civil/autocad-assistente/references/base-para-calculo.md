# Preparar a planta de arquitetura para lançar a estrutura (TQS, Revit, cálculo manual)

O projeto de arquitetura chega "sujo": dezenas de layers, blocos de mobiliário, cotas de arquitetura, unidades misturadas, xrefs quebradas. O calculista precisa de uma **base limpa**: eixos, contorno de paredes, aberturas, níveis e o que define vãos e apoios.

## Roteiro (modo IPC; no modo DXF, faça o mesmo em um DXF exportado pelo usuário)
1. **Diagnóstico**: `drawing` → `info` e `layer` → `list`. Relate unidade (`get_variables` `INSUNITS`), extents, nº de layers e de blocos, e a medida de uma porta conhecida para confirmar a escala.
2. **Proposta de limpeza** (mostre a lista e peça confirmação antes de alterar):
   - manter: paredes, pilares/alvenaria estrutural indicada, esquadrias, escadas, shafts, níveis, eixos;
   - congelar ou apagar: mobiliário, louças, vegetação, hachuras de piso, cotas e textos de arquitetura, carimbo;
   - unificar a unidade (o TQS e o Revit esperam a unidade configurada; o Modelador do TQS costuma trabalhar em cm).
3. **Aplicar**: congelar com `layer` → `freeze`; apagar em lote só via LISP com `UNDO` (ver `autolisp.md`); `drawing` → `purge`.
4. **Origem e eixos**: leve um ponto notável (cruzamento de eixos A-1) para 0,0 com `entity` → `move`, para que arquitetura, estrutura e instalações coincidam. Crie `EST-EIXO` com os eixos de pilares.
5. **Salvar a base**: `save_as_dxf` com nome `BASE-ESTRUTURA-<pavimento>.dxf`, um arquivo por pavimento. É o que o Modelador do TQS e o Revit importam/vinculam bem.

## Por destino
- **TQS**: a planta limpa (DWG/DXF) é usada como referência externa no Modelador Estrutural. Um arquivo por planta, mesma origem em todos. Ver skill `tqs-assistente`.
- **Revit**: vincule o DWG (`Inserir → Vincular CAD`) com "Somente vista atual" desligado e posicionamento "origem com origem". Ver skill `revit-assistente`.
- **Cálculo manual pelo pack**: meça vãos (`DIST`/LISP de comprimentos) e alimente as skills `cargas-combinacoes` e `concreto-armado-nbr6118`.

## Não fazer
- Não apague nada do arquivo original: trabalhe numa cópia (`drawing` → `save` com outro nome antes de limpar).
- Não explodir blocos dinâmicos de esquadrias sem necessidade, porque perdem a informação de largura.
