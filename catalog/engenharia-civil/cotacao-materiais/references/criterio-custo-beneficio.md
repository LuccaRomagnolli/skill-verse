# Critério de custo-benefício (como o script decide)

## Cálculo por oferta
1. Quantidade necessária = quantidade do item (ou `quantidade_servico × coeficiente`) × (1 + `perda_pct`/100). Peças inteiras arredondam para cima.
2. Quantidade a comprar = necessária ÷ `conteudo`, arredondada **para cima** (embalagem fechada), exceto quando `fracionavel: true`. Se ficar abaixo de `pedido_minimo`, sobe para o mínimo e gera alerta.
3. Total = quantidade a comprar × `preco` + `frete` informado.
4. Preço por unidade do item = `preco` ÷ `conteudo`. Serve para comparar com a referência SINAPI quando ela for informada.

## Quem entra no ranking
- Entram ofertas com `situacao: preco-publico`, `atende` igual a `sim` ou `parcial`, `preco` e `conteudo` válidos.
- Ficam fora `sob-consulta`, `indisponivel` e `atende: nao`. Elas aparecem no Comparativo e em Pedir cotação.

## Confiança
| Nível | Quando |
|---|---|
| baixa | atende parcialmente; sem `url`; `confirmado: false`; sem data de acesso ou acesso mais antigo que a validade (padrão 7 dias); preço por unidade abaixo de 50% da mediana do item (com 3 ou mais ofertas) |
| média | frete não informado ou prazo não informado |
| alta | nenhuma das situações acima |

## Recomendação
- **Melhor custo-benefício = menor total entre as ofertas de confiança alta ou média.** Em empate de total, vence o menor prazo.
- Se só houver ofertas de confiança baixa, a mais barata é indicada com o alerta "confirme antes de usar".
- Índice de custo-benefício no Comparativo = total da oferta ÷ menor total do item (1,00 = mais barata, 1,10 = 10% mais cara).
- A aba Por fornecedor mostra quantos itens cada empresa cobre e em quantos é a melhor opção. Concentrar a compra em um fornecedor pode reduzir o frete. Peça cotação conjunta antes de decidir.

## Por que não usar só o menor preço unitário
O menor preço por kg ou unidade pode perder no total por causa da embalagem (sobra), do pedido mínimo ou do frete. Por isso a comparação é feita pelo **total da compra entregue**. Oferta "parcial" fica com confiança baixa porque o material pode não servir. O usuário decide se aceita a troca.
