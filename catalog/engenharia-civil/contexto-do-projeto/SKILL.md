---
name: contexto-do-projeto
description: Cria e retoma a ficha compartilhada de um projeto de engenharia no Brasil; pesquisa exigências municipais e estaduais em fontes oficiais e registra requisitos, decisões, artefatos e pendências. Use quando iniciarem ou retomarem uma obra, ou perguntarem por código de obras, zoneamento, Bombeiros, concessionárias, edição de NBR ou regras aplicáveis à cidade e ao lote.
---

# Contexto do projeto e normas locais

Todo projeto começa por aqui. O **município** é o parâmetro que define quais regras locais valem. As outras skills leem a ficha (`projeto-contexto.json`) na pasta do projeto.

Script: `scripts/contexto.py` (stdlib). Guia de busca: `references/onde-buscar.md`. Exercício com fontes municipais oficiais e pendências honestas: `references/exemplo-municipal-sp.md`.

**Retomada:** se a ficha existir, comece por `python3 scripts/contexto.py resumo --pasta <pasta-da-obra>`. Confira a cidade/UF da obra, a versão dos arquivos e as pendências com o usuário. Não execute `iniciar --forcar` para continuar um projeto. Comandos e campos de continuidade: `references/continuidade.md`.

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
2. Abra a fonte **oficial**, confirme número, ano, vigência (alterações e revogações), âmbito e o trecho que importa ao projeto. Zoneamento e gabarito dependem da identificação do lote; sem endereço ou inscrição imobiliária, registre-os como pendência, mesmo que a lei municipal esteja localizada.
3. Registre:
   ```bash
   python3 scripts/contexto.py fonte --pasta . --checklist c1 --esfera municipal --tipo "Código de Obras" \
       --titulo "Lei nº ... de ... — Código de Obras de <município>" --url <link oficial> --vigente sim
   ```
   O comando devolve um ID (`f1`, `f2`…). Para cada valor que afeta o projeto, registre artigo/item, critério, valor, unidade e impacto com `contexto.py requisito --fonte f1 ...` (exemplo em `references/continuidade.md`). Uma fonte sem URL oficial e vigência confirmada não fundamenta um requisito. Item que não se aplica: `contexto.py nao-aplica --checklist c5 --motivo "..." --fonte f2`, citando a fonte da dispensa. O que não deu para confirmar vira `contexto.py pendencia --texto "..."`.
4. **Documento público e longo** (código de obras, IT dos Bombeiros, norma da concessionária): se o MCP `normas-publicas` estiver conectado, importe com `importar_documento_publico` para consultar item a item depois (`buscar_normas`, `fonte='local'`).
5. **NBR**: confirme número, edição e emendas no Catálogo ABNT e registre o link e a data. A referência atual do concreto é a NBR 6118:2026 (edição 2023 + Emenda 1:2026); os scripts do pack ainda têm validação integral pendente. Registre a data do protocolo de licenciamento e a decisão sobre a regra transitória do prefácio da emenda (180 dias). Não use PDFs de cópias na internet nem embuta o exemplar licenciado do usuário no pack. Antes de aplicar qualquer cálculo, confira o status normativo declarado pela skill e pelo resultado.
6. **ATP**: solicite ao projetista a classe de consequência, fundamento e situação da avaliação técnica. Use `contexto.py atp --classe CC3 --situacao pendente --fundamento "..."` e atualize quando houver parecer ou dispensa formal. A ATP é a regra geral; a dispensa só é prevista para CC1/CC2 mediante acordo formal entre projetista e contratante. Se a classe for duvidosa, trate como CC3 até definição profissional. Não declare independência do avaliador sem evidência.

## 3. Entrega ao usuário
- Mostre `python3 scripts/contexto.py mostrar --pasta .`: parâmetros, fontes com links e o que falta.
- Resuma **as exigências que mudam o projeto** (afastamentos, gabarito, taxa de ocupação, permeabilidade, vagas, saídas de emergência, padrão de entrada…) em tabela `Exigência | Valor | Fonte (artigo/item) | Impacto no projeto`.
- Separe claramente: **confirmado em fonte oficial** × **a confirmar** × **boa prática**.
- Registre hipóteses e escolhas com `contexto.py decisao`, arquivos finais com `contexto.py artefato` e dúvidas com `contexto.py pendencia`. Ao encerrar, mostre o `resumo` e o próximo passo. O registro não transforma hipótese em conformidade.

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
- A classificação de agressividade sugerida pela ficha depende do microambiente e deve ser confirmada pelo projetista. A ficha nunca estabelece automaticamente que uma edificação atende à legislação local.
- O CREA não define requisitos de projeto. Ele regula ART e atribuições.
- Interpretação de lei e de norma no caso concreto é do responsável técnico. Em dúvida, recomende consulta formal ao órgão.
