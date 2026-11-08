/* Toolbox frontend vanilla JS — appelle uniquement l'API privée (session cookie). */
const $ = (s) => document.querySelector(s);

/* ---------- catalogue d'outils Phase 1+2 ---------- */
const ANIME_GENRES = [["Action","Action"],["Adventure","Aventure"],["Comedy","Comédie"],["Drama","Drame"],["Ecchi","Ecchi"],["Fantasy","Fantasy"],["Horror","Horreur"],["Mahou Shoujo","Magical girl"],["Mecha","Mecha"],["Music","Musique"],["Mystery","Mystère"],["Psychological","Psychologique"],["Romance","Romance"],["Sci-Fi","Sci-Fi"],["Slice of Life","Tranche de vie"],["Sports","Sport"],["Supernatural","Surnaturel"],["Thriller","Thriller"]];
const GENRE_OPTS = [{v:"",l:"Tous les genres"}, ...ANIME_GENRES.map(([v,l])=>({v,l}))];
const GENRE_LABEL = Object.fromEntries(ANIME_GENRES);
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
  {id:"qr", cat:"qr", icon:"🔲", name:"Générateur QR code", desc:"QR local → PNG.", fields:[{k:"text",label:"Texte / URL",type:"textarea"},{k:"size",label:"Taille case (4-20)",type:"number",def:10}], ep:"/api/tools/qr/generate", blob:true},
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
  {id:"word2pdf", cat:"pdf", icon:"📝", name:"Word → PDF", desc:"Convertit un document DOCX en PDF sur le serveur.", fields:[{k:"file",label:"Document Word (.docx, max 50 Mo)",type:"file",accept:".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"}], ep:"/api/tools/office/word-to-pdf", blob:true, multipart:true},
  {id:"pdf2word", cat:"pdf", icon:"📄", name:"PDF → Word", desc:"Convertit un PDF texte en document DOCX modifiable.", fields:[{k:"file",label:"PDF (max 100 pages, 50 Mo)",type:"file",accept:"application/pdf"}], ep:"/api/tools/office/pdf-to-word", blob:true, multipart:true, hint:"Les scans doivent d'abord passer par OCR. La mise en page peut demander des retouches."},
  {id:"pdfocr", cat:"pdf", icon:"🔎", name:"OCR de PDF scanné", desc:"Reconnaît le texte d'un scan et télécharge un fichier TXT.", fields:[{k:"file",label:"PDF scanné (max 20 pages, 50 Mo)",type:"file",accept:"application/pdf"},{k:"language",label:"Langue du document",type:"select",opts:[{v:"fra",l:"Français"},{v:"eng",l:"Anglais"},{v:"fra+eng",l:"Français + anglais"}],def:"fra"},{k:"dpi",label:"Qualité OCR",type:"select",opts:["100","150","200"],def:"150"}], ep:"/api/tools/office/ocr", blob:true, multipart:true},
  // Média
  {id:"ytmp3", cat:"media", icon:"▶️", name:"YouTube → MP3 (bêta)", desc:"Extrait une vidéo publique autorisée (20 min max) en MP3.", fields:[{k:"url",label:"Lien direct vers une vidéo YouTube",type:"text"},{k:"bitrate",label:"Qualité MP3",type:"select",opts:[{v:"128",l:"128 kb/s — fichier léger"},{v:"192",l:"192 kb/s — meilleure qualité"}],def:"128"},{k:"authorized",label:"Je confirme que le téléchargement de cette vidéo est explicitement autorisé.",type:"check",def:false}], ep:"/api/tools/youtube/mp3", blob:true, multipart:true, hint:"Bêta : 20 minutes maximum, un téléchargement à la fois. Le site privé ne change pas les conditions YouTube : utilisez uniquement un téléchargement explicitement autorisé."},
  {id:"mp3", cat:"media", icon:"🎵", name:"MP4 → MP3", desc:"Extrait l'audio (128/192/320 kbps). Upload max ~50 Mo.", fields:[{k:"file",label:"Vidéo",type:"file",accept:"video/*"},{k:"bitrate",label:"Qualité",type:"select",opts:["128","192","320"],def:"192"}], ep:"/api/tools/media/mp4-to-mp3", blob:true, multipart:true},
  // Manga / Animé (100 % légal)
  {id:"anime", cat:"anime", icon:"🎌", name:"Chercher un animé / manga", desc:"Fiche, note, genres et où regarder légalement (AniList).", fields:[
    {k:"query",label:"Titre (ex : Frieren)",type:"text"},
    {k:"type",label:"Type",type:"select",opts:[{v:"anime",l:"Animé"},{v:"manga",l:"Manga"}]},
    {k:"sort",label:"Trier par",type:"select",opts:[{v:"SEARCH_MATCH",l:"Pertinence"},{v:"POPULARITY_DESC",l:"Popularité"},{v:"SCORE_DESC",l:"Meilleure note"},{v:"START_DATE_DESC",l:"Plus récent"}]},
    {k:"genre",label:"Genre (optionnel)",type:"select",opts:GENRE_OPTS}
  ], ep:"/api/tools/anime/search", custom:"anime"},
  {id:"animeTrend", cat:"anime", icon:"🔥", name:"Tendances animé & manga", desc:"Les titres du moment, filtrables par genre.", fields:[
    {k:"type",label:"Type",type:"select",opts:[{v:"anime",l:"Animé"},{v:"manga",l:"Manga"}]},
    {k:"sort",label:"Tri",type:"select",opts:[{v:"TRENDING_DESC",l:"Tendances"},{v:"POPULARITY_DESC",l:"Popularité"},{v:"SCORE_DESC",l:"Meilleures notes"},{v:"START_DATE_DESC",l:"Nouveautés"}]},
    {k:"genre",label:"Genre (optionnel)",type:"select",opts:GENRE_OPTS}
  ], ep:"/api/tools/anime/discover", custom:"discover"},
  {id:"legal", cat:"anime", icon:"📚", name:"Plateformes légales", desc:"Gratuit ou abonnement : où regarder / lire.", fields:[], ep:"/api/tools/anime/legal", custom:"legal"},
];


const CATEGORY_LABELS = {all:"Tous les outils",favorites:"Favoris",texte:"Texte & code",calc:"Calculatrices",bio:"Bioinformatique",qr:"QR codes",img:"Images",pdf:"Documents",media:"Audio & vidéo",anime:"Manga & animé"};
const ICON_PATHS = {
 all:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
 favorites:'<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9Z"/>',
 texte:'<path d="m8 7-5 5 5 5m8-10 5 5-5 5m-3-13-2 16"/>',
 calc:'<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M8 6h8M8 11h2m4 0h2m-8 4h2m4 0h2m-8 4h2m4 0h2"/>',
 bio:'<path d="M7 2c0 10 10 10 10 20M17 2C17 12 7 12 7 22M8 5h8M9 9h6M9 15h6M8 19h8"/>',
 qr:'<path d="M3 3h6v6H3zm12 0h6v6h-6zM3 15h6v6H3zm12 0h3v3h3v3h-6z"/>',
 img:'<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 5-5 4 4 4-6 5 7"/>',
 pdf:'<path d="M14 2H5v20h14V7Zm0 0v5h5M8 12h8m-8 4h8"/>',
 media:'<path d="M9 18V5l12-2v13M9 9l12-2"/><ellipse cx="6" cy="18" rx="3" ry="3"/><ellipse cx="18" cy="16" rx="3" ry="3"/>',
 anime:'<path d="M12 5c-3-2-6-2-10-1v15c4-1 7-1 10 1 3-2 6-2 10-1V4c-4-1-7-1-10 1Zm0 0v15"/>'
};
function uiIcon(category){return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+ICON_PATHS[category]+'</svg>';}
document.querySelector('.sidebar').appendChild(document.querySelector('.cats'));
document.querySelectorAll('.cat').forEach(b=>{b.innerHTML=uiIcon(b.dataset.cat)+'<span>'+CATEGORY_LABELS[b.dataset.cat]+'</span>';b.setAttribute('aria-pressed',String(b.classList.contains('active')));});

let currentTool = null;
function storeGet(k, fb){ try{ const v=localStorage.getItem(k); return v==null?fb:JSON.parse(v); }catch(e){ return fb; } }
function storeSet(k,v){ try{ localStorage.setItem(k,JSON.stringify(v)); }catch(e){} }
const favs = new Set(storeGet("tb_favs",[]));
let recent = storeGet("tb_recent",[]);

/* ---------- thème ---------- */
const menuToggle=$('#menuToggle');
function closeMenu(){
  document.querySelector('.topbar').classList.remove('menu-open');
  menuToggle.setAttribute('aria-expanded','false');
}
menuToggle.onclick=()=>{
  const open=menuToggle.getAttribute('aria-expanded')!=='true';
  document.querySelector('.topbar').classList.toggle('menu-open',open);
  menuToggle.setAttribute('aria-expanded',String(open));
};
$('#topActions').addEventListener('click',e=>{if(e.target.closest('button'))closeMenu();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&menuToggle.getAttribute('aria-expanded')==='true'){closeMenu();menuToggle.focus();}});
function initTheme(){
  let t; try{ t=localStorage.getItem("tb_theme"); }catch(e){ t=null; }
  t=t||"light";
  document.documentElement.dataset.theme = t;
  $("#themeBtn").textContent = t==="dark"?"Mode clair":"Mode sombre";
}
$("#themeBtn").onclick = ()=>{
  const t = document.documentElement.dataset.theme==="dark"?"light":"dark";
  document.documentElement.dataset.theme=t; try{localStorage.setItem("tb_theme",t);}catch(e){}
  $("#themeBtn").textContent = t==="dark"?"Mode clair":"Mode sombre";
};

/* ---------- auth ---------- */
async function checkMe(){
  try{
    const r = await fetch("/api/me");
    if(r.ok){ const me=await r.json(); $("#adminBtn").classList.toggle("hidden",!me.is_admin); $("#loadBtn").classList.toggle("hidden",!me.is_admin); $("#profileBtn").classList.toggle("hidden",me.is_admin); showApp(); return true; }
  }catch(e){}
  showLogin(); refreshRegistration(); return false;
}
function showLogin(){ $("#loginView").classList.remove("hidden"); $("#appView").classList.add("hidden"); $("#logoutBtn").classList.add("hidden"); }
function showApp(){ $("#loginView").classList.add("hidden"); $("#appView").classList.remove("hidden"); $("#logoutBtn").classList.remove("hidden"); renderGrid("all",""); renderRecent(); }

$("#loginForm").addEventListener("submit", async (e)=>{
  e.preventDefault();
  $("#loginError").textContent="";
  const r = await fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({username:$("#loginUser").value,password:$("#loginPass").value})});
  const j = await r.json().catch(()=>({}));
  if(j.ok){ $("#loginPass").value=""; await checkMe(); }
  else $("#loginError").textContent = j.error || "Échec de connexion.";
});
$("#logoutBtn").onclick = async ()=>{ await fetch("/api/logout",{method:"POST"}); location.reload(); };

/* ---------- grille ---------- */
let curCat="all";
document.querySelectorAll(".cat").forEach(b=>b.onclick=()=>{
  document.querySelectorAll(".cat").forEach(x=>{x.classList.remove("active");x.setAttribute("aria-pressed","false");});
  b.setAttribute("aria-pressed","true");
  b.classList.add("active"); curCat=b.dataset.cat; renderGrid(curCat,$("#search").value);
});
$("#search").addEventListener("input",(e)=>renderGrid(curCat,e.target.value));

function renderGrid(cat,q){
  q=(q||"").toLowerCase();
  const grid=$("#toolsGrid"); grid.innerHTML="";
  const items=TOOLS.filter(t=> (cat==="all"||(cat==="favorites"&&favs.has(t.id))||t.cat===cat))
    .filter(t=> (t.name+t.desc+t.id).toLowerCase().includes(q))
    .sort((a,b)=> (favs.has(b.id)?1:0)-(favs.has(a.id)?1:0));
  $("#gridTitle").textContent=CATEGORY_LABELS[cat]||"Outils";
  $("#toolCount").textContent=items.length+" outil"+(items.length>1?"s":"");
  items.forEach(t=>{
      const btn=document.createElement("button");
      btn.className="tool";
      btn.innerHTML=`<span class="fav">${favs.has(t.id)?"★":"☆"}</span><div class="tool-icon">${uiIcon(t.cat)}</div><h4>${t.name}</h4><p>${t.desc}</p><span class="tool-arrow" aria-hidden="true">↗</span>`;
      btn.onclick=(ev)=>{
        if(ev.target.classList.contains("fav")){ toggleFav(t.id); ev.stopPropagation(); return; }
        openTool(t);
      };
      grid.appendChild(btn);
    });
  if(!items.length){ const empty=document.createElement("div"); empty.className="empty-state"; empty.innerHTML="<span>⌕</span><h3>"+(cat==="favorites"?"Pas encore de favoris":"Aucun outil trouvé")+"</h3><p>"+(cat==="favorites"?"Ajoute un outil avec ☆ pour le retrouver ici.":"Essaie avec un autre mot-clé.")+"</p>"; grid.appendChild(empty); }
}
function toggleFav(id){ favs.has(id)?favs.delete(id):favs.add(id); storeSet("tb_favs",[...favs]); renderGrid(curCat,$("#search").value); }
function renderRecent(){ const line=$("#recentLine"); line.innerHTML=""; if(!recent.length)return; const label=document.createElement("span"); label.textContent="Récemment utilisés"; line.append(label); recent.forEach(id=>{const t=TOOLS.find(x=>x.id===id);if(!t)return;const b=document.createElement("button");b.className="recent-chip";b.textContent=t.name;b.onclick=()=>openTool(t);line.append(b);}); }

/* ---------- modal outil ---------- */
function openTool(t){
  currentTool=t;
  $("#toolTitle").textContent=t.name;
  $("#toolDesc").textContent=(t.desc||"")+(t.hint?" — "+t.hint:"");
  resetOutput(); $("#toolError").textContent="";
  $("#toolDownloadWrap").classList.add("hidden");
  $("#toolFav").textContent=favs.has(t.id)?"★ Favori":"☆ Favori";
  const box=$("#toolFields"); box.innerHTML="";
  t.fields.forEach(f=>{
    const div=document.createElement("div"); div.className="field";
    if(f.type==="file"){ const mult=f.multiple?" multiple":""; const acc=f.accept?` accept="${f.accept}"`:" accept=\"image/*\""; div.innerHTML=`<label>${f.label}<input type="file"${mult}${acc} data-k="${f.k}"></label>`; }
    else if(f.type==="textarea") div.innerHTML=`<label>${f.label}<textarea data-k="${f.k}">${f.def||""}</textarea></label>`;
    else if(f.type==="select"){
      const opts=f.opts.map(o=>typeof o==="object"?o:{v:o,l:o});
      const def=f.def!==undefined?f.def:opts[0].v;
      div.innerHTML=`<label>${f.label}<select data-k="${f.k}">${opts.map(o=>`<option value="${esc(o.v)}" ${o.v===def?"selected":""}>${esc(o.l)}</option>`).join("")}</select></label>`;
    }
    else if(f.type==="check") div.innerHTML=`<label><input type="checkbox" data-k="${f.k}" ${f.def?"checked":""}> ${f.label}</label>`;
    else if(f.type==="number") div.innerHTML=`<label>${f.label}<input type="number" data-k="${f.k}" value="${f.def??""}"></label>`;
    else div.innerHTML=`<label>${f.label}<input type="text" data-k="${f.k}" value="${f.def||""}"></label>`;
    box.appendChild(div);
  });
  $("#toolModal").classList.remove("hidden");
  document.body.classList.add("modal-open");
  if(t.custom==="anime") loadDiscover();
}
function closeTool(){ $("#toolModal").classList.add("hidden"); document.body.classList.remove("modal-open"); }
$("#toolClose").onclick=closeTool;
$("#toolModal").addEventListener("click",(e)=>{ if(e.target.id==="toolModal") closeTool(); });
document.addEventListener("keydown",e=>{ if(e.key==="Escape")closeTool(); if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();$("#search").focus();} });
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

/* ---------- sorties : texte brut ou cartes riches ---------- */
function resetOutput(){
  const pre=$("#toolOutput"); pre.textContent=""; pre.classList.remove("hidden");
  $("#outputWrap").classList.add("hidden");
  const rich=$("#toolResults"); rich.innerHTML=""; rich.classList.add("hidden");
}
function richOut(){
  const pre=$("#toolOutput"); pre.textContent=""; pre.classList.add("hidden");
  const rich=$("#toolResults"); rich.innerHTML=""; rich.classList.remove("hidden"); return rich;
}
function loadingBox(msg){
  richOut().innerHTML=`<div class="anime-loading"><span class="spinner"></span><span>${esc(msg)}</span></div>`;
}

$("#toolRun").onclick=async ()=>{
  const t=currentTool; if(!t) return;
  $("#toolError").textContent="";
  $("#toolDownloadWrap").classList.add("hidden");
  resetOutput();
  let payload;
  try{ payload=collectPayload(t); }catch(e){ $("#toolError").textContent=e.message; return; }
  $("#toolProgress").classList.remove("hidden");
  $("#toolRun").disabled=true; $("#toolRun").textContent="Traitement…";
  const stopWorkload = watchWorkload(t);
  try{
    if(t.custom==="anime") await runAnime(payload);
    else if(t.custom==="discover") await runDiscover(payload,true);
    else if(t.custom==="legal") await runLegal();
    else {
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
        $("#toolOutput").textContent=fmt(j); $("#outputWrap").classList.remove("hidden");
      }
      else if(t.blob){
        if(!r.ok){ const j=await r.json().catch(()=>({})); throw new Error(errMsg(j,r)); }
        const blob=await r.blob();
        const url=URL.createObjectURL(blob);
        const box=richOut();
        box.innerHTML=`<p class="muted">✅ Fichier généré (${(blob.size/1024).toFixed(1)} Ko).</p>`;
        if(blob.type.startsWith("image/")){
          const img=document.createElement("img"); img.className="preview-img"; img.src=url; img.alt="Aperçu";
          box.appendChild(img);
        }
        const a=$("#toolDownload"); a.href=url;
        const cd=r.headers.get("Content-Disposition")||""; const m=/filename="([^"]+)"/.exec(cd);
        if(m) a.download=m[1]; else a.download="resultat";
        $("#toolDownloadWrap").classList.remove("hidden");
      } else {
        const j=await r.json();
        if(!r.ok) throw new Error(errMsg(j,r));
        $("#toolOutput").textContent=fmt(j); $("#outputWrap").classList.remove("hidden");
      }
    }
    recent=[t.id,...recent.filter(x=>x!==t.id)].slice(0,5);
    storeSet("tb_recent",recent); renderRecent();
  }catch(e){ $("#toolError").textContent="❌ "+e.message; }
  finally{ stopWorkload(); $("#toolProgress").classList.add("hidden"); $("#toolRun").disabled=false; $("#toolRun").textContent="Exécuter"; }
};

$("#copyOutput").onclick=async()=>{
  const value=$("#toolOutput").textContent;
  try{await navigator.clipboard.writeText(value); $("#copyOutput").textContent="Copié ✓"; setTimeout(()=>$("#copyOutput").textContent="Copier",1400);}
  catch(e){ $("#toolError").textContent="Copie indisponible dans ce navigateur."; }
};

function fmt(j){
  if(j.result!==undefined) return typeof j.result==="string"?j.result:JSON.stringify(j.result,null,2);
  return JSON.stringify(j,null,2);
}

/* ---------- manga / animé (AniList, 100 % légal) ---------- */
const FORMAT_LABEL={TV:"Série TV",TV_SHORT:"Format court",MOVIE:"Film",SPECIAL:"Spécial",OVA:"OVA",ONA:"ONA",MUSIC:"Clip",MANGA:"Manga",NOVEL:"Light novel",ONE_SHOT:"One-shot"};
const STATUS_LABEL={FINISHED:"Terminé",RELEASING:"En cours",NOT_YET_RELEASED:"À venir",CANCELLED:"Annulé",HIATUS:"En pause"};
const SORT_LABEL={TRENDING_DESC:"Tendances",POPULARITY_DESC:"Popularité",SCORE_DESC:"Meilleures notes",FAVOURITES_DESC:"Coups de cœur",START_DATE_DESC:"Nouveautés"};

let animeSeq=0;
function compact(n){ n=Number(n)||0; return n>=1000?(n/1000).toFixed(n>=10000?0:1).replace(".",",")+"k":String(n); }

function animeCard(m){
  const score=m.score==null?"":`<span class="anime-score ${m.score>=8?"hi":m.score>=6?"mid":"lo"}">${Number(m.score).toFixed(1)}</span>`;
  const cover=m.cover
    ?`<a class="anime-cover" href="${esc(m.anilist)}" target="_blank" rel="noopener"><img src="${esc(m.cover)}" alt="" loading="lazy" referrerpolicy="no-referrer">${score}</a>`
    :`<div class="anime-cover empty">${score||'<span class="muted">?</span>'}</div>`;
  const bits=[];
  if(m.year) bits.push(esc(String(m.year)));
  if(m.format) bits.push(esc(FORMAT_LABEL[m.format]||m.format));
  if(m.status) bits.push(`<span class="anime-status ${esc(String(m.status).toLowerCase())}">${esc(STATUS_LABEL[m.status]||m.status)}</span>`);
  const len=m.type==="manga"
    ? [m.chapters?`${m.chapters} chap.`:"", m.volumes?`${m.volumes} vol.`:""]
    : [m.episodes?`${m.episodes} ép.`:"", m.duration?`${m.duration} min`:""];
  len.filter(Boolean).forEach(x=>bits.push(esc(x)));
  if(m.favourites) bits.push(`❤ ${compact(m.favourites)}`);
  const chips=(m.genres||[]).map(g=>`<span class="anime-chip">${esc(GENRE_LABEL[g]||g)}</span>`).join("");
  const links=(m.streaming||[]).slice(0,4).map(s=>
    `<a class="anime-link${s.official?" official":""}" href="${esc(s.url)}" target="_blank" rel="noopener">${s.official?"✓ ":""}${esc(s.site)}</a>`);
  if(m.trailer) links.push(`<a class="anime-link ghost" href="${esc(m.trailer)}" target="_blank" rel="noopener">▶ Bande-annonce</a>`);
  if(m.anilist) links.push(`<a class="anime-link ghost" href="${esc(m.anilist)}" target="_blank" rel="noopener">AniList ↗</a>`);
  const warn=(m.streaming&&m.streaming.length)?"":`<p class="anime-warn">Aucun diffuseur officiel listé sur AniList pour ce titre — voir les plateformes légales.</p>`;
  return `<article class="anime-card">${cover}<div class="anime-body"><h4>${esc(m.title)}</h4>${m.alt?`<span class="anime-alt">${esc(m.alt)}</span>`:""}<p class="anime-meta">${bits.join(" · ")}</p>${chips?`<div class="anime-chips">${chips}</div>`:""}<p class="anime-desc">${esc(m.desc)}</p><div class="anime-links">${links.join("")}</div>${warn}</div></article>`;
}

function renderAnimeResults(list,heading,sub){
  const box=richOut();
  box.innerHTML=`<div class="anime-head-bar"><div><h4>${esc(heading)}</h4>${sub?`<p class="muted">${esc(sub)}</p>`:""}</div><span class="anime-legal">100 % légal</span></div><div class="anime-list">${list.map(animeCard).join("")}</div>${list.length?`<p class="anime-foot">Métadonnées et liens officiels fournis par AniList — aucun contenu piraté.</p>`:`<p class="anime-empty">Aucun résultat. Essayez le titre original (romaji) ou un autre genre.</p>`}`;
}

async function runAnime(payload){
  const seq=++animeSeq;
  loadingBox("Recherche sur AniList…");
  const r=await fetch("/api/tools/anime/search",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  const j=await r.json().catch(()=>({}));
  if(seq!==animeSeq) return;
  if(!r.ok) throw new Error(errMsg(j,r));
  renderAnimeResults(j.results||[], `Résultats pour « ${payload.query||""} »`, `${j.count||0} résultat(s) — ${payload.type==="manga"?"manga":"animé"}`);
}

async function runDiscover(payload={},fromTool=false,seq){
  seq=seq||++animeSeq;
  const type=payload.type==="manga"?"manga":"anime";
  loadingBox(type==="manga"?"Chargement des mangas…":"Chargement des animés…");
  const qs=new URLSearchParams({type,limit:"10"});
  if(fromTool&&payload.sort) qs.set("sort",payload.sort);
  if(fromTool&&payload.genre) qs.set("genre",payload.genre);
  const r=await fetch("/api/tools/anime/discover?"+qs.toString());
  const j=await r.json().catch(()=>({}));
  if(seq!==animeSeq) return;
  if(!r.ok) throw new Error(errMsg(j,r));
  const sort=(fromTool&&payload.sort)||"TRENDING_DESC";
  const genre=(fromTool&&payload.genre)?` · ${payload.genre}`:"";
  renderAnimeResults(j.results||[], `${SORT_LABEL[sort]||"Tendances"} ${type==="manga"?"manga":"animé"}${genre}`, "Sélection AniList mise à jour en continu");
}

async function loadDiscover(){
  const seq=++animeSeq;
  try{ await runDiscover({type:"anime"},false,seq); }
  catch(e){
    if(seq!==animeSeq) return;
    richOut().innerHTML='<p class="anime-empty">Tendances indisponibles pour le moment — lancez une recherche ou choisissez un genre.</p>';
  }
}

async function runLegal(){
  const seq=++animeSeq;
  loadingBox("Chargement des plateformes…");
  const r=await fetch("/api/tools/anime/legal");
  const j=await r.json().catch(()=>({}));
  if(seq!==animeSeq) return;
  if(!r.ok) throw new Error(errMsg(j,r));
  const card=p=>`<article class="anime-card platform"><div class="anime-body"><h4>${esc(p.name)}</h4><div class="anime-chips"><span class="anime-chip">${p.type==="manga"?"Manga":"Animé"}</span><span class="anime-chip">${p.free?"Gratuit":"Abonnement"}</span></div><p class="anime-desc">${esc(p.note)}</p><div class="anime-links"><a class="anime-link${p.free?" official":""}" href="${esc(p.url)}" target="_blank" rel="noopener">Ouvrir</a></div></div></article>`;
  const group=(title,list)=>list.length?`<h4 class="anime-section">${title}</h4><div class="platform-grid">${list.map(card).join("")}</div>`:"";
  richOut().innerHTML=`<div class="anime-head-bar"><div><h4>Plateformes légales</h4><p class="muted">Offres gratuites et par abonnement, sans lien pirate.</p></div><span class="anime-legal">100 % légal</span></div>${group("🎁 Gratuit",j.free||[])}${group("💳 Abonnement",j.paid||[])}<p class="anime-foot">Liste vérifiée à la main ; les catalogues évoluent avec le temps.</p>`;
}

function esc(s){ return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }

function errMsg(j,r){
  if(!j) return "HTTP "+r.status;
  if(typeof j.detail==="string") return j.detail;
  if(j.error && typeof j.error==="string") return j.error;
  try{ return JSON.stringify(j.detail||j).slice(0,400); }catch(e){ return "HTTP "+r.status; }
}




/* Account approval beta. No role is inferred from client storage. */
async function refreshRegistration(){
  try {const r=await fetch('/api/registration'); const j=await r.json(); $('#signupOpen').classList.toggle('hidden',!j.enabled);} catch(e){$('#signupOpen').classList.add('hidden');}
}
$('#signupOpen').onclick=()=>{$('#loginView').classList.add('hidden');$('#signupView').classList.remove('hidden');};
$('#signupBack').onclick=()=>{$('#signupView').classList.add('hidden');$('#signupPass').value='';showLogin();refreshRegistration();};
async function betaPost(path,payload){
  const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Toolbox-Request':'1'},body:JSON.stringify(payload)});
  const j=await r.json(); if(!r.ok)throw new Error(typeof j.detail==='string'?j.detail:j.error||'Demande impossible. Vérifiez les champs puis réessayez.');return j;
}
$('#signupForm').onsubmit=async e=>{
  e.preventDefault();const button=e.submitter;button.disabled=true;$('#signupMessage').textContent='Envoi…';
  try{const j=await betaPost('/api/register',{email:$('#signupUser').value,password:$('#signupPass').value});$('#signupPass').value='';$('#signupMessage').textContent=j.message;}
  catch(e){$('#signupMessage').textContent=e.message;}finally{button.disabled=false;}
};
let registrationEnabled=false;
function adminFeedback(message){
  const output=$('#adminMessage');
  output.textContent=message;
  output.scrollIntoView({block:'nearest'});
}
async function adminPost(path,payload){
  const input=$('#adminPassword');
  if(!input.value){
    adminFeedback('Saisissez votre mot de passe administrateur dans le champ de confirmation, puis cliquez de nouveau sur l’action souhaitée.');
    input.focus();
    return false;
  }
  adminFeedback('Traitement en cours…');
  try{
    await betaPost(path,{...payload,password:input.value});
    return true;
  }catch(e){
    adminFeedback(e.message);
    return false;
  }
}
async function refreshAccounts(){
  const r=await fetch('/api/admin/accounts');if(!r.ok)throw new Error('Accès administrateur indisponible. Reconnectez-vous.');
  const j=await r.json();registrationEnabled=j.enabled;
  $('#registrationToggle').textContent=j.enabled?'Fermer les demandes':'Ouvrir les demandes';
  $('#mailSetup').textContent=j.mail_ready?'Envoi d’e-mails configuré.':'Gmail à configurer : inscriptions et récupération indisponibles. Créez une adresse d’envoi puis renseignez les réglages SMTP sur le serveur.';
  $('#registrationToggle').disabled=!j.mail_ready&&!j.enabled;
  const stats=$('#accountStats');stats.replaceChildren();
  [['active','Actifs'],['pending','À approuver'],['unverified','E-mail à confirmer'],['suspended','Suspendus']].forEach(([state,label])=>{const card=document.createElement('article');card.className='load-stat';card.textContent=label+' : '+j.accounts.filter(a=>a.status===state).length;stats.append(card);});
  const list=$('#accountsList');list.replaceChildren();
  if(!j.accounts.length){const p=document.createElement('p');p.textContent='Aucune demande pour le moment.';list.append(p);}
  const labels={unverified:'Adresse à confirmer',pending:'En attente',active:'Actif',rejected:'Refusé',suspended:'Suspendu'};
  j.accounts.filter(a=>($('#accountFilter').value==='all'||a.status===$('#accountFilter').value)&&((a.email||'')+' '+a.username).toLowerCase().includes($('#accountSearch').value.toLowerCase())).forEach(account=>{
    const row=document.createElement('div');row.className='account-row';
    const description=document.createElement('div');description.textContent=(account.email||account.username)+' — '+labels[account.status]+' · conversions sur 1 h : '+(account.conversions_hour||0)+' / 10 · dernière connexion : '+(account.last_login?new Date(account.last_login*1000).toLocaleString('fr-FR'):'Jamais')+(account.expires<253402300799?' · demande expire le '+new Date(account.expires*1000).toLocaleDateString('fr-FR'):'');row.append(description);
    const actions=account.status==='unverified'?[['reject','Refuser']]:account.status==='pending'?[['approve','Approuver'],['reject','Refuser']]:account.status==='active'?[['suspend','Suspendre'],['revoke','Déconnecter']]:account.status==='suspended'?[['reactivate','Réactiver'],['delete','Supprimer']]:account.status==='rejected'?[['delete','Supprimer']]:[];
    actions.forEach(([action,label])=>{
      const b=document.createElement('button');b.type='button';b.textContent=label;
      b.onclick=async()=>{
        if(action==='delete'&&!confirm('Supprimer définitivement ce compte ?'))return;
        b.disabled=true;
        try{
          if(!await adminPost('/api/admin/accounts',{username:account.username,action}))return;
          const messages={approve:'Compte approuvé. La personne peut maintenant se connecter avec son adresse e-mail et son mot de passe.',reactivate:'Compte réactivé. La personne peut se reconnecter.',reject:'Demande refusée.',suspend:'Compte suspendu.',revoke:'Sessions du compte déconnectées.',delete:'Compte supprimé.'};
          adminFeedback(messages[action]);
          try{await refreshAccounts();}catch(e){adminFeedback(messages[action]+' Actualisez la liste pour voir le nouvel état.');}
        }finally{b.disabled=false;}
      };
      row.append(b);
    });list.append(row);
  });
  const audit=$('#accountAudit');audit.replaceChildren();j.audit.forEach(entry=>{const li=document.createElement('li');li.textContent=new Date(entry.created*1000).toLocaleString('fr-FR')+' · '+(j.accounts.find(a=>a.username===entry.username)?.email||entry.username)+' · '+(labels[entry.action]||entry.action);audit.append(li);});
}
$('#adminBtn').onclick=async()=>{$('#profileView').classList.add('hidden');stopLoad();$('#loadView').classList.add('hidden');$('#appView').classList.add('hidden');$('#adminView').classList.remove('hidden');try{await refreshAccounts();}catch(e){$('#adminMessage').textContent=e.message;}};
$('#adminBack').onclick=()=>{$('#adminView').classList.add('hidden');$('#adminPassword').value='';showApp();};
$('#registrationToggle').onclick=async()=>{const b=$('#registrationToggle');b.disabled=true;try{if(!await adminPost('/api/admin/registration',{enabled:!registrationEnabled}))return;adminFeedback('Réglage des inscriptions enregistré.');try{await refreshAccounts();}catch(e){adminFeedback('Réglage enregistré. Actualisez la liste pour voir le nouvel état.');}}finally{b.disabled=false;}};


/* Private, read-only service dashboard. */
let loadTimer=null;
function stopLoad(){clearTimeout(loadTimer);loadTimer=null;}
function sizeLabel(bytes){return bytes==null?'Indisponible':bytes>=1024**3?(bytes/1024**3).toFixed(1)+' Go':(bytes/1024**2).toFixed(0)+' Mo';}
function percentLabel(value){return value==null?'Mesure en cours…':value.toFixed(1)+' %';}
async function refreshLoad(){
  stopLoad();
  if($('#loadView').classList.contains('hidden')||document.hidden)return;
  try{
    const r=await fetch('/api/admin/load',{cache:'no-store'});if(!r.ok)throw new Error(r.status===403||r.status===401?'Accès réservé au propriétaire. Reconnectez-vous.':'Mesures indisponibles.');
    const m=await r.json();const stats=$('#loadStats');stats.replaceChildren();
    const values=[['Processeur · site',percentLabel(m.cpu_service_percent),'Part de la limite de '+(m.service.cpu_cores??'—')+' cœur(s)'],['Mémoire · site',sizeLabel(m.service.used),'/ '+sizeLabel(m.service.limit)+' autorisés'],['Processeur · VM',percentLabel(m.cpu_vm_percent),m.cpu_count+' cœurs au total'],['Mémoire · VM',sizeLabel(m.memory_vm.used),'/ '+sizeLabel(m.memory_vm.total)],['Disque disponible',sizeLabel(m.disk.free),'/ '+sizeLabel(m.disk.total)],['Conversions terminées',String(m.workload.completed),m.workload.failed+' échec(s) · '+m.workload.rejected+' refus de file']];
    values.forEach(([label,value,note])=>{const article=document.createElement('article');article.className='load-stat';const title=document.createElement('span');title.textContent=label;const number=document.createElement('strong');number.textContent=value;const detail=document.createElement('small');detail.textContent=note;article.append(title,number,detail);stats.append(article);});
    const queue=$('#loadQueue');queue.replaceChildren();
    const rows=[...(m.workload.running?[['En cours',m.workload.running]]:[]),...m.workload.waiting.map((entry,i)=>['En attente · '+(i+1),entry])];
    if(!rows.length){const p=document.createElement('p');p.textContent='Aucune conversion en cours.';queue.append(p);}
    rows.forEach(([state,entry])=>{const div=document.createElement('div');div.className='account-row';div.textContent=state+' — '+entry.user+' · '+entry.tool.split('/').slice(-2).join(' / ');queue.append(div);});
    $('#loadUpdated').textContent='Dernier relevé : '+new Date(m.sampled_at*1000).toLocaleTimeString('fr-FR');
  }catch(e){$('#loadUpdated').textContent=e.message;}
  if(!$('#loadView').classList.contains('hidden'))loadTimer=setTimeout(refreshLoad,5000);
}
$('#loadBtn').onclick=()=>{$('#adminPassword').value='';$('#profileView').classList.add('hidden');$('#appView').classList.add('hidden');$('#adminView').classList.add('hidden');$('#loadView').classList.remove('hidden');refreshLoad();};
$('#loadBack').onclick=()=>{stopLoad();$('#loadView').classList.add('hidden');showApp();};
document.addEventListener('visibilitychange',()=>{if(document.hidden)stopLoad();else if(!$('#loadView').classList.contains('hidden'))refreshLoad();});
function watchWorkload(tool){
  let timer=null,stopped=false,busy=false;
  const heavy=['pdf','img','media'].includes(tool.cat);
  const label=$('#workloadStatus');
  if(!heavy)return ()=>{};
  label.textContent='Envoi du fichier ou attente de votre tour…';label.classList.remove('hidden');
  const poll=async()=>{if(stopped||busy)return;busy=true;try{const r=await fetch('/api/tools/workload',{cache:'no-store'});if(r.ok){const j=await r.json();if(!stopped)label.textContent=j.state==='running'?'Conversion en cours…':j.state==='waiting'?'En attente — position '+j.position+' dans la file.':'Envoi du fichier ou finalisation…';}}catch(e){}finally{busy=false;if(!stopped)timer=setTimeout(poll,2000);}};
  timer=setTimeout(poll,1000);
  return ()=>{stopped=true;clearTimeout(timer);label.classList.add('hidden');};
}

$('#accountSearch').oninput=()=>refreshAccounts().catch(e=>$('#adminMessage').textContent=e.message);
$('#accountFilter').onchange=$('#accountsRefresh').onclick=()=>refreshAccounts().catch(e=>$('#adminMessage').textContent=e.message);
$('#recoverOpen').onclick=()=>{$('#loginView').classList.add('hidden');$('#recoveryView').classList.remove('hidden');};
$('#recoveryBack').onclick=()=>{$('#recoveryView').classList.add('hidden');showLogin();};
$('#recoveryForm').onsubmit=async e=>{e.preventDefault();const b=e.submitter;b.disabled=true;try{const j=await betaPost('/api/account/email-link',{email:$('#recoveryEmail').value,purpose:$('#recoveryPurpose').value});$('#recoveryMessage').textContent=j.message;}catch(e){$('#recoveryMessage').textContent=e.message;}finally{b.disabled=false;}};
$('#profileBtn').onclick=async()=>{stopLoad();['appView','adminView','loadView'].forEach(id=>$('#'+id).classList.add('hidden'));$('#profileView').classList.remove('hidden');try{const r=await fetch('/api/me');if(!r.ok)throw new Error('Reconnectez-vous.');const me=await r.json();$('#profileIdentity').textContent=(me.email||me.user)+(me.email&&!me.verified?' — Adresse à confirmer. Utilisez « Renvoyer la confirmation » sur la page de connexion.':'');$('#legacyEmailForm').classList.toggle('hidden',!!me.email);}catch(e){$('#profileMessage').textContent=e.message;}};
$('#profileBack').onclick=()=>{$('#profileView').classList.add('hidden');showApp();};
$('#legacyEmailForm').onsubmit=async e=>{e.preventDefault();const b=e.submitter;b.disabled=true;try{const j=await betaPost('/api/account/link-email',{email:$('#legacyEmail').value,password:$('#legacyPassword').value});$('#legacyPassword').value='';$('#profileMessage').textContent=j.message;$('#legacyEmailForm').classList.add('hidden');}catch(e){$('#profileMessage').textContent=e.message;}finally{b.disabled=false;}};
let accountLink=null;
$('#authLinkForm').onsubmit=async e=>{e.preventDefault();const b=e.submitter;b.disabled=true;try{if(!accountLink)throw new Error('Lien déjà utilisé.');const payload={...accountLink};payload.password=$('#resetPassword').value;const j=await betaPost('/api/account/confirm',payload);accountLink=null;$('#resetPassword').value='';$('#authLinkMessage').textContent=j.message;}catch(e){$('#authLinkMessage').textContent=e.message;}finally{b.disabled=false;}};
initTheme();
const linkParams=new URLSearchParams(location.hash.slice(1));
const linkPurpose=linkParams.has('verify')?'verify':linkParams.has('reset')?'reset':null;
if(linkPurpose){accountLink={purpose:linkPurpose,token:linkParams.get(linkPurpose)};history.replaceState(null,'',location.pathname+location.search);$('#authLinkView').classList.remove('hidden');$('#authLinkTitle').textContent=linkPurpose==='verify'?'Confirmer mon adresse':'Nouveau mot de passe';$('#resetPasswordText').textContent=linkPurpose==='verify'?'Mot de passe choisi pour votre compte':'Nouveau mot de passe';$('#resetPassword').minLength=linkPurpose==='verify'?8:15;$('#resetPassword').autocomplete=linkPurpose==='verify'?'current-password':'new-password';$('#resetPassword').required=true;}else checkMe();
