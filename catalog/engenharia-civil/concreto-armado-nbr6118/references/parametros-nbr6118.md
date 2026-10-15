# Parâmetros usados pelos scripts (NBR 6118:2023)

> Valores implementados em `scripts/nbr6118.py`. Use esta página para explicar a origem de cada número ao usuário. Em caso de divergência com a norma em mãos, a norma prevalece: avise o autor do pack.

## Materiais
| Grandeza | Expressão | Item |
|---|---|---|
| fcd | fck / 1,4 | 12.3.3 |
| fyd | fyk / 1,15 (CA-50: 434,8 MPa) | 12.3 |
| αc | 0,85 (fck ≤ 50); 0,85·[1 − (fck − 50)/200] | 17.2.2 |
| λ (bloco) | 0,8 (fck ≤ 50); 0,8 − (fck − 50)/400 | 17.2.2 |
| εc2 / εcu | 2‰ / 3,5‰ (fck ≤ 50) | 8.2.10.1 |
| fct,m | 0,3·fck^(2/3) (≤ C50); 2,12·ln(1 + 0,11·fck) | 8.2.5 |
| fctk,inf | 0,7·fct,m | 8.2.5 |
| Eci | αE·5600·√fck (≤ C50) | 8.2.8 |
| Ecs | αi·Eci, αi = 0,8 + 0,2·fck/80 ≤ 1 | 8.2.8 |
| Es | 210 GPa | 8.3.5 |

## Ductilidade
x/d ≤ 0,45 (fck ≤ 50) e ≤ 0,35 (50 < fck ≤ 90) — item 14.6.4.3. Acima disso o script usa armadura dupla.

## Classe de agressividade e concreto mínimo
- CAA pelo ambiente (Tab. 6.1): rural/submersa I · urbano II · marinho/industrial III · industrial agressivo/respingos de maré IV. Os scripts leem a classe da ficha do projeto (`projeto-contexto.json`) quando `--caa` não é informado.
- Concreto armado mínimo (Tab. 7.1): CAA I ≥ C20 · II ≥ C25 · III ≥ C30 · IV ≥ C40 (a/c ≤ 0,65 · 0,60 · 0,55 · 0,45). Os scripts alertam quando o fck fica abaixo.

## Cobrimento nominal (Tabela 7.2, Δc = 10 mm), mm
| CAA | Laje | Viga/Pilar |
|---|---|---|
| I | 20 | 25 |
| II | 25 | 30 |
| III | 35 | 40 |
| IV | 45 | 50 |

## Armaduras mínimas e máximas
- Flexão (vigas): ρmín da Tabela 17.3 (0,150% até C30; 0,164% C35; 0,179% C40; 0,194% C45; 0,208% C50…). As + As' ≤ 4% Ac.
- Lajes (Tabela 19.1): negativa ≥ ρmín; positiva em cruz ≥ 0,67·ρmín; principal em uma direção ≥ ρmín; secundária ≥ máx(20% da principal; 0,9 cm²/m; 0,5·ρmín).
- Pilares (17.3.5.3): As,mín = máx(0,15·Nd/fyd; 0,4% Ac); As,máx = 8% Ac incluindo emendas (o script usa 4% fora da emenda).
- Estribos de viga: ρsw,mín = 0,2·fct,m/fywk; smáx = 0,6d ≤ 30 cm (VSd ≤ 0,67VRd2) ou 0,3d ≤ 20 cm.

## Força cortante — Modelo I (17.4.2.2)
VRd2 = 0,27·αv2·fcd·bw·d, αv2 = 1 − fck/250 · Vc = 0,6·fctd·bw·d (flexão simples) · Asw/s = (VSd − Vc)/(0,9·d·fywd), fywd ≤ 435 MPa.

## Lajes
- Momentos: teoria de placas de Kirchhoff resolvida por diferenças finitas com extrapolação de Richardson (`scripts/placa.py`), validada contra Timoshenko & Woinowsky-Krieger: placa apoiada quadrada (w = 0,00406·qa⁴/D, Mx = 0,0479·qa², ν = 0,3) e engastada (Mx = 0,0231·qa², Mborda = −0,0513·qa²). ν = 0,2 por padrão (concreto).
- Flecha: Branson (17.3.2.1.1), Mr = 1,5·fct,m·Ic/yt; flecha diferida αf = 1,32 (t0 = 1 mês, sem armadura de compressão); limite l/250 (Tabela 13.3), l = menor vão; balanço l = 2L.
- Reações nas vigas: charneiras a 45° entre bordas de mesmo tipo e 60° a partir do engaste (14.7.6.1).
- Compatibilização de negativos entre lajes vizinhas: maior valor entre a média e 80% do maior.

## Pilares
- γn (Tabela 13.1): 1,95 − 0,05·b para 14 ≤ b < 19 cm.
- M1d,mín = Nd·(0,015 + 0,03·h) [h em m] — 11.3.3.4.3.
- λ1 = (25 + 12,5·e1/h)/αb, 35 ≤ λ1 ≤ 90; αb = 0,6 + 0,4·MB/MA ≥ 0,4 — 15.8.2.
- Pilar-padrão com curvatura aproximada: 1/r = 0,005/[h(ν + 0,5)] ≤ 0,005/h; Md,tot = αb·M1d,A + Nd·le²/10·1/r ≥ M1d,A — 15.8.3.3.2. Válido para λ ≤ 90.
- Flexão oblíqua: (MRd,x/MRd,xx)^1,2 + (MRd,y/MRd,yy)^1,2 ≤ 1 — 17.2.5.2. Envoltória mínima de 2ª ordem: elipse com semieixos Md,tot,mín,x e Md,tot,mín,y — 11.3.3.4.3.
- Seção: integração por fibras com diagrama parábola-retângulo, domínios 2 a 5.
- Pré-dimensionamento: Ac = α·1,4·Nk/(0,85·fcd + 0,015·420), α = 1,3 (intermediário), 1,5 (extremidade), 1,8 (canto) — estimativa empírica de uso corrente no ensino.
