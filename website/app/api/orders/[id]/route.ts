import { json, loadOrder, orderView, refreshOrder } from '@/lib/payments';
export async function GET(request:Request,{params}:{params:Promise<{id:string}>}) {
  const {id}=await params; const secret=request.headers.get('authorization')?.replace(/^Bearer /,'')??'';
  const order=await loadOrder(id,secret); if(!order) return json({error:'Pedido não encontrado.'},404);
  return json(orderView(await refreshOrder(order)));
}
