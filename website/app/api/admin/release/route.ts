import { env } from 'cloudflare:workers';
import { json, hash } from '@/lib/payments';
export async function POST(request:Request) {
  // This endpoint uploads a released pack to private storage. Never accepts a path from the caller.
  const configured=env.RELEASE_UPLOAD_TOKEN;
  const authorization=request.headers.get('authorization')??'';
  const supplied=authorization.startsWith('Bearer ')?authorization.slice(7):'';
  if(!configured || configured.length<32 || !supplied) return json({error:'Não autorizado.'},401);
  const a=await hash(configured), b=await hash(supplied);let diff=0;for(let i=0;i<a.length;i++) diff|=a.charCodeAt(i)^b.charCodeAt(i);
  if(diff!==0 || !env.BUCKET || !env.PACK_OBJECT_KEY) return json({error:'Não autorizado.'},401);
  const size=Number(request.headers.get('content-length'));
  if(!Number.isSafeInteger(size)||size<4||size>20*1024*1024) return json({error:'Arquivo inválido ou maior que 20 MB.'},413);
  if(!request.body) return json({error:'Arquivo inválido.'},400);
  const reader=request.body.getReader();const chunks:Uint8Array[]=[];let total=0;
  for (;;) { const {done,value}=await reader.read(); if(done) break; total+=value.byteLength; if(total>size || total>20*1024*1024) {await reader.cancel(); return json({error:'Arquivo maior que o permitido.'},413);} chunks.push(value); }
  if(total!==size) return json({error:'Tamanho do arquivo inválido.'},400);
  const bytes=new Uint8Array(total);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
  if(bytes[0]!==0x50||bytes[1]!==0x4b||bytes[2]!==0x03||bytes[3]!==0x04) return json({error:'Envie um arquivo ZIP válido.'},400);
  const saved=await env.BUCKET.put(env.PACK_OBJECT_KEY,bytes,{onlyIf:new Headers({'If-None-Match':'*'}),httpMetadata:{contentType:'application/zip'}});
  if(!saved) return json({error:'Já existe um arquivo para esta versão.'},409);
  return json({uploaded:true,size});
}
