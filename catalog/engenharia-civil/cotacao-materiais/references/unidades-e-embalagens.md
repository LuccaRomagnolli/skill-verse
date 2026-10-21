# Unidades de venda e conversão para a unidade do item

`conteudo` = quanto **uma unidade de venda** contém, na **unidade do item** do quantitativo. Leia o valor na página do produto. Não presuma a embalagem.

| Material | Unidade usual no quantitativo | Vendas comuns | `conteudo` |
|---|---|---|---|
| Cimento | kg (ou saco) | saco 25, 40 ou 50 kg | massa do saco em kg; se o item estiver em "saco", use 1 e confira a massa |
| Cal hidratada, argamassa industrializada | kg | saco 20 kg | 20 |
| Aço CA-50/CA-60 | kg | barra de 12 m; rolo; kg (corte e dobra) | barra: `cotacao.py massa-barra --bitola <mm> --comprimento 12`; por kg: 1 e `fracionavel: true` |
| Tela soldada | m² ou un | painel (ex.: 2 × 3 m) | área do painel lida no anúncio, se o item estiver em m² |
| Bloco cerâmico/concreto | un | unidade ou milheiro | 1 ou 1000 |
| Areia, brita | m³ | m³; "carrada"/caçamba; saco | m³ da carga **confirmado com o fornecedor**; saco em kg só se o item estiver em kg |
| Concreto usinado | m³ | m³ (pedido mínimo, taxa de bomba à parte) | 1, `fracionavel: true`; taxa de bomba no `frete` ou em `obs` |
| Piso, revestimento cerâmico | m² | caixa | m² por caixa, lido na embalagem |
| Tinta | L ou m² | galão 3,6 L, lata 18 L | litros; se o item estiver em m², converta pelo rendimento declarado **e registre a fonte** |
| Tubo PVC, eletroduto | m | barra 3 ou 6 m | comprimento da barra |
| Fio/cabo | m | rolo 50 ou 100 m | metros do rolo |
| Telha | m² ou un | unidade | 1, se o item estiver em un; em m², use a área útil declarada pelo fabricante |
| Madeira, compensado | m², m ou un | chapa, peça | área da chapa ou comprimento da peça |

## Regras
- Item e oferta devem estar na mesma grandeza. Se o item está em kg e a loja vende saco, `conteudo` é a massa do saco. Se o item está em "saco", não converta.
- Peças inteiras (un, barra, saco, rolo, lata) têm a quantidade arredondada para cima pelo script.
- Conversões que dependem de densidade, rendimento ou área útil exigem fonte (ficha técnica do fabricante ou do fornecedor). Registre essa fonte em `obs`. Sem fonte, pergunte ao usuário ou peça a cotação na unidade do item.
- Massa linear do aço: NBR 7480:2022 (tabela no script). A barra comercial de 12 m é usual, mas confirme o comprimento no anúncio.
