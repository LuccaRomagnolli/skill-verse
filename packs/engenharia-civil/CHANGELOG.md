# Changelog — Pack Engenharia Civil

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
