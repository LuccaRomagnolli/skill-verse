# Padrão de layers — projeto estrutural

Baseado nas práticas usuais de escritórios e na ABNT NBR 6492/NBR 16752 (apresentação de projetos). Ajuste ao padrão do escritório do usuário se ele tiver um: pergunte antes de criar.

| Layer | Cor (ACI) | Uso | Espessura sugerida |
|---|---|---|---|
| EST-EIXO | 1 (vermelho), linetype CENTER | eixos e referências | 0,13 |
| EST-FORMA | 7 (branco/preto) | contorno de concreto em planta de fôrma e seções | 0,35 |
| EST-FORMA-OCULTA | 8, linetype HIDDEN | vigas/pilares abaixo do plano de corte | 0,18 |
| EST-ESTRIBO | 3 (verde) | estribos em seções e elevações | 0,25 |
| EST-BARRA | 1 (vermelho) | barras longitudinais (círculos cheios) | 0,40 |
| EST-COTA | 2 (amarelo) | cotas | 0,18 |
| EST-TEXTO | 4 (ciano) | textos, nomes de peças, especificações | 0,25 |
| EST-HACH | 9 | hachuras de corte | 0,09 |
| EST-CARIMBO | 7 | carimbo e moldura | 0,50 |

Convenções:
- Unidade do desenho em **centímetros** para detalhes e **metros ou centímetros** para plantas: confirme com o usuário e mantenha uma só por arquivo.
- Nomes de peças: L1, V1, P1 (laje, viga, pilar), com dimensões em cm (`V1 15×45`).
- Especificação de armadura: `3 ⌀12,5 C=530` (quantidade, bitola, comprimento em cm). No AutoCAD, ⌀ = `%%c`.
