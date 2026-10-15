# Macros VBA para o que o MCP não faz (folha de desenho, PDF, DXF)

O MCP não cria desenhos 2D nem exporta DXF/PDF. O agente **gera a macro** e o usuário executa no SOLIDWORKS: `Ferramentas → Macro → Novo` (salvar `.swp`), colar o código, `Executar` (F5). Antes, explique o que a macro faz. Ela só cria arquivos novos na pasta indicada e não altera a peça.

Brasil: projeção no **1º diedro** (padrão ABNT de desenho técnico). Nas opções do documento de desenho, ajuste "Tipo de projeção: Primeiro ângulo" se o template for americano.

## Folha com as 3 vistas padrão + PDF e DXF
Abra a peça (ou montagem) salva e rode:
```vba
Dim swApp As SldWorks.SldWorks
Sub main()
    Set swApp = Application.SldWorks
    Dim modelo As SldWorks.ModelDoc2
    Set modelo = swApp.ActiveDoc
    If modelo Is Nothing Then MsgBox "Abra a peça antes.": Exit Sub
    If modelo.GetPathName = "" Then MsgBox "Salve a peça antes.": Exit Sub

    Dim tpl As String
    tpl = swApp.GetUserPreferenceStringValue(swUserPreferenceStringValue_e.swDefaultTemplateDrawing)
    Dim desenho As SldWorks.DrawingDoc
    Set desenho = swApp.NewDocument(tpl, 0, 0, 0)          ' formato do template padrão do usuário
    desenho.Create1stAngleViews2 modelo.GetPathName           ' frontal, superior e lateral no 1º diedro

    ' importa as cotas do modelo para as vistas
    desenho.InsertModelAnnotations3 swImportModelItemsSource_e.swImportModelItemsFromEntireModel, _
        swInsertAnnotation_e.swInsertDimensionsMarkedForDrawing, True, True, False, False
    Dim dm As SldWorks.ModelDoc2
    Set dm = desenho
    dm.ForceRebuild3 False

    Dim base As String, erros As Long, avisos As Long
    base = Left(modelo.GetPathName, InStrRev(modelo.GetPathName, ".") - 1)
    dm.Extension.SaveAs base & ".SLDDRW", swSaveAsVersion_e.swSaveAsCurrentVersion, swSaveAsOptions_e.swSaveAsOptions_Silent, Nothing, erros, avisos
    dm.Extension.SaveAs base & ".PDF", swSaveAsVersion_e.swSaveAsCurrentVersion, swSaveAsOptions_e.swSaveAsOptions_Silent, Nothing, erros, avisos
    dm.Extension.SaveAs base & ".DXF", swSaveAsVersion_e.swSaveAsCurrentVersion, swSaveAsOptions_e.swSaveAsOptions_Silent, Nothing, erros, avisos
    MsgBox "Gerados: " & base & ".SLDDRW/.PDF/.DXF"
End Sub
```
As cotas importadas são as **cotas que dirigem o esboço**. Por isso os esboços devem estar bem cotados (`boas-praticas-modelagem.md`). Depois, a prancha pode ser finalizada no AutoCAD (`autocad-assistente`): abrir o DXF, aplicar o carimbo com `prancha.py`.

## DXF só da face de uma chapa (para corte)
Selecione a face plana maior da chapa na tela e rode:
```vba
Dim swApp As SldWorks.SldWorks
Sub main()
    Set swApp = Application.SldWorks
    Dim p As SldWorks.PartDoc
    Set p = swApp.ActiveDoc
    Dim m As SldWorks.ModelDoc2
    Set m = p
    Dim saida As String
    saida = Left(m.GetPathName, InStrRev(m.GetPathName, ".") - 1) & "-corte.DXF"
    Dim dados(11) As Double   ' vista: normal à face selecionada
    Dim ok As Boolean
    ok = p.ExportToDWG2(saida, m.GetPathName, swExportToDWG_e.swExportToDWG_ExportSelectedFacesOrLoops, True, dados, False, False, 0, Nothing)
    MsgBox IIf(ok, "DXF gerado: " & saida, "Falhou: selecione uma face plana antes")
End Sub
```

## Lista de peças da montagem (CSV)
```vba
Dim swApp As SldWorks.SldWorks
Sub main()
    Set swApp = Application.SldWorks
    Dim a As SldWorks.AssemblyDoc
    Set a = swApp.ActiveDoc
    Dim comps As Variant, i As Long, f As Integer, c As SldWorks.Component2
    comps = a.GetComponents(True)   ' só o 1º nível: subconjuntos entram com a massa total, sem contar duas vezes
    f = FreeFile
    Open Left(swApp.ActiveDoc.GetPathName, InStrRev(swApp.ActiveDoc.GetPathName, "\")) & "lista-pecas.csv" For Output As #f
    Print #f, "componente;arquivo;massa_kg"
    For i = 0 To UBound(comps)
        Set c = comps(i)
        If Not c.GetModelDoc2 Is Nothing Then
            Print #f, c.Name2 & ";" & c.GetPathName & ";" & Format(c.GetModelDoc2.Extension.CreateMassProperty.Mass, "0.000")
        End If
    Next i
    Close #f
    MsgBox "lista-pecas.csv gravada na pasta da montagem"
End Sub
```
Some os pesos do CSV com um script (por exemplo, o de quantitativos), e não de cabeça.

## Cuidados
- A exportação de face (`ExportToDWG2`) varia entre versões. Se a macro falhar, faça manualmente: com a face selecionada, `Arquivo → Salvar como → DXF` → "Faces/Loops/Arestas selecionadas".
- Os nomes de constantes (`swSaveAsCurrentVersion`, `swDefaultTemplateDrawing`…) vêm da biblioteca de tipos do SOLIDWORKS, já referenciada nas macros novas. Se o editor acusar "variável não definida", verifique `Ferramentas → Referências → SOLIDWORKS <ano> Constant type library`.
- Nunca gere macro que apague arquivos ou altere opções globais do sistema sem pedido explícito.
