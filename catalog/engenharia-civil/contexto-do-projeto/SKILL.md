---
name: contexto-do-projeto
description: Abre todo projeto pela ficha de contexto — município, UF, uso, pavimentos, área e ambiente (classe de agressividade) — e pesquisa na internet as exigências locais em fontes oficiais (código de obras, plano diretor e zoneamento, aprovação/alvará, Corpo de Bombeiros e suas ITs, concessionárias de energia e água, CREA/ART) e a edição vigente das NBR usadas, registrando cada fonte com link e data para as outras skills usarem. Use quando o usuário começar um projeto novo, citar uma cidade, perguntar "quais normas valem em <cidade>", "código de obras", "zoneamento", "afastamentos", "taxa de ocupação", "Corpo de Bombeiros", "IT", "padrão de entrada", "aprovação na prefeitura", "alvará" ou "qual edição da NBR está em vigor".
---

# Contexto do projeto e normas locais

Todo projeto começa por aqui. O **município** é o parâmetro que define quais regras locais valem. As outras skills leem a ficha (`projeto-contexto.json`) na pasta do projeto.

Script: `scripts/contexto.py` (stdlib). Guia de busca: `references/onde-buscar.md`.

## 1. Ficha do projeto (perguntas iniciais)
Se não existir `projeto-contexto.json` na pasta de trabalho, pergunte numa única mensagem:
1. **Município e UF da obra.** Ofereça o padrão do perfil: `python3 scripts/contexto.py perfil`.
2. **Uso** da edificação (residencial unifamiliar/multifamiliar, comercial, serviços, industrial, institucional, saúde, educacional, misto, infraestrutura).
3. **Porte**: pavimentos e área construída aproximada.
4. **Ambiente** para durabilidade: rural, urbano, marinho (até ~1 km do mar), industrial, industrial agressivo ou respingos de maré.
5. Se já souber: endereço ou inscrição do lote (o zoneamento depende disso).

```bash
python3 scripts/contexto.py iniciar --pasta . --projeto "<nome>" --municipio "<município>" --uf <UF> \
    --uso <uso> --pavimentos <n> --area <m2> --ambiente <ambiente>
```
O script grava a ficha, sugere a classe de agressividade (NBR 6118, Tab. 6.1) e devolve o **checklist de pesquisa** (`c1`, `c2`…).

## 2. Pesquisa na internet
Para cada item do checklist, siga `references/onde-buscar.md`:
1. Busque com as consultas sugeridas, trocando município/UF. Você precisa de uma ferramenta de busca e leitura web: no Claude Code, WebSearch/WebFetch; no Codex, a busca web habilitada. **Sem busca web**, diga isso ao usuário e peça os links ou documentos. Não preencha de memória.
2. Abra a fonte **oficial**, confirme número, ano e vigência (alterações e revogações) e leia o trecho que importa ao projeto.
3. Registre:
   ```bash
   python3 scripts/contexto.py fonte --pasta . --checklist c1 --esfera municipal --tipo "Código de Obras" \
       --titulo "Lei nº ... de ... — Código de Obras de <município>" --url <link oficial> --vigente sim
   ```
   Item que não se aplica (ex.: Bombeiros isenta residência unifamiliar naquele estado): `contexto.py nao-aplica --checklist c5 --motivo "..."`, com a fonte da isenção. O que não deu para confirmar vira `contexto.py pendencia --texto "..."`.
4. **Documento público e longo** (código de obras, IT dos Bombeiros, norma da concessionária): se o MCP `normas-publicas` estiver conectado, importe com `importar_documento_publico` para consultar item a item depois (`buscar_normas`, `fonte='local'`).
5. **NBR**: só metadados (número, edição vigente, emendas). Não abra, não baixe e não cite texto integral de NBR encontrado na internet. O conteúdo vem das sínteses das skills de cálculo ou da cópia licenciada do usuário.

## 3. Entrega ao usuário
- Mostre `python3 scripts/contexto.py mostrar --pasta .`: parâmetros, fontes com links e o que falta.
- Resuma **as exigências que mudam o projeto** (afastamentos, gabarito, taxa de ocupação, permeabilidade, vagas, saídas de emergência, padrão de entrada…) em tabela `Exigência | Valor | Fonte (artigo/item) | Impacto no projeto`.
- Separe claramente: **confirmado em fonte oficial** × **a confirmar** × **boa prática**.

## Como as outras skills usam a ficha
- `concreto-armado-nbr6118`: classe de agressividade e cobrimento (`--caa`).
- `cargas-combinacoes`: município para localizar V0 no mapa de isopletas da NBR 6123 (o valor é lido no mapa, com o usuário).
- `quantitativos-sinapi`: UF da planilha SINAPI.
- `memorial-de-calculo` e `relatorio-tecnico`: endereço, município e lista de normas/legislação aplicáveis.
- `concreto-armado-nbr6118` e `autocad-assistente`: os **scripts** leem a CAA da ficha automaticamente (cobrimento e concreto mínimo) quando rodam na pasta do projeto.
- `archicad-bim-check`: confere no modelo os parâmetros numéricos do código de obras/zoneamento levantados aqui.
- `consulta-normas`: NRs (canteiro, NR-18) e documentos locais importados no índice; para obra, combine as exigências locais com o checklist de segurança.

## Limites e responsabilidade
- Legislação muda: registre a data de acesso e confira a vigência a cada fase do projeto. A pesquisa não substitui a consulta prévia à prefeitura e aos órgãos (certidão de uso do solo, consulta prévia aos Bombeiros, viabilidade técnica das concessionárias).
- O CREA não define requisitos de projeto. Ele regula ART e atribuições.
- Interpretação de lei e de norma no caso concreto é do responsável técnico. Em dúvida, recomende consulta formal ao órgão.
