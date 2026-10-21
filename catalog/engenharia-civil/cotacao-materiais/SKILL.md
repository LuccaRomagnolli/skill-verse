---
name: cotacao-materiais
description: Pesquisa na web preços de fornecedores para cada material de uma planilha de quantitativos ou lista de materiais, compara embalagem, frete, prazo e especificação e gera planilha Excel com a opção de melhor custo-benefício por item, nome da empresa, descrição do produto, link, quantidade a comprar e total estimado. Use quando pedirem cotação de materiais, pesquisa de fornecedores, "onde comprar mais barato", menor preço, preço do cimento/aço/bloco hoje, comparar lojas ou estimar o custo de compra de uma lista de materiais.
---

# Cotação de materiais na web

Script em `scripts/cotacao.py` (stdlib). Rode a partir da pasta desta skill. **Toda conta é do script**: perdas, conversão de embalagem, arredondamento de compra, frete, totais e ranking. O agente pesquisa e registra; não soma nem converte de cabeça.

Retome pela ficha (`contexto-do-projeto` → `resumo`): município, UF e, se houver, CEP da obra. Sem local de entrega, pergunte antes de pesquisar, porque preço e frete dependem do CEP. Pergunte também: prazo em que precisa do material, se já tem fornecedores preferidos ou cadastro em atacadista, e se o preço deve ser à vista (Pix/boleto) ou parcelado.

## 1. Importar a lista
1. Aceite XLSX/CSV com colunas de descrição (ou serviço/material/insumo), unidade e quantidade, como a saída de `quantitativos-sinapi`:
   ```bash
   python3 scripts/cotacao.py importar --arquivo quantitativos.xlsx --saida cotacoes.json
   ```
   Se o cabeçalho não for achado, informe `--aba` ou peça a aba exportada em CSV.
2. Mostre a lista importada e confirme com o usuário. Preencha `obra`, `local` (município, UF, CEP) e `especificacao` de cada item (classe, bitola, dimensões, resistência, cor, norma de conformidade só pelo número e ano). Especificação ambígua: pergunte, não suponha.
3. **Serviço não é material.** Itens marcados `alerta_servico` (alvenaria m², fôrma m², revestimento…) precisam virar insumos de compra. Use o coeficiente da composição analítica escolhida (SINAPI do mês/UF, catálogo do fabricante ou critério do usuário) e registre no item:
   `"derivado_de": {"servico": "Alvenaria", "quantidade_servico": 31.77, "coeficiente": 13.5, "fonte": "SINAPI analítico <código> GO 09/2026"}`. O script multiplica. Confirme os coeficientes com o usuário.
4. `perda_pct`: perda de compra por item (quebra, sobra de corte). Não aplique duas vezes: o aço de `quantitativos.py` já sai com perda. Na dúvida, pergunte.

## 2. Pesquisar fornecedores na web
Siga `references/pesquisa-web.md`. Em resumo, para **cada item**:
1. Busque com a especificação + cidade/UF ("cimento CP II-F-32 50 kg Goiânia"). Procure **3 fornecedores distintos** quando houver: lojas de materiais e home centers com preço público, distribuidores e atacadistas da região, lojas oficiais de fabricantes e, por último, marketplaces (registre o vendedor, não só a plataforma).
2. **Abra a página do produto** e confirme ali preço, embalagem, unidade, vendedor e disponibilidade. Preço visto só no resultado de busca recebe `"confirmado": false` (confiança baixa). Se a página mostrar frete e prazo para o CEP da obra, registre; se não, deixe `frete` vazio.
3. Converta a embalagem para a unidade do item em `conteudo`, com o valor lido na página (saco 50 kg → 50; milheiro → 1000; caixa 2,5 m² → 2.5). Barra de aço em kg: `python3 scripts/cotacao.py massa-barra --bitola 10 --comprimento 12`. Tabela de embalagens: `references/unidades-e-embalagens.md`.
4. Compare a especificação: `atende` = `sim`, `parcial` (ex.: CP II-E no lugar de CP II-F, outra dimensão) ou `nao`. Explique o `parcial` em `obs`.
5. Material a granel ou sob encomenda (concreto usinado, areia, brita, aço cortado e dobrado, blocos por carga, pré-moldados) quase nunca tem preço on-line. Localize fornecedores locais com site ou telefone e registre `"situacao": "sob-consulta"` com `contato`. **Nunca invente preço.**
6. Registre a oferta em `ofertas` do item, com `acesso` (data de hoje) e `url`, no formato de `assets/cotacoes.exemplo.json`. Opcional: `referencia` com o preço SINAPI do insumo para comparar.

Não faça login, não preencha cadastro, não contorne captcha nem bloqueio de robôs e não compre nada. Se o site exigir CEP ou login para mostrar preço, registre como sob consulta e siga em frente.

## 3. Gerar a planilha
```bash
python3 scripts/cotacao.py validar --cotacoes cotacoes.json
python3 scripts/cotacao.py gerar --cotacoes cotacoes.json --saida cotacao-materiais.xlsx --csv cotacao-materiais.csv
python3 scripts/cotacao.py pedido --cotacoes cotacoes.json            # textos de pedido de cotação
```
A planilha tem as abas **Resumo**, **Melhor custo-benefício** (uma linha por item: material, produto encontrado, empresa, embalagem, quantidade a comprar, preço, frete, total estimado, link e alertas, com fórmulas editáveis e total geral), **Comparativo** (todas as ofertas ranqueadas), **Por fornecedor** (quem cobre mais itens, para concentrar o frete) e **Pedir cotação**.

**Critério de custo-benefício** (detalhes em `references/criterio-custo-beneficio.md`): entram só ofertas que atendem à especificação e têm preço público. Compra em embalagens inteiras, com perda e pedido mínimo, mais o frete informado. Recomenda-se o **menor total** entre ofertas de confiança alta ou média, com desempate pelo prazo. A confiança cai com especificação parcial, preço não confirmado, falta de link, acesso antigo ou preço abaixo de 50% da mediana, sinal de erro de unidade ou golpe.

## 4. Entregar
1. Mostre a tabela do terminal, o **total estimado** e quantos itens ficaram sem preço. Destaque alertas: ofertas de confiança baixa, itens com menos de 3 fornecedores, frete não informado e fornecedor que cobre vários itens (comprar junto pode baratear o frete; peça a cotação conjunta).
2. Para itens sob consulta, entregue os textos de `pedido` (e-mail/WhatsApp) e ofereça atualizar a planilha quando o usuário receber as respostas: inclua o preço em `ofertas`, com `"confirmado": true`, e rode `gerar` de novo.
3. Registre `cotacoes.json` e a planilha com `contexto.py artefato --estado em-revisao`, com a data da pesquisa. Ao retomar após a validade (padrão 7 dias, `--validade-dias`), repita a pesquisa antes de usar os preços.

## Limites e responsabilidade
- Preços de varejo on-line mudam a cada dia e variam com CEP, estoque, forma de pagamento, frete e promoções. A planilha é **estimativa de compra na data da pesquisa**, não proposta comercial: confirme preço, frete, prazo e condições com o fornecedor antes de comprar.
- O agente não verifica qualidade de produto nem idoneidade de empresa. Antes de pagar, confira CNPJ e reputação do vendedor, sobretudo em ofertas muito abaixo da média. Exija nota fiscal.
- Conformidade técnica (classe do cimento, CA-50, bloco conforme norma, programas setoriais da qualidade do PBQP-H) é verificada pelo responsável técnico no recebimento. A skill só compara a descrição do anúncio.
- Em contratação pública, a pesquisa de preços segue regras próprias (Lei 14.133/2021, art. 23, e regulamentos do órgão). Esta planilha não substitui esse procedimento. Avise o usuário quando for o caso.
- Coeficientes de consumo e perdas vêm de composição ou critério informado e confirmado pelo usuário. O quantitativo de origem é responsabilidade de quem o levantou.
