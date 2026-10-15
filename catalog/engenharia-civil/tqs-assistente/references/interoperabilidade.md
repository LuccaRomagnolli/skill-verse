# TQS ↔ AutoCAD, Revit, ArchiCAD e SolidWorks

## Entrada: arquitetura no Modelador
- **DWG/DXF por planta**, limpo, com o cruzamento de eixos de referência em 0,0, na unidade esperada pelo Modelador (cm é o usual). Prepare com a skill `autocad-assistente` ("base para cálculo"): `BASE-ESTRUTURA-<pavimento>.dxf`.
- **IFC da arquitetura** (Revit/ArchiCAD): versões recentes do TQS aceitam IFC como referência. Exporte com a vista só da arquitetura relevante e confira níveis.
- Use os mesmos nomes de planta e as mesmas cotas da arquitetura (lista do Revit: receita "Listar níveis" da skill `revit-assistente`; do TQS: `tqs_edificio.py ler`).

## Saída: estrutura para os outros projetistas
- **IFC do TQS** (caminho recomendado para o modelo completo, com lajes e fundações): exportado pelo próprio TQS. No Revit, vincular (`Inserir → Vincular IFC`). No ArchiCAD, mesclar/vincular IFC e auditar com `archicad-bim-check`.
- **Lançamento para o Revit pelo agente** (alternativa quando o IFC não serve, por exemplo para obter elementos nativos editáveis):
  ```bash
  python scripts/tqs_edificio.py ler --edificio "<nome>" --saida ed.json
  python scripts/tqs_modelo.py listar --edificio "<nome>" --saida modelo.json
  python scripts/tqs_modelo.py para-revit --modelo modelo.json --edificio-json ed.json --saida lancamento.json
  ```
  e então `revit-assistente` → `lancamento.py lancamento.json`. Leia os `avisos`: lajes não convertidas, plantas repetidas, seções não retangulares, posições aproximadas.
- **Plantas e detalhes em DXF/PDF**: `python scripts/tqs_dwg.py exportar <arquivo>.DWG <arquivo>.DXF` → carimbo/prancha com `autocad-assistente`.
- **Quantitativos**: tabela de ferros (`--tabela-ferros`) e volumes/formas dos relatórios do TQS → `quantitativos-sinapi`.

## SolidWorks
Insertos, chapas de ligação e peças metálicas modeladas no SolidWorks (STEP) servem para compatibilizar com o modelo 3D do TQS/Revit. O dimensionamento dessas peças não é feito pelo TQS de concreto.

## Erros clássicos de compatibilização
- Origem diferente entre arquitetura e estrutura (deslocamento de metros): sempre 0,0 no mesmo cruzamento de eixos.
- Nível = piso acabado na arquitetura × topo da laje na estrutura: combine o critério e registre na ficha.
- Unidade: DXF em metros lido como cm (desenho 100× menor).
