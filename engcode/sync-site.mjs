#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const source=path.join(root,'engcode/catalog.json');
const target=path.join(root,'website/public/catalog.json');
const items=JSON.parse(fs.readFileSync(source,'utf8'));
const keys=new Set();
for(const item of items){
  const key=`${item.type}:${item.id}`;
  if(keys.has(key))throw new Error(`Item duplicado: ${key}`);
  keys.add(key);
  if(!item.name||!item.summary||!['skill','mcp'].includes(item.type))throw new Error(`Item incompleto: ${key}`);
  if(item.type==='skill'&&!fs.existsSync(path.join(root,item.path,'SKILL.md')))throw new Error(`Skill ausente: ${item.path}`);
  if(item.type==='mcp'&&!fs.existsSync(path.join(root,'mcps',item.id,'mcp.yaml')))throw new Error(`MCP ausente: ${item.id}`);
}
const data=JSON.stringify(items,null,2)+'\n';
if(process.argv.includes('--check')){
  if(!fs.existsSync(target)||fs.readFileSync(target,'utf8')!==data)throw new Error('website/public/catalog.json está desatualizado. Rode node engcode/sync-site.mjs.');
  console.log(`${items.length} itens sincronizados`);
}else{fs.writeFileSync(target,data);console.log(`${items.length} itens enviados ao site`)}
