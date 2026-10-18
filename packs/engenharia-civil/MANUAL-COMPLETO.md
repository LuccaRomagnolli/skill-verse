# Manual completo de uso — {{PACK_NOME}}

Versão {{VERSAO}} (candidato)

Este guia acompanha o ZIP. O instalador gera também um `MANUAL.md` com as skills e conexões escolhidas na sua instalação.

## 1. O que o pack faz

| Tarefa | Skill | Resultado a conferir |
|---|---|---|
| Criar ou retomar a ficha da obra | `contexto-do-projeto` | `projeto-contexto.json`, fontes, decisões e pendências |
| Preparar cortes de planta baixa e modelagem arquitetônica | `planta-arquitetonica` | DXF, `planos-bim.json` e manifesto |
| Desenhar e preparar pranchas CAD | `autocad-assistente` | DXF e, com aplicativo operável, DWG/PDF |
| Trabalhar no BIM | `revit-assistente` ou `archicad-assistente` | modelo salvo, IDs/GUIDs e IFC conferidos |
| Modelar componentes | `solidworks-assistente` | peça, massa e exportações conferidas |
| Levantar quantidades e orçamento | `quantitativos-sinapi` | quantidades e planilha com mês/UF informados |
| Consultar fontes públicas | `consulta-normas` | documento oficial, item, edição e data de acesso |
| Redigir laudo ou relatório | `relatorio-tecnico` | texto e evidências revisados pelo responsável |

As nove skills são instruções e ferramentas de apoio. Nenhuma conclusão de projeto decorre apenas de um arquivo gerado ou de um MCP conectado.

## 2. Instalação

Descompacte o ZIP e abra sua pasta no Claude Code ou Codex. Peça **“instale este pack”**. Se necessário, peça **“leia `instalador/SKILL.md` e siga as instruções”**. Escolha apenas os aplicativos que usa e confira a prévia antes de alterar o ambiente.

```bash
python3 instalador/scripts/install.py detectar
python3 instalador/scripts/install.py instalar --plataforma codex --simular
python3 instalador/scripts/install.py instalar --plataforma codex
python3 instalador/scripts/install.py verificar --sem-mcp
python3 instalador/scripts/install.py manual
```

No Windows, use `py -3` se `python3` não estiver disponível. Escolha `claude`, `codex` ou `ambas`. Depois de configurar uma conexão, repita `verificar` com o aplicativo aberto e um arquivo de teste. Um handshake prova apenas que o servidor respondeu.

Para atualizar, descompacte uma nova versão e peça **“atualize o pack”**. Confira a lista de skills instaladas e remova componentes de versões anteriores que não integrem mais o pack. Para desinstalar, peça **“desinstale o pack”** na pasta instalada. Mantenha projetos e entregas fora da pasta da instalação.

## 3. Começar e retomar uma obra

Use uma pasta por obra. Peça: **“Inicie a ficha de uma edificação em Município/UF, revisão A. Tenho a planta em `arquitetura/planta.dxf`; confirme unidade, uso, níveis, fontes oficiais e pendências antes de desenhar.”**

A ficha `projeto-contexto.json` guarda fontes com edição, item e data, decisões, arquivos, revisão e pendências. Não preencha cotas ou parâmetros normativos desconhecidos. Na próxima sessão, abra a mesma pasta e peça: **“Retome este projeto pela ficha; mostre arquivos, decisões e pendências.”**

Normas ABNT completas e licenciadas não acompanham o pack. Confirme sua edição e os valores aplicáveis no exemplar autorizado para o projeto.

## 4. Fluxo 1 — planta baixa, cortes CAD e BIM arquitetônico

1. **Origem:** no DWG/DXF, confira unidade, escala, origem, camadas e duas dimensões conhecidas. Para PDF/imagem, trace os pontos em pixels e calibre com uma medida; confira com uma segunda medida independente.
2. **Dados que faltam:** informe cotas de piso, pé-direito, paredes, portas, janelas, alturas, peitoris, linhas de corte e sentido de vista. Uma planta 2D não contém todos esses dados.
3. **Preparação:** use `planta-arquitetonica/scripts/planta.py` para estruturar e validar `planta-arquitetonica.json`. Gere `corte-<id>.dxf`, `planos-bim.json` e `manifesto-arquitetura.json`.
4. **CAD:** abra cada DXF no AutoCAD, compare com a fonte, meça cotas e verifique aberturas. Salve DWG/PDF no aplicativo quando a conexão real permitir.
5. **BIM:** escolha Revit ou Archicad. Em cópia do RVT/PLN, resolva níveis, famílias/favoritos e IDs/GUIDs reais antes de cada lote. Simule, confirme, crie, releia as propriedades e salve. Audite o IFC no destino.

`planos-bim.json` é um plano com placeholders, não uma importação automática. O corte inclui elementos interceptados pelo plano e exige inspeção e complementação. O fluxo completo com planta real de cliente ainda não foi validado.

## 5. Outras tarefas

- **CAD:** forneça medidas, unidade, revisão e objetivo; peça desenho ou prancha. Revise camadas, cotas, escala e plotagem no aplicativo.
- **Revit e Archicad:** o pack ajuda a ler, modelar e auditar elementos com as conexões compatíveis. Dados de geometria, materiais e tipos devem vir de fonte conferida pelo profissional; a criação BIM não valida um projeto de engenharia.
- **SOLIDWORKS:** forneça dimensões e material de uma peça ou montagem; confira massa, desenho e STEP/DXF no aplicativo.
- **SINAPI:** forneça a planilha oficial de mês e UF, quantitativos com origem e o BDI escolhido. Confira unidades, critérios de medição e exclusões.
- **Normas públicas e laudos:** registre fonte, item, data e evidências. Revise o documento com o responsável técnico antes de usar externamente.

## 6. Conexões opcionais

O instalador oferece cinco MCPs: `normas-publicas`, `autocad`, `archicad`, `revit` e `solidworks`. Configure apenas o que usa. Teste uma leitura em arquivo de cópia; para gravações, examine a prévia, confirme o lote, confira o resultado no aplicativo e salve uma nova revisão.

## 7. Conferência e limites

Antes de entregar, confira origem e revisão, geometria e unidades, quantidade e propriedades dos elementos, fontes oficiais, arquivos salvos e exportações reabertas. Registre pendências e o responsável pela revisão. Testes locais de scripts e empacotamento demonstram integridade do pacote, não validação normativa ou funcionamento integral dos softwares. Consulte `CHANGELOG.md` para o estado da versão.
