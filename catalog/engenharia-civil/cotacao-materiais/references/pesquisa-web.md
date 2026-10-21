# Pesquisa de preços na web — roteiro

## Onde procurar (ordem de preferência)
1. **Fornecedores da região da obra** com loja on-line ou tabela pública: lojas de materiais de construção, home centers regionais, depósitos, distribuidores e atacadistas. Têm preço e frete mais próximos da compra real.
2. **Redes nacionais** com preço por CEP (home centers e varejistas de construção). Informe o CEP da obra quando o site permitir sem login.
3. **Lojas oficiais de fabricantes** e distribuidores autorizados, úteis para especificação exata (linha, classe, dimensões) e para conferir a embalagem.
4. **Marketplaces**: registre o **vendedor** (razão social ou nome da loja) em `fornecedor`, não só a plataforma. Desconfie de vendedor sem histórico.

Para granel e sob encomenda (concreto usinado, areia, brita, aço cortado e dobrado, pré-moldados, blocos por carga), busque "concreteira", "areia e brita", "corte e dobra", "olaria" + cidade. Registre telefone, site ou e-mail como `sob-consulta`.

## Como buscar
- Consulta = material + especificação essencial + embalagem + cidade/UF. Ex.: `bloco cerâmico 14x19x29 milheiro Anápolis GO`, `vergalhão CA-50 10mm barra 12m preço Goiânia`.
- Faça ao menos uma busca por item sem a cidade para achar redes com entrega na região.
- Use o resultado de busca só para achar a página. **Preço vale apenas se lido na página do produto** (`"confirmado": true`). Snippets e comparadores costumam estar desatualizados.
- Leia na página: preço à vista e condição (Pix, boleto, cartão), embalagem e conteúdo, vendedor, estoque e frete/prazo para o CEP, quando aparecerem sem login.
- Preço com desconto só no Pix ou para quantidade mínima: registre a condição em `obs` e o pedido mínimo em `pedido_minimo`, na unidade de venda.

## O que registrar em cada oferta
| Campo | Conteúdo |
|---|---|
| `fornecedor` | nome da empresa/loja (vendedor, em marketplace) |
| `produto` | descrição do anúncio (marca, linha, dimensões) |
| `url` | link da página do produto |
| `preco` | preço da unidade de venda, em R$ |
| `unidade_venda` / `conteudo` | embalagem e quanto ela contém na unidade do item |
| `fracionavel` | `true` quando vende a quantidade exata (kg, m³, metro) |
| `pedido_minimo` | mínimo exigido, em unidades de venda |
| `frete` / `prazo_dias` | frete para o CEP da obra e prazo; vazio se não informado |
| `cidade` | cidade/UF do fornecedor ou do centro de distribuição |
| `acesso` | data da consulta (AAAA-MM-DD) |
| `atende` | `sim`, `parcial` ou `nao` frente à especificação |
| `confirmado` | `true` se o preço foi lido na página do produto |
| `situacao` | `preco-publico`, `sob-consulta` ou `indisponivel` |
| `contato` / `obs` | telefone, e-mail ou observações (condição de pagamento, restrições) |

## Sinais de alerta
- Preço muito abaixo dos demais (o script marca abaixo de 50% da mediana): costuma ser erro de unidade (preço por kg × saco), embalagem menor, produto diferente ou golpe.
- Loja sem CNPJ visível, só Pix, domínio recém-criado ou sem endereço físico. Oriente o usuário a consultar o CNPJ no site da Receita Federal e a reputação da loja antes de pagar.
- Produto "similar" ou de linha diferente da especificada: registre `atende: parcial`.
- Página que pede login, cadastro ou CEP com captcha para mostrar preço: não contorne. Registre `sob-consulta`.

## O que não fazer
- Não inventar ou estimar preço que não foi lido.
- Não raspar sites em massa, não automatizar carrinho e não fazer login ou compra.
- Não copiar textos longos dos anúncios. Registre só os dados da oferta.
- Não usar sites de cópia de normas para conferir especificação (lista bloqueada no MCP `normas-publicas`). De NBR, cite só número e ano.
