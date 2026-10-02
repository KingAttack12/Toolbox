/* Toolbox frontend vanilla JS — appelle uniquement l'API privée (session cookie). */
const $ = (s) => document.querySelector(s);

/* ---------- catalogue d'outils Phase 1+2 ---------- */
const TOOLS = [
  // Texte & code
  {id:"count", cat:"texte", icon:"🔢", name:"Compteur mots/caractères", desc:"Mots, caractères, lignes, phrases.", fields:[{k:"text",label:"Texte",type:"textarea"}], ep:"/api/tools/text/count"},
  {id:"clean", cat:"texte", icon:"🧹", name:"Nettoyeur de texte", desc:"Espaces inutiles, lignes vides.", fields:[{k:"text",label:"Texte",type:"textarea"},{k:"remove_extra_spaces",label:"Réduire espaces multiples",type:"check",def:true},{k:"trim_lines",label:"Trim lignes",type:"check",def:true},{k:"remove_empty_lines",label:"Supprimer lignes vides",type:"check",def:false}], ep:"/api/tools/text/clean"},
  {id:"case", cat:"texte", icon:"🔡", name:"Majuscules / minuscules", desc:"upper, lower, title, invert.", fields:[{k:"text",label:"Texte",type:"textarea"},{k:"mode",label:"Mode",type:"select",opts:["upper","lower","title","capitalize","invert"]}], ep:"/api/tools/text/case"},
  {id:"b64", cat:"texte", icon:"🔐", name:"Base64 encode/decode", desc:"Encode ou décode en Base64.", fields:[{k:"data",label:"Données",type:"textarea"},{k:"mode",label:"Mode",type:"select",opts:["encode","decode"]}], ep:"/api/tools/text/base64"},
  {id:"hash", cat:"texte", icon:"#️⃣", name:"Hash SHA-256 / SHA-512", desc:"Empreinte cryptographique.", fields:[{k:"text",label:"Texte",type:"textarea"},{k:"algo",label:"Algo",type:"select",opts:["sha256","sha512"]}], ep:"/api/tools/text/hash"},
  {id:"uuid", cat:"texte", icon:"🆔", name:"Générateur UUID", desc:"UUID v4 aléatoires.", fields:[{k:"count",label:"Quantité (1-50)",type:"number",def:1}], ep:"/api/tools/text/uuid"},
  {id:"pwdgen", cat:"texte", icon:"🔑", name:"Mot de passe (secrets)", desc:"Aléatoire sûr côté serveur.", fields:[{k:"length",label:"Longueur",type:"number",def:20},{k:"symbols",label:"Symboles",type:"check",def:true}], ep:"/api/tools/text/password"},
  {id:"jsonfmt", cat:"texte", icon:"🧾", name:"JSON Formatter", desc:"Valide + pretty-print.", fields:[{k:"data",label:"JSON",type:"textarea"},{k:"indent",label:"Indentation",type:"number",def:2}], ep:"/api/tools/text/json-format"},
  {id:"jsonval", cat:"texte", icon:"✅", name:"JSON Validator", desc:"Vérifie la syntaxe.", fields:[{k:"text",label:"JSON",type:"textarea"}], ep:"/api/tools/text/json-validate"},
  {id:"xmlfmt", cat:"texte", icon:"🗂️", name:"XML Formatter", desc:"Pretty-print XML.", fields:[{k:"text",label:"XML",type:"textarea"}], ep:"/api/tools/text/xml-format"},
  {id:"diff", cat:"texte", icon:"↔️", name:"Diff Checker", desc:"Diff unifié de 2 textes.", fields:[{k:"a",label:"Texte A",type:"textarea"},{k:"b",label:"Texte B",type:"textarea"}], ep:"/api/tools/text/diff"},
  {id:"csv", cat:"texte", icon:"📊", name:"CSV Viewer", desc:"Aperçu (100 lignes max).", fields:[{k:"csv_text",label:"CSV",type:"textarea"},{k:"delimiter",label:"Délimiteur",type:"select",opts:[",",";","\\t","|"]}], ep:"/api/tools/text/csv-preview"},
  // Calculatrices
  {id:"expr", cat:"calc", icon:"🧪", name:"Calculatrice scientifique", desc:"sin cos sqrt log pi e... (éval sûre).", fields:[{k:"expression",label:"Expression ex: sqrt(16)+sin(pi/2)",type:"text"}], ep:"/api/tools/calc/expr"},
  {id:"pct", cat:"calc", icon:"％", name:"Pourcentages", desc:"of / increase / decrease.", fields:[{k:"value",label:"Valeur",type:"number",def:100},{k:"percent",label:"%",type:"number",def:20},{k:"mode",label:"Mode",type:"select",opts:["of","increase","decrease"]}], ep:"/api/tools/calc/percent"},
  {id:"tva", cat:"calc", icon:"🧾", name:"TVA", desc:"HT↔TTC.", fields:[{k:"amount",label:"Montant",type:"number",def:100},{k:"rate",label:"Taux %",type:"number",def:20},{k:"mode",label:"Mode",type:"select",opts:["ht_to_ttc","ttc_to_ht"]}], ep:"/api/tools/calc/tva"},
  {id:"conv", cat:"calc", icon:"📏", name:"Conversion d'unités", desc:"longueur masse volume vitesse stockage.", fields:[{k:"category",label:"Catégorie",type:"select",opts:["length","mass","volume","speed","storage"]},{k:"value",label:"Valeur",type:"number",def:1},{k:"from",label:"De",type:"text",def:"m"},{k:"to",label:"Vers",type:"text",def:"km"}], ep:"/api/tools/calc/convert", hint:"Ex: length m→km, mass kg→lb, storage go→mo, speed km/h→m/s"},
  {id:"temp", cat:"calc", icon:"🌡️", name:"Température", desc:"C / F / K.", fields:[{k:"value",label:"Valeur",type:"number",def:20},{k:"from",label:"De",type:"select",opts:["C","F","K"]},{k:"to",label:"Vers",type:"select",opts:["C","F","K"]}], ep:"/api/tools/calc/temperature"},
  {id:"datediff", cat:"calc", icon:"📅", name:"Différence de dates", desc:"Jours / semaines / mois.", fields:[{k:"date1",label:"Date 1 (AAAA-MM-JJ)",type:"text",def:"2026-01-01"},{k:"date2",label:"Date 2",type:"text",def:"2026-09-22"}], ep:"/api/tools/calc/date-diff"},
  {id:"moy", cat:"calc", icon:"🎓", name:"Moyenne pondérée", desc:"Notes + coefficients + mention.", fields:[{k:"notes",label:'Notes JSON ex: [{"value":14,"coef":2},{"value":12,"coef":1}]',type:"textarea"}], ep:"/api/tools/calc/moyenne", jsonNotes:true},
  // Bioinfo
  {id:"gc", cat:"bio", icon:"🧬", name:"Taux de GC", desc:"GC% / AT% d'une séquence.", fields:[{k:"sequence",label:"Séquence ADN/ARN",type:"textarea"}], ep:"/api/tools/bio/gc"},
  {id:"trscr", cat:"bio", icon:"🧪", name:"Transcription ADN→ARN", desc:"T→U.", fields:[{k:"sequence",label:"Séquence ADN",type:"textarea"}], ep:"/api/tools/bio/transcribe"},
  {id:"trsl", cat:"bio", icon:"🥩", name:"Traduction ADN→protéine", desc:"Code génétique standard.", fields:[{k:"sequence",label:"Séquence ADN",type:"textarea"}], ep:"/api/tools/bio/translate"},
  {id:"motif", cat:"bio", icon:"🔍", name:"Recherche de motifs", desc:"Positions 1-indexed.", fields:[{k:"sequence",label:"Séquence",type:"textarea"},{k:"motif",label:"Motif",type:"text"}], ep:"/api/tools/bio/motif"},
  {id:"fasta", cat:"bio", icon:"📄", name:"FASTA stats", desc:"Nb séquences, longueurs, GC.", fields:[{k:"fasta",label:"FASTA ou séquence brute",type:"textarea"}], ep:"/api/tools/bio/fasta-stats"},
  // QR
  {id:"qr", cat:"qr", icon:"🔳", name:"Générateur QR code", desc:"QR local → PNG.", fields:[{k:"text",label:"Texte / URL",type:"textarea"},{k:"size",label:"Taille case (4-20)",type:"number",def:10}], ep:"/api/tools/qr/generate", blob:true},
  // Images
  {id:"imgconv", cat:"img", icon:"🖼️", name:"Convertisseur d'image", desc:"JPG/PNG/WebP + resize, rotation, miroir, N&B.", fields:[{k:"file",label:"Image (max 20 Mo)",type:"file"},{k:"format",label:"Format de sortie",type:"select",opts:["jpg","png","webp"],def:"jpg"},{k:"quality",label:"Qualité JPG/WebP (10-100)",type:"number",def:85},{k:"resize_max",label:"Redimensionner (plus grand côté px, 0 = inchangé)",type:"number",def:0},{k:"rotate",label:"Rotation",type:"select",opts:["0","90","180","270"]},{k:"flip",label:"Miroir",type:"select",opts:["none","horizontal","vertical"]},{k:"grayscale",label:"Noir & blanc",type:"check",def:false},{k:"strip_exif",label:"Supprimer métadonnées EXIF",type:"check",def:true}], ep:"/api/tools/image/convert", blob:true, multipart:true},
  // Documents PDF
  {id:"pdfmerge", cat:"pdf", icon:"📚", name:"Fusionner des PDF", desc:"2 à 20 PDF en un seul.", fields:[{k:"files",label:"PDF (2 mini)",type:"file",multiple:true,accept:"application/pdf"}], ep:"/api/tools/pdf/merge", blob:true, multipart:true},
  {id:"pdfsplit", cat:"pdf", icon:"✂️", name:"Séparer / extraire pages", desc:"Ex : 1-3,5. Max 500 pages.", fields:[{k:"file",label:"PDF",type:"file",accept:"application/pdf"},{k:"pages",label:"Pages (ex : 1-3,5 — vide = tout)",type:"text",def:""}], ep:"/api/tools/pdf/split", blob:true, multipart:true},
  {id:"pdfrotate", cat:"pdf", icon:"🔄", name:"Rotation de pages", desc:"90/180/270° sur tout ou sélection.", fields:[{k:"file",label:"PDF",type:"file",accept:"application/pdf"},{k:"pages",label:"Pages (vide = tout)",type:"text",def:""},{k:"angle",label:"Angle",type:"select",opts:["90","180","270"]}], ep:"/api/tools/pdf/rotate", blob:true, multipart:true},
  {id:"pdf2img", cat:"pdf", icon:"🖼️", name:"PDF → images (ZIP)", desc:"Chaque page en PNG/JPG. Max 50 pages.", fields:[{k:"file",label:"PDF",type:"file",accept:"application/pdf"},{k:"dpi",label:"Qualité DPI",type:"select",opts:["72","100","150","200","300"],def:"150"},{k:"format",label:"Format",type:"select",opts:["png","jpg"]}], ep:"/api/tools/pdf/to-images", blob:true, multipart:true},
  {id:"img2pdf", cat:"pdf", icon:"📄", name:"Images → PDF", desc:"1 à 20 images en un PDF.", fields:[{k:"files",label:"Images",type:"file",multiple:true}], ep:"/api/tools/pdf/from-images", blob:true, multipart:true},
  {id:"pdfmeta", cat:"pdf", icon:"🏷️", name:"Métadonnées PDF", desc:"Lire, ou nettoyer + télécharger.", fields:[{k:"file",label:"PDF",type:"file",accept:"application/pdf"},{k:"strip",label:"Supprimer les métadonnées (renvoie un PDF nettoyé)",type:"check",def:false}], ep:"/api/tools/pdf/metadata", blob:true, multipart:true, metaSwitch:true},
  {id:"pdfcompress", cat:"pdf", icon:"🗜️", name:"Compresser un PDF", desc:"Réenregistrement optimisé (gain variable).", fields:[{k:"file",label:"PDF",type:"file",accept:"application/pdf"}], ep:"/api/tools/pdf/compress", blob:true, multipart:true},
  // Média
  {id:"yt", cat:"media", icon:"📥", name:"YouTube (contenus autorisés)", desc:"Formats puis téléchargement. Max 30 min.", fields:[{k:"url",label:"URL YouTube",type:"text"},{k:"confirm_rights",label:"Je confirme avoir le droit de télécharger ce contenu",type:"check",def:false},{k:"format_id",label:"Format (cliquez Exécuter pour lister)",type:"select",opts:["—"]},{k:"compat_h264",label:"Convertir en H264/AAC si besoin (montage, vidéos ≤10 min)",type:"check",def:false}], ep:"/api/tools/media/fetch", youtube:true, hint:"Si YouTube répond 'not a bot' : utilisez l'outil Cookies YouTube (compte jetable) puis réessayez."},
  {id:"ytcookies", cat:"media", icon:"🍪", name:"Cookies YouTube", desc:"Anti-bot : compte JETABLE uniquement. status/save/delete.", fields:[{k:"action",label:"Action",type:"select",opts:["status","save","delete"]},{k:"data",label:"Contenu cookies.txt (Netscape, pour save)",type:"textarea"}], ep:"/api/tools/media/cookies"},
  {id:"mp3", cat:"media", icon:"🎵", name:"MP4 → MP3", desc:"Extrait l'audio (128/192/320 kbps). Upload max ~50 Mo.", fields:[{k:"file",label:"Vidéo",type:"file",accept:"video/*"},{k:"bitrate",label:"Qualité",type:"select",opts:["128","192","320"],def:"192"}], ep:"/api/tools/media/mp4-to-mp3", blob:true, multipart:true},
  // Bientôt
  {id:"office", cat:"soon", icon:"📝", name:"Word/PDF + OCR (bientôt)", desc:"LibreOffice, Tesseract…", soon:true},
  {id:"ai", cat:"soon", icon:"🤖", name:"IA (Phase 6, optionnel)", desc:"Résumé, QCM… désactivé.", soon:true},
];

let currentTool = null;
const favs = new Set(JSON.parse(localStorage.getItem("tb_favs")||"[]"));
let recent = JSON.parse(localStorage.getItem("tb_recent")||"[]");

/* ---------- thème ---------- */
function initTheme(){
  const t = localStorage.getItem("tb_theme") || "light";
  document.documentElement.dataset.theme = t;
  $("#themeBtn").textContent = t==="dark"?"☀️":"🌙";
}
$("#themeBtn").onclick = ()=>{
  const t = document.documentElement.dataset.theme==="dark"?"light":"dark";
  document.documentElement.dataset.theme=t; localStorage.setItem("tb_theme",t);
  $("#themeBtn").textContent = t==="dark"?"☀️":"🌙";
};

/* ---------- auth ---------- */
async function checkMe(){
  try{
    const r = await fetch("/api/me");
    if(r.ok){ showApp(); return true; }
  }catch(e){}
  showLogin(); return false;
}
function showLogin(){ $("#loginView").classList.remove("hidden"); $("#appView").classList.add("hidden"); $("#logoutBtn").classList.add("hidden"); }
function showApp(){ $("#loginView").classList.add("hidden"); $("#appView").classList.remove("hidden"); $("#logoutBtn").classList.remove("hidden"); renderGrid("all",""); renderRecent(); }

$("#loginForm").addEventListener("submit", async (e)=>{
  e.preventDefault();
  $("#loginError").textContent="";
  const r = await fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({username:$("#loginUser").value,password:$("#loginPass").value})});
  const j = await r.json().catch(()=>({}));
  if(j.ok){ $("#loginPass").value=""; showApp(); }
  else $("#loginError").textContent = j.error || "Échec de connexion.";
});
$("#logoutBtn").onclick = async ()=>{ await fetch("/api/logout",{method:"POST"}); location.reload(); };

/* ---------- grille ---------- */
let curCat="all";
document.querySelectorAll(".cat").forEach(b=>b.onclick=()=>{
  document.querySelectorAll(".cat").forEach(x=>x.classList.remove("active"));
  b.classList.add("active"); curCat=b.dataset.cat; renderGrid(curCat,$("#search").value);
});
$("#search").addEventListener("input",(e)=>renderGrid(curCat,e.target.value));

function renderGrid(cat,q){
  q=(q||"").toLowerCase();
  const grid=$("#toolsGrid"); grid.innerHTML="";
  TOOLS.filter(t=>{
    if(favs.has(t.id)) return true; // favoris toujours visibles dans "all"? non, simple:
    return true;
  }).filter(t=> (cat==="all"||t.cat===cat||(cat==="soon"&&t.soon)))
    .filter(t=> (t.name+t.desc+t.id).toLowerCase().includes(q))
    .sort((a,b)=> (favs.has(b.id)?1:0)-(favs.has(a.id)?1:0))
    .forEach(t=>{
      const btn=document.createElement("button");
      btn.className="tool"+(t.soon?" disabled":"");
      btn.innerHTML=`<span class="fav">${favs.has(t.id)?"★":"☆"}</span><div style="font-size:1.5rem">${t.icon}</div><h4>${t.name}</h4><p>${t.desc}</p>`;
      btn.onclick=(ev)=>{
        if(ev.target.classList.contains("fav")){ toggleFav(t.id); ev.stopPropagation(); return; }
        if(t.soon){ alert("Prévu dans une phase suivante (PDF/Images/Média/IA)."); return; }
        openTool(t);
      };
      grid.appendChild(btn);
    });
}
function toggleFav(id){ favs.has(id)?favs.delete(id):favs.add(id); localStorage.setItem("tb_favs",JSON.stringify([...favs])); renderGrid(curCat,$("#search").value); }
function renderRecent(){ $("#recentLine").textContent = recent.length? "🕘 Récents : "+recent.map(id=>{const t=TOOLS.find(x=>x.id===id);return t?t.name:id;}).join(" • ") : ""; }

/* ---------- modal outil ---------- */
function openTool(t){
  currentTool=t;
  $("#toolTitle").textContent=t.icon+" "+t.name;
  $("#toolDesc").textContent=(t.desc||"")+(t.hint?" Hint: "+t.hint:"");
  $("#toolOutput").textContent=""; $("#toolError").textContent="";
  $("#toolDownloadWrap").classList.add("hidden");
  $("#toolFav").textContent=favs.has(t.id)?"★ Favori":"☆ Favori";
  const box=$("#toolFields"); box.innerHTML="";
  t.fields.forEach(f=>{
    const div=document.createElement("div"); div.className="field";
    if(f.type==="file"){ const mult=f.multiple?" multiple":""; const acc=f.accept?` accept="${f.accept}"`:" accept=\"image/*\""; div.innerHTML=`<label>${f.label}<input type="file"${mult}${acc} data-k="${f.k}"></label>`; }
    else if(f.type==="textarea") div.innerHTML=`<label>${f.label}<textarea data-k="${f.k}">${f.def||""}</textarea></label>`;
    else if(f.type==="select") div.innerHTML=`<label>${f.label}<select data-k="${f.k}">${f.opts.map(o=>`<option ${o===(f.def||f.opts[0])?"selected":""}>${o}</option>`).join("")}</select></label>`;
    else if(f.type==="check") div.innerHTML=`<label><input type="checkbox" data-k="${f.k}" ${f.def?"checked":""}> ${f.label}</label>`;
    else if(f.type==="number") div.innerHTML=`<label>${f.label}<input type="number" data-k="${f.k}" value="${f.def??""}"></label>`;
    else div.innerHTML=`<label>${f.label}<input type="text" data-k="${f.k}" value="${f.def||""}"></label>`;
    box.appendChild(div);
  });
  $("#toolModal").classList.remove("hidden");
}
$("#toolClose").onclick=()=>$("#toolModal").classList.add("hidden");
$("#toolModal").addEventListener("click",(e)=>{ if(e.target.id==="toolModal") $("#toolModal").classList.add("hidden"); });
$("#toolFav").onclick=()=>{ if(currentTool){toggleFav(currentTool.id); $("#toolFav").textContent=favs.has(currentTool.id)?"★ Favori":"☆ Favori";} };

function collectPayload(t){
  const p={};
  t.fields.forEach(f=>{
    const el=document.querySelector(`[data-k="${f.k}"]`);
    if(f.type==="check") p[f.k]=el.checked;
    else if(f.type==="number") p[f.k]=Number(el.value);
    else if(f.type==="file"){
      if(!el.files.length) throw new Error("Choisissez un fichier.");
      p[f.k]= f.multiple ? [...el.files] : el.files[0];
    }
    else p[f.k]=el.value;
  });
  if(t.jsonNotes){ try{ p.notes=JSON.parse(p.notes);}catch(e){ throw new Error("Champ notes : JSON invalide."); } }
  if(t.id==="csv"&&p.delimiter==="\\t") p.delimiter="\t";
  return p;
}

$("#toolRun").onclick=async ()=>{
  const t=currentTool; if(!t) return;
  $("#toolError").textContent=""; $("#toolOutput").textContent="";
  $("#toolDownloadWrap").classList.add("hidden");
  let payload;
  try{ payload=collectPayload(t); }catch(e){ $("#toolError").textContent=e.message; return; }
  $("#toolProgress").classList.remove("hidden");
  try{
    if(t.youtube){ await runYoutube(t); }
    else{
    let opts;
    if(t.multipart){
      const fd=new FormData();
      for(const [k,v] of Object.entries(payload)){
        if(Array.isArray(v)) v.forEach(f=>fd.append(k,f));
        else fd.append(k, v instanceof File?v:String(v));
      }
      opts={method:"POST",body:fd};
    } else opts={method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)};
    const r=await fetch(t.ep,opts);
    const ctype=r.headers.get("Content-Type")||"";
    if(t.metaSwitch && ctype.includes("application/json")){
      const j=await r.json();
      if(!r.ok) throw new Error(errMsg(j,r));
      $("#toolOutput").textContent=fmt(j);
    }
    else if(t.blob){
      if(!r.ok){ const j=await r.json().catch(()=>({})); throw new Error(errMsg(j,r)); }
      const blob=await r.blob();
      const url=URL.createObjectURL(blob);
      $("#toolOutput").textContent="✅ Fichier généré ("+(blob.size/1024).toFixed(1)+" Ko). Aperçu ci-dessous :";
      if(blob.type.startsWith("image/")){
        const img=document.createElement("img"); img.src=url; img.style.maxWidth="100%"; img.style.display="block"; img.style.marginTop="8px";
        $("#toolOutput").appendChild(img);
      }
      const a=$("#toolDownload"); a.href=url;
      const cd=r.headers.get("Content-Disposition")||""; const m=/filename="([^"]+)"/.exec(cd);
      if(m) a.download=m[1]; else a.download="resultat";
      $("#toolDownloadWrap").classList.remove("hidden");
    } else {
      const j=await r.json();
      if(!r.ok) throw new Error(errMsg(j,r));
      $("#toolOutput").textContent=fmt(j);
    }
    }
    recent=[t.id,...recent.filter(x=>x!==t.id)].slice(0,5);
    localStorage.setItem("tb_recent",JSON.stringify(recent)); renderRecent();
  }catch(e){ $("#toolError").textContent="❌ "+e.message; }
  finally{ $("#toolProgress").classList.add("hidden"); }
};

function fmt(j){
  if(j.result!==undefined) return typeof j.result==="string"?j.result:JSON.stringify(j.result,null,2);
  return JSON.stringify(j,null,2);
}

function errMsg(j,r){
  if(!j) return "HTTP "+r.status;
  if(typeof j.detail==="string") return j.detail;
  if(j.error && typeof j.error==="string") return j.error;
  try{ return JSON.stringify(j.detail||j).slice(0,400); }catch(e){ return "HTTP "+r.status; }
}

async function runYoutube(t){
  $("#toolProgress").classList.remove("hidden");
  try{
    const url=document.querySelector('[data-k="url"]').value.trim();
    const confirm=document.querySelector('[data-k="confirm_rights"]').checked;
    const sel=document.querySelector('[data-k="format_id"]');
    if(!url) throw new Error("Collez une URL YouTube.");
    if(!confirm) throw new Error("Cochez la confirmation de droits.");
    if(!sel.dataset.loaded){
      $("#toolOutput").textContent="⏳ Analyse de la vidéo…";
      const r=await fetch("/api/tools/media/formats",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url})});
      const j=await r.json();
      if(!r.ok) throw new Error(errMsg(j,r));
      if(!j.formats.length) throw new Error("Aucun format récupérable.");
      sel.innerHTML=j.formats.map(f=>`<option value="${f.id}">${f.resolution} • ${f.ext} • ${f.vcodec}/${f.acodec}${f.size_mo?" • "+f.size_mo+" Mo":""}</option>`).join("");
      sel.dataset.loaded="1";
      $("#toolOutput").textContent=`🎬 ${j.title} (${Math.round((j.duration_s||0)/60)} min)\nChoisissez un format puis cliquez Exécuter.`;
      return;
    }
    const fid=sel.value;
    const compat=document.querySelector('[data-k="compat_h264"]').checked;
    $("#toolOutput").textContent="⏳ Téléchargement lancé…";
    const r2=await fetch(t.ep,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url,format_id:fid,confirm_rights:true,compat_h264:compat})});
    const j2=await r2.json();
    if(!r2.ok) throw new Error(errMsg(j2,r2));
    for(let i=0;i<150;i++){
      await new Promise(res=>setTimeout(res,2000));
      const jj=await (await fetch("/api/tools/media/job/"+j2.job_id)).json();
      if(jj.status==="processing"||jj.status==="queued"){
        $("#toolOutput").textContent = jj.phase==="convert"
          ? `🎬 Conversion H264/AAC… ${jj.progress}%`
          : `⏳ Téléchargement… ${jj.progress}%${jj.speed?" • "+jj.speed:""}${jj.eta?" • ETA "+jj.eta+"s":""}`;
        continue;
      }
      if(jj.status==="completed"){
        $("#toolOutput").textContent=`✅ Terminé : ${jj.filename}`;
        const a=$("#toolDownload"); a.href="/api/tools/media/result/"+j2.job_id; a.download=jj.filename||"video.mp4";
        $("#toolDownloadWrap").classList.remove("hidden");
      } else throw new Error(jj.error||"Échec du téléchargement.");
      break;
    }
  }catch(e){ showYtError(e.message); }
  finally{ $("#toolProgress").classList.add("hidden"); }
}

function showYtError(msg){
  $("#toolError").textContent="❌ "+msg;
  if(/bot|sign in|captcha/i.test(msg)){
    const out=$("#toolOutput"); out.innerHTML="";
    const d=document.createElement("div");
    d.innerHTML=`<b>🤖 YouTube bloque l'IP du serveur (datacenter).</b><br><br><b>Méthode fiable :</b><ol><li>Crée un <b>compte Google jetable</b> (jamais ton compte principal).</li><li>Connecte-le sur youtube.com avec Firefox.</li><li>Exporte les cookies en format Netscape (extension « cookies.txt »).</li><li>Colle le contenu dans l'outil <b>🍪 Cookies YouTube → save</b>.</li><li>Relance le téléchargement.</li></ol>Docs officielles : <a href="https://github.com/yt-dlp/yt-dlp/wiki/FAQ" target="_blank" rel="noopener">FAQ cookies yt-dlp</a> • <a href="https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide" target="_blank" rel="noopener">Guide PO Token</a>`;
    out.appendChild(d);
  }
}

initTheme(); checkMe();
