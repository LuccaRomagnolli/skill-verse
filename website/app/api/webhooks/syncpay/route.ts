import { env } from 'cloudflare:workers';
import { hash, json, readLimited, refreshOrder, validId, type Order } from '@/lib/payments';
async function authenticated(request:Request,raw:string,secret:string) {
  const signature=request.headers.get('x-syncpay-signature');
  if(signature){
    const match=/^t=(\d+),v1=([0-9a-f]{64})$/.exec(signature);if(!match || Math.abs(Math.floor(Date.now()/1000)-Number(match[1]))>300)return false;
    const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(secret),{name:'HMAC',hash:'SHA-256'},false,['verify']);
    const bytes=Uint8Array.from(match[2].match(/../g)!.map(pair=>parseInt(pair,16)));
    return crypto.subtle.verify('HMAC',key,bytes,new TextEncoder().encode(`${match[1]}.${raw}`));
  }
  const authorization=request.headers.get('authorization')??'';
  if(!authorization.startsWith('Bearer '))return false;
  const a=await hash(secret),b=await hash(authorization.slice(7));let diff=0;for(let i=0;i<a.length;i++)diff|=a.charCodeAt(i)^b.charCodeAt(i);return diff===0;
}
export async function POST(request:Request) {
  // Notifications are triggers only; the authenticated transaction API is the authority.
  const expected=env.SYNCPAY_WEBHOOK_TOKEN;if(!expected||!env.DB)return json({error:'Não autorizado.'},401);
  let raw:string;try {raw=await readLimited(request,32768);}catch{return json({error:'Dados inválidos.'},400);}
  if(!await authenticated(request,raw,expected))return json({error:'Não autorizado.'},401);
  let body:{id?:string;transaction?:{reference_id?:string}};try{body=JSON.parse(raw);}catch{return json({error:'Dados inválidos.'},400);}
  const id=body.transaction?.reference_id??body.id;if(!id || !validId(id))return json({error:'Dados inválidos.'},400);
  const order=await env.DB.prepare('SELECT * FROM orders WHERE provider_id = ?').bind(id).first<Order>();
  if(order) await refreshOrder(order,true);
  return json({received:true});
}
