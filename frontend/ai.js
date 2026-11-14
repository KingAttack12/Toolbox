/* Owner-only local AI trial. No prompts or answers in browser storage. */
(()=>{
  const el=id=>document.getElementById('ai'+id);
  let busy=false,timer=null,previous=null;
  async function metrics(){
    clearTimeout(timer);
    if(el('Modal').classList.contains('hidden')||document.hidden)return;
    try{
      const response=await fetch('/api/admin/ai/status',{cache:'no-store'});
      if(!response.ok)throw Error('Mesures réservées au propriétaire. Reconnectez-vous.');
      const data=await response.json(),now=performance.now();
      let cpu='mesure en cours';
      if(previous&&data.cpu_usec!=null&&previous.cpu!=null){const cores=Math.max(0,(data.cpu_usec-previous.cpu)/1000/(now-previous.time));cpu=cores.toFixed(2)+' / 1,5 cœur';}
      previous={time:now,cpu:data.cpu_usec};
      el('Resources').textContent=(data.ready?'Moteur prêt':'Moteur indisponible')+' · CPU IA : '+cpu+' · RAM : '+(data.memory_used==null?'—':(data.memory_used/1024**3).toFixed(2)+' / 4 Go');
      if(!busy)el('Run').disabled=!data.ready;
    }catch(error){el('Resources').textContent=error.message;}
    if(!el('Modal').classList.contains('hidden'))timer=setTimeout(metrics,5000);
  }
  function close(){el('Modal').classList.add('hidden');document.body.classList.remove('modal-open');clearTimeout(timer);el('Btn').focus();}
  el('Btn').onclick=()=>{el('Modal').classList.remove('hidden');document.body.classList.add('modal-open');previous=null;metrics();el('Text').focus();};
  el('Close').onclick=close;
  el('Modal').addEventListener('click',event=>{if(event.target===el('Modal'))close();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!el('Modal').classList.contains('hidden'))close();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)clearTimeout(timer);else metrics();});
  el('Form').onsubmit=async event=>{
    event.preventDefault();if(busy)return;busy=true;el('Run').disabled=true;
    el('Error').textContent='';el('Output').textContent='';el('Output').classList.add('hidden');
    el('Status').textContent='En attente ou génération en cours… Le premier essai charge aussi le modèle.';
    try{
      const result=await betaPost('/api/admin/ai/generate',{mode:el('Mode').value,text:el('Text').value});
      el('Output').textContent=result.text;el('Output').classList.remove('hidden');
      el('Status').textContent='Réponse en '+result.seconds+' s · '+(result.tokens_per_second??'—')+' tokens/s · CPU consommé : '+(result.cpu_seconds??'—')+' s'+(result.truncated?' · Limite de réponse atteinte.':'');
    }catch(error){el('Status').textContent='';el('Error').textContent=error.message;}
    finally{busy=false;el('Run').disabled=false;metrics();}
  };
})();
