import { env } from 'cloudflare:workers';
import { PRODUCT, callSyncpay, cleanClient, hash, json, loadOrder, orderView, readLimited, ready, sameOrigin, validId, validSecret } from '@/lib/payments';
export async function GET(){ return json({enabled:await ready(),amountCents:PRODUCT.amountCents,methods:['pix', ...(env.SYNCPAY_PUBLIC_KEY?.startsWith('pk_live_') ? ['card'] : [])], publicKey:env.SYNCPAY_PUBLIC_KEY?.startsWith('pk_live_') ? env.SYNCPAY_PUBLIC_KEY : null}); }
export async function POST(request:Request) {
  if (!sameOrigin(request)) return json({error:'Requisição não autorizada.'},403);
  if (!await ready() || !env.DB || !env.SITE_ORIGIN) return json({error:'Pagamento indisponível no momento.'},503);
  let body: {id?:string;accessToken?:string;client?:unknown;product?:string;method?:string;cardToken?:string};
  try { const raw=await readLimited(request,4096); body=JSON.parse(raw); } catch {return json({error:'Dados inválidos.'},400);}
  if (!body.id || !validId(body.id) || !body.accessToken || !validSecret(body.accessToken) || body.product!==PRODUCT.id) return json({error:'Dados inválidos.'},400);
  const method=body.method;
  if(method !== 'pix' && method !== 'card') return json({error:'Forma de pagamento inválida.'},400);
  if(method === 'card' && (!env.SYNCPAY_PUBLIC_KEY?.startsWith('pk_live_') || typeof body.cardToken !== 'string' || !/^card_token\.[A-Za-z0-9_-]{20,500}$/.test(body.cardToken) || !request.headers.get('cf-connecting-ip'))) return json({error:'Pagamento com cartão indisponível ou dados inválidos.'},400);
  const client=cleanClient(body.client); if(!client) return json({error:'Confira nome, e-mail, CPF e telefone.'},422);
  const old=await loadOrder(body.id,body.accessToken); if(old) return json(orderView(old));
  const ip=request.headers.get('cf-connecting-ip')||'unknown'; const ipHash=await hash(`skillverse-rate:${ip}`); const now=Date.now();
  const count=await env.DB.prepare('SELECT COUNT(*) AS n FROM orders WHERE ip_hash = ? AND created_at > ?').bind(ipHash,now-60000).first<{n:number}>();
  if ((count?.n??0)>=5) return json({error:'Aguarde um minuto antes de tentar novamente.'},429);
  const tokenHash=await hash(body.accessToken);
  const inserted=await env.DB.prepare('INSERT OR IGNORE INTO orders (id, token_hash, ip_hash, product, amount_cents, email, method, status, created_at, checked_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)').bind(body.id,tokenHash,ipHash,PRODUCT.id,PRODUCT.amountCents,client.email,method,'creating',now).run();
  if(!inserted.meta.changes) { const found=await loadOrder(body.id,body.accessToken);return found?json(orderView(found)):json({error:'Pedido indisponível.'},409); }
  try {
    const common={amount:PRODUCT.amountCents/100,description:`${PRODUCT.name} ${body.id}`,webhook_url:`${env.SITE_ORIGIN}/api/webhooks/syncpay`};
    const payload=method==='pix' ? {...common,client} : {...common,installments:1,card:{token:body.cardToken},client:{name:client.name,email:client.email,phone:`55${client.phone}`,document:{type:'cpf',number:client.cpf}},device:{ip:request.headers.get('cf-connecting-ip'),user_agent:(request.headers.get('user-agent')||'').slice(0,512),page_url:`${env.SITE_ORIGIN}/`,metadata:{order_id:body.id}}};
    const response=await callSyncpay(method==='pix'?'/cash-in':'/credit-card',{method:'POST',body:JSON.stringify(payload)});
    if(response.status===422) {await env.DB.prepare("UPDATE orders SET status = 'failed' WHERE id = ?").bind(body.id).run();return json({error:'A SyncPay não aceitou os dados informados. Revise-os antes de criar outro pedido.'},422);}
    if(!response.ok) throw new Error('syncpay_charge_failed');
    const data=await response.json() as {identifier?:string;pix_code?:string;data?:{transaction_id?:string}};
    const identifier=method==='pix'?data.identifier:data.data?.transaction_id;
    if(typeof identifier!=='string'||!validId(identifier)) throw new Error('syncpay_invalid_charge');
    const pixCode=typeof data.pix_code==='string' && data.pix_code.length>=20 && data.pix_code.length<=1000 ? data.pix_code : null;
    await env.DB.prepare("UPDATE orders SET provider_id = ?, pix_code = ?, status = 'pending' WHERE id = ?").bind(identifier,pixCode,body.id).run();
    return json(orderView((await loadOrder(body.id,body.accessToken))!));
  } catch {
    await env.DB.prepare("UPDATE orders SET status = 'unknown' WHERE id = ? AND status = 'creating'").bind(body.id).run();
    return json({id:body.id,status:'unknown',error:'Não foi possível confirmar a criação da cobrança. Consulte o suporte antes de tentar novamente.'},502);
  }
}
