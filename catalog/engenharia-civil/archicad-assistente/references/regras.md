# Regras de auditoria (formato do MCP do ArchiCAD)

Arquivos `.yaml` em `~/.engcode/archicad-regras/` (o instalador da skill copia `assets/regras/entrega-br.yaml` para lá). Cada arquivo é uma **lista** de regras. O servidor lê a pasta ao iniciar: depois de editar, reinicie o Claude Code/Codex.

Campos comuns: `id` (único), `type`, `severity` (`error` reprova a entrega; `warning` só pontua), `tags` (usadas como `ruleset` na auditoria), `applies_to` (`element_type`: Wall, Slab, Column, Beam, Door, Window, Zone… e opcional `where`: lista de comparações `{property, operator, value}`).

| type | Campos próprios | Verifica |
|---|---|---|
| `zone-number-required` | — | toda zona (ambiente) tem número |
| `classification-required` | `system` (nome exato do sistema de classificação) | elemento tem item de classificação nesse sistema |
| `property-required` | `property` (`Grupo/Nome` de propriedade do usuário ou nome de API) | propriedade preenchida |
| `ifc-property-required` | `property` (`Pset_X.Nome`) | propriedade IFC preenchida (requer Tapir) |
| `layer-compliance` | `allowed` (lista) e/ou `pattern` (regex) | layer do elemento segue o padrão |

Exemplo de regra própria:
```yaml
- id: paredes-com-material-de-acabamento
  type: property-required
  property: "Acabamentos/Revestimento interno"
  applies_to: { element_type: Wall }
  severity: warning
  tags: [entrega]
```

Dicas:
- Nome do sistema de classificação ou de propriedade incerto → use a ferramenta `search_definitions` para achar o endereço exato.
- Erros de carga das regras aparecem em `list_rules` → corrija o YAML e reinicie.
