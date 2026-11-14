/* Select a file first; reuse the authenticated, validated conversion endpoints. */
(()=>{
  const el=id=>document.getElementById('convert'+id);
  const drop=el('Drop'),input=el('Files'),form=el('Form'),format=el('Format');
  let selected=[],options=[],busy=false,version=0,resultUrl=null,dragDepth=0;
  const imageOutputs=[['jpg','JPG'],['png','PNG'],['webp','WebP'],['bmp','BMP'],['tiff','TIFF'],['gif','GIF — image fixe'],['ico','ICO — icône']];
  const imageTypes=new Set(['jpg','png','webp','gif','bmp','tiff','ico']);
  function option(value,label,endpoint,fields,hint=''){
    return {value,label,endpoint,fields,hint};
  }
  function choices(types){
    if(types.length>1){
      if(types.every(type=>imageTypes.has(type)))return [option('pdf','PDF — toutes les images','/api/tools/pdf/from-images',{},'Un PDF avec une page par image, dans l’ordre de sélection. Maximum 20 images.')];
      if(types.every(type=>type==='pdf'))return [option('merge','PDF — fusionner les documents','/api/tools/pdf/merge',{},'Un seul PDF, dans l’ordre de sélection. Maximum 20 documents.')];
      return [];
    }
    const type=types[0];
    if(imageTypes.has(type))return [
      ...imageOutputs.filter(([value])=>value!==type).map(([value,label])=>option(value,label,'/api/tools/image/convert',{format:value},'Les images animées sont converties en image fixe. Les métadonnées sont retirées.')),
      option('pdf','PDF','/api/tools/pdf/from-images',{},'Une page PDF avec votre image. Pour une animation, seule la première image est utilisée.'),
      option('txt','Texte (.txt) — OCR','/api/tools/office/image-ocr',{},'Reconnaissance du texte français et anglais de votre image. La précision dépend de sa netteté.')
    ];
    if(type==='pdf')return [
      option('docx','Word (.docx)','/api/tools/office/pdf-to-word',{},'PDF texte : 100 pages maximum. La mise en page peut demander des retouches. Pour un scan, choisissez le texte OCR.'),
      option('png','Images PNG (ZIP)','/api/tools/pdf/to-images',{format:'png',dpi:150},'Une image par page, regroupées dans un ZIP. Maximum 50 pages.'),
      option('jpg','Images JPG (ZIP)','/api/tools/pdf/to-images',{format:'jpg',dpi:150},'Une image par page, regroupées dans un ZIP. Maximum 50 pages.'),
      option('text','Texte (.txt) — extraction directe','/api/tools/office/pdf-text',{},'Extrait le texte déjà intégré au PDF, sans reconnaissance OCR. Maximum 100 pages.'),
      option('txt','Texte (.txt) — OCR','/api/tools/office/ocr',{language:'fra+eng',dpi:150},'Reconnaissance du texte français et anglais. Maximum 20 pages.')
    ];
    if(type==='docx')return [option('pdf','PDF','/api/tools/office/word-to-pdf',{},'Document Word .docx. La mise en page est conservée autant que possible.'),option('txt','Texte (.txt)','/api/tools/office/word-text',{},'Extrait le texte du document sans sa mise en forme.')];
    if(type==='audio'||type==='video'){
      const outputs=[['mp3','MP3'],['wav','WAV'],['flac','FLAC'],['ogg','OGG'],['m4a','M4A']].map(([value,label])=>option(value,label+' — audio','/api/tools/media/convert',{format:value},'Durée maximale : 10 minutes. Sortie limitée à 50 Mo. WAV et FLAC peuvent produire des fichiers volumineux.'));
      if(type==='video')outputs.push(...[['mp4','MP4'],['webm','WebM']].map(([value,label])=>option(value,label+' — vidéo','/api/tools/media/convert',{format:value},'Durée maximale : 10 minutes. Sortie en 720p et 30 images/s maximum, limitée à 50 Mo.')));
      return outputs;
    }
    return [];
  }
  async function detect(file){
    const bytes=new Uint8Array(await file.slice(0,16).arrayBuffer());
    const starts=(...values)=>values.every((value,index)=>bytes[index]===value);
    const ascii=(start,end)=>String.fromCharCode(...bytes.slice(start,end));
    if(starts(0x25,0x50,0x44,0x46,0x2d))return 'pdf';
    if(starts(0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a))return 'png';
    if(starts(0xff,0xd8,0xff))return 'jpg';
    if(['GIF87a','GIF89a'].includes(ascii(0,6)))return 'gif';
    if(ascii(0,4)==='RIFF'&&ascii(8,12)==='WEBP')return 'webp';
    if(ascii(0,2)==='BM')return 'bmp';
    if(starts(0x49,0x49,0x2a,0)||starts(0x4d,0x4d,0,0x2a))return 'tiff';
    if(starts(0,0,1,0))return 'ico';
    if(starts(0x50,0x4b,3,4)&&/\.docx$/i.test(file.name))return 'docx';
    if(ascii(0,4)==='RIFF'&&ascii(8,12)==='WAVE')return 'audio';
    if(ascii(0,4)==='fLaC'||ascii(0,4)==='OggS'||ascii(0,3)==='ID3')return 'audio';
    if(bytes[0]===255&&(bytes[1]&0xe0)===0xe0)return 'audio';
    if(ascii(4,8)==='ftyp'&&/\.(m4a|aac)$/i.test(file.name))return 'audio';
    if(ascii(4,8)==='ftyp'&&/\.(mp4|mov|m4v)$/i.test(file.name))return 'video';
    if(starts(0x1a,0x45,0xdf,0xa3)&&/\.(webm|mkv)$/i.test(file.name))return 'video';
    if(ascii(0,4)==='RIFF'&&ascii(8,12)==='AVI ')return 'video';
    throw new Error('Format non reconnu pour « '+file.name+' ». Utilisez un PDF, un Word .docx, une image, un fichier audio ou une vidéo compatible.');
  }
  function clearResult(){
    if(resultUrl)URL.revokeObjectURL(resultUrl);
    resultUrl=null;el('Download').classList.add('hidden');el('Download').removeAttribute('href');
    el('Status').textContent='';el('Error').textContent='';
  }
  function reset(){
    version++;selected=[];options=[];input.value='';format.replaceChildren();
    form.classList.add('hidden');drop.classList.remove('hidden');clearResult();
  }
  function hint(){el('Hint').textContent=options.find(item=>item.value===format.value)?.hint||'';}
  async function selectFiles(files){
    if(busy)return;
    const list=Array.from(files);
    reset();const current=version;
    try{
      if(!list.length)return;
      if(list.length>20)throw new Error('Sélectionnez au maximum 20 fichiers.');
      if(list.some(file=>!file.size))throw new Error('Un des fichiers est vide.');
      if(list.some(file=>file.size>50*1024*1024))throw new Error('Chaque fichier doit peser au maximum 50 Mo.');
      if(list.reduce((total,file)=>total+file.size,0)>50*1024*1024)throw new Error('La sélection complète doit peser au maximum 50 Mo.');
      el('Status').textContent='Reconnaissance du format…';
      const types=await Promise.all(list.map(detect));
      if(current!==version)return;
      if(list.some((file,index)=>imageTypes.has(types[index])&&file.size>20*1024*1024))throw new Error('Chaque image doit peser au maximum 20 Mo.');
      options=choices(types);
      if(!options.length)throw new Error('Choisissez un seul fichier, plusieurs images pour un PDF, ou plusieurs PDF à fusionner.');
      selected=list;
      options.forEach(item=>{const opt=document.createElement('option');opt.value=item.value;opt.textContent=item.label;format.append(opt);});
      el('Selection').textContent=list.map(file=>file.name).join(' · ')+' — '+(list.reduce((total,file)=>total+file.size,0)/1024/1024).toFixed(1)+' Mo';
      form.classList.remove('hidden');drop.classList.add('hidden');el('Status').textContent='';hint();format.focus();
    }catch(error){if(current===version){el('Status').textContent='';el('Error').textContent=error.message;}}
  }
  el('Choose').onclick=()=>{input.value='';input.click();};
  input.onchange=()=>selectFiles(input.files);
  el('Reset').onclick=()=>{if(!busy){reset();el('Choose').focus();}};
  format.onchange=()=>{clearResult();hint();};
  // Prevent the browser from navigating away when a file misses the drop zone.
  for(const eventName of ['dragover','drop'])document.addEventListener(eventName,event=>{
    if(Array.from(event.dataTransfer?.types||[]).includes('Files'))event.preventDefault();
  });
  drop.addEventListener('dragenter',event=>{event.preventDefault();dragDepth++;drop.classList.add('drag-active');});
  drop.addEventListener('dragover',event=>{event.preventDefault();event.dataTransfer.dropEffect='copy';});
  drop.addEventListener('dragleave',()=>{if(--dragDepth<=0){dragDepth=0;drop.classList.remove('drag-active');}});
  drop.addEventListener('drop',event=>{event.preventDefault();dragDepth=0;drop.classList.remove('drag-active');selectFiles(event.dataTransfer.files);});
  form.onsubmit=async event=>{
    event.preventDefault();if(busy||!selected.length)return;
    const choice=options.find(item=>item.value===format.value);if(!choice)return;
    busy=true;clearResult();form.querySelectorAll('button,select').forEach(control=>control.disabled=true);
    el('Status').textContent='Conversion en cours… Une attente est possible si un autre fichier est en traitement.';
    try{
      const data=new FormData();
      const multi=['/api/tools/pdf/from-images','/api/tools/pdf/merge'].includes(choice.endpoint);
      selected.forEach(file=>data.append(multi?'files':'file',file));
      Object.entries(choice.fields).forEach(([key,value])=>data.append(key,String(value)));
      const response=await fetch(choice.endpoint,{method:'POST',body:data});
      if(!response.ok){
        if(response.status===401)throw new Error('Votre session a expiré. Reconnectez-vous avant de réessayer.');
        const error=await response.json().catch(()=>({}));throw new Error(errMsg(error,response));
      }
      const blob=await response.blob();resultUrl=URL.createObjectURL(blob);
      const link=el('Download');link.href=resultUrl;
      const filename=/filename="([^"]+)"/.exec(response.headers.get('Content-Disposition')||'');
      const extension=choice.endpoint==='/api/tools/pdf/to-images'?'zip':choice.value==='merge'?'pdf':choice.value==='text'?'txt':choice.value;
      link.download=filename?filename[1]:'conversion.'+extension;
      link.classList.remove('hidden');el('Status').textContent='Conversion terminée. Votre fichier est prêt à être téléchargé.';
    }catch(error){el('Status').textContent='';el('Error').textContent=error.message;}
    finally{busy=false;form.querySelectorAll('button,select').forEach(control=>control.disabled=false);}
  };
})();
