---
name: modelo-estrutural
description: Cria e valida o modelo estrutural versionado que alimenta SkyCiv, plantas CAD e um destino BIM. Use quando o usuário quiser preparar análise estrutural, manter geometria e cargas em uma fonte única ou passar uma revisão do cálculo para AutoCAD, Revit ou Archicad.
---

# Modelo estrutural do projeto

Use `assets/modelo.exemplo.json` como formato v1. O exemplo é didático: seus números e combinações não são valores de projeto. Leia a ficha `projeto-contexto.json` antes de começar e registre a revisão escolhida. Posições/seções em m; cargas em kN, kN/m ou kPa conforme o tipo; eixo vertical Z. O script `scripts/modelo.py` valida unidades, materiais, geometria, apoios, ações, combinações e fontes.

## Preparar

1. Obtenha geometria, materiais, vínculos e liberações do projetista. A planta arquitetônica não define automaticamente o modelo analítico. Dê IDs estáveis às peças e explicite o apoio em cada nó relevante.
2. Use `cargas-combinacoes` para o mapa por zona/elemento e para produzir as combinações com o perfil normativo escolhido. Salve o mapa ao lado do modelo e informe seu nome em `mapa_acoes`. Transcreva cada ação para `acoes` com alvo, direção global, sinal, grupo, origem e `mapa_ref` no formato `zona/acao`; cargas de área ficam em lajes, lineares em barras e concentradas em barras com posição percentual. Não dilua carga linear/concentrada na área. Compare o valor, unidade e item da fonte com o mapa; se não houver alvo ou posição determinados, registre pendência e não envie à API.
3. Transcreva fatores explícitos em `combinacoes[].fatores`; cada chave deve coincidir com um grupo de carga. Inclua `SW1` quando `peso_proprio` for verdadeiro. Registre documento, item e data. As combinações prontas internacionais da SkyCiv não substituem a conferência das NBR.
4. Valide: `python3 scripts/modelo.py validar modelo-estrutural.json --mapa mapa-acoes.json`; o comando confere referência, forma, unidade, módulo e origem de cada ação. O MCP também confere o mapa antes do envio e registra seu hash. Exporte para inspeção: `python3 scripts/modelo.py skyciv modelo-estrutural.json --saida skyciv-previa.json`. Confira nós coincidentes, eixo vertical, apoios, liberações, espessuras, pressão e cada fator antes de autorizar o envio à nuvem.

## Entregas

O comando `revit` produz o formato já aceito por `revit-assistente/scripts/lancamento.py`; ele não altera o exemplo ou os projetos Revit anteriores. CAD e Archicad usam o mesmo arquivo estrutural. Guarde o modelo, o hash da entrada exportada, os resultados, plantas e modelos BIM na pasta da obra e registre caminhos/revisões com `contexto.py artefato`; decisões e lacunas vão para `decisao` e `pendencia`. Uma alteração de geometria, material, vínculo, ação ou combinação exige nova revisão e nova análise.

## Limites e responsabilidade

O conversor cobre barras retangulares, placas de três/quatro vértices e cargas constantes básicas. Não infere ligações, apoios, ações de vento, diafragma, torção, punção, segunda ordem nem dimensionamento. Interseções internas e conectividade da malha devem ser conferidas visualmente na SkyCiv por responsável técnico. Não use o exemplo didático em obra.
