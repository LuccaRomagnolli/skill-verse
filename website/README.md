# SkillVerse — loja e pagamentos SyncPay

A loja usa Vinext em Cloudflare Workers, com D1 para pedidos e R2 privado para o arquivo do pack. A vitrine está em `server/store.html` e `public/`; os endpoints estão em `app/api/`. O preço é definido no servidor em `lib/payments.ts` (R$ 39,90). A configuração do navegador é apenas apresentação e não determina a cobrança.

## Estado atual

O pagamento inicia desativado. O pack de Engenharia Civil 1.4.1 ainda é candidato, conforme o README principal do repositório: não disponibilize o ZIP até sua liberação técnica. A hospedagem do site está privada; visitantes e webhooks externos da SyncPay não podem alcançá-la nesse estado. Os testes automatizados usam respostas simuladas, sem efetuar cobranças reais.

A SyncPay exige IP de origem autorizado. Confirme com a SyncPay e a hospedagem uma solução de saída compatível; este projeto não presume que o Worker tenha um IP fixo. A chave pública do cartão exige que a origem da loja esteja autorizada no painel SyncPay. O checkout mantém os dados do cartão no navegador apenas durante a tokenização direta na SyncPay: o servidor recebe somente o token. A página própria continua sujeita às obrigações de segurança aplicáveis a cartão; não pressupõe certificação PCI.

## Configuração no ambiente seguro da hospedagem

Não coloque credenciais em código, Git, arquivos públicos ou mensagens. Defina as variáveis no gerenciador de segredos de Sites:

| Nome | Conteúdo |
| --- | --- |
| `SYNCPAY_CLIENT_ID` e `SYNCPAY_CLIENT_SECRET` | Credenciais do painel de desenvolvedor SyncPay; tratar como secretas. |
| `SYNCPAY_PUBLIC_KEY` | Chave pública `pk_live_…` do cartão; habilite o domínio da loja no painel. |
| `SYNCPAY_WEBHOOK_TOKEN` | Segredo retornado pela SyncPay ao criar o webhook de transações; não invente um valor para substituir o token do provedor. |
| `RELEASE_UPLOAD_TOKEN` | Segredo aleatório com pelo menos 32 caracteres para upload do ZIP; gere um valor próprio. |
| `SITE_ORIGIN` | Origem HTTPS da loja sem barra final; também usada para montar o webhook. |
| `PACK_OBJECT_KEY` | Chave privada da versão liberada no R2, por exemplo `releases/engenharia-civil-v1.zip`. Não reutilize a mesma chave ao atualizar. |
| `PAYMENTS_ENABLED` | `false` até as verificações e a liberação do pack; depois `true`. |

Configure na SyncPay o evento `transaction` para `/api/webhooks/syncpay` quando o endpoint puder receber notificações. A SyncPay retorna o segredo de assinatura somente na criação; armazene-o com segurança como `SYNCPAY_WEBHOOK_TOKEN` na hospedagem. O novo contrato usa HMAC-SHA256 e janela de 5 minutos. O endpoint também aceita o Bearer do contrato legado. Os webhooks são gatilhos: o servidor consulta a API autenticada e confere identificador, moeda e valor antes de atualizar o pedido. Enquanto o site estiver privado, a consulta de status feita pelo navegador continua disponível ao proprietário, mas os webhooks externos não chegam.

O endpoint administrativo `POST /api/admin/syncpay-check`, protegido pelo `RELEASE_UPLOAD_TOKEN`, testa a autenticação e uma consulta de parceiro a partir da hospedagem sem criar uma cobrança. Ele não retorna dados da conta, credenciais ou o token da API.

Após revisão e liberação do ZIP, envie-o ao R2 privado pelo endpoint protegido. Para o script local, carregue `SITE_ORIGIN` e `RELEASE_UPLOAD_TOKEN` em um arquivo local não rastreado; para um site privado, inclua também `SITE_PRIVATE_BYPASS_TOKEN` obtido pela plataforma. Então execute:

```sh
node --env-file=.env.local scripts/upload-release.mjs /caminho/para/pack-liberado.zip
```

O servidor aceita somente um ZIP de até 20 MB e não sobrescreve uma versão existente. O arquivo não é incluído nos assets públicos. O checkout só é habilitado se as credenciais, o webhook, a origem, o objeto privado e `PAYMENTS_ENABLED=true` estiverem configurados. Faça teste controlado de ponta a ponta com a conta SyncPay antes de usar com clientes e confirme a compatibilidade da lista de IPs.

Pedidos são vinculados a um token aleatório guardado no navegador. O comprador pode guardar um código de acesso pessoal e usá-lo no carrinho para consultar o pedido em outro navegador. Esse código permite acessar o pedido e o download: deve ser mantido em sigilo. Não há envio automático por e-mail nem recuperação automática caso o código e os dados do navegador sejam perdidos. As tentativas com resposta incerta são marcadas para verificação manual, sem uma segunda cobrança automática. Não recrie a cobrança até conferir o painel da SyncPay.

## Desenvolvimento e testes

Node 24 é recomendado para o teste integrado, que usa `node:sqlite`. Dependências e build devem seguir o fluxo Sites:

```sh
node /caminho/para/sites/scripts/install-dependencies.mjs
npm run db:generate # somente após mudanças no schema
node /caminho/para/sites/scripts/build-site.mjs
node tests/run-payments-tests.mjs
npx tsc --noEmit
```

## Segurança e qualidade do site

O Worker aplica CSP restrita às respostas HTML e headers de proteção às rotas dinâmicas. `public/_headers` cobre os assets servidos diretamente pela Cloudflare. A CSP libera somente os scripts do próprio site, as fontes do Google usadas pelo CSS e a conexão do navegador com a API de tokenização da SyncPay. Revise essa lista ao acrescentar qualquer serviço externo. `SITE_ORIGIN` deve ser a origem HTTPS definitiva, sem barra final: a página usa esse valor para a tag canonical e para o `og:url`. Se faltar ou for inválido, essas tags não são emitidas.

O workflow `Website quality` executa instalação limpa, auditoria das dependências de produção, testes de pagamento, tipos, build e Lighthouse CI em três execuções. Os limites são 80 para desempenho e 95 para acessibilidade, boas práticas e SEO. Rode o mesmo conjunto localmente com:

```sh
npm run install:ci
npm audit --omit=dev --audit-level=moderate
node tests/run-payments-tests.mjs
npx tsc --noEmit
npm run build
npm exec --yes --package=@lhci/cli@0.15.1 -- lhci autorun
```

O Lighthouse local mede o Worker em HTTP. Confirme no domínio publicado o HTTPS, o certificado, o redirecionamento HTTP para HTTPS, o HSTS e a tag canonical antes de abrir o acesso público. Não ative `includeSubDomains` ou `preload` no HSTS sem validar todos os subdomínios. Refaça a checagem da CSP e do fluxo completo de pagamento com a conta real antes de habilitar cobranças.

Referências: [OWASP HTTP Security Response Headers](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html), [OWASP Content Security Policy](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html), [OWASP Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [OWASP TLS](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html) e [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci).

Para uma base local nova, após o build, aplique cada migração uma vez e em ordem antes de usar `npm run start`:

```sh
node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0000_hesitant_lake.sql
node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0001_pink_owl.sql
```

A publicação aplica as migrações pendentes com o fluxo Sites. `.env.local`, `.dev.vars`, credenciais, cache e artefatos de build não devem ser versionados. O diretório `dist/` é somente saída gerada, não fonte.

## Referências

- [Documentação da SyncPay](https://syncpay.apidog.io/llms.txt)
- [SyncPay Developers](https://syncpayments.com.br/desenvolvedores.html)
- `public/qrcode.js`: QR Code Generator de Kazuhiko Arase, licença MIT (aviso no arquivo).
