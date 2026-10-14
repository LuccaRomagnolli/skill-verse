# Manual — {{PACK_NOME}}

Versão {{VERSAO}} · instalado em {{DATA}} · plataforma: {{PLATAFORMAS}}

{{PARA_VOCE}}
## Como usar
Você não precisa decorar comandos. Abra o Claude Code ou o Codex na pasta do seu projeto e **descreva o que quer em português**. O agente escolhe a skill certa. Se quiser forçar uma skill, use a chamada direta indicada em cada uma.

Três hábitos que dão resultado melhor:
1. **Dê os dados de uma vez**: dimensões, materiais, cargas e normas que você usa.
2. **Peça a memória**: os cálculos saem de scripts testados, com passo a passo e o item da norma, e não "de cabeça".
3. **Trabalhe numa pasta do projeto**: resultados, memorial e desenhos ficam organizados juntos.

## Suas skills
{{SKILLS}}
## Softwares conectados
{{MCPS}}
## Fluxos de trabalho
{{FLUXOS}}
## Solução de problemas
| Sintoma | O que fazer |
|---|---|
| A skill não aparece | Reinicie o Claude Code/Codex. No Claude Code, `/plugin` mostra se o pack está ativo. |
| "python3 não encontrado" | Instale o Python 3.10+ em python.org (no Windows, marque "Add to PATH"). |
| AutoCAD não responde | Abra o AutoCAD LT e carregue o `mcp_dispatch.lsp` (APPLOAD). No Mac, o modo é headless: gera DXF. |
| ArchiCAD não responde | Abra o ArchiCAD 29 com o projeto. Instale o add-on Tapir para IFC, issues e BCF. |
| Busca de normas sem resultado | Peça "baixe os documentos do DNIT/SINAPI sobre <assunto>" ou "atualize o catálogo de normas". Normas ABNT não estão no índice. |
| Resultado estranho | Peça "mostre as hipóteses e a memória" e confira os dados de entrada. |
| Atualizar o pack | Baixe a versão nova na área de membros, abra a pasta e diga "atualize o pack". |
| Remover o pack | Abra a pasta do pack ({{PASTA}}) e diga "desinstale o pack". |

## Responsabilidade técnica
As skills são **ferramentas de apoio**. Projeto, laudo e orçamento continuam sob responsabilidade do profissional habilitado que os assina (ART/RRT). Confira hipóteses, dados de entrada e resultados antes de usar em obra.
