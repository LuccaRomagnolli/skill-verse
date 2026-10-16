# Modelagem estrutural no Revit (fluxo de escritório brasileiro)

## Ordem de trabalho
1. **Projeto e template**: confirme o template (estrutural, com famílias de concreto) e as unidades do projeto (`Gerenciar → Unidades`; usual: m para comprimentos, cm para seções).
2. **Vínculos**: arquitetura em RVT ou DWG vinculada **origem com origem**. Coordenadas compartilhadas se houver implantação georreferenciada.
3. **Níveis**: os mesmos nomes e cotas do TQS/arquitetura (`Fundação`, `Térreo`, `Pav 1`…, `Cobertura`, `Barrilete`, `Fundo caixa`). Cota = nível de **topo da laje estrutural** (não o piso acabado), salvo se o escritório usar outro critério. Pergunte uma vez.
4. **Eixos**: numéricos numa direção, letras na outra, conforme a arquitetura.
5. **Pilares** (`OST_StructuralColumns`) do nível de base ao de topo, um tipo por seção (`P 20x50`). Pilares que mudam de seção: elementos separados por trecho.
6. **Vigas** (`OST_StructuralFraming`) no nível do pavimento, com o topo alinhado ao topo da laje (padrão da família). Rebaixos: `Deslocamento do nível inicial/final`.
7. **Lajes** (`OST_Floors`, estrutural) com contorno até a face das vigas ou até o eixo. Combine com o calculista para o quantitativo não contar duas vezes.
8. **Fundações** (`OST_StructuralFoundation`): blocos, sapatas e estacas como famílias. O MCP não tem ferramenta específica: use `create_point_based_element` com o tipo da família ou C#.
9. **Unir geometrias** (pilar × viga × laje) antes de extrair volumes.
10. **Revisão visual**: `color_elements` por `Tipo` ou por material; `analyze_model_statistics`; vista 3D.

## Do cálculo do pack para o modelo
- Resultados de `concreto-armado-nbr6118` (seções de pilares, vigas, espessura de lajes) + posições → JSON no formato de `assets/lancamento.exemplo.json` → `scripts/lancamento.py` → executar as ops na ordem.
- Arquitetura em DWG: limpe antes com a skill `autocad-assistente` (base por pavimento, 0,0 no cruzamento de eixos) e use as mesmas coordenadas no JSON.

## Convenções
- **Marca**: P1, V1, L1 iguais ao cálculo e ao TQS (`marcas_csharp` do `lancamento.py`).
- **Material**: um material por classe de concreto (`Concreto C30`), com o fck na descrição. A classe vem da ficha do projeto; a triagem automática de CAA usa a tabela 7.1 da NBR 6118:2023 e precisa ser confrontada com a referência declarada NBR 6118:2026 antes de aprovação.
- **Modelo analítico**: o Revit gera, mas o cálculo oficial é do software estrutural (TQS etc.). Não use resultados analíticos do Revit como dimensionamento.
- **Armaduras** (Rebar) no Revit: possível via C#, mas trabalhoso. O detalhamento oficial costuma sair do TQS. Ofereça apenas se o usuário pedir.

## Quantitativos
- `get_material_quantities` (área/volume por material) para uma visão rápida.
- Por peça/nível: receita "Volume de concreto por nível" em `revit-api-csharp.md`, com conversão por script e orçamento com `quantitativos-sinapi` (critério de medição do SINAPI, consulta via `consulta-normas`).
- Fôrma (m²) e aço (kg) não saem prontos do modelo. Fôrma pode ser estimada pela área de faces via C#. Aço vem do detalhamento.
