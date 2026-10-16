---
name: cargas-combinacoes
description: Organiza cargas permanentes e de uso e calcula vento e combinações auxiliares com memória e origem dos parâmetros. Use quando pedirem carga, vento, pressão, ELU, ELS ou envoltória; os scripts de vento e combinações ainda exigem validação frente às edições normativas vigentes antes do uso em projeto real.
---

# Cargas e combinações

Scripts em `scripts/` (Python 3.10+, stdlib). Rode a partir da pasta desta skill. Os números saem dos scripts; você conduz e explica.

Comece por `contexto-do-projeto` → `resumo` para obter município/UF, uso, fontes e pendências. Registre na ficha a origem de cada carga e decisão. Os scripts `vento.py` e `combinacoes.py` implementam parâmetros declarados das edições 1988 da NBR 6123 e 2003/2023 da NBR 8681/6118. **Não os apresente como verificação normativa atual** antes do confronto com as edições vigentes. Para projeto real, obtenha os coeficientes de edição licenciada ou software verificado e registre a verificação independente.

## 1. Cargas permanentes e de uso
Se existir `projeto-contexto.json` (skill `contexto-do-projeto`), parta do **uso** da ficha para escolher a carga de uso e o tipo de ação nas combinações (`residencial` ou `comercial`) e confirme com o usuário. Use `references/cargas-usuais.md`. Monte uma **tabela de carga por m²** com as camadas (material, espessura, γ, carga) e some. Regras:
- Valor que não está na referência → **peça ao usuário** o valor da Tabela da NBR 6120:2019 que ele tem. Não chute.
- Alvenaria sobre laje sem viga embaixo: distribua o peso da parede pela área da laje (laje armada em cruz) ou trate como linha de carga, e diga qual hipótese usou.
- Entregue: g (permanente adicional, sem peso próprio da laje) e q (uso), prontos para a skill `concreto-armado-nbr6118`.
- Registre em `contexto.py decisao` as camadas, densidades e categorias adotadas; diferencie valor medido, dado de fabricante, norma e estimativa. Se faltar ocupação, espessura ou carga de equipamento, crie `pendencia`.

## 2. Vento
```bash
python3 scripts/vento.py --V0 35 --categoria IV --maior-dimensao 25 --altura-total 15 --passo 3 --S3-grupo 2
python3 scripts/vento.py --V0 35 --categoria IV --classe B --alturas 3 6 9 12 15 --Ca 1.3 --largura 20
```
Antes de rodar, confirme com o usuário: **V0 da cidade da obra** (mapa de isopletas; o município está em `projeto-contexto.json` se a ficha da skill `contexto-do-projeto` existir; a classe de rugosidade também pode ser discutida a partir do endereço do lote), categoria do terreno, maior dimensão da edificação e grupo de S3. Descrições de cada fator em `references/vento-nbr6123.md`. O Ca vem do ábaco da norma: ajude a ler, mas o valor é do usuário.

Para uma obra real, não transforme a saída histórica do script em ação de projeto até conferir na edição vigente mapa, fatores, coeficientes aerodinâmicos, vizinhança e aplicabilidade do método. Registre V0, S1/S2/S3, Ca e suas fontes; se algum não estiver confirmado, registre `pendencia`.

## 3. Combinações
Cada ação entra como `nome:tipo:valor[:grupo]`, com o **efeito característico** (esforço numa seção, reação, carga). Ações do mesmo grupo são exclusivas (ex.: vento em direções diferentes).
```bash
python3 scripts/combinacoes.py --acao G:permanente:120 --acao Q:comercial:45 \
    --acao W0:vento:30:vento --acao W90:vento:-25:vento
```
Tipos: `permanente`, `retracao`, `residencial`, `comercial`, `biblioteca`, `vento`, `temperatura`. Combinação especial/de construção: `--gamma-g 1.3 1.0`.

O script gera todas as combinações de ELU normal (cada variável como principal, permanentes com γ desfavorável ou favorável conforme o sentido) e as de ELS (rara, frequente, quase permanente), além da envoltória máx./mín. Destaque para o usuário a **combinação que governa** e para que serve cada ELS (quase permanente → flecha; frequente → fissuração/vibração; rara → formação de fissuras).

Salve as saídas JSON na pasta da obra, registre com `contexto.py artefato --estado em-revisao` e abra pendência para parâmetros normativos ainda não verificados. Unidades dos efeitos em todas as ações da mesma execução devem ser idênticas; não misture força, momento e carga linear na mesma envoltória.

## Limites e responsabilidade
- Os valores de referência não substituem a NBR 6120:2019, a NBR 6123 e a NBR 8681. Cite a tabela de onde cada valor saiu e marque como "a confirmar" o que veio do usuário ou de estimativa.
- Vento: só a parte estática simplificada (Vk, q, força global com Ca informado). Coeficientes de pressão em paredes e coberturas, efeitos dinâmicos, vizinhança e excentricidade ficam fora.
- Combinações excepcionais (sismo, incêndio, impacto) e ações de protensão: fora do escopo.
- O resultado é auxílio ao projeto. A definição das ações é responsabilidade do engenheiro (ART).
