# Fluxo de projeto no TQS (o que o agente orienta e o que automatiza)

| Etapa | Onde, no TQS | O agente |
|---|---|---|
| 1. Edifício novo | Gerenciador → Edifício → Novo (Editor de Dados do Edifício) | orienta. Com um edifício-modelo existente, cria variantes por `tqs_edificio.py aplicar --salvar-como` |
| 2. Dados gerais e normas | aba Gerais: norma de concreto, tipo de estrutura | lê/confere (`tqs_edificio.py ler/conferir`) |
| 3. Modelo estrutural | aba Modelo: Modelo IV (pórtico + grelhas) ou VI (pórtico com lajes); γz ou P-Delta; ISE | explica as opções. Altera numa cópia, com pedido |
| 4. Pavimentos | aba Pavimentos: nome, classe (fundação, térreo, tipo, cobertura…), altura, repetições | lê e compara com a arquitetura/Revit (mesmos nomes e cotas) |
| 5. Materiais e cobrimentos | abas Materiais e Cobrimentos: CAA, fck por elemento, cobrimentos | `conferir` faz triagem numérica pelas Tabelas 7.1 e 7.2 da NBR 6118:2026 (base + emenda), sem verificar exceções nem o projeto completo |
| 6. Cargas | aba Cargas: casos (PP, permanente, acidental, vento, desaprumo…), γf, ψ; vento pela NBR 6123 (V0, S1, S3, rugosidade, classe) | lê os coeficientes. Valores de carga e vento vêm da skill `cargas-combinacoes` |
| 7. Lançamento | Modelador Estrutural: referência da arquitetura (DWG por planta), pilares, vigas, lajes, cargas, furos | prepara a base (skill `autocad-assistente`, "base para cálculo"). Lista o que foi lançado (`tqs_modelo.py listar`) |
| 8. Processamento global | Gerenciador → Processamento → Global | `tqs_processar.py` (simula; executa com "sim") |
| 9. Análise | Visualizador de pórtico/grelha, γz, deslocamentos, fissuração, avisos e erros | orienta a leitura. Nunca aprova resultado sozinho |
| 10. Detalhamento | editores de vigas, pilares, lajes, fundações, escadas | orienta. Tabela de ferros única: `--tabela-ferros` |
| 11. Plotagem | Plotagem/PDF, DWG para outros softwares | `tqs_dwg.py exportar` (DXF/PDF); prancha final com `autocad-assistente` |
| 12. BIM | exportação IFC / integração | ver `interoperabilidade.md` |

## Pontos de atenção que o agente sempre levanta
- **Norma no edifício**: a versão de API usada como base expunha constantes até `NORMA_NBR_6118_2014`. Consulte a instalação local com `--introspectar TQSBuild`; registre a edição efetiva do TQS e compare com a referência declarada NBR 6118:2026. Uma opção anterior não prova conformidade 2026.
- **γz** e estabilidade global: valores altos pedem P-Delta e revisão de rigidez. O agente aponta, e o engenheiro decide.
- **CAA × fck × cobrimento** coerentes com a ficha do projeto (`contexto-do-projeto`).
- **Repetição de pavimentos**: altera cargas acumuladas nos pilares. Confira com a arquitetura.
- **Avisos do processamento** (erros graves, médios, leves) sempre são lidos antes de usar armaduras ou desenhos.

## Estudo de alternativas (automação que mais economiza tempo)
1. Edifício base pronto e conferido.
2. `tqs_edificio.py aplicar --dados variante.json --salvar-como "<base>-C30"` para cada variante (fck, modelo IV/VI, cobrimento…).
3. `tqs_processar.py --edificios "<base>-C25,<base>-C30" --preset completo --tabela-ferros --executar` (com "sim").
4. Compare consumo de aço (tabela de ferros), volume de concreto e γz por variante. Some e compare por script, nunca de cabeça.
