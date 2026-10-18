# Manual — {{PACK_NOME}}

Versão {{VERSAO}} · instalado em {{DATA}} · plataforma: {{PLATAFORMAS}}

Consulte `MANUAL-COMPLETO.md` ou `MANUAL-COMPLETO.html` para os fluxos de projeto, desenho, documentação e BIM.

{{PARA_VOCE}}
{{PERFIL}}

## Como usar
Abra o Claude Code ou Codex na pasta da obra e descreva sua tarefa em português. O agente escolhe a skill adequada; as chamadas diretas aparecem abaixo no manual personalizado.

1. Inicie a ficha: “Comece um projeto de <uso> em <município>/<UF> e registre fontes oficiais e pendências”.
2. Para uma planta, informe arquivo, unidade e duas medidas conhecidas. Peça cortes DXF e um plano BIM; confira níveis, alturas e aberturas antes de modelar.
3. Para desenhos, quantitativos ou relatórios, forneça os dados de origem e a revisão. Confira o resultado no aplicativo e com o responsável técnico.
4. Para retomar, abra a mesma pasta e peça um resumo de `projeto-contexto.json`.

## Conexões escolhidas
Depois da instalação, rode `python3 instalador/scripts/install.py verificar`. Um MCP iniciado não comprova que o aplicativo responde. Abra um arquivo de teste no software escolhido, faça uma leitura, simule qualquer gravação e confira o resultado em uma cópia antes de usar em projeto.

## Estado da versão {{VERSAO}}
Este ZIP é candidato. Os fluxos de planta, cortes e BIM ainda precisam de validação completa com projetos reais e revisão profissional. Normas ABNT licenciadas não acompanham o pacote. A versão para macOS testou operações limitadas no AutoCAD e Archicad; isso não demonstra funcionamento integral no Windows, Revit ou demais aplicativos. Consulte o changelog para os limites atuais.

## Skills instaladas
{{SKILLS}}

## MCPs configurados
{{MCPS}}
