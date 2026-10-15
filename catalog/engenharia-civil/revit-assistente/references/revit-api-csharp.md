# C# da Revit API pelo `send_code_to_revit`

O add-in compila o código com Roslyn e o coloca dentro de:
```csharp
using System; using System.Linq; using Autodesk.Revit.DB; using Autodesk.Revit.UI; using System.Collections.Generic;
public static class CodeExecutor {
    public static object Execute(Document document, object[] parameters) {
        /* SEU CÓDIGO AQUI */
    }
}
```
e executa **dentro de uma `Transaction` já aberta** pelo add-in (commit no fim, desfeita em caso de exceção).

## Regras
1. Variáveis disponíveis: `document` (não `doc`) e `parameters`. O código **precisa terminar com `return`** (qualquer objeto, que volta serializado em JSON). `return null;` se não houver o que devolver.
2. **Não abra outra `Transaction`** (dá erro de transação aninhada). Para isolar um trecho, use `SubTransaction`. Para pré-visualizar sem alterar, o caminho é ler e devolver os dados, sem chamar métodos de escrita.
3. Unidades internas: **pés** (comprimento), ft², ft³, **radianos**. Converta com `/ 304.8` (mm → pés) ou `UnitUtils.ConvertToInternalUnits(v, UnitTypeId.Meters)` (Revit 2021+). Para conferir números, use `scripts/revit_unidades.py`.
4. `ElementId`: no Revit 2024+ o valor é `long` (`id.Value`); até 2023 é `int` (`id.IntegerValue`). Para funcionar em todas as versões, compare `id.ToString()`.
5. Só `using` do template. Para outros namespaces, qualifique o nome completo (`Autodesk.Revit.DB.Structure.StructuralType.Column`).
6. Antes de executar: mostre o código ao usuário, explique o que ele altera e peça "sim". Código que apaga ou altera muitos elementos deve primeiro **contar** o que vai afetar e devolver a contagem para confirmação.

## Receitas
**Listar níveis** (o MCP não tem ferramenta própria):
```csharp
return new FilteredElementCollector(document).OfClass(typeof(Level)).Cast<Level>()
    .OrderBy(l => l.Elevation).Select(l => new { l.Name, cota_m = l.Elevation * 0.3048, id = l.Id.ToString() }).ToList();
```

**Volume de concreto por nível e categoria** (para o orçamento):
```csharp
var cats = new[] { BuiltInCategory.OST_StructuralColumns, BuiltInCategory.OST_StructuralFraming,
                   BuiltInCategory.OST_Floors, BuiltInCategory.OST_StructuralFoundation };
var linhas = new List<object>();
foreach (var c in cats)
    foreach (var e in new FilteredElementCollector(document).OfCategory(c).WhereElementIsNotElementType())
    {
        var v = e.get_Parameter(BuiltInParameter.HOST_VOLUME_COMPUTED)?.AsDouble() ?? 0;
        var nivel = document.GetElement(e.LevelId)?.Name ?? (e.get_Parameter(BuiltInParameter.FAMILY_BASE_LEVEL_PARAM)?.AsValueString() ?? "");
        linhas.Add(new { cat = c.ToString(), nivel, marca = e.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)?.AsString(), volume_ft3 = v });
    }
return linhas;
```
Converta `volume_ft3` → m³ com `scripts/revit_unidades.py` (ou o script de quantitativos) e não de cabeça.

**Definir material estrutural / fck** em pilares e vigas: parâmetro `BuiltInParameter.STRUCTURAL_MATERIAL_PARAM` (ElementId do material). Materiais: `new FilteredElementCollector(document).OfClass(typeof(Material))`, pelo nome (ex.: "Concreto C30").

**Unir geometrias** (laje × viga × pilar, para volumes corretos): `JoinGeometryUtils.JoinGeometry(document, a, b)` dentro de `try` (falha se não se tocam).

**Criar tabela (schedule)** de pilares:
```csharp
var s = ViewSchedule.CreateSchedule(document, new ElementId(BuiltInCategory.OST_StructuralColumns));
s.Name = "Quadro de pilares";
foreach (var f in s.Definition.GetSchedulableFields())
    if (new[] { "Marca", "Mark", "Tipo", "Type", "Volume" }.Contains(f.GetName(document))) s.Definition.AddField(f);
return s.Id.ToString();
```

**Exportar IFC** (dentro da transação, como o add-in exige):
```csharp
var op = new IFCExportOptions { FileVersion = IFCVersion.IFC4RV };
op.AddOption("ExportBaseQuantities", "true");
document.Export(@"C:\Projetos\Obra\IFC", "estrutura", op);
return "ok";
```
Pergunte a pasta ao usuário. Não use caminho inventado.

## Erros comuns
- `CS0103 'doc' does not exist`: use `document`.
- `Modification of the document is forbidden`: chamada fora do contexto (ex.: dentro de `Task.Run`). Mantenha o código síncrono.
- `Starting a new transaction is not permitted`: você abriu `Transaction`. Remova.
- Parâmetro `null`: o nome varia por idioma do template ("Marca"/"Mark"). Prefira `BuiltInParameter`.
