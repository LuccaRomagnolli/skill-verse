# SkillVerse — loja de packs

Vitrine responsiva em português, implementada em HTML, CSS e JavaScript sem etapa de build. Os arquivos publicados ficam em `dist/`. O catálogo comercial original, scripts e ZIPs de skills permanecem fora do site.

## Executar localmente

```sh
python3 -m http.server 4173 --bind 127.0.0.1 --directory dist
```

Abra http://127.0.0.1:4173.

## Pagamentos

O valor definido é R$ 39,90 por pack completo, em pagamento único. O carrinho guarda somente a seleção do produto no navegador. Não há cobrança, coleta de cartão, cadastro ou simulação de compra concluída.

Após escolher um provedor, configure o produto e a entrega protegida do ZIP no checkout hospedado. Em `dist/config.js`, informe a URL HTTPS pública de checkout em `checkoutUrl`. Nunca coloque chaves secretas neste arquivo ou em qualquer outro arquivo de `dist/`.

O link habilita o redirecionamento, mas não implementa confirmação de pagamento, entrega por webhook, autenticação ou controle de pedidos. Esses fluxos devem ser realizados pelo provedor escolhido ou por uma integração de servidor posterior. O preço exibido deve coincidir com o cadastrado no provedor.

Antes de ativar vendas, conclua a liberação técnica do pack, revise os textos de disponibilidade no produto e FAQ, publique os termos comerciais, identifique o responsável pela loja e adapte a política de privacidade ao provedor real. O pack 1.3.3 continua identificado como candidato em validação, conforme o repositório.

## Conteúdo e interações

- `dist/index.html`: estrutura, catálogo de packs, preço, FAQ e detalhes comerciais.
- `dist/styles.css`: paleta, layout, desenhos vetoriais, responsividade e movimento reduzido.
- `dist/app.js`: catálogo de 12 skills, busca, filtros, exemplos interativos, diálogos nativos acessíveis e carrinho.
- `dist/config.js`: preço e destino futuro de checkout.
- `.openai/hosting.json`: identidade e configuração de hospedagem Sites.

O pack Professores está explicitamente em desenvolvimento. As demonstrações são ilustrativas; não executam agentes nem cálculos. Nenhum arquivo proprietário do pack está exposto para download.

## Referências

- https://github.com/shadcn-ui/ui — referência de composição e padrões de interface. Nenhuma dependência React ou componente copiado foi necessário nesta implementação estática.
- https://github.com/anthropics/skills — referência do formato Agent Skills e orientação de apresentação.
- `../README.md` e `../packs/engenharia-civil/pack.yaml` — fonte do conteúdo factual do produto.

As fontes Manrope e DM Sans são carregadas pelo Google Fonts; há fontes locais alternativas caso o serviço esteja indisponível.
