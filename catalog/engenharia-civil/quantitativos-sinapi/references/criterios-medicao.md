# Critérios de medição usados

| Serviço | Unidade | Critério no script | Observação |
|---|---|---|---|
| Concreto | m³ | volume geométrico (sem perdas: as composições SINAPI já consideram perdas) | descontar cruzamentos se o usuário pedir precisão (viga×pilar) |
| Fôrma de viga | m² | fundo + 2 laterais descontando a espessura da laje; viga de borda (`"borda": true`) tem a lateral externa inteira | |
| Fôrma de pilar | m² | perímetro × altura | |
| Fôrma de laje | m² | área do fundo (lx × ly) | bordas livres: some à parte |
| Fôrma de sapata | m² | perímetro × altura | |
| Aço | kg | n × comprimento × massa linear (NBR 7480) + perda (padrão 10%) | o comprimento já deve incluir ganchos e transpasses |
| Alvenaria | m² | área bruta − vãos; regra `total` (desconta todos os vãos) ou `excedente-2m2` (desconta só o que excede 2 m² por vão) | **confira no Caderno Técnico SINAPI da composição escolhida qual regra vale** |

Massas lineares (kg/m): φ5 0,154 · φ6,3 0,245 · φ8 0,395 · φ10 0,617 · φ12,5 0,963 · φ16 1,578 · φ20 2,466 · φ25 3,853 · φ32 6,313.

Indicadores para conferir ordem de grandeza (edificações residenciais usuais de concreto armado): taxa de aço ~ 70–110 kg/m³ e fôrma ~ 8–12 m²/m³ na estrutura completa. Valores muito fora disso indicam erro de lançamento: avise o usuário.

## SINAPI
- A planilha oficial é baixada pelo usuário no site da Caixa (SINAPI → relatórios mensais), escolhendo **UF, mês de referência e desonerado/não desonerado**. Registre esses três dados no orçamento.
- Use **composições** (serviços) para orçar; insumos só quando não houver composição adequada.
- O BDI varia por tipo de obra (o TCU publica faixas de referência para obras públicas). Peça o BDI ao usuário. Não arbitre.
