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
  // Média
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
  // Bientôt
  {id:"office", cat:"soon", icon:"📝", name:"Word/PDF + OCR (bientôt)", desc:"LibreOffice, Tesseract…", soon:true},
  {id:"ai", cat:"soon", icon:"🤖", name:"IA (Phase 6, optionnel)", desc:"Résumé, QCM… désactivé.", soon:true},
];

let currentTool = null;
function storeGet(k, fb){ try{ const v=localStorage.getItem(k); return v==null?fb:JSON.parse(v); }catch(e){ return fb; } }
function storeSet(k,v){ try{ localStorage.setItem(k,JSON.stringify(v)); }catch(e){} }
const favs = new Set(storeGet("tb_favs",[]));
let recent = storeGet("tb_recent",[]);

/* ---------- thème ---------- */
function initTheme(){
  let t; try{ t=localStorage.getItem("tb_theme"); }catch(e){ t=null; }
  t=t||"light";
  document.documentElement.dataset.theme = t;
  $("#themeBtn").textContent = t==="dark"?"☀️":"🌙";
}
$("#themeBtn").onclick = ()=>{
  const t = document.documentElement.dataset.theme==="dark"?"light":"dark";
  document.documentElement.dataset.theme=t; try{localStorage.setItem("tb_theme",t);}catch(e){}
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
        if(t.soon){ alert("Prévu dans une phase suivante."); return; }
        openTool(t);
      };
      grid.appendChild(btn);
    });
}
function toggleFav(id){ favs.has(id)?favs.delete(id):favs.add(id); storeSet("tb_favs",[...favs]); renderGrid(curCat,$("#search").value); }
function renderRecent(){ $("#recentLine").textContent = recent.length? "🕘 Récents : "+recent.map(id=>{const t=TOOLS.find(x=>x.id===id);return t?t.name:id;}).join(" • ") : ""; }

/* ---------- modal outil ---------- */
function openTool(t){
  currentTool=t;
  $("#toolTitle").textContent=t.icon+" "+t.name;
  $("#toolDesc").textContent=(t.desc||"")+(t.hint?" Hint: "+t.hint:"");
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
  if(t.custom==="anime") loadDiscover();
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

/* ---------- sorties : texte brut ou cartes riches ---------- */
function resetOutput(){
  const pre=$("#toolOutput"); pre.textContent=""; pre.classList.remove("hidden");
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
        $("#toolOutput").textContent=fmt(j);
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
        $("#toolOutput").textContent=fmt(j);
      }
    }
    recent=[t.id,...recent.filter(x=>x!==t.id)].slice(0,5);
    storeSet("tb_recent",recent); renderRecent();
  }catch(e){ $("#toolError").textContent="❌ "+e.message; }
  finally{ $("#toolProgress").classList.add("hidden"); }
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

initTheme(); checkMe();
