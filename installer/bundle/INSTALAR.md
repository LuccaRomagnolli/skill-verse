# Instalar — {{PACK_NOME}} v{{VERSAO}}

## Jeito fácil
Abra esta pasta no **Claude Code** ou no **Codex** e diga: **"instale este pack"**.
O agente segue o roteiro de `instalador/SKILL.md`.

> Se o agente não reconhecer o pedido, cole esta mensagem:
>
> Leia o arquivo `instalador/SKILL.md` desta pasta e siga o roteiro para instalar o pack, conversando comigo em cada etapa.

## O que vem no pack
{{LISTA_SKILLS}}

### Conexões com softwares (opcionais)
{{LISTA_SOFTWARES}}

## Jeito manual (terminal)
```bash
cd instalador
python3 scripts/install.py detectar                                    # diagnóstico
python3 scripts/install.py instalar --plataforma claude --mcps autocad --simular
python3 scripts/install.py instalar --plataforma claude --mcps autocad  # claude | codex | ambas
python3 scripts/install.py verificar
python3 scripts/install.py manual
```
No Windows use `py -3` no lugar de `python3`.

`verificar` separa o servidor MCP da leitura do software aberto. Uma conexão ainda não testada no aplicativo não está validada. O pack Engenharia Civil 1.3.0 é candidato: consulte as pendências normativas e de testes reais no `MANUAL.md` gerado e no changelog.

## Atualizar / remover
- Versão nova: baixe o .zip novo, abra a pasta e diga **"atualize o pack"**.
- Remover: **"desinstale o pack"** (ou `python3 scripts/install.py desinstalar`).
