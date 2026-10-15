# API Python do TQS: síntese para o agente

Fonte: documentação pública do TQS Docs (seção "Python"), interface TQS-Python 1.2.x, que vem com o TQS desde a V23. Síntese própria, não cópia. **Nomes exatos variam entre versões**: antes de escrever código novo, rode `python scripts/tqs_ambiente.py --introspectar <Módulo>` e use os nomes que a versão instalada expõe.

## Instalação e execução
- Windows apenas. O wheel `TQSPythonInterface-<versão>-py3xx-none-any.whl` fica em `TQSW\EXEC\Python`. O instalador do TQS tenta instalá-lo. Se falhar: `<python> -m pip install "<caminho do .whl>"`.
- A documentação pede **Python 32 bits ≥ 3.7**. O TQSModel do V25 roda em 64 bits. Erro de DLL ao importar quase sempre é arquitetura trocada: `tqs_ambiente.py` diagnostica.
- Importação: `from TQS import TQSBuild, TQSExec, TQSModel, TQSDwg`.
- Programas que rodam **dentro** dos editores gráficos (TQSEag) ficam em `TQSW\EXEC\Python`. Scripts avulsos (os desta skill) rodam de qualquer pasta.
- Feche o edifício no TQS antes de gravar ou processar por script, para não ter dois programas no mesmo arquivo.

## Módulos
| Módulo | Para quê | Script da skill |
|---|---|---|
| **TQSBuild** | Dados do edifício (o que o "Editor de Dados do Edifício" mostra): plantas, cotas, materiais, cobrimentos, cargas, critérios gerais. Lê, altera e grava, inclusive "salvar como" (família de variantes) | `tqs_edificio.py` |
| **TQSExec** | Fila de tarefas do Gerenciador: processamento global, planta de cargas, desenhos de lajes/formas, tabela de ferros, pré-moldados | `tqs_processar.py` |
| **TQSModel** | Modelo estrutural do Modelador: pilares (seções por lance), vigas (nós e trechos), lajes, fundações, cargas, furos, eixos. Lê e grava | `tqs_modelo.py` |
| **TQSDwg** | Desenhos DWG do TQS: ler (iterador), criar (linhas, polilinhas, textos, blocos, cotas, ferros inteligentes), salvar como DXF/PDF | `tqs_dwg.py` |
| TQSEag | Comandos Python nos menus dos editores gráficos | — |
| TQSJan | Janela com desenho TQS (wxPython) | — |
| TQSGeo / TQSUtil | Geometria 2D e utilidades comuns | — |
| TQSGrid | Tabelas em DWG/HTML/LST | — |

## Padrões que se repetem
- **Funções devolvem `istat`**: 0 = sucesso, diferente de 0 = erro. Sempre teste.
- **Índices**: plantas no TQSBuild começam em 0; no TQSModel, `floors.GetFloorName(i)` vai de **1** a `GetNumFloors()`.
- **Unidades**: TQSDwg e coordenadas do Modelador em **cm** e graus; cotas/alturas de piso em **m**; cobrimentos em cm; cargas em **tf**, tf/m e tf/m² (converta para kN por script: 1 tf = 9,80665 kN).

## TQSBuild (essencial)
- `b = TQSBuild.Building()`, `b.file.Open(nome)`, `b.file.Save()`, `b.file.SaveAs(novo)`, `b.file.SuppressMessages(1)`.
- Funções globais: `TQSBuild.BuildingRoot()` (raiz da árvore de edifícios), `TQSBuild.BuildingContext()` (edifício/pavimento da pasta atual).
- Subobjetos: `project` (títulos, norma `concreteCode` = constantes `NORMA_*`, tipo de estrutura, cota inicial `floorHeight`), `model` (`structuralModel` = `PORTICO_HORVER` Modelo IV / `PORTICO_LAJES` Modelo VI, `secondOrderEfect` γz × P-Delta, análise dinâmica, ISE, efeito incremental), `floorsplan` (por índice: nome, título, classe `ICL*`, altura para a planta de baixo, repetições, modelo de grelha `GRELHA_*`, protensão, temperatura/retração), `materials` (`environmentalClass` 0..3 = CAA I..IV, fck de vigas/lajes, pilares e fundações, variação de fck em pilares por piso), `covers` (cobrimentos por elemento, por planta, ACI, pré-moldados), `loads` (`GetLoad/SetLoad` por prefixo `PREFIXO*`: γf, ψ0, ψ1, ψ2…; redução de sobrecarga por piso; desaprumo; `windloads` com parâmetros da NBR 6123 (V0, S1, S3, rugosidade, classe) e casos por direção).

## TQSExec (essencial)
- `job = TQSExec.Job()` → `job.EnterTask(tarefa)` (várias) → `job.Execute()` (abre o Gerenciador, processa e fecha).
- `TaskFolder(edificio, TaskFolder.FOLDER_FRAMES | FOLDER_FLOORS (+ nome da planta) | FOLDER_COLUMNS | FOLDER_FOUNDATIONS | FOLDER_GENERAL…)` define a pasta atual.
- `TaskGlobalProc(...)`: parâmetros 0/1/2/3 iguais aos da janela do processamento global (plantas, formas, lajes, vigas, pilares, grelha, pórtico, transferências, fundações, escadas, incêndio, pré-moldados).
- Outras tarefas: `TaskLoadsReport()`, `TaskSlabDrawings(...)`, `TaskLatticeSlabs(...)`, `TaskFloorPlanDrawings(...)` (exige pasta da planta), `TaskRebarSchedule()` (tabela de ferros única na pasta GERAIS), `TaskStairs()`, `TaskPreCast*()`.
- Uso típico de estudo de alternativas: TQSBuild "salvar como" com fck/modelo diferentes → TQSExec na fila → comparar resultados (tabela de ferros, relatórios).

## TQSModel (essencial)
- Abrir: `TQSBuild.Building().RootFolder(nome)` (entra na pasta do edifício) → `m = TQSModel.Model()` → `m.file.OpenModel()` (ou `OpenNewModel()` para criar) → … → `m.file.Save()` / `Close()`.
- Plantas: `m.floors.GetNumFloors()`, `GetFloorName(i)`, `GetFloor(nome)` (torna atual e devolve `Floor`).
- Iterar: `floor.iterator.GetNumObjects(TQSModel.TYPE_x)` e `GetObject(TYPE_x, k)`, com `TYPE_SECPIL` (seções de pilar), `TYPE_VIGAS`, `TYPE_LAJES`, `TYPE_FUNDAC`, cargas `TYPE_CARCON/CARLIN/CARARE` etc.
- Criar: o padrão do Modelador é "**dados atuais** + criar". Preencha `m.current.globalColumnData.columnData` (ou `floor.current.floorBeamData`, `floorSlabData`) e chame `floor.create.CreateColumn(x, y)`, `CreateBeam(((x1,y1),(x2,y2)…))`, `CreateSlab(x, y, ângulo)`, `CreateFoundation`, cargas `Create*Load`. Depois de mudar geometria, `floor.util.DoIntersections()` em cada planta.
- Pilar: lista espacial, uma ou mais **seções** (`ColumnNumSections`, `ColumnGetSection(i)`, `ColumnSectionUpdateGeometry`); geometria `columnGeometry.sectionType` (`COLUMNTYPE_R/L/U/C/P/N`), `sectionB1/H1/B2/H2`, `sectionAngle`; inserção `insertionX/Y` + `columnInsertion` (centro ou canto); `GetFoudation()` (grafia da API) devolve o apoio.
- Viga: `beamIdent` (número/título), `NumNodes()`, `GetBeamNode(k)` (`nodeX`, `nodeY`, tipo de cruzamento), `GetBeamGeometry()` / `GetSegmentBeamGeometry(k)` (`width`, `depth`, excentricidade), articulações, carga distribuída.
- Laje: `slabIdent`, `slabGeometry` (`type` `SLABTYPE_*`, `thickness`, rebaixo; nervuradas com `LoadManufacturer(fabricante, forma)`), `mainAngle`. O contorno é calculado pelo TQS a partir de vigas/pilares/bordos, e não é dado de entrada.

## TQSDwg (essencial)
- `d = TQSDwg.Dwg()`; `d.file.Open/New/Save/SaveAs(nome)` (extensão `.DXF` ou `.PDF` converte); `PurgeBlocks/PurgeLevels`.
- Desenhar: propriedades atuais `d.draw.level/style/color` e depois `Line`, `Rectangle`, `PolyStart`+`PolyEnterPoint`+`Polyline`, `Arc`, `Circle`, `Text(x, y, h, ang, texto)`, blocos (`BlockOpen/Close/Insert`), `DwgMix`, `XrefInsert`; cotas `d.dim.DimHorizontal/Vertical/Aligned/…`; `d.settings.scale` multiplica alturas de texto e símbolos.
- Ler: `d.iterator.Begin()` e `Next()` até `DWGTYPE_EOF`; propriedades do elemento lido (`itype`, `x1..y2`, `xy`, `xc/yc/radius`, `text`, `blockName`, `level`, `color`…).
