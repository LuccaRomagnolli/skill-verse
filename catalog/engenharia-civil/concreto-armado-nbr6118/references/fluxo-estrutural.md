# Fluxo de cálculo de um pavimento (ordem recomendada)

1. **Lançamento**: identifique lajes (L1, L2…), vigas (V1…) e pilares (P1…), vãos teóricos (eixo a eixo dos apoios, item 14.6.2.4) e condições de borda de cada laje (engaste onde há laje vizinha contínua de rigidez semelhante; apoio em bordas externas).
2. **Cargas** (skill `cargas-combinacoes`): peso próprio, revestimentos, alvenarias sobre lajes, carga de uso pela NBR 6120.
3. **Lajes** — `scripts/laje.py` em cada laje → compatibilize os negativos entre lajes vizinhas → anote as **reações nas vigas** (saída "Reações nas vigas").
4. **Vigas** — carregamento = reações das lajes + alvenaria + peso próprio. Para viga biapoiada simples use `scripts/viga.py --biapoiada`; para vigas contínuas, obtenha os esforços (pórtico/viga contínua, ex.: Ftool) e passe `--Md/--Vd` de cada seção crítica.
5. **Pilares** — some as reações das vigas por pavimento (Nk acumulado) → `scripts/pilar.py`, com momentos de ligação viga-pilar quando houver (item 14.6.7.1) nos pilares de extremidade e canto.
6. **Memorial** — rode cada script com `--formato json > resultados/<elemento>.json` e use a skill `memorial-de-calculo`.

Pórtico espacial, vento e estabilidade global (γz, α) ficam fora destes scripts: recomende software de análise estrutural para edifícios com mais de 4 pavimentos ou com vento relevante.
