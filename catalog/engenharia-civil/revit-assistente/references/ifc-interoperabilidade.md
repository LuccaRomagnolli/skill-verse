# IFC e troca com Archicad, AutoCAD e SOLIDWORKS

## Exportar IFC do Revit
- Formato: **IFC4 Reference View** para coordenação/visualização; **IFC2x3 Coordination View 2.0** quando o destino for software mais antigo ou o edital pedir.
- Inclua quantidades base (`ExportBaseQuantities`) para quantitativo no destino.
- Exporte por **vista 3D filtrada** (só estrutura) quando for para o calculista/compatibilização.
- Confira o mapeamento de categorias (`Arquivo → Exportar → Opções → IFC`): pilares → `IfcColumn`, vigas → `IfcBeam`, lajes → `IfcSlab`, fundações → `IfcFooting`/`IfcPile`.
- Pelo agente: receita em `revit-api-csharp.md` (com a pasta informada pelo usuário).

## Com o ArchiCAD
- Troca por IFC nos dois sentidos. A auditoria de entrega do lado ArchiCAD é a skill `archicad-assistente` (BCF para pendências).

## Com o AutoCAD
- Plantas/cortes do Revit → DWG: `Arquivo → Exportar → CAD` (configuração de layers por categoria). A prancha final pode ser montada com `autocad-assistente`.
- DWG da arquitetura → Revit: vincular, nunca explodir. Limpe a base antes (`autocad-assistente`, "base de arquitetura").

## Com o SolidWorks
- Peças metálicas/equipamentos: STEP do SolidWorks → família genérica no Revit (importar em família `Modelo genérico`), ou IFC se o SolidWorks exportar. Ver skill `solidworks-assistente`.

## Coordenadas
- Combine com todos os projetistas um **ponto base** (cruzamento de eixos A-1 = 0,0) e a mesma rotação do norte de projeto. Registre na ficha do projeto.
