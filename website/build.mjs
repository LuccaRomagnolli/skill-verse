import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const dist=path.join(root,'dist');
const template=fs.readFileSync(path.join(root,'index.html'),'utf8');
const items=JSON.parse(fs.readFileSync(path.join(root,'public/catalog.json'),'utf8'));
const origin='https://engcode.adoredmochi2.chatgpt.site';
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const routes=[['/','MCPcad — Ferramentas para engenharia','Skills e conexões MCP para projetos de engenharia.'],['/skills/','Skills — MCPcad','Skills de engenharia para Claude Code e Codex.'],['/mcps/','MCPs — MCPcad','Conexões MCP para softwares e fontes técnicas de engenharia.'],['/disclaimer/','Responsabilidade técnica — MCPcad','Limites e responsabilidade técnica no uso das ferramentas MCPcad.']];
for(const [name,slug] of [['Projeto e obra','projeto-e-obra'],['CAD e BIM','cad-e-bim'],['Orçamento e suprimentos','orcamento-e-suprimentos'],['Normas e documentação','normas-e-documentacao']])routes.push([`/areas/${slug}/`,`${name} — MCPcad`,`Ferramentas MCPcad para ${name.toLowerCase()}.`]);
for(const item of items)routes.push([`/${item.type==='skill'?'skills':'mcps'}/${item.id}/`,`${item.name} — MCPcad`,item.summary]);
fs.rmSync(dist,{recursive:true,force:true});fs.mkdirSync(dist,{recursive:true});
for(const [url,title,description] of routes){const dir=path.join(dist,url);fs.mkdirSync(dir,{recursive:true});const html=template.replaceAll('%%TITLE%%',esc(title)).replaceAll('%%DESCRIPTION%%',esc(description)).replaceAll('%%CANONICAL%%',origin+url);fs.writeFileSync(path.join(dir,'index.html'),html)}
for(const name of ['app.js','styles.css','catalog.json','favicon.svg','_headers'])fs.copyFileSync(path.join(root,'public',name),path.join(dist,name));
console.log(`MCPcad: ${items.length} ferramentas, ${routes.length} páginas estáticas.`);
