# Conexão Archicad

## Backend do pack

O MCP `archicad` do pack fixa `archicad-mcp-server==0.8.0` em modo `full`. Ele fornece as regras YAML do escritório e o gateway para comandos Tapir. Em mais de uma instância aberta, execute `list_instances`, escolha conscientemente o projeto e passe a porta retornada (19723–19743) em todas as leituras e gravações.

O Public MCP incluído no Archicad 30 é uma conexão separada. Ele depende de uma assinatura Archicad Collaborate ou Max. Use o comando e o argumento copiados de **Options > Desktop AI Tool Connection**; os caminhos variam por instalação e não são gravados automaticamente pelo pack. Sua presença não substitui o Tapir no fluxo de lançamento estrutural deste pack.

## Tapir

Sem Tapir, o bridge ainda lista instâncias, conta elementos de modelo, lê parte dos atributos e carrega regras. Ficam indisponíveis ou incompletos: `GetStories`, criação de pilares/vigas/lajes, issues, BCF, propriedades IFC, publicação e a cobertura de elementos 2D. Instale uma versão compatível com o Archicad aberto pelo gerenciador de add-ons e reinicie o aplicativo. No ensaio de 2026-10-18, o bundle universal e notarizado do Tapir 1.7.1 funcionou no Archicad 30 INT build 3001 para macOS; outras combinações de versão precisam de teste próprio.

Confirme em `list_instances`:

```json
{"tapir_available": true, "tapir_version": "...", "project_open": true}
```

## Diagnóstico mínimo

1. `list_instances`: selecione porta, versão e projeto; pare se a instância não corresponder ao PLN pretendido.
2. `get_project_info` e `GetStories`: confira nome, pavimentos e cotas.
3. `get_model_summary`: uma contagem zero não valida auditoria.
4. `list_rules`: confirme o diretório e erros de carga.
5. `audit_delivery_readiness` e `verify_ifc_export_readiness`: examine cada resultado. Qualquer `skipped=true` é pendência, mesmo se o agregado trouxer `score=100` e `pass=true`.
6. Grave as respostas em um JSON, mantendo as chaves retornadas pelo MCP ou as chaves curtas `instancias`, `resumo`, `auditoria` e `ifc`. Rode `python3 scripts/validar_auditoria.py evidencia-archicad.json` antes de declarar prontidão.

Faça gravações somente em cópia salva, primeiro com `dry_run=true` ou `confirm=false`. Depois da confirmação do lote, use a mesma porta e confira os GUIDs, a geometria no Archicad e o arquivo salvo. Para lajes, o `CreateSlabs` herda a estrutura do favorito: use favorito Basic e confirme depois da criação `structureType`, `thickness` e `buildingMaterialId` com `GetDetailsOfElements`.
