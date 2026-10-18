# Manual completo de uso — {{PACK_NOME}}

Versão {{VERSAO}} (candidato) · leitura recomendada antes do primeiro projeto

Este manual acompanha o ZIP. Após a instalação, há uma cópia em `~/SkillVerse/engenharia-civil/MANUAL-COMPLETO.md` e uma versão para navegador em `MANUAL-COMPLETO.html`. O `MANUAL.md` gerado pelo instalador mostra as chamadas de skills e as conexões escolhidas **na sua instalação**. Consulte também `CHANGELOG.md` para o estado de validação desta versão.

## 1. Escolha o fluxo

| Preciso fazer | Comece por | Resultado principal |
|---|---|---|
| Organizar uma obra e retomar em outra sessão | `contexto-do-projeto` | `projeto-contexto.json` com fontes, decisões, artefatos e pendências |
| Criar cortes de planta baixa e preparar BIM arquitetônico | `planta-arquitetonica` | DXF dos cortes, `planos-bim.json` e manifesto |
| Analisar e documentar uma estrutura | `cargas-combinacoes` e `modelo-estrutural` | mapa de ações, revisão do modelo, resultados e memorial |
| Desenhar formas e seções no CAD | `autocad-assistente` | DXF para conferência e eventual DWG/PDF no aplicativo |
| Modelar no Revit ou Archicad | skill do software escolhido | modelo conferido no aplicativo, com IDs/GUIDs e arquivo salvo |
| Preparar quantitativos, orçamento ou laudo | `quantitativos-sinapi` ou `relatorio-tecnico` | planilhas e documentos revisáveis |

Você pode pedir em português, sem decorar comandos. Diga qual é a obra, a revisão, o arquivo de origem, as unidades, o software de destino e o que deseja entregar. O agente deve registrar o que falta antes de executar uma etapa dependente desses dados.

## 2. Requisitos e instalação

**Base:** Python 3.10 ou mais recente, Claude Code ou Codex e permissão para criar arquivos na pasta da obra. Descompacte o ZIP antes de instalar. Alguns scripts precisam de bibliotecas próprias indicadas pelo instalador; conexões com softwares podem precisar de `uv`, Node, API, add-in ou licença. Cada aplicativo precisa estar instalado e aberto quando a operação pedir leitura ou gravação nele.

1. Abra a pasta descompactada no Claude Code ou Codex.
2. Diga **“instale este pack”**. Se o agente não reconhecer o instalador, peça **“leia `instalador/SKILL.md` e siga as instruções”**.
3. Escolha Claude Code, Codex ou ambos e somente as conexões de software que você usa. Examine o diagnóstico e a prévia antes de permitir alterações no ambiente.
4. Rode a verificação proposta pelo instalador. Um MCP que inicia ou responde ao handshake ainda precisa ser testado com o aplicativo real e um arquivo de teste.
5. Abra `~/SkillVerse/engenharia-civil/MANUAL.html` para as chamadas específicas desta instalação e `MANUAL-COMPLETO.html` para este guia.

Pelo terminal, na raiz da pasta descompactada:

```bash
python3 instalador/scripts/install.py detectar
python3 instalador/scripts/install.py instalar --plataforma codex --simular
python3 instalador/scripts/install.py instalar --plataforma codex
python3 instalador/scripts/install.py verificar --sem-mcp
python3 instalador/scripts/install.py manual
```

No Windows, use `py -3` em vez de `python3`. Em `--plataforma`, escolha `claude`, `codex` ou `ambas`. `--sem-mcp` verifica a instalação das skills sem afirmar que um software foi conectado. Para conexões, consulte as opções em `python3 instalador/scripts/install.py instalar --help`, selecione os MCPs desejados e repita `verificar` com o aplicativo aberto. Não ponha chaves de API em arquivos da obra ou no ZIP.

Para atualizar, descompacte a nova versão e peça **“atualize o pack”** nessa pasta; depois regenere o manual e confira o changelog. Para remover, abra a pasta do pack instalado e peça **“desinstale o pack”**. Guarde uma cópia da obra e dos resultados fora da pasta de instalação. A instalação fica em `~/SkillVerse/packs/engenharia-civil/`; os projetos ficam onde você os criou.

## 3. Comece e retome um projeto

Crie uma pasta exclusiva para cada obra. Primeiro pedido sugerido:

**Exemplo:** “Inicie a ficha de uma edificação residencial em Município/UF, revisão A. Tenho planta em `arquitetura/planta.dxf`; confirme unidades, níveis, finalidade da obra, fontes oficiais e pendências antes de gerar qualquer desenho ou cálculo.”

O agente registra `projeto-contexto.json` na pasta da obra. Esse arquivo concentra uso, município, revisão, fontes com edição/item/data, decisões, hipóteses, artefatos gerados e pendências. Responda às perguntas sobre pavimentos, área, materiais, exposição, cargas e destino BIM apenas com dados conhecidos; marque o restante como pendente. Não invente cotas, alturas ou parâmetros normativos.

Uma organização possível:

```text
obra/
  projeto-contexto.json
  arquitetura/planta.dxf
  arquitetura/planta-arquitetonica.json
  arquitetura/desenhos-arquitetura/
  estrutura/modelo-estrutural.json
  estrutura/resultados/
  entregas/
```

O nome das subpastas é escolha da equipe. Mantenha a fonte original, revisões e unidades. Ao terminar uma etapa, peça ao agente para registrar caminho, revisão, data, hash ou identificador disponível, avisos e responsável pela conferência. Em outra sessão, abra a **mesma pasta da obra** e diga:

**Exemplo:** “Retome este projeto pelo `projeto-contexto.json`. Mostre revisão, fontes, decisões, arquivos produzidos e pendências antes de continuar.”

O agente deve verificar se a fonte local ainda é vigente quando isso puder ter mudado. Normas ABNT completas e licenciadas não acompanham o pack; forneça os itens que você pode consultar no seu exemplar e registre a edição conferida.

## 4. As 15 skills

As instruções detalhadas de cada skill estão em `plugin/skills/<nome>/SKILL.md` no ZIP e em `~/SkillVerse/packs/engenharia-civil/plugin/skills/` após instalar. A chamada direta de cada skill aparece no seu `MANUAL.md`; também é possível fazer um pedido normal em português.

| Skill | Quando chamar | Entradas e saída a conferir |
|---|---|---|
| `contexto-do-projeto` | início, retomada e registro de decisões | município, uso, revisão, fontes e `projeto-contexto.json` |
| `planta-arquitetonica` | cortes arquitetônicos e preparação de BIM | geometria conferida, níveis e aberturas; DXF, plano BIM e manifesto |
| `modelo-estrutural` | modelo analítico da mesma revisão | `modelo-estrutural.json`, validação e conversões rastreáveis |
| `cargas-combinacoes` | mapa de ações, vento e combinações | cargas com unidade/origem/posição e combinações com perfil declarado |
| `skyciv-assistente` | análise linear opcional | prévia, confirmação de envio, resultados, créditos e manifesto |
| `concreto-armado-nbr6118` | triagem de viga, laje e pilar suportados | dados geométricos e esforços; memória, alertas e revisão técnica |
| `autocad-assistente` | formas, seções, pranchas e conferência CAD | DXF e, quando operável no aplicativo, DWG/PDF conferidos |
| `revit-assistente` | lançamento estrutural e operação BIM no Revit | projeto aberto, níveis, famílias, IDs, RVT e leitura de volta |
| `archicad-assistente` | lançamento estrutural e operação BIM no Archicad | PLN copiado, pavimentos, favoritos, GUIDs, IFC/BCF e auditoria |
| `solidworks-assistente` | peças metálicas e componentes de obra | dimensões, material, massa, peça, desenho/STEP/DXF conforme operação |
| `tqs-assistente` | diagnóstico e automação de TQS no Windows | edifício, variantes, processamento confirmado e arquivos do TQS |
| `quantitativos-sinapi` | levantamento e orçamento | quantidades com unidades, planilha oficial de mês/UF e BDI informado |
| `memorial-de-calculo` | reunir hipóteses, cálculo e pendências | memória revisável com fontes, resultados e limitações declaradas |
| `consulta-normas` | consultar fontes públicas NRs, DNIT e SINAPI | documento oficial, item, edição, link e data de acesso |
| `relatorio-tecnico` | laudo e relatório de vistoria | fotos, notas de campo, método, conclusões e revisão do responsável |

As skills podem orientar etapas sem MCP. A capacidade de ler ou alterar um arquivo em um software depende da conexão realmente configurada, da versão e do projeto aberto. TQS usa a API Python do próprio TQS, não um MCP deste pack.

## 5. Fluxo 1 — planta baixa, cortes CAD e BIM arquitetônico

### 5.1 Prepare a origem

**DWG/DXF:** abra o desenho no CAD e confira unidade, escala, origem, direção dos eixos, camadas e duas dimensões conhecidas. `extrair-dxf` lê somente segmentos `LINE` e `LWPOLYLINE` da camada explicitamente indicada como eixo de parede. Se a origem for DWG, exporte uma cópia DXF adequada ou transcreva a geometria conferida. Blocos, cotas, textos, hachuras e camadas arbitrárias não viram paredes automaticamente.

**PDF ou imagem:** preserve o original e trace os pontos necessários em coordenadas de pixel. Calibre com uma medida conhecida e use uma **segunda medida independente** de controle. Corrija escala, rotação e traçado quando a conferência falhar. Um PDF/imagem sem medidas confiáveis não fornece geometria pronta para executar.

Para ambas as origens, informe ou confirme cotas de piso, pé-direito, espessuras, posições de portas/janelas, alturas, peitoris, linhas de corte e sentido de vista. A planta 2D não traz todos esses valores. Peça ao agente para deixar campos desconhecidos como pendência.

### 5.2 Estruture, valide e gere

Pedido sugerido:

**Exemplo:** “Leia a planta da revisão A. Mostre as unidades, os eixos de parede reconhecidos e tudo que falta para o corte A-A. Prepare `planta-arquitetonica.json`, valide e só gere o DXF após minha conferência das alturas e aberturas.”

O agente usa `planta-arquitetonica/scripts/planta.py` na skill instalada. Um exemplo de DXF com eixos de parede já separados:

```bash
python3 scripts/planta.py extrair-dxf planta.dxf --layer ARQ-EIXO-PAREDE --unidade m --projeto Obra-1 --revisao A --nivel Terreo --cota-m 0 --altura-m 3 --espessura-m 0.15 --corte A-A 2 -1 2 4 --saida planta-arquitetonica.json
python3 scripts/planta.py validar planta-arquitetonica.json
python3 scripts/planta.py gerar planta-arquitetonica.json --saida desenhos-arquitetura
```

Esses comandos são executados a partir de `plugin/skills/planta-arquitetonica/`, com caminhos ajustados para os arquivos da obra. A extração gera uma **base a completar**: aberturas, pisos, níveis e outras paredes precisam ser conferidos no JSON. Para PDF/imagem, peça ao agente para usar `calibrar` após o traçado dos pontos; há sintaxe e modelo de entrada em `SKILL.md` dessa skill.

A saída inclui `corte-<id>.dxf`, `planos-bim.json` e `manifesto-arquitetura.json`. O corte mostra interseções com o plano, pisos e níveis cadastrados. Ele não projeta objetos atrás do plano nem resolve cobertura, escadas, terreno ou detalhes executivos. Abra cada DXF no AutoCAD, compare com a fonte, meça cotas, examine as aberturas e complete a documentação gráfica. Salve DWG/PDF no aplicativo quando a conexão estiver operacional.

### 5.3 Modele em Revit ou Archicad

Escolha um destino BIM por operação e trabalhe em uma cópia salva do RVT ou PLN. `planos-bim.json` é um **plano de chamadas**, com placeholders que dependem do modelo aberto. Não é uma importação automática da planta.

**Revit:** diagnostique o MCP e leia níveis, famílias e tipos no RVT. Relacione os níveis do JSON aos reais, substitua `$tipo:<id>` por `typeId` de portas e janelas, crie paredes primeiro e substitua `$parede:<id>` pelo `hostWallId` retornado. Mostre quantidade, categoria, unidade, tipos e arquivo de destino; confirme cada lote. Leia IDs, geometria, espessura, nível, altura e hospedeiro de volta. Salve o RVT. As vistas de corte do Revit ainda são criadas/conferidas manualmente.

**Archicad:** selecione a instância, confirme Tapir, pavimentos e favoritos no PLN copiado. Resolva `$pavimento:<id>` para `floorIndex` e `$favorito:*` para favoritos reais do template; confirme estrutura/material/espessura do piso. Faça prévia (`confirm=false`) e mostre os lotes antes de criar. Após as paredes, associe `id_origem` aos GUIDs e resolva `$parede:<id>` para portas e janelas. Confira biblioteca, orientação, lado de abertura, peitoril, espessura e elementos lidos de volta. Salve e audite o IFC depois da inspeção.

Nenhum dos dois caminhos foi validado de ponta a ponta com uma planta arquitetônica real de cliente nesta versão. O destino BIM exige famílias/favoritos e propriedades adequadas ao template. TQS não é o destino arquitetônico desse fluxo; SOLIDWORKS atende componentes, não o modelo de edifício.

## 6. Fluxo 2 — estrutura, SkyCiv, CAD e BIM

1. **Contexto:** escolha obra, revisão, uso, município, classe/ambiente, fontes oficiais e destino BIM. Registre os itens NBR conferidos no exemplar licenciado. Peça a lista de dados pendentes.
2. **Ações:** peça um mapa por ambiente e por elemento com tipo, intensidade, unidade, geometria/posição, origem e combinação. Inclua paredes, cargas concentradas, cobertura, garagem, equipamentos e construção quando aplicáveis. Para vento, forneça os parâmetros exigidos por `vento.py`; a Errata 1:2025 da NBR 6123 permanece pendente de confronto.
3. **Combinações:** declare o perfil usado (`concreto-6118` ou `geral-8681`), coeficientes e fonte. As rotinas de combinação de esforços exigem efeitos correspondentes na mesma seção e unidade; não misture cargas brutas com momentos ou cortantes.
4. **Modelo:** prepare `modelo-estrutural.json` com níveis, eixos, materiais, barras, placas, vínculos, ações, combinações e revisão. Execute a validação de `modelo-estrutural/scripts/modelo.py` e confira os avisos. Esse modelo é analítico/estrutural e não substitui o modelo arquitetônico do fluxo 1.
5. **SkyCiv opcional:** use credenciais da conta do cliente em `SKYCIV_USERNAME` e `SKYCIV_API_KEY`. Revise o objeto enviado e a prévia. `skyciv_status` só verifica o ambiente local; a análise `S3D.model.solve` consome créditos. Confirme o envio, guarde entrada, resposta, manifesto, resultados e crédito consumido. Se o resultado da chamada for incerto por falha de rede, confira a atividade da conta antes de reenviar. Compare reações/esforços/deslocamentos com caso independente.
6. **Dimensionamento e CAD:** use as rotinas suportadas de concreto para triagem, com hipóteses explícitas e revisão profissional. Gere plantas de fôrma e seções DXF da **mesma revisão** do modelo; confira medidas, escala, etiquetas e impressão no AutoCAD. Salve DWG/PDF no aplicativo quando possível.
7. **BIM:** modele a mesma revisão no Revit ou Archicad. Confirme níveis, tipos/favoritos, materiais e quantidades em uma cópia salva. Faça prévia antes de gravar, confira IDs/GUIDs e propriedades lidas de volta, e valide o IFC no destino. Um IFC que abre não prova preservação semântica das categorias.
8. **Entrega:** produza memorial, quantitativos e lista de pendências vinculados à revisão. Registre quem fará a revisão técnica independente e o que ainda impede o uso em obra.

Pedido sugerido:

**Exemplo:** “Para a revisão A desta obra, organize o mapa de ações, valide o modelo estrutural e mostre um plano de análise SkyCiv, pranchas CAD e lançamento no Archicad. Não envie análise com créditos nem altere o PLN antes de eu revisar as entradas e os lotes.”

## 7. Softwares, conexões e custos

| Integração | Ambiente e preparação | O que conferir no aplicativo |
|---|---|---|
| AutoCAD | MCP opcional; no macOS o backend local trabalha com DXF | desenho aberto, unidade, medidas, layers, DWG e PDF |
| Revit | Windows, Revit compatível, MCP Switch/add-in configurado | RVT, níveis, tipos, contagens, seções, IFC |
| Archicad | Archicad 29/30, bridge e Tapir conforme recursos usados | PLN copiado, pavimentos, favoritos, GUIDs, propriedades, IFC/BCF |
| SOLIDWORKS | aplicativo/licença e MCP opcional | peça/montagem, massa, desenho, STEP/DXF |
| TQS | Windows, TQS licenciado e API Python oficial; sem MCP deste pack | edifício, variante copiada, processamento, resultados e desenhos |
| SkyCiv | conta/API/créditos do cliente; MCP opcional | modelo enviado, atividade da conta, resultados e créditos |
| Normas públicas | MCP opcional e fontes oficiais disponíveis | edição, item, endereço e data de acesso |

O instalador oferece seis MCPs opcionais: `normas-publicas`, `skyciv`, `autocad`, `archicad`, `revit` e `solidworks`. Use `verificar` para separar: skill instalada, servidor iniciado, ferramentas expostas e leitura do aplicativo. Teste uma operação pequena em arquivo de **cópia**, inspecione o resultado e só então amplie o lote. Processamento TQS, envio SkyCiv e alterações em modelos precisam de confirmação explícita; o custo SkyCiv é da conta do cliente.

## 8. Pedidos prontos por tarefa

| Tarefa | Pedido que você pode adaptar |
|---|---|
| Regras locais | “Inicie esta obra em Cidade/UF; liste código de obras, zoneamento, Bombeiros e concessionárias em fontes oficiais, com itens e pendências.” |
| Cortes de arquitetura | “Confira a escala da planta e gere o corte A-A em DXF; peça as alturas e aberturas que não estiverem na fonte.” |
| BIM arquitetônico | “Use `planos-bim.json` para preparar lotes no Revit; resolva níveis, famílias e IDs, mostre a prévia e compare os elementos criados.” |
| Ações e vento | “Monte o mapa de ações do pavimento por ambiente e elemento; aponte unidades, posições, valores sem fonte e itens faltantes.” |
| Análise estrutural | “Valide `modelo-estrutural.json` e mostre a prévia SkyCiv da revisão B, com custo e parâmetros, para minha conferência.” |
| Concreto | “Calcule esta viga com geometria, material, cobrimento, esforços e combinações informados; mostre memória e verificações fora do escopo.” |
| CAD | “Gere planta de fôrma DXF da revisão B e liste o que devo conferir no AutoCAD antes de salvar DWG/PDF.” |
| Archicad | “Diagnostique Tapir e a instância; simule o lançamento em cópia do PLN, confirme favoritos/pavimentos e leia de volta todos os GUIDs.” |
| Revit estrutural | “Faça a prévia dos pilares e vigas no RVT de teste; confirme níveis/tipos e compare os IDs e medidas depois de lançar.” |
| TQS | “Leia o edifício TQS e proponha uma variante em cópia; mostre o plano antes de processar.” |
| SOLIDWORKS | “Modele uma chapa de base com dimensões e material fornecidos; confira massa e prepare desenho/DXF.” |
| Orçamento | “Levante quantitativos por revisão e orce com a planilha SINAPI oficial de mês/UF informado; mostre unidades, exclusões e BDI.” |
| Memorial | “Monte o memorial com hipóteses, fontes, cálculo, resultados, pendências e revisão do responsável técnico.” |
| Laudo | “Organize as fotos e anotações de campo em um laudo; separe observação, hipótese, conclusão e limite da vistoria.” |

## 9. Como conferir um resultado

Antes de usar um desenho, modelo, cálculo ou documento, confira:

1. **Origem e revisão:** fonte preservada, versão do modelo, arquivo de destino e modificações posteriores.
2. **Geometria e unidades:** medidas conhecidas, coordenadas, níveis, aberturas, seção, espessura e cotas verificadas no software de destino.
3. **Ações e cálculo:** cargas com fonte e posição, combinações e normas com edição/item, hipóteses e verificações que ficaram fora do escopo do script.
4. **Software:** quantidade de elementos e propriedades lidas de volta, arquivo salvo, exportações reabertas e avisos do aplicativo.
5. **Rastreabilidade:** manifeste entradas, hash quando disponível, saída, pendências, data e nome de quem revisou.

Os testes locais do pacote verificam scripts e instalação, mas **não** demonstram conformidade normativa nem validam todos os softwares reais. Houve ensaio real de uma planta **estrutural** no AutoCAD para Mac 2027 e de um modelo **estrutural** pequeno no Archicad 30 macOS; leia `VALIDACAO-AUTOCAD-MAC-2027.md` e `VALIDACAO-ARCHICAD-30-MAC.md` para evidência e limites. Restam, entre outros, análise SkyCiv real, teste arquitetônico completo, Revit real, revisão normativa independente e conferências Windows. O pack permanece candidato.

Projeto, orçamento e laudo para uso profissional dependem do responsável técnico habilitado, de revisão independente quando aplicável e de ART/RRT conforme o caso. Confira normas vigentes e requisitos locais antes de aprovação, execução ou assinatura.

## 10. Problemas frequentes

| Sintoma | Verificação e próximo passo |
|---|---|
| A skill não aparece | Confirme a plataforma instalada, reinicie o agente e execute `verificar --sem-mcp`; consulte `MANUAL.md` para a chamada direta. |
| Python ou biblioteca ausente | Rode `detectar`, confira Python 3.10+ e siga o requisito indicado pela skill/conexão; não altere o Python do software sem necessidade. |
| Nenhuma parede saiu do DXF | Confira camada passada a `--layer`, unidades e entidades `LINE`/`LWPOLYLINE`; blocos e hachuras exigem transcrição/conversão conferida. |
| PDF/imagem não bate com a cota | Refaça o traçado e a calibração com duas medidas independentes; não gere cortes com escala incerta. |
| Corte sem interseção ou estranho | Confira linha e sentido do corte, níveis e coordenadas; compare o DXF com a fonte no CAD. |
| `planos-bim.json` tem `$tipo`, `$parede`, `$favorito` ou `$pavimento` | Resolva esses identificadores no modelo aberto antes de qualquer chamada de criação. |
| MCP responde, aplicativo não | Abra o projeto de teste, confira versão, add-in, porta, licença e acesso; handshake isolado não valida operação. |
| IFC mudou categoria/espessura | Confira template, tradutor, estrutura de laje e propriedades no destino; registre o desvio e corrija antes da entrega. |
| SkyCiv perdeu a resposta | Consulte a atividade e o consumo de créditos da conta antes de tentar novo envio. |
| Valor normativo sem referência | Use fonte oficial ou exemplar licenciado, registre edição/item e deixe a verificação pendente até o responsável conferir. |

Se a dúvida persistir, abra a pasta da obra no agente e peça: **“Mostre a entrada, o comando, o aviso original, a saída e a pendência registrada; não substitua dados ausentes por suposições.”**
