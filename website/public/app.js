const icons = {
 clock:'M12 8v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',
 'arrow-right':'M4 12h16m-6-6 6 6-6 6','arrow-up-right':'M6 18 18 6M6 6h12v12',check:'m5 12 4 4L19 6',bag:'M5 7h14l1 14H4L5 7Zm3 0V5a4 4 0 0 1 8 0v2',menu:'M4 6h16M4 12h16M4 18h16',x:'m6 6 12 12M6 18 18 6',layers:'m12 3 10 5-10 5L2 8l10-5ZM2 12l10 5 10-5M2 16l10 5 10-5',file:'M14 2H5v20h14V7l-5-5Zm0 0v5h5M8 12h8M8 16h6',box:'m12 2 9 5v10l-9 5-9-5V7l9-5ZM3 7l9 5 9-5M12 12v10M7 4.8l10 5.5',terminal:'m5 7 4 5-4 5m8 0h6',puzzle:'M8 3H3v6a3 3 0 1 1 0 6v6h6a3 3 0 1 1 6 0h6v-6a3 3 0 1 0 0-6V3h-6a3 3 0 1 0-6 0H8Z',grid:'M3 3h7v7H3V3Zm11 0h7v7h-7V3ZM3 14h7v7H3v-7Zm11 0h7v7h-7v-7Z',sparkles:'m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3ZM20 2v4M18 4h4',download:'M12 3v12m-5-5 5 5 5-5M4 15v6h16v-6',panel:'M3 4h18v16H3V4Zm6 0v16',search:'M20 20l-5-5M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z',info:'M12 11v6m0-10v1M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',plus:'M12 5v14M5 12h14',trash:'M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7',ruler:'m3 16 13-13 5 5L8 21l-5-5Zm4-4 3 3m1-7 3 3m1-7 3 3',book:'M12 5c-3-2-7-2-10-1v15c3-1 7-1 10 1m0-15c3-2 7-2 10-1v15c-3-1-7-1-10 1V5Z',calculator:'M5 2h14v20H5V2Zm3 3h8v4H8V5Zm0 8h1m3 0h1m3 0h1m-9 4h1m3 0h1m3 0h1',lock:'M5 10h14v12H5V10Zm3 0V6a4 4 0 0 1 8 0v4M12 14v4'
};
const icon = name => `<svg class="icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="${icons[name] || icons.sparkles}"/></svg>`;
function hydrateIcons(root=document){root.querySelectorAll('[data-icon]').forEach(el=>{el.innerHTML=icon(el.dataset.icon);});}
const money = new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'});
const config = window.SKILLVERSE_CONFIG;
document.querySelectorAll('[data-price]').forEach(el=>el.textContent=money.format(config.price));
const skills = [
 {name:'Contexto do projeto',category:'project',label:'Projeto & cálculo',icon:'layers',description:'Organize a ficha persistente da obra: decisões, fontes, artefatos e pendências para retomar o trabalho em outra sessão.',prompt:'Retome este projeto pela ficha e mostre as decisões e pendências antes de avançar.'},
 {name:'Concreto armado',category:'project',label:'Projeto & cálculo',icon:'ruler',description:'Apoio ao cálculo de elementos de concreto armado com scripts. A referência declarada é NBR 6118:2026; a validação integral e a revisão independente permanecem pendentes.',prompt:'Organize os dados e as hipóteses que precisamos revisar antes de dimensionar esta viga.'},
 {name:'Cargas e combinações',category:'project',label:'Projeto & cálculo',icon:'calculator',description:'Estruture o mapa de ações por ambiente e elemento e defina o perfil de combinações antes de avançar no cálculo. Resultados dependem dos dados de entrada e de revisão técnica.',prompt:'Monte o mapa de ações deste pavimento e identifique quais dados ainda faltam.'},
 {name:'Memorial de cálculo',category:'documents',label:'Documentação',icon:'file',description:'Reúna hipóteses, dados, cálculos e resultados em um memorial organizado para revisão e documentação do projeto.',prompt:'Organize o memorial com os cálculos já realizados e destaque os pontos para revisão.'},
 {name:'Quantitativos e SINAPI',category:'project',label:'Projeto & cálculo',icon:'calculator',description:'Apoie o levantamento de quantitativos e o orçamento com uma base SINAPI fornecida para o estado e o mês de referência.',prompt:'Organize os quantitativos da estrutura para orçar com a planilha SINAPI que forneci.'},
 {name:'AutoCAD assistente',category:'software',label:'Softwares · CAD',icon:'ruler',description:'Apoio a desenhos e seções no AutoCAD com conexão compatível. Sem aplicativo operável, o fluxo pode gerar arquivos DXF; isso não equivale a controlar o AutoCAD.',prompt:'Gere o DXF das seções dos pilares a partir dos dados revisados.'},
 {name:'Revit assistente',category:'software',label:'Softwares · BIM',icon:'box',description:'Apoio a operações no Revit por conexão MCP opcional. Requer aplicativo, complemento compatível e conferência do modelo pelo profissional.',prompt:'Liste os níveis e os elementos estruturais do modelo para eu revisar.'},
 {name:'SOLIDWORKS assistente',category:'software',label:'Softwares · CAD',icon:'box',description:'Apoio à modelagem de peças, desenhos e exportações com o SOLIDWORKS em ambiente compatível.',prompt:'Prepare a modelagem de uma chapa de base com as dimensões e os furos que vou informar.'},
 {name:'TQS assistente',category:'software',label:'Softwares · Estruturas',icon:'grid',description:'Diagnóstico do ambiente Python/TQS, leitura de dados do edifício e apoio à comparação de variantes. Operações de processamento exigem confirmação.',prompt:'Confira os pisos, o fck e os cobrimentos do edifício no TQS e liste pendências.'},
 {name:'ArchiCAD BIM check',category:'software',label:'Softwares · BIM',icon:'layers',description:'Apoio à verificação do modelo no ArchiCAD 29 para entrega IFC e organização de pendências em BCF, com conexão opcional compatível.',prompt:'Audite o modelo para exportação IFC e organize as pendências encontradas.'},
 {name:'Consulta a normas',category:'documents',label:'Referências & documentação',icon:'book',description:'Consulte referências e fontes públicas como NRs, DNIT e SINAPI. Textos de normas ABNT protegidos não estão incluídos no pack.',prompt:'Organize um checklist da NR-18 com fonte e item para revisão do canteiro.'},
 {name:'Relatório técnico',category:'documents',label:'Documentação',icon:'file',description:'Estruture relatórios e laudos com as fotos, evidências e anotações fornecidas. O documento deve ser revisado e assumido pelo profissional responsável.',prompt:'Organize um relatório de vistoria com estas fotos e minhas anotações de campo.'}
];
let skillFilter='all';
const normalize = text=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
function renderSkills(){const query=normalize(document.querySelector('#skill-search').value);const filtered=skills.filter(s=>(skillFilter==='all'||s.category===skillFilter)&&normalize(`${s.name} ${s.label} ${s.description}`).includes(query));document.querySelector('#skills-grid').innerHTML=filtered.map(s=>`<button class="skill-card" data-skill="${skills.indexOf(s)}"><span class="skill-icon">${icon(s.icon)}</span><span><strong>${s.name}</strong><small>${s.label}</small></span>${icon('arrow-up-right')}</button>`).join('');document.querySelector('.search-empty').hidden=filtered.length>0;}
document.querySelector('#skill-search').addEventListener('input',renderSkills);
document.querySelectorAll('[data-skill-filter]').forEach(button=>button.addEventListener('click',()=>{skillFilter=button.dataset.skillFilter;setActive('[data-skill-filter]',button);renderSkills();}));
function setActive(selector,button){document.querySelectorAll(selector).forEach(el=>{el.classList.toggle('active',el===button);el.setAttribute('aria-pressed',String(el===button));});}
document.querySelectorAll('[data-pack-filter]').forEach(button=>button.addEventListener('click',()=>{setActive('[data-pack-filter]',button);document.querySelectorAll('[data-pack]').forEach(card=>card.hidden=button.dataset.packFilter!=='all'&&card.dataset.pack!==button.dataset.packFilter);}));
let lastFocus=null;
function showDialog(dialog){const previous=document.querySelector('dialog[open]');lastFocus=previous?lastFocus:document.activeElement;if(previous)previous.close();dialog.showModal();document.body.style.overflow='hidden';}
function closeDialog(dialog){dialog.close();document.body.style.overflow='';if(lastFocus?.isConnected)lastFocus.focus();}
document.querySelectorAll('dialog').forEach(dialog=>{dialog.querySelector('.dialog-close').addEventListener('click',()=>closeDialog(dialog));dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)closeDialog(dialog);}});dialog.addEventListener('cancel',event=>{event.preventDefault();closeDialog(dialog);});});
function info(title,content){document.querySelector('#info-title').textContent=title;document.querySelector('#info-content').innerHTML=content;showDialog(document.querySelector('#info-dialog'));}
document.querySelector('#skills-grid').addEventListener('click',event=>{const button=event.target.closest('[data-skill]');if(!button)return;const skill=skills[Number(button.dataset.skill)];info(skill.name,`<p>${skill.description}</p><p><strong>Um exemplo de como começar:</strong></p><p class="prompt-example">“${skill.prompt}”</p><p>Incluída no Pack Engenharia Civil. Exemplo ilustrativo; a execução acontece no agente instalado.</p><button class="button button-dark" data-open-pack>Conhecer o pack ${icon('arrow-right')}</button>`);});
document.addEventListener('click',event=>{if(event.target.closest('[data-open-pack]'))showDialog(document.querySelector('#product-dialog'));});
document.querySelector('#view-skills').addEventListener('click',()=>{closeDialog(document.querySelector('#product-dialog'));document.querySelector('#skills').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});});
document.querySelector('[data-upcoming]').addEventListener('click',()=>info('Um novo capítulo para ensinar.', '<p>O pack Professores é o próximo nicho previsto no catálogo SkillVerse. O conteúdo ainda está em preparação e não está disponível para compra.</p><p>O preço previsto para o pack completo é <strong>R$ 39,90</strong>. As skills e os requisitos serão apresentados aqui quando forem definidos.</p>'));
document.querySelector('[data-privacy]').addEventListener('click',()=>info('Privacidade, com clareza.', '<p>Para processar um pedido, solicitamos nome, e-mail, CPF e telefone e os enviamos à SyncPay. O cartão é tokenizado diretamente pela SyncPay. Guardamos o e-mail e dados do pedido para acompanhar o pagamento; o carrinho e o acesso ao pedido ficam neste navegador. Você pode guardar um código pessoal para acessá-lo em outro navegador; ele não é enviado automaticamente por e-mail.</p><p>Não adicionamos rastreadores de publicidade ou analytics. As fontes são servidas pelo Google Fonts, que pode receber dados técnicos da conexão, como endereço IP.</p><p>Os dados do pagamento são tratados pela SyncPay segundo seus termos e sua política de privacidade. O site não armazena o número ou o código de segurança do cartão.</p>'));
let inCart=false;try{inCart=localStorage.getItem('skillverse-cart')==='engineering';}catch{}
function persistCart(){try{inCart?localStorage.setItem('skillverse-cart','engineering'):localStorage.removeItem('skillverse-cart');}catch{}document.querySelector('.cart-count').hidden=!inCart;}
function renderCart(){ window.SkillVerseCheckout.render(); }
document.querySelector('.cart-trigger').addEventListener('click',()=>{renderCart();showDialog(document.querySelector('#cart-dialog'));});
document.querySelector('#add-cart').addEventListener('click',()=>{inCart=true;persistCart();renderCart();showDialog(document.querySelector('#cart-dialog'));});
const demoScenarios={context:{prompt:'Vamos começar um projeto residencial. Me ajude a organizar os dados da obra.',title:'Primeiro, vamos dar contexto ao seu projeto.',answer:'Antes de avançar, a skill organiza as informações e aponta o que ainda precisa ser confirmado.',tasks:['Identificar município, uso e características da obra','Separar decisões, fontes e pendências','Preparar a ficha para retomar o projeto'],file:'projeto-contexto.json',caption:'Exemplo de ficha · dados a preencher'},report:{prompt:'Organize o memorial com os cálculos revisados deste projeto.',title:'Vamos transformar os dados em documentação.',answer:'A skill estrutura o memorial a partir dos dados fornecidos e evidencia os pontos que precisam de revisão.',tasks:['Reunir hipóteses e parâmetros do projeto','Organizar etapas, referências e resultados','Destacar pendências para o responsável técnico'],file:'memorial-de-calculo.docx',caption:'Exemplo de entrega · sujeito à revisão'},bim:{prompt:'Prepare uma revisão do modelo antes da entrega em IFC.',title:'Vamos organizar a conferência do modelo.',answer:'Com o ArchiCAD e a conexão compatível, a skill apoia a verificação e organiza as pendências.',tasks:['Confirmar o ambiente e a versão do modelo','Organizar as verificações para exportação IFC','Reunir pendências para correção e revisão'],file:'pendencias-bim.bcf',caption:'Exemplo de entrega · conexão necessária'}};
function renderDemo(key){const d=demoScenarios[key];document.querySelector('#demo-content').innerHTML=`<div class="demo-user">${d.prompt}</div><div class="demo-agent"><span class="demo-avatar" aria-hidden="true">✳</span><div class="demo-answer"><strong>${d.title}</strong><p>${d.answer}</p>${d.tasks.map(t=>`<div class="demo-task">${icon('check')}<span>${t}</span></div>`).join('')}<div class="demo-file">${icon('file')}<div><strong>${d.file}</strong><small>${d.caption}</small></div>${icon('arrow-up-right')}</div></div></div>`;}
document.querySelectorAll('[data-demo]').forEach(button=>button.addEventListener('click',()=>{setActive('[data-demo]',button);renderDemo(button.dataset.demo);}));
const menuButton=document.querySelector('.menu-trigger');const mobileNav=document.querySelector('.mobile-nav');menuButton.addEventListener('click',()=>{mobileNav.hidden=!mobileNav.hidden;menuButton.setAttribute('aria-expanded',String(!mobileNav.hidden));menuButton.setAttribute('aria-label',mobileNav.hidden?'Abrir menu':'Fechar menu');});mobileNav.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{mobileNav.hidden=true;menuButton.setAttribute('aria-expanded','false');menuButton.setAttribute('aria-label','Abrir menu');}));
hydrateIcons();renderSkills();renderDemo('context');persistCart();

// Keep pointer, touch and keyboard interaction in the same accessible state.
const skillBox = document.querySelector('[data-skill-box]');
const boxToggle = skillBox.querySelector('.box-toggle');
const boxBenefits = document.querySelector('#box-benefits');
const boxHover = matchMedia('(any-hover: hover)');
function setBoxOpen(open) {
  skillBox.classList.toggle('is-open', open);
  boxToggle.setAttribute('aria-expanded', String(open));
  boxToggle.setAttribute('aria-label', `${open ? 'Fechar' : 'Abrir'} a caixa de possibilidades SkillVerse`);
  boxBenefits.setAttribute('aria-hidden', String(!open));
  skillBox.querySelector('[data-box-label]').textContent = open
    ? (boxHover.matches ? 'Novas skills. Novas possibilidades.' : 'Toque para fechar sua caixa')
    : (boxHover.matches ? 'Passe o mouse e abra possibilidades' : 'Toque e abra novas possibilidades');
}
skillBox.addEventListener('pointerenter', event => {
  if (event.pointerType === 'mouse' && boxHover.matches) setBoxOpen(true);
});
skillBox.addEventListener('pointerleave', event => {
  if (event.pointerType === 'mouse' && !boxToggle.matches(':focus-visible')) setBoxOpen(false);
});
boxToggle.addEventListener('focus', () => {
  if (boxToggle.matches(':focus-visible')) setBoxOpen(true);
});
boxToggle.addEventListener('blur', () => setBoxOpen(false));
boxToggle.addEventListener('click', () => setBoxOpen(boxToggle.getAttribute('aria-expanded') !== 'true'));
boxToggle.addEventListener('keydown', event => {
  if (event.key === 'Escape') setBoxOpen(false);
});
boxHover.addEventListener('change', () => setBoxOpen(false));
setBoxOpen(false);
