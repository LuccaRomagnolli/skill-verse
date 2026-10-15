# Solução de problemas da conexão com o Revit

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| "connect to revit client failed" / tempo esgotado (5 s) | serviço MCP desligado no Revit | Revit aberto **com um projeto**, faixa Suplementos → "Revit MCP Plugin" → **Revit MCP Switch** |
| A faixa "Revit MCP Plugin" não aparece | add-in não carregado | conferir `%APPDATA%\Autodesk\Revit\Addins\<ano>\mcp-servers-for-revit.addin`; reabrir o Revit e escolher "Sempre carregar"; rodar `install.py atualizar` se a pasta estiver vazia |
| Aviso de complemento duplicado | existe outro `.addin` com o mesmo ClientId (ex.: `revit-mcp.addin` de instalação manual antiga) | remover o duplicado (com confirmação do usuário) |
| Comando responde "command not found/enabled" | comando não habilitado em **Settings** do plugin | Settings → marcar todos → salvar |
| Porta 8080 ocupada | outro programa (servidor web local) | fechar o programa. A porta é fixa nesta versão |
| Elemento criado com tipo errado | `typeId` inexistente; o add-in usou o padrão e avisou | ler o aviso, obter o id certo (`get_available_family_types`) ou criar o tipo (`tipos_csharp`), apagar e recriar com confirmação |
| Pilar com topo errado | `height` não corresponde à diferença entre níveis | o topo é o nível mais próximo de `baseLevel + height`. Recalcule com o `lancamento.py` |
| `send_code_to_revit` com erro de compilação | `doc` em vez de `document`, falta `return`, `Transaction` aninhada, namespace fora do template | ver `revit-api-csharp.md` |
| Revit travado durante a chamada | operação pesada (milhares de elementos) | lotes menores. `ai_element_filter` limita a 50 por chamada |
| `npx` não encontrado | Node.js ausente | instalar o Node.js LTS e reabrir o terminal/agente |
| Revit 2027+ | sem add-in publicado na versão fixada | informar o usuário; aguardar nova versão do pack |
