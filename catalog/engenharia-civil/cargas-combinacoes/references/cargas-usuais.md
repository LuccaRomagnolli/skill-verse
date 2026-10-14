# Cargas usuais — valores de referência

> **Confirme na norma** antes de usar em projeto: os valores abaixo são os mais usados no dia a dia e servem para estudo e pré-dimensionamento. A NBR 6120:2019 tem tabelas extensas (por material, espessura e uso). Quando o caso não estiver aqui, **peça ao usuário o valor da tabela da norma**, em vez de supor.

## Pesos específicos (kN/m³)
| Material | γ |
|---|---|
| Concreto armado | 25 |
| Concreto simples | 24 |
| Aço | 78,5 |
| Argamassa de cimento e areia | 21 |
| Argamassa de cal, cimento e areia | 19 |

## Revestimentos e vedações — composição típica (kN/m²)
Monte a carga permanente adicional da laje somando camadas: **espessura (m) × γ (kN/m³)**.
- Contrapiso de argamassa 3 cm: 0,03 × 21 = 0,63
- Reboco de teto 1,5 cm: 0,015 × 19 = 0,29
- Piso cerâmico/porcelanato colado: confira na NBR 6120 (ordem de 0,2–0,3 incluindo argamassa colante)
- Forro de gesso: confira na NBR 6120 (ordem de 0,1–0,25)
- Alvenaria sobre laje: peso por m² de parede × altura ÷ área da laje (ou linha de carga na viga). A NBR 6120:2019 tabela alvenarias **por m² de parede** conforme bloco e espessura — use a tabela.

## Cargas variáveis de uso (NBR 6120:2019) — kN/m²
| Uso | q |
|---|---|
| Residencial: dormitórios, sala, cozinha, banheiro | 1,5 |
| Residencial: despensa, área de serviço, lavanderia | 2,0 |
| Corredores e escadas de uso comum | 3,0 |
| Escritórios: salas de uso geral | 2,5 |
| Garagens de veículos de passeio | 3,0 |

Outros usos (lojas, bibliotecas, coberturas, forros, academias, auditórios): **consulte a Tabela 10 da NBR 6120:2019**.

## Fatores de combinação ψ (NBR 6118 Tabela 11.2)
| Ação | ψ0 | ψ1 | ψ2 |
|---|---|---|---|
| Residencial (sem predominância de pesos fixos) | 0,5 | 0,4 | 0,3 |
| Comercial/escritórios/edifícios públicos | 0,7 | 0,6 | 0,4 |
| Bibliotecas, arquivos, oficinas, garagens | 0,8 | 0,7 | 0,6 |
| Vento | 0,6 | 0,3 | 0 |
| Temperatura | 0,6 | 0,5 | 0,3 |

## Coeficientes de ponderação no ELU (NBR 6118 Tabela 11.1)
| Combinação | γg desf./fav. | γq | γε (retração/temperatura) |
|---|---|---|---|
| Normal | 1,4 / 1,0 | 1,4 | 1,2 / 0 |
| Especial ou de construção | 1,3 / 1,0 | 1,2 | 1,2 / 0 |
| Excepcional | 1,2 / 1,0 | 1,0 | 0 / 0 |

Use `--gamma-g` no script para combinações especiais.
