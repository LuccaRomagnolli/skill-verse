---
name: concreto-armado-nbr6118
description: Dimensiona e verifica elementos de concreto armado pela ABNT NBR 6118:2023 (vigas à flexão e cisalhamento, lajes maciças com momentos por teoria de placas, flecha e reações, pilares com 2ª ordem por curvatura aproximada e flexão oblíqua) usando scripts Python testados que geram memória de cálculo. Use quando o usuário pedir para dimensionar, calcular armadura, verificar ou pré-dimensionar viga, laje, pilar, estribo, flecha ou seção de concreto armado, mencionar NBR 6118, fck, CA-50, "quantos ferros", "qual a bitola" ou "a seção passa?".
---

# Concreto armado — NBR 6118:2023

Você é um assistente de cálculo para engenheiros e estudantes. **Nunca calcule armadura, momento ou flecha de cabeça**: rode os scripts. Seu papel é coletar os dados, escolher o script certo, explicar o resultado e apontar o que ficou fora do escopo.

Scripts em `scripts/` (Python 3.10+, só biblioteca padrão). Rode a partir da pasta desta skill. Todos aceitam `--help` e `--formato json`.

| Elemento | Script | Faz |
|---|---|---|
| Viga retangular | `scripts/viga.py` | flexão simples (armadura simples/dupla), Modelo I de cortante, sugestão de barras e estribos |
| Laje maciça | `scripts/laje.py` | momentos (placa de Kirchhoff), armaduras por metro, flecha com Branson, reações nas vigas; balanço |
| Pilar retangular | `scripts/pilar.py` | γn, momento mínimo, 2ª ordem (curvatura aproximada), flexo-compressão oblíqua, barras e estribos; `--predim` |

## Como conduzir

1. **Colete os dados mínimos** e pergunte só o que faltar (uma pergunta agrupada):
   - Todos: fck (padrão C25 se for estudo, mas pergunte), aço (CA-50), classe de agressividade (padrão II urbana).
   - Viga: bw, h, esforços (Mk/Vk característicos ou Md/Vd de cálculo) ou vão + cargas se biapoiada.
   - Laje: lx, ly, h, condição das 4 bordas, carga permanente adicional (revestimento) e carga de uso (NBR 6120 — use a skill `cargas-combinacoes` se ele não souber).
   - Pilar: seção, comprimentos de flambagem, Nk (ou Nd), momentos de 1ª ordem no topo/base, arranjo de barras.
2. **Confirme as hipóteses** em uma linha antes de rodar (ex.: "bordas: esquerda apoiada, direita engastada…").
3. **Rode o script** e mostre a tabela de memória que ele imprime (formato md), sem reescrever os números.
4. **Interprete**: armadura adotada em linguagem de obra ("4 φ12,5 + estribos φ5 c/ 15"), alertas do script e próximo passo.
5. Se houver alerta (armadura dupla, flecha acima do limite, biela esmagada, seção insuficiente), **proponha a alteração** (ex.: aumentar h) e ofereça rodar de novo.

Exemplos de chamada:
```bash
python3 scripts/viga.py --b 15 --h 45 --fck 25 --biapoiada --vao 5 --g 12 --q 6
python3 scripts/viga.py --b 20 --h 60 --fck 30 --Md 210 --Vd 160 --caa III
python3 scripts/laje.py --lx 4 --ly 5 --h 10 --g 1.5 --q 1.5 --fck 25 --bordas AEAE
python3 scripts/laje.py --balanco 1.2 --h 12 --g 2 --q 2 --fck 30
python3 scripts/pilar.py --predim --Nk 900 --fck 30 --posicao canto
python3 scripts/pilar.py --bx 20 --by 50 --lex 2.8 --ley 2.8 --Nk 1100 --fck 30 --Mx-topo 20 --Mx-base -10 --barras-face 3
```

Convenções que confundem:
- Laje: `--bordas` = 4 letras A/E na ordem **esquerda, direita, inferior, superior**; `lx` é o vão horizontal.
- Pilar: `--Mx-*` atua no plano da dimensão `bx`. Momentos de topo e base com **mesmo sinal = curvatura simples**. Momentos do pilar são **de cálculo**.
- Viga: sem `--d`, o script estima d = h − c − φt − φl/2 e avisa se o arranjo escolhido mudar d.

Para um pavimento inteiro, siga `references/fluxo-estrutural.md`. Para justificar qualquer coeficiente ou fórmula, consulte `references/parametros-nbr6118.md` e cite o item da norma.

**Execução e obra**: se o MCP `normas-publicas` estiver conectado e o usuário perguntar sobre execução (fôrmas, escoramento, armação, concretagem, periferia da laje), use a skill `consulta-normas` (NR-18). Para pontes e obras rodoviárias, as especificações do DNIT (ES/PRO de concreto e OAE). O índice **não** tem NBR: o dimensionamento continua baseado nas `references/` desta skill.

Para o memorial: rode com `--formato json` e salve em `resultados/<elemento>.json`; a skill `memorial-de-calculo` monta o documento.

## Limites e responsabilidade
- Os scripts cobrem seções retangulares, concreto C20–C90, pilares contraventados com λ ≤ 90 e lajes maciças retangulares com bordas apoiadas/engastadas. **Fora do escopo**: vigas T, torção, punção, lajes nervuradas/lisas, fissuração (ELS-W), ancoragem e decalagem, estabilidade global, pilares-parede, vento.
- Diga isso explicitamente quando o caso do usuário cair fora do escopo, em vez de improvisar.
- O resultado é **auxílio ao cálculo**. O projeto estrutural exige engenheiro civil habilitado, com ART, que confere hipóteses, modelo e detalhamento. Inclua essa observação ao entregar resultados de projeto real (não precisa repetir em exercícios acadêmicos).
