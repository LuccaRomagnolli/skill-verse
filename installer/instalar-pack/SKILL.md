---
name: instalar-pack
description: Instala, verifica, atualiza ou remove um pack Skill-Verse (skills + conexões com softwares via MCP) no Claude Code ou no Codex e gera o manual personalizado do usuário. Use quando o usuário abrir a pasta de um pack e disser "instale este pack", "instalar", "configurar o pack", "atualize o pack", "desinstalar o pack" ou "gerar o manual".
---

# Instalar pack Skill-Verse

Você está conduzindo a instalação para alguém que **não é necessariamente técnico**. Fale em português simples, um passo por vez, e peça confirmação antes de qualquer ação que altere a máquina.

O script `scripts/install.py` (só biblioteca padrão do Python) faz todo o trabalho. Rode-o com o Python do sistema (`python3`; no Windows, `py -3` ou `python`). Todos os caminhos abaixo são relativos à pasta desta skill (`instalador/` dentro do pack).

## 1. Diagnóstico
```bash
python3 scripts/install.py detectar
```
Leia o JSON e conte ao usuário, em 3–5 linhas: qual pack e versão, em qual plataforma você está rodando (você sabe se é Claude Code ou Codex), quais softwares foram encontrados e se já existe uma instalação anterior (`instalacao_atual`).

Se o Python não existir ou for < 3.10, oriente a instalação (python.org) e pare.

## 2. Perguntas (uma mensagem só)
1. **Onde instalar**: só aqui (a plataforma atual) ou também na outra (`claude`, `codex`, `ambas`). Padrão: a atual.
2. **Quais softwares conectar**: liste cada item de `softwares` com o status detectado. Recomende conectar os detectados e os marcados com `recomendado: true` (ex.: índice de normas públicas, que não depende de software, só de internet; use a `descricao` para explicar). Para os não detectados, ofereça só se `util_sem_software` for true (explique o que funciona sem o software). Não ofereça os que `suporta_este_so` é false.
3. Pergunte **como ele trabalha** (ex.: tipo de projeto, escritório/autônomo, normas que mais usa) — uma linha basta. Isso vai personalizar o manual.
4. Pergunte **em qual município/UF ele mais atua**. Vira o padrão das fichas de projeto: o agente usa o município para pesquisar código de obras, Corpo de Bombeiros e concessionárias, e sempre confirma o da obra em cada projeto novo. Grave:
   ```bash
   python3 scripts/install.py perfil --municipio "<município>" --uf <UF> --atuacao "<resposta da pergunta 3>"
   ```

## 3. Pré-requisito dos softwares (só se escolheu algum)
Se `uv` for null, explique que é um gerenciador de Python necessário para as conexões e peça permissão. Com o "sim":
```bash
python3 scripts/install.py instalar-uv
```
Depois disso o PATH pode exigir reiniciar o terminal/agente; se `uv` ainda não aparecer, peça para reiniciar e retomar daqui.

## 4. Simular e instalar
Mostre o plano antes:
```bash
python3 scripts/install.py instalar --plataforma <claude|codex|ambas> --mcps <lista,ou vazio> --simular
```
Resuma o que vai acontecer e peça confirmação. Então rode sem `--simular`.

- No Claude Code com a CLI `claude` disponível, as skills entram como **plugin** (namespace `/<pack>:<skill>`). Se o usuário preferir nomes curtos, use `--sem-plugin`.
- Se aparecer aviso de skill com mesmo nome de outra que ele já tem, pergunte antes de usar `--forcar`.
- Erros de download/`uv sync`: mostre a mensagem curta, verifique internet e tente de novo uma vez.

## 5. Verificar
```bash
python3 scripts/install.py verificar
```
A primeira verificação dos MCPs pode levar alguns minutos (baixa dependências). Se um MCP falhar porque o software não está aberto, isso é normal: diga que funciona quando ele abrir o programa.

## 6. Manual personalizado
Escreva um arquivo temporário `para-voce.md` começando com `## Para você`, com 3–5 sugestões de uso ligadas ao que o usuário contou nos passos 2.3 e 2.4. Use os exemplos das skills, adaptados ao trabalho dele, e cite as skills pelo nome. Depois:
```bash
python3 scripts/install.py manual --extra para-voce.md
```
O script gera `MANUAL.md` e `MANUAL.html` (abre em qualquer navegador e imprime em PDF). Mostre os caminhos e apague o arquivo temporário.

## 7. Encerramento
- Liste os **passos manuais** que o script imprimiu (ex.: carregar o arquivo LISP no AutoCAD, instalar o add-on Tapir) como checklist.
- Diga para **reiniciar o Claude Code/Codex** para as skills aparecerem.
- Sugira um primeiro pedido de teste tirado do manual.

## Atualizar e remover
- Nova versão: o usuário baixa o .zip novo, abre a pasta e pede "atualize o pack" → `python3 scripts/install.py atualizar` (reaproveita as escolhas anteriores) → `verificar` → `manual`.
- Remover: `python3 scripts/install.py desinstalar --simular`, confirme, e rode sem `--simular`.

## Regras
- Nunca edite `~/.claude.json`, `settings.json` ou `~/.codex/config.toml` à mão: use o script (ele marca o que é do pack e respeita o que é do usuário).
- Nunca rode `--forcar`, `instalar-uv` ou `desinstalar` sem o "sim" explícito do usuário.
- Se algo fugir deste roteiro, explique o que aconteceu e pare, em vez de improvisar comandos.
