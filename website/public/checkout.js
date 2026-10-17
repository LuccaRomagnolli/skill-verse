(() => {
  const key='skillverse-order-v1';
  const cart=document.querySelector('#cart-body');
  let options=null, busy=false, timer;
  function stored(){ try { const o=JSON.parse(localStorage.getItem(key)||'null'); return o && typeof o.id==='string' && typeof o.token==='string' ? o : null; } catch {return null;} }
  function save(o){localStorage.setItem(key,JSON.stringify(o));}
  function forget(){localStorage.removeItem(key);}
  const error=(message)=>{ const p=cart.querySelector('[data-checkout-error]'); if(p){p.textContent=message;p.hidden=false;} };
  const newToken=()=>{const data=crypto.getRandomValues(new Uint8Array(32));return btoa(String.fromCharCode(...data)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');};
  async function config(){if(!options){try{let r=await fetch('/api/orders',{cache:'no-store'});if(!r.ok)throw Error();options=await r.json();}catch{options={enabled:false,methods:[]};}} return options;}
  function row(){return `<div class="cart-item"><span class="skill-icon">${icon('layers')}</span><div><strong>Pack Engenharia Civil</strong><small>12 skills · pack completo · 1 unidade</small></div><button class="icon-button" id="remove-cart" aria-label="Remover Engenharia Civil do carrinho">${icon('trash')}</button></div><div class="cart-total"><span>Total · pagamento único</span><strong>${money.format(39.90)}</strong></div>`;}
  function wireRemove(){cart.querySelector('#remove-cart')?.addEventListener('click',()=>{inCart=false;persistCart();render();});}
  async function render(){
    clearTimeout(timer);
    const order=stored(); if(order){await showOrder(order);return;}
    if(!inCart){cart.innerHTML=`<div class="empty-cart">${icon('bag')}<p>Seu próximo conjunto de habilidades começa aqui.</p><button class="button button-dark" data-open-pack>Explorar Engenharia Civil ${icon('arrow-right')}</button></div>`;return;}
    cart.innerHTML=row()+'<p class="checkout-notice">Verificando disponibilidade do pagamento…</p>';wireRemove();
    const settings=await config();if(!document.querySelector('#cart-dialog').open)return;
    if(!settings.enabled){cart.innerHTML=row()+`<button class="button checkout-button" disabled>${icon('lock')} Pagamento indisponível</button><p class="checkout-notice">O pagamento será habilitado após a configuração e a liberação do pack. Nenhuma cobrança foi realizada.</p>`;wireRemove();return;}
    cart.innerHTML=row()+`<button class="button button-dark checkout-button" id="start-checkout">Ir para pagamento ${icon('arrow-right')}</button><p class="checkout-notice">Pagamento processado pela SyncPay. Você revisará seus dados antes de confirmar.</p>`;wireRemove();cart.querySelector('#start-checkout').addEventListener('click',showForm);
  }
  function showForm(){
    cart.innerHTML=`<button class="checkout-back" type="button" id="back-cart">← Voltar ao carrinho</button><p class="checkout-intro">Pack Engenharia Civil <strong>R$ 39,90</strong></p><form id="checkout-form"><fieldset><legend>Seus dados</legend><div class="checkout-fields"><label>Nome completo<input name="name" autocomplete="name" required minlength="3" maxlength="100"></label><label>E-mail<input name="email" type="email" autocomplete="email" required maxlength="254"></label><label>CPF<input name="cpf" inputmode="numeric" autocomplete="off" required maxlength="14" placeholder="000.000.000-00"></label><label>Telefone com DDD<input name="phone" type="tel" inputmode="tel" autocomplete="tel" required maxlength="18" placeholder="(00) 00000-0000"></label></div></fieldset><fieldset><legend>Forma de pagamento</legend><div class="payment-methods"><label><input type="radio" name="method" value="pix" checked> Pix</label>${options.methods.includes('card')?'<label><input type="radio" name="method" value="card"> Cartão de crédito · à vista</label>':''}</div><div id="card-fields" hidden><div class="checkout-fields"><label class="field-wide">Número do cartão<input id="card-number" inputmode="numeric" autocomplete="cc-number" maxlength="23"></label><label class="field-wide">Nome no cartão<input id="card-holder" autocomplete="cc-name" maxlength="100"></label><label>Validade<input id="card-expiry" autocomplete="cc-exp" inputmode="numeric" placeholder="MM/AAAA" maxlength="7"></label><label>Código de segurança<input id="card-cvv" autocomplete="cc-csc" inputmode="numeric" type="password" maxlength="4"></label></div><p class="checkout-hint">Os dados do cartão são enviados diretamente à SyncPay para tokenização.</p></div></fieldset><p class="checkout-error" data-checkout-error role="alert" hidden></p><button class="button button-dark checkout-button" id="submit-order" type="submit">Gerar Pix · R$ 39,90</button><p class="checkout-notice">Ao continuar, seus dados serão usados para processar o pagamento e o pedido.</p></form>`;
    cart.querySelector('#back-cart').addEventListener('click',render);
    const form=cart.querySelector('form');
    form.addEventListener('change',()=>{const card=form.elements.method.value==='card';cart.querySelector('#card-fields').hidden=!card;cart.querySelectorAll('#card-fields input').forEach(el=>el.required=card);cart.querySelector('#submit-order').textContent=card?'Pagar no cartão · R$ 39,90':'Gerar Pix · R$ 39,90';});
    form.addEventListener('submit',submit);
  }
  async function submit(event){
    event.preventDefault();if(busy)return;busy=true;const form=event.currentTarget, button=form.querySelector('#submit-order');button.disabled=true;button.textContent='Preparando pagamento…';
    const fields=new FormData(form), method=fields.get('method');
    const client={name:String(fields.get('name')),email:String(fields.get('email')),cpf:String(fields.get('cpf')),phone:String(fields.get('phone'))};
    let cardToken;
    try{
      if(method==='card'){
        const number=cart.querySelector('#card-number').value.replace(/\D/g,''), holder=cart.querySelector('#card-holder').value.trim(), exp=cart.querySelector('#card-expiry').value.replace(/\D/g,''), cvv=cart.querySelector('#card-cvv').value.trim();
        if(!/^\d{13,19}$/.test(number)||!holder||!/^\d{6}$/.test(exp)||!/^\d{3,4}$/.test(cvv)){throw new Error('Confira os dados do cartão. Use a validade no formato MM/AAAA.');}
        const response=await fetch('https://api.syncpayments.com.br/api/public/v1/card-tokens',{method:'POST',credentials:'omit',headers:{'Content-Type':'application/json','X-Public-Key':options.publicKey},body:JSON.stringify({card:{number,holder_name:holder,expiry_month:exp.slice(0,2),expiry_year:exp.slice(2),cvv}})});
        if(!response.ok)throw new Error('Não foi possível validar o cartão. Confira os dados ou tente outra forma de pagamento.');
        const result=await response.json();cardToken=result.data?.token;if(typeof cardToken!=='string'||!cardToken.startsWith('card_token.'))throw new Error('Não foi possível validar o cartão.');
        for(const input of cart.querySelectorAll('#card-fields input'))input.value='';
      }
      const order={id:crypto.randomUUID(),token:newToken()};save(order);
      let response;
      try {response=await fetch('/api/orders',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:order.id,accessToken:order.token,product:'engenharia-civil',method,client,cardToken})});}
      catch{await showOrder(order);return;}
      let result;
      try {result=await response.json();} catch {await showOrder(order);return;}
      if(response.status===422){forget();throw new Error(result.error||'Confira os dados informados.');}
      if(!response.ok && result.status!=='unknown'){
        if(response.status>=500 || response.status===409){await showOrder(order);return;}
        forget();throw new Error(result.error||'Pagamento indisponível no momento.');
      }
      await showOrder(order,result);
    }catch(err){error(err.message||'Não foi possível iniciar o pagamento.');button.disabled=false;button.textContent=method==='card'?'Pagar no cartão · R$ 39,90':'Gerar Pix · R$ 39,90';}
    finally{busy=false;}
  }
  async function showOrder(order,known){
    clearTimeout(timer);cart.innerHTML='<p class="checkout-notice">Consultando o pedido…</p>';
    try{
      const response=known?null:await fetch(`/api/orders/${encodeURIComponent(order.id)}`,{headers:{Authorization:`Bearer ${order.token}`},cache:'no-store'});
      if(response&&!response.ok)throw new Error();const data=known||await response.json();
      cart.innerHTML=`<p class="checkout-intro">Pack Engenharia Civil <strong>R$ 39,90</strong></p><div class="order-status" role="status" aria-live="polite"></div><p class="checkout-hint">Número do pedido: <code data-order-id></code></p><p class="checkout-error" data-checkout-error role="alert" hidden></p>`;
      cart.querySelector('[data-order-id]').textContent=order.id;
      const status=cart.querySelector('.order-status');
      if(data.status==='completed'){
        status.innerHTML=`<span class="order-status-icon">✓</span><h3>Pagamento confirmado</h3><p>Seu pack está pronto. Faça o download neste navegador.</p><button class="button button-dark checkout-button" id="download-pack">Baixar o pack ${icon('download')}</button>`;
        cart.querySelector('#download-pack').addEventListener('click',()=>download(order));
      } else if(data.status==='pending' && data.pixCode){
        status.innerHTML=`<h3>Seu Pix está pronto</h3><p>Leia o QR Code ou copie o código para pagar no aplicativo do seu banco.</p><div class="pix-qr" role="img" aria-label="QR Code Pix"></div><label class="pix-code-label">Pix copia e cola<textarea readonly aria-label="Código Pix copia e cola"></textarea></label><button class="button button-dark checkout-button" id="copy-pix">Copiar código Pix</button><p class="checkout-hint">Aguardando confirmação. Mantenha esta página aberta.</p>`;
        const qr=qrcode(0,'M');qr.addData(data.pixCode);qr.make();cart.querySelector('.pix-qr').innerHTML=qr.createSvgTag({cellSize:3,margin:4});cart.querySelector('textarea').value=data.pixCode;cart.querySelector('#copy-pix').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(data.pixCode);cart.querySelector('#copy-pix').textContent='Código copiado';}catch{cart.querySelector('textarea').select();error('Selecione e copie o código Pix acima.');}});
      } else if(data.status==='pending' || data.status==='creating'){
        status.innerHTML='<h3>Processando pagamento</h3><p>A confirmação pode levar alguns instantes. Aguarde nesta página.</p>';
      } else if(data.status==='unknown'){
        status.innerHTML='<h3>Pagamento em verificação</h3><p>Não foi possível confirmar se a cobrança foi criada. Consulte o suporte antes de tentar novamente para evitar cobranças duplicadas.</p>';
      } else {
        status.innerHTML='<h3>Pagamento não concluído</h3><p>O pedido não está disponível para download. Você pode voltar ao carrinho e iniciar outro pagamento.</p><button class="button button-outline checkout-button" id="clear-order">Voltar ao carrinho</button>';
        cart.querySelector('#clear-order').addEventListener('click',()=>{forget();render();});
      }
      if(['pending','creating'].includes(data.status))timer=setTimeout(()=>{if(document.querySelector('#cart-dialog').open)showOrder(order);},15000);
    } catch {cart.innerHTML='<p class="checkout-error" role="alert">Não foi possível consultar o pedido. Guarde o número abaixo e consulte novamente antes de iniciar outra cobrança.</p><p class="checkout-hint">Número do pedido: <code data-order-id></code></p><button class="button button-outline checkout-button" id="retry-status">Consultar novamente</button>';cart.querySelector('[data-order-id]').textContent=order.id;cart.querySelector('#retry-status').addEventListener('click',()=>showOrder(order));}
  }
  async function download(order){const b=cart.querySelector('#download-pack');b.disabled=true;try{const response=await fetch(`/api/orders/${encodeURIComponent(order.id)}/download`,{headers:{Authorization:`Bearer ${order.token}`},cache:'no-store'});if(!response.ok)throw new Error();const blob=await response.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='skillverse-engenharia-civil.zip';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}catch{error('Não foi possível baixar o pack. Tente novamente.');}finally{b.disabled=false;}}
  window.SkillVerseCheckout={render};
})();
