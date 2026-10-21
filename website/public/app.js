const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const normalize = value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const areas = [
  ['Projeto e obra','projeto-e-obra'],
  ['CAD e BIM','cad-e-bim'],
  ['Orçamento e suprimentos','orcamento-e-suprimentos'],
  ['Normas e documentação','normas-e-documentacao']
];
const slugArea = new Map(areas.map(([name,slug])=>[slug,name]));
const packageSpec = 'github:LuccaRomagnolli/skill-verse#mcpcad-catalog';
let catalog = [];
let selected;
try { selected = new Set(JSON.parse(localStorage.getItem('mcpcad-selection') || '[]')); } catch { selected = new Set(); }
let agent = 'claude';
let gridView = localStorage.getItem('mcpcad-view') !== 'list';
let sortBy = 'suggested';
let detailTab = 'terminal';
const titleFor = type => type === 'skill' ? 'Skill' : 'MCP';
const hrefFor = item => `/${item.type === 'skill' ? 'skills' : 'mcps'}/${item.id}/`;
const commitHash = /^[a-f0-9]{7,64}$/i;
function versionLabel(version) {
  const value = String(version ?? '');
  return commitHash.test(value) ? `commit ${value.slice(0, 7)}` : value.startsWith('v') ? value : `v${value}`;
}
function route() {
  const parts = location.pathname.split('/').filter(Boolean);
  const query = new URLSearchParams(location.search);
  if (parts[0] === 'disclaimer') return {kind:'disclaimer'};
  if ((parts[0] === 'skills' || parts[0] === 'mcps') && parts[1]) return {kind:'detail',type:parts[0] === 'skills' ? 'skill':'mcp',id:parts[1]};
  if (parts[0] === 'areas') return {kind:'catalog',type:query.get('type') || 'all',area:slugArea.get(parts[1]) || ''};
  return {kind:'catalog',type:parts[0] === 'skills' ? 'skill':parts[0] === 'mcps' ? 'mcp':'all',area:slugArea.get(query.get('area')) || ''};
}
function navigate(href) {
  history.pushState({},'',href);
  renderPage();
  if(location.hash) document.querySelector(location.hash)?.scrollIntoView();
  else window.scrollTo({top:0,behavior:'instant'});
  closeSidebar();
}
function commandFor(items) {
  const skills = items.filter(item=>item.type==='skill').map(item=>item.id);
  const mcps = items.filter(item=>item.type==='mcp').map(item=>item.id);
  const flags = [skills.length ? `--skills ${skills.join(',')}` : '',mcps.length ? `--mcps ${mcps.join(',')}` : '',`--target ${agent}`,`--scope ${$('input[name="scope"]:checked').value}`].filter(Boolean).join(' ');
  return `npx --yes --package=${packageSpec} mcpcad ${flags}`;
}
function saveSelection() {
  localStorage.setItem('mcpcad-selection',JSON.stringify([...selected]));
  renderDrawer();
  const r = route();
  if (r.kind === 'detail') renderDetail(catalog.find(x=>x.id===r.id && x.type===r.type));
  else if (r.kind === 'catalog') renderCatalog(r);
}
function card(item) {
  const added = selected.has(item.id);
  const version = versionLabel(item.version);
  return `<article class="tool-card"><div class="card-top"><a href="${hrefFor(item)}" data-link>${esc(item.name)}</a><span class="type-badge">${titleFor(item.type)}</span></div><p>${esc(item.summary)}</p><div class="card-footer"><span class="version-pill" title="${esc(item.version)}">${esc(version)}</span><button type="button" class="card-add ${added?'added':''}" data-add="${esc(item.id)}"><span aria-hidden="true">${added?'✓':'+'}</span>${added?'Adicionado':'Adicionar'}</button></div></article>`;
}
function renderCatalog(r) {
  document.title = `${r.area || (r.type==='skill'?'Skills':r.type==='mcp'?'MCPs':'Biblioteca')} — MCPcad`;
  const base = catalog.filter(item=>r.type==='all'||item.type===r.type);
  const list = base.filter(item=>!r.area||item.area===r.area);
  const q = normalize($('#search').value.trim());
  let shown = list.filter(item=>normalize([item.name,item.summary,item.area,item.id,item.software].join(' ')).includes(q));
  if(sortBy==='az') shown=[...shown].sort((a,b)=>a.name.localeCompare(b.name,'pt-BR'));
  const heading=r.area || (r.type==='skill'?'Skills':r.type==='mcp'?'MCPs':'Ferramentas para engenharia');
  const description=r.area?`${list.length} ferramentas para esta etapa do trabalho. Selecione as que fazem sentido para o seu projeto.`:r.type==='skill'?'Instruções, referências e scripts para orientar o trabalho de engenharia no seu agente.':r.type==='mcp'?'Conexões para levar o agente aos softwares e às fontes técnicas do seu fluxo.':'Skills e conexões MCP para projeto, CAD, BIM, orçamento e documentação. Escolha o que precisa e instale no seu agente.';
  const filters=[['Todas',null],...areas].map(([name,slug])=>{const value=slug ?? '';const count=value?base.filter(x=>x.area===name).length:base.length;const active=slug ? r.area===name : !r.area;return `<button type="button" data-filter="${esc(value)}" class="${active?'active':''}" aria-pressed="${active}">${esc(name)} <span>${count}</span></button>`}).join('');
  let groups='';
  if(!shown.length) groups='<div class="no-results">Nenhuma ferramenta encontrada. <button type="button" id="clear-search">Limpar busca</button></div>';
  else if(r.area||q){groups=`<section class="group"><h2 class="group-heading">${esc(r.area||'Resultados')} <span>${shown.length}</span></h2><div class="card-grid ${gridView?'':'list'}">${shown.map(card).join('')}</div></section>`}
  else groups=areas.map(([name])=>{const group=shown.filter(item=>item.area===name);return group.length?`<section class="group"><h2 class="group-heading">${esc(name)} <span>${group.length}</span></h2><div class="card-grid ${gridView?'':'list'}">${group.map(card).join('')}</div></section>`:''}).join('');
  $('#catalog-view').innerHTML=`<div class="catalog-intro"><h1>${esc(heading)}</h1><p>${esc(description)}</p></div><div class="catalog-controls"><label class="sort-label">Ordenar por <select id="sort-select" aria-label="Ordenar ferramentas"><option value="suggested" ${sortBy==='suggested'?'selected':''}>Sugeridos</option><option value="az" ${sortBy==='az'?'selected':''}>Nome A–Z</option></select></label><div class="view-switch" role="group" aria-label="Modo de exibição"><button type="button" data-view="grid" class="${gridView?'active':''}" aria-label="Grade" aria-pressed="${gridView}">▦</button><button type="button" data-view="list" class="${gridView?'':'active'}" aria-label="Lista" aria-pressed="${!gridView}">▤</button></div></div><div class="filter-row" role="group" aria-label="Filtrar por área">${filters}</div>${groups}<div class="catalog-note" id="como-instalar">Selecione uma ou mais ferramentas e abra “Sua lista” para copiar o comando de instalação. Resultados de engenharia exigem conferência profissional; conexões MCP dependem do software e dos complementos indicados em cada página.</div>`;
}
function renderDetail(item) {
  if(!item){navigate('/');return}
  document.title=`${item.name} — MCPcad`;
  const typePath=item.type==='skill'?'skills':'mcps';
  const osNames={windows:'Windows',macos:'macOS',linux:'Linux'};
  const software=item.type==='mcp'?`<p class="sublead">Conecta o agente a uma ferramenta externa. Verifique o software, a versão e os complementos antes de usar.</p>`:`<p class="sublead">A skill reúne instruções, referências e scripts. Confira dados e resultados no ambiente técnico correspondente.</p>`;
  const added=selected.has(item.id);
  const steps=item.type==='mcp'?[
    ...(item.post?.todos||[]).map(text=>({text})),
    ...['windows','macos','linux'].flatMap(os=>(item.post?.[os]||[]).map(text=>({text,os:osNames[os]})))
  ]:[];
  const code=commandFor([item]);
  const version = versionLabel(item.version);
  $('#detail-view').innerHTML=`<nav class="detail-breadcrumb" aria-label="Você está aqui"><a href="/" data-link>Biblioteca</a><span>/</span><a href="/${typePath}/" data-link>${item.type==='skill'?'Skills':'MCPs'}</a><span>/</span><strong>${esc(item.id)}</strong></nav><div class="detail-intro"><h1>${esc(item.name)}</h1><p class="lead">${esc(item.summary)}</p>${software}<button type="button" class="outline-button" data-add="${esc(item.id)}">${added?'✓ Adicionado':'+ Adicionar'}</button></div><div class="detail-columns"><div class="detail-content"><section><h2>Instalar só esta ferramenta</h2><div class="detail-tabs" role="group" aria-label="Informações de instalação"><button type="button" data-detail-tab="terminal" class="${detailTab==='terminal'?'active':''}">No terminal</button><button type="button" data-detail-tab="requirements" class="${detailTab==='requirements'?'active':''}">Requisitos</button></div>${detailTab==='terminal'?`<div class="code-panel"><div class="code-head"><span>Execute no terminal — requer Node.js</span><button type="button" id="copy-single">Copiar</button></div><pre>${esc(code)}</pre></div>`:`<div class="detail-example"><strong>Antes de começar</strong><p>${item.type==='mcp'?esc(item.software):'Claude Code ou Codex com acesso à pasta do projeto.'}</p><p>Node.js 20+, Git e acesso ao GitHub para instalar via comando.</p></div>`}<details class="install-guide"><summary>Primeira vez? Veja a instalação passo a passo</summary><div class="guide-body"><ol><li>Instale Node.js 20+ e Git.</li><li>Abra o terminal ${item.type==='skill'?'na pasta do projeto ou em qualquer pasta, conforme o escopo escolhido':'e confira os requisitos do software ao lado'}.</li><li>Copie o comando acima, execute e reinicie o agente.</li><li>Abra “Sua lista” para mudar o agente e o escopo da instalação.</li></ol></div></details></section><section><h2>O que esta ferramenta faz</h2><p class="detail-copy">${esc(item.summary)}</p>${item.example?`<div class="detail-example"><small>Exemplo de pedido</small>“${esc(item.example)}”</div>`:''}${steps.length?`<h2 style="margin-top:32px">Depois de instalar</h2><ul class="detail-copy">${steps.map(step=>`<li>${step.os?`<strong>${step.os}:</strong> `:''}${esc(step.text)}</li>`).join('')}</ul>`:''}</section></div><aside class="detail-meta"><div class="meta-item"><small>Categoria</small><strong>${esc(item.area)}</strong></div><div class="meta-item"><small>Tipo</small><strong>${titleFor(item.type)}</strong></div><div class="meta-item"><small>Versão</small><strong title="${esc(item.version)}">${esc(version)}</strong></div>${item.type==='mcp'?`<div class="meta-item"><small>Sistemas</small><div class="meta-tags">${item.os.map(os=>`<span>${esc(osNames[os]||os)}</span>`).join('')}</div></div><div class="meta-item"><small>Origem</small>${item.upstream==='interno'?'<strong>MCPcad</strong>':`<a href="${esc(item.upstream)}" target="_blank" rel="noopener noreferrer">Ver projeto original ↗</a>`}</div>`:''}<p class="detail-warning">${item.type==='mcp'?'O registro do servidor não comprova a conexão com o aplicativo. Faça uma leitura de teste no software antes de trabalhar no projeto.':'Revise medidas, fontes e documentos produzidos com apoio do agente.'}</p></aside></div>`;
}
function renderDisclaimer(){document.title='Responsabilidade técnica — MCPcad';$('#disclaimer-view').innerHTML='<div class="disclaimer"><h1>Responsabilidade técnica</h1><p>As ferramentas MCPcad auxiliam profissionais de engenharia. Elas não substituem responsabilidade técnica, conferência no software, validação das fontes e revisão de documentos, desenhos ou modelos.</p><p>Normas ABNT protegidas não são distribuídas. Consulte a edição e os itens aplicáveis em sua cópia licenciada.</p><a class="outline-button" href="/" data-link>Voltar à biblioteca</a></div>'}
function updateSidebar(r){document.querySelectorAll('[data-nav-area]').forEach(el=>el.classList.toggle('active',el.dataset.navArea===r.area));document.querySelectorAll('[data-nav-type]').forEach(el=>el.classList.toggle('active',el.dataset.navType===r.type && r.kind==='catalog'))}
function renderPage(){if(!catalog.length)return;const r=route();$('#catalog-view').hidden=r.kind!=='catalog';$('#detail-view').hidden=r.kind!=='detail';$('#disclaimer-view').hidden=r.kind!=='disclaimer';if(r.kind==='catalog')renderCatalog(r);else if(r.kind==='detail')renderDetail(catalog.find(x=>x.id===r.id&&x.type===r.type));else renderDisclaimer();updateSidebar(r)}
function renderDrawer(){const items=[...selected].map(id=>catalog.find(x=>x.id===id)).filter(Boolean);$('#list-count').textContent=items.length;$('#drawer-count').textContent=items.length;$('#selected-items').innerHTML=items.length?items.map(item=>`<div class="selected-row"><span>${esc(item.name)}</span><small>${titleFor(item.type)}</small><button type="button" data-remove="${esc(item.id)}" aria-label="Remover ${esc(item.name)}">×</button></div>`).join(''):'<p class="selected-empty">Sua lista está vazia. Adicione ferramentas ao catálogo.</p>';$('#command-block').textContent=items.length?commandFor(items):'Adicione ferramentas para gerar o comando.';$('#copy-command').disabled=!items.length;document.querySelectorAll('[data-agent]').forEach(button=>button.classList.toggle('active',button.dataset.agent===agent))}
function openDrawer(){closeSidebar();$('#drawer').classList.add('open');$('#drawer').inert=false;$('#drawer').setAttribute('aria-hidden','false');$('#overlay').hidden=false;$('#close-list').focus()}
function closeDrawer(){if(!$('#drawer').classList.contains('open'))return;$('#drawer').classList.remove('open');$('#drawer').inert=true;$('#drawer').setAttribute('aria-hidden','true');$('#overlay').hidden=true;$('#open-list').focus()}
function closeSidebar(){$('#sidebar').classList.remove('open');$('#menu-toggle').setAttribute('aria-expanded','false');if(!$('#drawer').classList.contains('open'))$('#overlay').hidden=true}
async function copy(text,button){try{await navigator.clipboard.writeText(text);button.textContent='Copiado ✓';setTimeout(()=>{button.textContent='Copiar'},1600)}catch{button.textContent='Selecione o comando para copiar'}}
document.addEventListener('click',event=>{
  const link=event.target.closest('a[data-link]');if(link&&link.origin===location.origin){event.preventDefault();navigate(link.pathname+link.search+link.hash);return}
  const add=event.target.closest('[data-add]');if(add){selected.has(add.dataset.add)?selected.delete(add.dataset.add):selected.add(add.dataset.add);saveSelection();return}
  const remove=event.target.closest('[data-remove]');if(remove){selected.delete(remove.dataset.remove);saveSelection();return}
  const filter=event.target.closest('[data-filter]');if(filter){const r=route(),area=filter.dataset.filter;let url=r.type==='skill'?'/skills/':r.type==='mcp'?'/mcps/':'/';if(area)url+=`?area=${area}`;navigate(url);return}
  const view=event.target.closest('[data-view]');if(view){gridView=view.dataset.view==='grid';localStorage.setItem('mcpcad-view',gridView?'grid':'list');renderPage();return}
  const agentButton=event.target.closest('[data-agent]');if(agentButton){agent=agentButton.dataset.agent;renderDrawer();if(route().kind==='detail')renderPage();return}
  const tab=event.target.closest('[data-detail-tab]');if(tab){detailTab=tab.dataset.detailTab;renderPage();return}
  if(event.target.id==='copy-single'){const r=route(),item=catalog.find(x=>x.id===r.id&&x.type===r.type);if(item)copy(commandFor([item]),event.target)}
  if(event.target.id==='clear-search'){$('#search').value='';renderPage()}
});
document.addEventListener('change',event=>{if(event.target.id==='sort-select'){sortBy=event.target.value;renderPage()}if(event.target.name==='scope'){renderDrawer();if(route().kind==='detail')renderPage()}});
$('#search').addEventListener('input',()=>{const r=route();if(r.kind!=='catalog')history.pushState({},'','/');renderPage()});
$('#search').addEventListener('keydown',event=>{if(event.key==='Escape'){$('#search').value='';renderPage()}});
$('#open-list').addEventListener('click',openDrawer);$('#close-list').addEventListener('click',closeDrawer);$('#overlay').addEventListener('click',()=>{closeDrawer();closeSidebar()});$('#remove-all').addEventListener('click',()=>{selected.clear();saveSelection()});$('#copy-command').addEventListener('click',event=>copy($('#command-block').textContent,event.target));$('#menu-toggle').addEventListener('click',()=>{if(matchMedia('(max-width:780px)').matches){const open=!$('#sidebar').classList.contains('open');$('#sidebar').classList.toggle('open',open);$('#menu-toggle').setAttribute('aria-expanded',String(open));$('#overlay').hidden=!open}else{document.body.classList.toggle('sidebar-collapsed');$('#menu-toggle').setAttribute('aria-expanded',String(!document.body.classList.contains('sidebar-collapsed')))}});
addEventListener('keydown',event=>{if(event.key==='Escape'){closeDrawer();closeSidebar()}if((event.key==='k'&&(event.metaKey||event.ctrlKey))||(event.key==='/'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName))){event.preventDefault();$('#search').focus()}});
addEventListener('popstate',renderPage);
fetch('/catalog.json').then(response=>{if(!response.ok)throw new Error('catálogo indisponível');return response.json()}).then(items=>{catalog=items;selected=new Set([...selected].filter(id=>catalog.some(item=>item.id===id)));for(const [name] of areas)document.querySelectorAll('[data-area-count]').forEach(el=>{if(el.dataset.areaCount===name)el.textContent=catalog.filter(item=>item.area===name).length});for(const type of ['skill','mcp'])$(`[data-type-count="${type}"]`).textContent=catalog.filter(item=>item.type===type).length;renderPage();renderDrawer()}).catch(()=>{$('#catalog-view').innerHTML='<p class="no-results">Não foi possível carregar o catálogo. Atualize a página.</p>'});
