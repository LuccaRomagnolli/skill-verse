import { env } from 'cloudflare:workers';
import { callSyncpay, json, loadOrder, refreshOrder } from '@/lib/payments';
export async function GET(request:Request,{params}:{params:Promise<{id:string}>}) {
  const {id}=await params; const secret=request.headers.get('authorization')?.replace(/^Bearer /,'')??'';
  const order=await loadOrder(id,secret); if(!order) return json({error:'Pedido não encontrado.'},404);
  if (!order.provider_id || order.status !== 'completed') return json({error:'O pagamento ainda não foi confirmado.'},403);
  let verified=false;
  try { const response=await callSyncpay(`/transaction/${encodeURIComponent(order.provider_id)}`); if(response.ok) { const data=(await response.json() as {data?:{reference_id?:string;currency?:string;amount?:number;status?:string}}).data; verified=!!data && data.reference_id===order.provider_id && data.currency==='BRL' && typeof data.amount==='number' && Math.round(data.amount*100)===order.amount_cents && data.status==='completed'; } } catch {}
  if(!verified) { await refreshOrder(order,true); return json({error:'Não foi possível confirmar o pagamento para liberar o download.'},503); }
  const checked=await refreshOrder(order);
  if(checked.status!=='completed') return json({error:'O pagamento ainda não foi confirmado.'},403);
  if(!env.BUCKET||!env.PACK_OBJECT_KEY) return json({error:'O arquivo está indisponível.'},503);
  const object=await env.BUCKET.get(env.PACK_OBJECT_KEY); if(!object) return json({error:'O arquivo está indisponível.'},503);
  return new Response(object.body,{headers:{'content-type':'application/zip','content-disposition':'attachment; filename="skillverse-engenharia-civil.zip"','cache-control':'private, no-store','x-content-type-options':'nosniff'}});
}
