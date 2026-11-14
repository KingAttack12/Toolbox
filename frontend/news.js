/* Brief RSS headlines; text-only DOM insertion and a device-local preference. */
(()=>{
  const banner=document.querySelector('#newsBanner');
  const toggle=document.querySelector('#newsToggle');
  const track=document.querySelector('#newsTrack');
  const pause=document.querySelector('#newsPause');
  const details=document.querySelector('#newsDetails');
  let enabled=storeGet('tb_news_enabled',true)!==false;
  let paused=false,timer=null,busy=false,loaded=false;
  function motion(){
    banner.classList.toggle('news-paused',paused||details.open);
    pause.textContent=paused?'Reprendre':'Pause';
    pause.setAttribute('aria-pressed',String(paused));
    pause.setAttribute('aria-label',paused?'Reprendre le défilement':'Mettre le défilement en pause');
  }
  function preference(){
    banner.classList.toggle('hidden',!enabled);
    toggle.setAttribute('aria-pressed',String(enabled));
    toggle.setAttribute('aria-label',enabled?'Masquer les actualités':'Afficher les actualités');
    clearTimeout(timer);
    if(enabled&&!document.hidden)refresh();
  }
  function itemNode(item){
    const li=document.createElement('li');
    const a=document.createElement('a');
    a.href=item.url;a.target='_blank';a.rel='noopener noreferrer';
    a.textContent=item.title;
    const source=document.createElement('span');
    source.textContent=' — '+item.source;
    li.append(a,source);return li;
  }
  async function refresh(){
    if(busy||!enabled||document.hidden)return;
    busy=true;clearTimeout(timer);
    try{
      const response=await fetch('/api/news',{signal:AbortSignal.timeout(12000)});
      if(!response.ok)throw new Error('News unavailable');
      const data=await response.json();
      const items=(data.items||[]).filter(item=>{
        try{const url=new URL(item.url);return url.protocol==='https:'&&['www.lemonde.fr','www.france24.com'].includes(url.host)&&typeof item.title==='string';}catch{return false;}
      });
      // Do not restart a moving list while someone is reading or focusing it.
      if((paused||details.open||banner.contains(document.activeElement))&&loaded)return;
      track.replaceChildren();document.querySelector('#newsList').replaceChildren();
      if(items.length){
        const group=document.createElement('li');group.className='news-group';
        const list=document.createElement('ul');items.forEach(item=>list.append(itemNode(item)));group.append(list);track.append(group);
        const copy=group.cloneNode(true);copy.classList.add('news-copy');copy.setAttribute('aria-hidden','true');copy.setAttribute('inert','');track.append(copy);
        items.forEach(item=>document.querySelector('#newsList').append(itemNode(item)));
        track.style.setProperty('--news-duration',Math.max(60,items.reduce((sum,item)=>sum+item.title.length+item.source.length,0)*.28)+'s');
        document.querySelector('#newsUpdated').textContent=data.updated_at?' · relevé à '+new Date(data.updated_at*1000).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'})+(data.stale?' · mise à jour retardée':''):'';
        details.classList.remove('hidden');loaded=true;
      }else{
        const li=document.createElement('li');li.className='news-unavailable';li.textContent='Actualités momentanément indisponibles.';track.append(li);details.classList.add('hidden');loaded=false;
      }
      track.classList.toggle('news-moving',items.length>0);motion();
    }catch{
      if(!loaded){track.replaceChildren();const li=document.createElement('li');li.textContent='Actualités momentanément indisponibles.';track.append(li);details.classList.add('hidden');}
    }finally{
      busy=false;if(enabled&&!document.hidden)timer=setTimeout(refresh,loaded?900000:60000);
    }
  }
  toggle.onclick=()=>{enabled=!enabled;storeSet('tb_news_enabled',enabled);preference();};
  document.querySelector('#newsHide').onclick=()=>{enabled=false;storeSet('tb_news_enabled',false);preference();toggle.focus();};
  pause.onclick=()=>{paused=!paused;motion();};
  details.addEventListener('toggle',motion);
  document.addEventListener('visibilitychange',()=>{clearTimeout(timer);if(!document.hidden&&enabled)refresh();});
  preference();
})();
