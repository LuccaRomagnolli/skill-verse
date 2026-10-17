import { env } from 'cloudflare:workers';

export const PRODUCT = { id: 'engenharia-civil', amountCents: 3990, name: 'Pack Engenharia Civil' } as const;
const API = 'https://api.syncpayments.com.br/api/partner/v1';
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const secretPattern = /^[A-Za-z0-9_-]{43}$/;
export type Order = { id:string; token_hash:string; ip_hash:string; product:string; amount_cents:number; email:string; method:string; status:string; provider_id:string|null; pix_code:string|null; created_at:number; checked_at:number };
let bearer: { value: string; expires: number } | undefined;
let pendingToken: Promise<string> | undefined;
export function json(data: unknown, status = 200) { return Response.json(data, { status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } }); }
export async function readLimited(request:Request, limit:number) {
  const declared=Number(request.headers.get('content-length')||0);if(declared>limit)throw new Error('body_too_large');
  if(!request.body)return '';const reader=request.body.getReader();const decoder=new TextDecoder();let raw='',size=0;
  for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>limit){await reader.cancel();throw new Error('body_too_large');}raw+=decoder.decode(value,{stream:true});}
  return raw+decoder.decode();
}
export function sameOrigin(request: Request) { return request.headers.get('origin') === new URL(request.url).origin; }
export async function hash(value: string) { const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value)); return Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, '0')).join(''); }
export function validId(value:string) { return uuid.test(value); }
export function validSecret(value:string) { return secretPattern.test(value); }
export function isCPF(value:string) { if (!/^\d{11}$/.test(value) || /^(\d)\1{10}$/.test(value)) return false; for (let n=9;n<11;n++) { let sum=0; for (let i=0;i<n;i++) sum+=Number(value[i])*(n+1-i); const digit=(sum*10%11)%10; if (digit!==Number(value[n])) return false; } return true; }
export function cleanClient(input: unknown) {
  if (!input || typeof input !== 'object') return null;
  const c = input as Record<string, unknown>;
  if (typeof c.name !== 'string' || typeof c.email !== 'string' || typeof c.cpf !== 'string' || typeof c.phone !== 'string') return null;
  const name=c.name.trim(), email=c.email.trim().toLowerCase(), cpf=c.cpf.replace(/\D/g,''), phone=c.phone.replace(/\D/g,'').replace(/^55(?=\d{10,11}$)/,'');
  if (name.length < 3 || name.length > 100 || !/^[^\s@]{1,64}@[^\s@.]+(?:\.[^\s@.]+)+$/.test(email) || email.length > 254 || !isCPF(cpf) || !/^[1-9]\d{9,10}$/.test(phone)) return null;
  return { name, email, cpf, phone };
}
export async function ready() {
  if (env.PAYMENTS_ENABLED !== 'true' || !env.DB || !env.BUCKET || !env.PACK_OBJECT_KEY || !env.SYNCPAY_CLIENT_ID || !env.SYNCPAY_CLIENT_SECRET || !env.SYNCPAY_WEBHOOK_TOKEN || !env.SITE_ORIGIN) return false;
  try { const origin=new URL(env.SITE_ORIGIN); if (origin.protocol !== 'https:' || origin.origin !== env.SITE_ORIGIN) return false; return !!(await env.BUCKET.head(env.PACK_OBJECT_KEY)); } catch { return false; }
}
async function token(force=false):Promise<string> {
  if (!force && bearer && Date.now() < bearer.expires) return bearer.value;
  if (pendingToken) return pendingToken;
  pendingToken = (async () => {
    const response = await fetch(`${API}/auth-token`, { method:'POST', headers:{'Content-Type':'application/json','Accept':'application/json'}, body:JSON.stringify({client_id:env.SYNCPAY_CLIENT_ID,client_secret:env.SYNCPAY_CLIENT_SECRET}) });
    if (!response.ok) throw new Error('syncpay_auth_failed');
    const data = await response.json() as {access_token?:string;expires_in?:number};
    if (typeof data.access_token !== 'string' || !data.access_token) throw new Error('syncpay_invalid_auth');
    bearer = {value:data.access_token, expires:Date.now()+Math.max(0,Math.min(Number(data.expires_in)||3600,3600)-60)*1000};
    return bearer.value;
  })();
  try { return await pendingToken; } finally { pendingToken = undefined; }
}
export async function callSyncpay(path:string, init:RequestInit={}) {
  let access=await token();
  const send=()=>fetch(`${API}${path}`, {...init, headers:{'Accept':'application/json','Content-Type':'application/json','Authorization':`Bearer ${access}`}});
  let response=await send();
  if(response.status===401) { bearer=undefined; access=await token(true); response=await send(); }
  return response;
}
export async function loadOrder(id:string, secret:string) {
  if (!env.DB || !validId(id) || !validSecret(secret)) return null;
  const row=await env.DB.prepare('SELECT * FROM orders WHERE id = ? AND token_hash = ?').bind(id,await hash(secret)).first<Order>();
  return row ?? null;
}
export async function refreshOrder(order:Order, force=false):Promise<Order> {
  if (!order.provider_id || !env.DB) return order;
  const now=Date.now();
  if(!force && now-order.checked_at < 12000) return order;
  const claimed=await env.DB.prepare('UPDATE orders SET checked_at = ? WHERE id = ? AND checked_at = ?').bind(now,order.id,order.checked_at).run();
  if (!claimed.meta.changes) return (await env.DB.prepare('SELECT * FROM orders WHERE id = ?').bind(order.id).first<Order>()) ?? order;
  try {
    const response=await callSyncpay(`/transaction/${encodeURIComponent(order.provider_id)}`);
    if (!response.ok) return {...order,checked_at:now};
    const payload=await response.json() as {data?: {reference_id?:string; currency?:string;amount?:number;status?:string;pix_code?:string|null}};
    const data=payload.data;
    if (!data || data.reference_id!==order.provider_id || data.currency!=='BRL' || typeof data.amount!=='number' || Math.round(data.amount*100)!==order.amount_cents || !['pending','completed','failed','refunded','med'].includes(data.status??'')) return {...order,checked_at:now};
    // A late pending response may not undo an already confirmed or refunded payment.
    const status=data.status!;
    await env.DB.prepare("UPDATE orders SET status = CASE WHEN status IN ('refunded','med') AND ? NOT IN ('refunded','med') THEN status WHEN status = 'completed' AND ? = 'pending' THEN status ELSE ? END, pix_code = COALESCE(?, pix_code) WHERE id = ?").bind(status,status,status,data.pix_code??null,order.id).run();
    return (await env.DB.prepare('SELECT * FROM orders WHERE id = ?').bind(order.id).first<Order>()) ?? order;
  } catch { return {...order,checked_at:now}; }
}
export function orderView(order:Order) { return {id:order.id,status:order.status,pixCode:order.status==='pending'?order.pix_code:null, amountCents:order.amount_cents,product:PRODUCT.name,method:order.method}; }
