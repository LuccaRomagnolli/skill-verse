# Padrões de desenho técnico (síntese própria, sem texto das normas)

As normas ABNT são vendidas pela ABNT. Aqui ficam só a referência (número/ano) e a prática que o agente aplica. A **edição vigente** deve ser confirmada no catálogo ABNT (skill `consulta-normas`) e o **padrão da prefeitura** pela skill `contexto-do-projeto`. O padrão da prefeitura prevalece na prancha de aprovação.

| Tema | Norma de referência | O que o agente aplica |
|---|---|---|
| Folha, margens, moldura, legenda | NBR 16752:2020 (substituiu NBR 10068, 10582 e 13142) | série A; margem esquerda maior para encadernação; legenda no canto inferior direito; dobra final no formato A4. `scripts/prancha.py` gera a folha |
| Projeto de arquitetura e urbanismo | NBR 6492:2021 | conjunto de pranchas (situação, implantação, plantas, cortes, fachadas, detalhes), indicação de norte, níveis e cotas de piso |
| Escalas | NBR 8196 | escalas de redução usuais; sempre indicadas na legenda e sob cada vista com escala diferente |
| Tipos e espessuras de linha | NBR 8403 | contínua grossa = contorno visível cortado; contínua fina = cotas, hachuras, chamadas; tracejada = oculto; traço-ponto = eixo/simetria |
| Letras e algarismos | NBR 8402 | alturas usuais de 2,5 / 3,5 / 5 / 7 mm no papel, fonte legível e uniforme |
| Cotagem | NBR 10126 | cotas fora da peça sempre que possível, sem repetir, encadeadas ou em linha de base, texto acima da linha de cota |
| Hachuras | NBR 12298 | hachura distinta por material; concreto cortado com padrão próprio |
| Desenhos de concreto | NBR 7191 | fôrma separada de armação; posições numeradas; quantidade, bitola, espaçamento e comprimento em cada posição; tabela/resumo de aço por prancha |

## Convenções que o agente segue (sem perguntar, a menos que o escritório tenha padrão próprio)
- **Unidade**: detalhes e plantas estruturais em centímetros. Arquitetura recebida costuma vir em metros ou milímetros: conferir `INSUNITS` e o tamanho de uma porta conhecida (≈ 0,80 m) antes de qualquer medição.
- **Escala de anotação**: altura do texto no modelo = altura no papel (mm) × escala ÷ mm por unidade. O `prancha.py` devolve a tabela pronta (`alturas_texto`).
- **Espessuras de penas** usuais em plotagem monocromática: 0,13–0,18 (finas), 0,25–0,35 (médias), 0,50–0,70 (grossas). A tabela de layers em `padrao-layers.md` já atribui.
- **Indicação de peças**: L1, V1, P1, B1 (bloco), S1 (sapata), E1 (estaca), com dimensões em cm. Armadura no formato `N1 3 %%c12,5 c/15 C=530`.
- **Norte, níveis e cortes**: símbolo de norte em plantas de situação/implantação; níveis em metros com duas casas (`+3,06`); cortes indicados com letra e sentido de vista.
- **Carimbo**: obra, local, cliente, conteúdo, escala, data, folha (n/total), responsável técnico com registro (CREA/CAU), ART/RRT e revisão. Os dados vêm da ficha do projeto e do usuário, e nunca são inventados.
