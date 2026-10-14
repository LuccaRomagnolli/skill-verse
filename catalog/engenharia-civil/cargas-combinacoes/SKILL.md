---
name: cargas-combinacoes
description: Levanta cargas de projeto (peso próprio, revestimentos, alvenarias, cargas de uso da NBR 6120), calcula a ação do vento pela NBR 6123 (S1, S2, S3, pressão dinâmica e forças por pavimento) e gera as combinações de ações de ELU e ELS da NBR 8681/NBR 6118 com envoltória. Use quando o usuário perguntar "qual carga usar", "carga de uso", "sobrecarga", "carga acidental", "peso da alvenaria", "vento", "pressão de vento", "combinação de ações", "coeficiente de ponderação", "ψ0/ψ1/ψ2", "ELU" ou "ELS".
---

# Cargas e combinações

Scripts em `scripts/` (Python 3.10+, stdlib). Rode a partir da pasta desta skill. Os números saem dos scripts; você conduz e explica.

## 1. Cargas permanentes e de uso
Use `references/cargas-usuais.md`. Monte uma **tabela de carga por m²** com as camadas (material, espessura, γ, carga) e some. Regras:
- Valor que não está na referência → **peça ao usuário** o valor da Tabela da NBR 6120:2019 que ele tem. Não chute.
- Alvenaria sobre laje sem viga embaixo: distribua o peso da parede pela área da laje (laje armada em cruz) ou trate como linha de carga, e diga qual hipótese usou.
- Entregue: g (permanente adicional, sem peso próprio da laje) e q (uso), prontos para a skill `concreto-armado-nbr6118`.

## 2. Vento
```bash
python3 scripts/vento.py --V0 35 --categoria IV --maior-dimensao 25 --altura-total 15 --passo 3 --S3-grupo 2
python3 scripts/vento.py --V0 35 --categoria IV --classe B --alturas 3 6 9 12 15 --Ca 1.3 --largura 20
```
Antes de rodar, confirme com o usuário: **V0 da cidade** (mapa de isopletas), categoria do terreno, maior dimensão da edificação e grupo de S3. Descrições de cada fator em `references/vento-nbr6123.md`. O Ca vem do ábaco da norma: ajude a ler, mas o valor é do usuário.

## 3. Combinações
Cada ação entra como `nome:tipo:valor[:grupo]`, com o **efeito característico** (esforço numa seção, reação, carga). Ações do mesmo grupo são exclusivas (ex.: vento em direções diferentes).
```bash
python3 scripts/combinacoes.py --acao G:permanente:120 --acao Q:comercial:45 \
    --acao W0:vento:30:vento --acao W90:vento:-25:vento
```
Tipos: `permanente`, `retracao`, `residencial`, `comercial`, `biblioteca`, `vento`, `temperatura`. Combinação especial/de construção: `--gamma-g 1.3 1.0`.

O script gera todas as combinações de ELU normal (cada variável como principal, permanentes com γ desfavorável ou favorável conforme o sentido) e as de ELS (rara, frequente, quase permanente), além da envoltória máx./mín. Destaque para o usuário a **combinação que governa** e para que serve cada ELS (quase permanente → flecha; frequente → fissuração/vibração; rara → formação de fissuras).

## Limites e responsabilidade
- Os valores de referência não substituem a NBR 6120:2019, a NBR 6123 e a NBR 8681. Cite a tabela de onde cada valor saiu e marque como "a confirmar" o que veio do usuário ou de estimativa.
- Vento: só a parte estática simplificada (Vk, q, força global com Ca informado). Coeficientes de pressão em paredes e coberturas, efeitos dinâmicos, vizinhança e excentricidade ficam fora.
- Combinações excepcionais (sismo, incêndio, impacto) e ações de protensão: fora do escopo.
- O resultado é auxílio ao projeto. A definição das ações é responsabilidade do engenheiro (ART).
