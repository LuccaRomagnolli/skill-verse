# Vento — guia rápido NBR 6123:1988

## Fatores
- **V0**: velocidade básica (rajada de 3 s, 50 anos, 10 m, terreno aberto), do mapa de isopletas (Figura 1). Peça ao usuário o valor da cidade. Se ele não souber, explique onde achar e **não invente**.
- **S1 (topográfico)**: 1,0 terreno plano ou pouco acidentado; 0,9 vales profundos protegidos; taludes e morros: item 5.2 (cresce no topo).
- **S2 (rugosidade × dimensões × altura)**: S2 = b·Fr·(z/10)^p.
  - Categoria I: mar calmo, lagos, rios largos. II: campo aberto, poucos obstáculos. III: chácaras, casas esparsas, muros. IV: subúrbios, cidades pequenas, áreas industriais (obstáculos ~10 m). V: centros de grandes cidades, florestas altas (obstáculos ≥ 25 m).
  - Classe A: maior dimensão ≤ 20 m; B: 20–50 m; C: > 50 m.
- **S3 (estatístico)**: grupo 1 = 1,10; 2 = 1,00; 3 = 0,95; 4 = 0,88; 5 = 0,83.

## Pressão e força
- q = 0,613·Vk² (N/m²).
- Força global numa direção: F = Ca·q·Ae. **Ca** vem dos ábacos (Figura 4 para vento de baixa turbulência; Figura 5 de alta turbulência) em função de h/l1 e l1/l2. Valores típicos para edifícios retangulares em baixa turbulência ficam entre ~1,0 e ~1,5: **leia no ábaco** com o usuário e passe `--Ca`.
- Coeficientes de pressão externa (paredes e telhados, Tabelas 4 e 5) e pressões internas (item 6.2): fora do script; explique a tabela quando o usuário pedir.
- Efeitos de vizinhança, excentricidade (item 6.6) e dinâmica (edifícios esbeltos, frequência < 1 Hz): fora do escopo.
