# Changelog — Pack Engenharia Civil

## 1.3.0 — 2026-10-15
- **Candidato à liberação**: 12 skills revisadas para leitura da ficha na retomada, fontes/edições/itens oficiais, decisões, artefatos e pendências persistentes. A referência declarada é NBR 6118:2026; scripts herdados de 2023 exibem status pendente, sem alegar conformidade 2026.
- As cinco skills de software incluem diagnóstico, plano em lotes, inspeção, salvamento e registro. NBR 8800 atualizada para edição 2024 corrigida em 2025. Instalador sugere só conexões selecionáveis, diferencia handshake de aplicativo operável e protege add-ins do Revit preexistentes/alterados.
- Nova skill **revit-assistente** + conexão **revit** (mcp-servers-for-revit v1.0.0, MIT): o agente lê e cria
  níveis, eixos, pilares, vigas, lajes, cotas, tags e ambientes no Revit 2020–2026; `lancamento.py` converte o
  cálculo em chamadas com os tipos de seção certos; quantitativos de concreto por nível; IFC; C# com confirmação.
- Nova skill **solidworks-assistente** + conexão **solidworks** (Solidworks-MCP-Server v0.4.0, MIT): peças e
  montagens metálicas de obra, `perfis.py` (geometria, área, massa e peso de chapas e perfis), interferência,
  STEP e macros VBA para folha de desenho, PDF e DXF de corte.
- Nova skill **tqs-assistente** (sem MCP, via API Python oficial do TQS no Windows): diagnóstico do ambiente com
  introspecção da API instalada, leitura e conferência dos dados do edifício contra a NBR 6118:2023
  (Tab. 7.1 e 7.2), variantes numa cópia, processamento global em fila (só com confirmação), leitura do modelo,
  conversão para o Revit, exportação de desenhos DXF/PDF e conversão tf↔kN.
- **autocad-assistente** 1.3.0: proficiência geral (mapa completo das operações do MCP, comandos, AutoLISP seguro,
  padrões de desenho ABNT, plotagem), `prancha.py` (formatos A0–A4, carimbo, escala e alturas de texto) e
  roteiro de base de arquitetura limpa para TQS/Revit.
- Instalador: requisitos de ferramenta por conexão (`uv`, `node`), passo `extrair_zip` por versão do software
  (add-in do Revit em `%APPDATA%`, mesclando sem apagar nada) e remoção só do que o pack instalou.

### Validação pendente no software real (sem máquina Windows nesta versão)
- [ ] Confrontar cada critério herdado dos scripts com NBR 6118:2023 licenciada e Emenda 1:2026; revisar ATP (item 5.3) e balanços (item 20.6) com responsável técnico. O PDF da emenda não é distribuído.
- [ ] Revit: add-in carrega em 2024/2025/2026; `verificar` com handshake; `lancamento.py` no exemplo (tipos C#,
      eixos irregulares C#, pilares/vigas/lajes) e marcas; receitas C# de `revit-api-csharp.md` compilam.
- [ ] SOLIDWORKS: `uv sync` no Windows; chapa de base e perfil I do `perfis.py` com massa < 1% do script;
      macros VBA de `api-vba.md` (folha 1º diedro, PDF, DXF, lista de peças).
- [ ] TQS: `tqs_ambiente.py` (32/64 bits) em V23/V24/V25; `tqs_edificio.py ler/conferir/aplicar` no
      "Mod-Padrão"; `tqs_processar.py --executar`; `tqs_modelo.py listar/para-revit`; `tqs_dwg.py ler/exportar`.
- [ ] AutoCAD: `prancha.py` em modo IPC (Windows) e headless; `plot_pdf`.
- [ ] ArchiCAD 29: conexão, auditoria sem travamento de propriedades, destaque, issues e BCF reimportável.

## 1.2.0 — 2026-10-15
- Nova skill **contexto-do-projeto**: ficha do projeto (município, UF, uso, porte, ambiente → classe de agressividade)
  e pesquisa web guiada das exigências locais em fontes oficiais (código de obras, zoneamento, aprovação, Corpo de
  Bombeiros, concessionárias, CREA/ART) e da edição vigente das NBR, com registro de cada fonte.
- Instalação pergunta o município/UF de atuação (perfil padrão das fichas).
- MCP normas-publicas: `importar_documento_publico` (lei municipal, IT, norma de concessionária em PDF ou HTML),
  com bloqueio de sites de cópias e de exemplares de NBR.
- Memorial de cálculo inclui município, classe de agressividade e legislação local consultada (`--contexto`).
- Ficha do projeto conectada às demais skills: scripts de viga/laje/pilar e o detalhe do AutoCAD leem a CAA da ficha
  (cobrimento automático) e alertam concreto abaixo do mínimo da classe (NBR 6118, Tab. 7.1); auditoria ArchiCAD
  confere parâmetros numéricos do código de obras/zoneamento; cargas parte do uso da ficha; pranchas seguem o
  padrão de apresentação da prefeitura.

## 1.1.0 — 2026-10-14
- Nova conexão **normas-publicas**: índice local com NRs (texto vigente + manuais oficiais), normas e manuais
  do DNIT e cadernos técnicos do SINAPI, baixados das fontes oficiais na instalação/sob demanda.
- Nova skill **consulta-normas** (citação de item/página, checklists de canteiro e de medição).
- concreto-armado-nbr6118, quantitativos-sinapi, autocad-assistente e relatorio-tecnico passam a consultar
  o índice quando ele estiver conectado.

## 1.0.0 — 2026-10-14
- Primeira versão: concreto armado (vigas, lajes, pilares), cargas/vento/combinações, memorial de cálculo,
  quantitativos + SINAPI, assistente AutoCAD, auditoria BIM ArchiCAD e relatórios técnicos.
- Conexões: AutoCAD LT (puran-water/autocad-mcp @ 95476a3, v3.1) e ArchiCAD 29 (archicad-mcp-server 0.7.1).
