# Manual — {{PACK_NOME}}

Versão {{VERSAO}} · instalado em {{DATA}} · plataforma: {{PLATAFORMAS}}

{{PARA_VOCE}}
{{PERFIL}}

## Como usar
Você não precisa decorar comandos. Abra o Claude Code ou o Codex na pasta do seu projeto e **descreva o que quer em português**. O agente escolhe a skill certa. Se quiser forçar uma skill, use a chamada direta indicada em cada uma.

Quatro hábitos que dão resultado melhor:
1. **Dê os dados de uma vez**: dimensões, materiais, cargas e normas que você usa.
2. **Peça a memória**: o agente mostra cálculo, unidades, hipóteses, alertas e itens normativos. Scripts testados não equivalem a aprovação de engenharia.
3. **Trabalhe numa pasta do projeto**: resultados, memorial e desenhos ficam organizados juntos.
4. **Comece cada projeto pelo município**: diga "vamos começar um projeto em <cidade>". O agente monta a ficha do projeto e pesquisa as regras locais (código de obras, zoneamento, Corpo de Bombeiros, concessionárias) em fontes oficiais.

## Seu primeiro projeto guiado
1. Abra uma pasta exclusiva da obra e peça: **"Inicie a ficha de um projeto de <uso> em <município>/<UF>; pergunte o que faltar."** Confirme uso, pavimentos, área, ambiente/CAA e revisão. O município do perfil é só sugestão; a obra pode ser em outro local.
2. Peça: **"Liste fontes oficiais vigentes e requisitos aplicáveis, com edição, artigo/item, link e data de acesso; registre as pendências."** Código de obras, zoneamento, Bombeiros, concessionárias e NRs dependem do local e do escopo.
3. Peça um cálculo pequeno ou uma auditoria de modelo. Forneça dimensões, unidades, origem dos valores e arquivo de entrada. Solicite o relatório de alertas e verificações não cobertas.
4. Peça para salvar o entregável na pasta da obra e registrá-lo na ficha. Antes de usar em aprovação ou obra, solicite revisão ao responsável técnico.
5. Em outra sessão, abra a mesma pasta e diga: **"Retome este projeto pelo projeto-contexto.json; resuma decisões, arquivos, fontes e pendências antes de continuar."**

## Teste das conexões que você escolheu
Depois de instalar, rode `python3 instalador/scripts/install.py verificar` na pasta do pack. Um servidor MCP iniciado **não** prova que o aplicativo responde. Abra o projeto no software e faça uma leitura sem alterar nada: AutoCAD `system → status` e `drawing → info` (ou DXF headless), Revit `get_current_view_info`, SOLIDWORKS `solidworks_list_documents`, ArchiCAD `get_project_info`. Só depois, com sua confirmação, faça um objeto de teste numa cópia, inspecione-o no programa e salve. Para TQS, use `tqs_ambiente.py`, leia um edifício de teste e confira os dados na interface; TQS não usa MCP neste pack. Se uma conexão não estiver instalada, ignore esse teste e registre a pendência se precisar dela depois.

## Estado da versão 1.3.0
Este ZIP é **candidato**, não certificação de conformidade. A referência declarada é NBR 6118:2026. Os scripts herdados da edição 2023 exigem comparação com o texto-base licenciado e a Emenda 1 antes de uso profissional como verificação normativa. As demais edições devem ser confirmadas no Catálogo ABNT; textos ABNT não acompanham o ZIP. As integrações exigem teste no programa real antes de serem anunciadas como validadas.

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
| Revit não responde | Abra o Revit e o projeto, ative o `Revit MCP Switch` e habilite os comandos nas configurações do add-in. Reexecute `verificar`. |
| SOLIDWORKS não responde | Abra o SOLIDWORKS e um documento; confirme versão/licença e repita a leitura de documentos. |
| TQS não lê o edifício | Rode `tqs_ambiente.py` no Windows com o Python compatível; compare a API instalada com o diagnóstico da skill. |
| MCP inicia, mas o software falha | O servidor e o aplicativo são testes distintos. Confira projeto aberto, add-in/serviço ativo e permissões; não use a integração até a leitura passar. |
| Busca de normas sem resultado | Peça "baixe os documentos do DNIT/SINAPI sobre <assunto>" ou "atualize o catálogo de normas". Normas ABNT não estão no índice. |
| Resultado estranho | Peça "mostre as hipóteses e a memória" e confira os dados de entrada. |
| Atualizar o pack | Baixe a versão nova na área de membros, abra a pasta e diga "atualize o pack". |
| Remover o pack | Abra a pasta do pack ({{PASTA}}) e diga "desinstale o pack". |

## Responsabilidade técnica
As skills são **ferramentas de apoio**. Projeto, laudo e orçamento continuam sob responsabilidade do profissional habilitado que os assina (ART/RRT). Confira hipóteses, dados de entrada, normas vigentes, resultados e necessidade de Avaliação Técnica do Projeto independente antes de usar em obra.
