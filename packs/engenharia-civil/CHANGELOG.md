# Changelog — Pack Engenharia Civil

## 1.4.1 — 2026-10-17 (candidato)
- Teste no AutoCAD para Mac 2027 Education: DXF de planta aberto; `INSUNITS=6` (metros), 4 pilares, 8 linhas de vigas, 4 linhas de laje e cotas geométricas de 4,000 × 5,000 m lidas por AutoLISP. DWG salvo e reaberto com as mesmas contagens e medidas. PDF da prancha gerado no próprio AutoCAD em A3 completo, 1:50, e inspecionado visualmente.
- Corrigidos os escapes Unicode do DXF R12, a fonte TrueType, o espaçamento do carimbo e as posições de etiquetas/cota após inspeção da prancha real. A configuração de plotagem A3 usa mídia `ISO full bleed A3 (420.00 x 297.00 MM)` e escala `1=0.05` para desenho em metros a 1:50.
- O AutoCAD para Mac aceita AutoLISP e scripts `.scr`; a conexão MCP fixada continua em `ezdxf` no macOS e ainda não controla o aplicativo. Licença usada no teste: Education (uso não comercial). Persistem as pendências SkyCiv real, revisão normativa independente, Revit, Archicad e validação da conexão AutoCAD no Windows.

## 1.4.0 — 2026-10-17 (candidato)
- Modelo estrutural JSON v1 com unidades explícitas, revisão, níveis, eixos, barras, placas, materiais, apoios, ações e combinações. Conversão para SkyCiv e para a entrada Revit anterior, com IDs e SHA-256 rastreáveis. Conferência do mapa de ações por `mapa_ref`, unidade, módulo e fonte; o exemplo é didático.
- MCP SkyCiv opcional com credenciais do cliente no ambiente, prévia sem cobrança, confirmação antes da análise linear, `validate_input`, malha de placas, inspeção de status, resultados, relatório e consumo de créditos. Falha de rede após envio é incerta e não gera repetição automática. Triagem conservadora gera argumentos para a rotina local de viga apenas após transcrição conferida de caso uniaxial suportado. Não executa `S3D.design.rc.check` como NBR 6118.
- DXF de planta de fôrma por nível, seções geométricas e pranchas da mesma revisão; AutoCAD real ainda é necessário para conferir medidas e salvar DWG/PDF. Skill Archicad substituída por `archicad-assistente`, com plano de criação de pilares, vigas e lajes via MCP/Tapir, simulação antes de gravar, auditoria, IFC e BCF. As exclusões locais da skill anterior foram preservadas.
- Fluxos, manual, gatilhos e testes atualizados; 14 skills e 6 MCPs opcionais.

### Pendências para liberação
| Verificação | Responsável | Evidência exigida | Estado |
|---|---|---|---|
| Conta SkyCiv real e créditos | Cliente com conta API + responsável técnico | Manifesto, consumo, relatório e resposta da análise de referência | Pendente |
| Reações, esforços, deslocamentos e malha | Engenheiro estrutural independente | Comparação assinada com caso analítico/software independente, tolerâncias e capturas do modelo | Pendente |
| Valores, edições e combinações NBR | Responsável técnico com exemplar licenciado | Mapa de ações, itens/edições conferidos, fatores e parecer; Errata 1:2025 da NBR 6123 | Pendente |
| Plantas AutoCAD | Projetista CAD em Windows com AutoCAD | DWG/PDF salvos, cotas e escala medidas, seções e coordenadas conferidas | Pendente |
| Modelo Revit | Projetista BIM em Windows com Revit | RVT, contagens, tipos, níveis, cotas, IFC reaberto e checklist | Pendente |
| Modelo Archicad | Projetista BIM com Archicad 29 e Tapir | PLN, simulação e criação conferidas, GUIDs, seções, coordenadas, IFC/BCF reabertos | Pendente |
| Instalação no cliente | Equipe Skill-Verse | Handshake, verificação e remoção no Claude Code e Codex nas plataformas de entrega | Pendente para Windows; macOS local verificado |

## 1.3.3 — 2026-10-15 (candidato)
- `cargas-combinacoes` 1.3.0: mapa de ações por zona/elemento com unidade, origem, item e checagens explícitas de carga concentrada, paredes, cobertura, garagem, equipamentos e construção. Uso genérico deixa de ser aceito como critério de carga; ações concentradas/lineares não são diluídas na área.
- Combinações normais com perfil obrigatório na CLI: NBR 6118:2023 + Emenda 1:2026 para concreto ou hipótese geral agrupada da NBR 8681:2025. Corrigida a ponderação por tipo de variável e a exclusão de variáveis favoráveis no ELU; `--gamma-g` isolado não gera mais combinação especial. A diferença entre normas específicas e gerais depende de decisão documentada do projetista.
- Vento passa da base NBR 6123:1988 para a base 2023: S3 reclassificado (residências usuais no grupo 3), limite de altura de S2 e categoria V corrigidos, fator de vizinhança `fv` exigido para força, faixas de influência sem perda de área. **Recalcule todo resultado antigo de vento e combinações.**
- **Ainda não liberado:** confrontar a Errata 1:2025 da NBR 6123 (divulgada pela ABNT, não fornecida), confirmar vigência/erratas no Catálogo ABNT, compatibilizar 8681:2025 com 6118:2026 em revisão independente, conferir projetos reais e testar integrações nos softwares.

## 1.3.2 — 2026-10-15 (candidato)
- Texto-base NBR 6118:2023 confrontado com a Emenda 1:2026 para os critérios implementados; matrizes de rastreabilidade da base e da emenda documentam cobertura e lacunas sem distribuir os PDFs.
- **Correção de resistência:** `ηc` passa a reduzir o bloco comprimido e o diagrama de concreto para C45–C90. Recalcular saídas e memoriais gerados antes desta versão nessas classes.
- Armadura mínima de flexão passa a considerar o momento mínimo e a altura útil, sem extrapolar a Tabela 17.3 (CA-50, d/h=0,8) para outros casos. Sugestões de barras respeitam diâmetro ≤ cobrimento nominal; alertas adicionados para bordas de laje sem continuidade e armadura de pele em vigas altas.
- A triagem TQS de CAA/fck/cobrimento foi conferida contra as Tabelas 7.1/7.2 da referência 2026; deixou de reduzir cobrimento por flag genérica e passou a exigir 45 mm no trecho de pilar junto à fundação. Não equivale a validação do modelo estrutural.
- **Ainda não liberado:** validação independente dos cálculos e modelos, ATP dos projetos, verificações fora do escopo e testes de operação nos programas reais.

## 1.3.1 — 2026-10-15 (candidato)
- Emenda 1 da NBR 6118:2026 conferida por item e mapeada em `concreto-armado-nbr6118/references/auditoria-emenda-1-2026.md`, sem reproduzir ou distribuir o PDF licenciado. O texto-base 2023 ainda não foi disponibilizado para confronto integral.
- ATP do item 5.3: ficha registra classe, fundamento, estado e documento; impede dispensa de CC3 e exige evidência formal para dispensa/parecer. Memorial explicita a regra geral e as pendências. Responsável técnico deve confirmar classificação, acordo e independência do avaliador.
- Alertas de laje e viga ampliados para balanços, flecha/combinações, vibração de piso e detalhamento alterado pela emenda. Os scripts não passaram a dimensionar verificações fora de seu escopo.

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
- [ ] Validar independentemente os cálculos corrigidos com casos de referência e software real; revisar ATP (item 5.3), balanços (item 20.6), demais verificações estruturais e detalhamento com responsável técnico. Nenhum PDF ABNT é distribuído.
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
