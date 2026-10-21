#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const catalog=JSON.parse(fs.readFileSync(path.join(root,'engcode/catalog.json'),'utf8'));
const byId=new Map(catalog.map(x=>[x.id,x]));
const args=process.argv.slice(2);
const opt=(key,defaultValue='')=>{const i=args.indexOf('--'+key);return i<0?defaultValue:args[i+1]||''};
const flag=key=>args.includes('--'+key);
const exit=(message,code=1)=>{console.error(message);process.exit(code)};
const selected={skill:(opt('skills')||opt('skill')).split(',').filter(Boolean),mcp:(opt('mcps')||opt('mcp')).split(',').filter(Boolean)};
const target=opt('target','claude');
const scope=opt('scope','user');
const dry=flag('dry-run');
const home=os.homedir();
const project=process.cwd();
const data=path.join(home,'.engcode');
const system=process.platform;
function command(binary,argv,options={}){
  if(dry){console.log('  $',binary,...argv);return}
  const result=spawnSync(binary,argv,{stdio:'inherit',shell:false,...options});
  if(result.error||result.status!==0)throw new Error(`${binary} falhou: ${result.error?.message||`código ${result.status}`}`);
}
function available(binary){return spawnSync(binary,['--version'],{stdio:'ignore',shell:false}).status===0}
function copyTree(src,dst,id){
  if(fs.existsSync(dst)){
    const marker=path.join(dst,'.engcode.json');
    if(fs.existsSync(marker)&&JSON.parse(fs.readFileSync(marker,'utf8')).id===id){console.log(`  • ${id}: já instalado em ${dst}`);return}
    throw new Error(`Destino já existe e foi preservado: ${dst}`);
  }
  console.log(`  • ${id} → ${dst}`);
  if(!dry){fs.mkdirSync(path.dirname(dst),{recursive:true});fs.cpSync(src,dst,{recursive:true});fs.writeFileSync(path.join(dst,'.engcode.json'),JSON.stringify({id,installedAt:new Date().toISOString()})+'\n')}
}
function addCodex(id,srv){
  const cfg=path.join(scope==='project'?path.join(project,'.codex'):(process.env.CODEX_HOME||path.join(home,'.codex')),'config.toml');
  const name='engcode-'+id;
  const old=fs.existsSync(cfg)?fs.readFileSync(cfg,'utf8'):'';
  if(old.includes(`[mcp_servers.${name}]`)){console.log(`  • ${name}: já registrado em ${cfg}`);return}
  const q=x=>JSON.stringify(String(x));
  let block=`\n# Engcode: ${id}\n[mcp_servers.${name}]\ncommand = ${q(srv.command)}\nargs = [${srv.args.map(q).join(', ')}]\nstartup_timeout_sec = 120\n`;
  if(Object.keys(srv.env).length){block+=`[mcp_servers.${name}.env]\n`;for(const [k,v] of Object.entries(srv.env))block+=`${k} = ${q(v)}\n`}
  console.log(`  • ${name} → ${cfg}`);
  if(!dry){fs.mkdirSync(path.dirname(cfg),{recursive:true});fs.writeFileSync(cfg,old.replace(/\s*$/,'')+'\n'+block)}
}
function addClaude(id,srv){
  const name='engcode-'+id;
  const s=scope==='project'?'local':'user';
  if(!dry&&!available('claude'))throw new Error('Claude Code CLI não encontrado. Instale Claude Code antes de registrar MCPs.');
  if(!dry&&spawnSync('claude',['mcp','get',name],{stdio:'ignore'}).status===0){console.log(`  • ${name}: já registrado no Claude Code`);return}
  const env=Object.entries(srv.env).flatMap(([k,v])=>['-e',`${k}=${v}`]);
  console.log(`  • ${name} → Claude Code (${s})`);
  command('claude',['mcp','add','--scope',s,name,...env,'--',srv.command,...srv.args]);
}
function gitSource(id,url,sha){
  if(!dry&&!available('git'))throw new Error('Git é necessário para este MCP.');
  const dest=path.join(data,'mcps',id);
  const marker=path.join(dest,'.engcode-source.json');
  if(fs.existsSync(dest)){
    if(fs.existsSync(marker)&&JSON.parse(fs.readFileSync(marker,'utf8')).sha===sha){console.log(`  • ${id}: fonte fixada já presente`);return dest}
    throw new Error(`Fonte existente preservada: ${dest}`);
  }
  console.log(`  • baixar ${url} @ ${sha}`);
  if(!dry){fs.mkdirSync(path.dirname(dest),{recursive:true});command('git',['clone','--quiet',url,dest]);try{command('git',['-C',dest,'checkout','--quiet',sha]);fs.writeFileSync(marker,JSON.stringify({id,sha})+'\n')}catch(e){fs.rmSync(dest,{recursive:true,force:true});throw e}}
  return dest;
}
function installMcp(id){
  const item=byId.get(id);
  const supported=item.os.some(x=>({windows:'win32',macos:'darwin',linux:'linux'}[x]===system));
  if(!supported)throw new Error(`${item.name} exige ${item.os.join(' ou ')}; sistema atual: ${system}`);
  const needUv=['archicad','autocad','solidworks','normas-publicas'].includes(id);
  if(!dry&&needUv&&!available('uv'))throw new Error(`${item.name} exige uv (https://docs.astral.sh/uv/getting-started/installation/)`);
  let srv;
  if(id==='revit'){
    srv=system==='win32'?{command:'cmd',args:['/c','npx','-y','mcp-server-for-revit@1.0.0'],env:{}}:{command:'npx',args:['-y','mcp-server-for-revit@1.0.0'],env:{}};
  }else if(id==='archicad'){
    const rules=path.join(data,'archicad-regras');
    if(!fs.existsSync(rules)){console.log(`  • regras Archicad → ${rules}`);if(!dry){fs.mkdirSync(path.dirname(rules),{recursive:true});fs.cpSync(path.join(root,'catalog/engenharia-civil/archicad-assistente/assets/regras'),rules,{recursive:true})}}
    srv={command:'uvx',args:['--from','archicad-mcp-server==0.8.0','archicad-mcp','--mode','full','--rules-dir',rules],env:{}};
  }else if(id==='autocad'||id==='solidworks'){
    const upstream=id==='autocad'?'https://github.com/puran-water/autocad-mcp':'https://github.com/HarrierPigeon/Solidworks-MCP-Server';
    const src=gitSource(id,upstream,item.version);
    command('uv',['sync','--directory',src]);
    srv=id==='autocad'?{command:'uv',args:['run','--directory',src,'python','-m','autocad_mcp'],env:{AUTOCAD_MCP_BACKEND:system==='win32'?'auto':'ezdxf'}}:{command:'uv',args:['run','--directory',src,'python','server.py'],env:{}};
  }else if(id==='normas-publicas'){
    const src=path.join(data,'mcps',id);
    copyTree(path.join(root,'mcps/normas-publicas/servidor'),src,id);
    const normDir=path.join(data,'normas-publicas');
    const env={NORMAS_DIR:normDir};
    const base=['run','-q','--no-project','--with','pypdf>=4','--with','certifi','python',path.join(src,'normas.py')];
    command('uv',[...base,'catalogo'],{env:{...process.env,...env}});
    command('uv',[...base,'baixar','--padrao'],{env:{...process.env,...env}});
    srv={command:'uv',args:['run','-q','--no-project','--with','mcp[cli]>=1.2,<2','--with','pypdf>=4','--with','certifi','python',path.join(src,'server.py')],env};
  }
  for(const client of target==='both'?['claude','codex']:[target])client==='claude'?addClaude(id,srv):addCodex(id,srv);
  console.log(`  ↳ ${item.software}`);
  const steps=[...(item.post.todos||[]),...(item.post[system==='win32'?'windows':system==='darwin'?'macos':'linux']||[])];
  for(const step of steps)console.log('  ↳ '+step);
}
if(flag('help')||args.length===0){console.log('Engcode — instalação individual de skills e MCPs\n\nUso: engcode --skills id1,id2 --mcps id3 --target claude|codex|both --scope user|project [--dry-run]\n       engcode --list\n\nNenhum pack é necessário. --scope project usa a pasta atual.');process.exit(0)}
if(flag('list')){for(const x of catalog)console.log(`${x.type.padEnd(6)} ${x.id.padEnd(25)} ${x.name}`);process.exit(0)}
if(!['claude','codex','both'].includes(target))exit('--target deve ser claude, codex ou both');
if(!['user','project'].includes(scope))exit('--scope deve ser user ou project');
if(!selected.skill.length&&!selected.mcp.length)exit('Escolha pelo menos uma skill ou um MCP. Use --list para ver os IDs.');
for(const [type,ids] of Object.entries(selected))for(const id of ids){if(!byId.has(id)||byId.get(id).type!==type)exit(`ID ${type} inválido: ${id}`)}
console.log(`Engcode · ${scope==='user'?'todos os projetos':project} · ${target}${dry?' · simulação':''}`);
try{
  for(const id of new Set(selected.skill)){
    const item=byId.get(id);
    const src=path.join(root,item.path);
    for(const client of target==='both'?['claude','codex']:[target]){
      const base=client==='claude'?(scope==='user'?path.join(process.env.CLAUDE_CONFIG_DIR||path.join(home,'.claude'),'skills'):path.join(project,'.claude/skills')):(scope==='user'?path.join(home,'.agents/skills'):path.join(project,'.agents/skills'));
      copyTree(src,path.join(base,id),id);
    }
  }
  for(const id of new Set(selected.mcp))installMcp(id);
  console.log('Concluído. Reinicie o agente para carregar as novas ferramentas. Confirme a conexão no software antes de usar em um projeto real.');
}catch(e){exit('Instalação interrompida: '+e.message)}
