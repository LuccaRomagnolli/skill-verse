---
name: cargas-combinacoes
description: Inventaria ações por ambiente/elemento, calcula vento estático auxiliar e combina efeitos ELU/ELS com perfis normativos explícitos. Use quando pedirem cargas, mapa de ações, vento, pressão, ELU, ELS ou envoltória de uma edificação brasileira.
---

# Cargas e combinações

Scripts Python 3.10+ em `scripts/`. Comece sempre pelo `resumo` da skill `contexto-do-projeto`: município/UF, uso, fontes, decisões, artefatos e pendências. O uso **geral** da ficha não determina a carga de cada laje. Consulte a edição aplicável no Catálogo ABNT; os PDFs licenciados são apenas para consulta local, nunca para o ZIP. O PDF recebido da NBR 6123 é a edição 2023; a ABNT anunciou Errata 1:2025, ainda não conferida neste pack. Logo, resultados permanecem **em revisão técnica**.

## 1. Mapa de ações por ambiente e elemento

Leia `references/cargas-usuais.md` e use `assets/mapa-acoes.exemplo.json` apenas como formato. Para cada zona, identifique pavimento, elemento, **uso específico** (quarto, varanda, circulação, cobertura, garagem etc.), geometria e estado de ocupação. Confira no exemplar licenciado da NBR 6120:2019, versão corrigida, a linha aplicável da Tabela 10, inclusive carga distribuída e concentrada, além das cláusulas específicas quando pertinentes. Para elementos de vedação, instalações, reservatórios, equipamentos, paredes móveis, cargas de construção e garagens, levante as ações que efetivamente atuam; não converta automaticamente carga concentrada ou linear em carga por área.

Registre cada ação característica como `permanente` ou `variavel`, forma `distribuida` (kN/m²), `linear` (kN/m) ou `concentrada` (kN), valor, documento/edição, item, data de consulta e origem (norma, fabricante, medição, levantamento ou hipótese). Ação distribuída exige `area_m2` da zona; ação linear exige `extensao_m` e concentrada exige `posicao` no elemento. Em cada zona, preencha as seis `checagens` do exemplo: concentrada, paredes/divisórias, cobertura, garagem, equipamentos e construção, com estado e justificativa; `pendente` permanece visível no JSON. Para camadas permanentes, calcule espessura (m) × peso específico (kN/m³), com valores e dimensões verificados. Paredes exigem localização, composição/altura e caminho de cargas; a diluição pela área da laje só pode resultar de modelo e justificativa do projetista. Compare o mapa com arquitetura/BIM e marque mudanças de uso previstas.

```bash
python3 scripts/mapa_acoes.py --entrada /obra/mapa-acoes.entrada.json --saida /obra/mapa-acoes.json
```

O script **rejeita** uso genérico, ações sem fonte/item/data, unidade incompatível e zonas sem ações. Não atribui valores nem analisa esforços. Se faltar categoria, carga concentrada, especificação de parede/equipamento ou condição de construção, pare a definição daquela zona e registre `contexto.py pendencia`; não preencha com o uso geral da ficha. O exemplo de varanda demonstra a distinção de carga distribuída, mas não dispensa a checagem da carga concentrada. Após conferência, registre o mapa com `contexto.py artefato --tipo mapa-de-acoes --estado em-revisao` e as escolhas com `contexto.py decisao` (comandos em `contexto-do-projeto/references/continuidade.md`).

## 2. Vento

Leia `references/vento-nbr6123.md`. Confirme V0 na isopleta/estudo local para o município, S1 pela topografia, categoria por **direção** e entorno, classe pela dimensão frontal e S3 pelo risco/uso. `Ca` e `fv` exigem leitura dos critérios aerodinâmicos e de vizinhança no caso concreto. O script não os escolhe. Entrada mínima: V0 em m/s, S1, categoria, classe ou dimensão, S3 e cotas em m.

```bash
python3 scripts/vento.py --V0 35 --S1 1 --categoria IV --maior-dimensao 25 \
  --altura-total 15 --passo 3 --S3-grupo 3 --formato json
python3 scripts/vento.py --V0 35 --S1 1 --categoria IV --classe B \
  --alturas 3 6 9 12 15 --S3-grupo 3 --Ca 1.3 --fv 1 --largura 20 --formato json
```

Saídas: S2, Vk (m/s), q (kN/m²) e, se todos os parâmetros de arrasto forem fornecidos, Fa (kN) por faixa. A pressão na cota superior representa a faixa (aproximação explícita); não substitui integração/refinamento do modelo. Registre fontes de cada fator, direção, coeficientes e revisão independente. Sem a Errata 1:2025 conferida, não marque o cálculo como conforme à edição vigente.

## 3. Combinações de efeitos

Leia `references/combinacoes-normativas.md`. A entrada de `combinacoes.py` é o **efeito característico assinado** de cada ação na mesma seção e unidade (por exemplo, todos momentos em kN·m); não misture força, momento e carga linear. Transforme as cargas do mapa em efeitos por um modelo estrutural antes de combinar. Registre ações que podem ocorrer juntas, alternativas de um mesmo grupo e condições favoráveis/desfavoráveis. Escolha explicitamente `--perfil concreto-6118` para a estrutura de concreto ou `--perfil geral-8681` para o caso geral da NBR 8681:2025; o perfil geral usa permanentes diretas **agrupadas** e variáveis **separadas**. O projetista deve documentar a compatibilização entre 8681:2025 e a tabela específica da 6118:2023 + Emenda 1:2026.

```bash
python3 scripts/combinacoes.py --perfil concreto-6118 --acao G:permanente:120 \
  --acao Q:comercial:45 --acao W0:vento:30:vento --acao W90:vento:-25:vento --formato json
```

Tipos de fator ψ: `residencial` (acesso restrito), `comercial` (comércio/escritório/acesso público), `biblioteca` (inclui arquivos, oficinas, garagens), `vento`, `temperatura`; `cobertura` apenas no perfil geral. Esses nomes **não** selecionam q da NBR 6120. O script gera ELU **normal** e ELS rara/frequente/quase permanente; exclui ações variáveis favoráveis do ELU e não combina ações alternativas do mesmo grupo. Interprete a envoltória e identifique combinação governante, mas verifique manualmente ações correlatas inseparáveis, sequência construtiva, deslocamentos, estabilidade e resistência. `--gamma-g` antigo é recusado: combinações especiais/de construção e excepcionais não são simuláveis por esse único parâmetro.

Salve JSONs na pasta da obra, confira `status_normativo` e `limites`, registre como artefatos `em-revisao` e abra pendências para fontes ou verificações não concluídas. Um memorial só deve usar resultados acompanhados do mapa, modelo, unidade, perfil e revisão independente.

## Limites e responsabilidade

- NBR 6120:2019, NBR 8681:2025 e NBR 6118:2023/Em1:2026 foram consultadas em exemplares locais; a vigência e erratas devem ser verificadas no Catálogo ABNT em cada projeto. NBR 6123:2023/Errata 1:2025 está **pendente de confronto com o texto da errata**.
- Vento cobre Vk, q e arrasto estático simplificado com coeficientes fornecidos. Pressões em paredes/coberturas, pressão interna, efeitos dinâmicos, topografia/vizinhança complexas e classes/tempos especiais permanecem fora do script.
- Combinações cobrem efeitos lineares e carregamento normal. Não verificam estabilidade como corpo rígido, fadiga, incêndio, impacto, ações excepcionais, protensão ou fase de construção. Para efeitos não lineares, combinar ações antes da análise pode ser necessário.
- Nenhum JSON constitui aprovação, ART, ATP ou parecer independente. A definição das ações, compatibilização normativa e liberação do projeto cabem ao responsável técnico.
