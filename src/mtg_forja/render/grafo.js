const IMG=(n,v)=>`https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(n).replace(/%20/g,'+')}&format=image&version=${v}&face=front`;
/* Escapa los datos que se meten en innerHTML. Misma política que guia.py y
   chuleta.py: los nombres y el texto de oráculo se escapan; el resumen y la
   estrategia van en crudo a propósito, porque pueden traer énfasis escrito. */
const E=t=>String(t==null?'':t).replace(/&/g,'&amp;').replace(/</g,'&lt;')
  .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#x27;');
const CARDS=DATOS.cartas, LINKS=DATOS.enlaces, ROL=DATOS.roles;
const keys=Object.keys(CARDS);
const svg=document.getElementById('svg'), NS="http://www.w3.org/2000/svg";
const nodes={},vecinos={};
keys.forEach(k=>vecinos[k]=[]);
LINKS.forEach((l,i)=>{l.i=i;if(vecinos[l.a])vecinos[l.a].push(l);if(vecinos[l.b])vecinos[l.b].push(l)});
let W=svg.clientWidth||1000,H=svg.clientHeight||700;
keys.forEach((k,i)=>{const a=i/keys.length*Math.PI*2;
  nodes[k]={k,x:W/2+Math.cos(a)*Math.min(W,H)*.33,y:H/2+Math.sin(a)*Math.min(W,H)*.33,
    vx:0,vy:0,r:16+Math.min(CARDS[k].copias,6)*2.2}});
const gRoot=document.createElementNS(NS,'g');svg.appendChild(gRoot);
const gL=document.createElementNS(NS,'g'),gE=document.createElementNS(NS,'g'),gN=document.createElementNS(NS,'g');
gRoot.append(gL,gE,gN);
const defs=document.createElementNS(NS,'defs');svg.appendChild(defs);
const elL=[],elE=[],elN={};
LINKS.forEach(l=>{
  const ln=document.createElementNS(NS,'line');
  ln.setAttribute('class','enlace'+(l.m?' mana':(l.r?' riesgo':''))+(!l.m&&l.f>=3?' fuerte':''));
  gL.appendChild(ln);elL.push(ln);
  const tx=document.createElementNS(NS,'text');
  tx.setAttribute('class','etq'+(l.r?' riesgo':''));tx.setAttribute('text-anchor','middle');
  tx.textContent=l.t;tx.style.display='none';gE.appendChild(tx);elE.push(tx)});
keys.forEach(k=>{
  const C=CARDS[k],n=nodes[k],g=document.createElementNS(NS,'g');
  g.setAttribute('class','nodo');
  const cp=document.createElementNS(NS,'clipPath'),id='cp-'+encodeURIComponent(k).replace(/%/g,'');
  cp.setAttribute('id',id);
  const cc=document.createElementNS(NS,'circle');cc.setAttribute('r',n.r-3);cp.appendChild(cc);
  defs.appendChild(cp);
  const aro=document.createElementNS(NS,'circle');
  aro.setAttribute('class','aro');aro.setAttribute('r',n.r);
  aro.setAttribute('stroke',(ROL[C.rol]||{}).c||'#888');
  const im=document.createElementNS(NS,'image');
  im.setAttribute('href',IMG(k,'art_crop'));
  im.setAttribute('x',-(n.r-3));im.setAttribute('y',-(n.r-3));
  im.setAttribute('width',(n.r-3)*2);im.setAttribute('height',(n.r-3)*2);
  im.setAttribute('preserveAspectRatio','xMidYMid slice');
  im.setAttribute('clip-path','url(#'+id+')');
  const bg=document.createElementNS(NS,'circle');
  bg.setAttribute('class','cntbg');bg.setAttribute('r',9);
  bg.setAttribute('cx',n.r*.72);bg.setAttribute('cy',-n.r*.72);
  const ct=document.createElementNS(NS,'text');
  ct.setAttribute('class','cnt');ct.setAttribute('x',n.r*.72);ct.setAttribute('y',-n.r*.72+4);
  ct.textContent=C.copias;
  const nm=document.createElementNS(NS,'text');
  nm.setAttribute('class','nom');nm.setAttribute('y',n.r+15);nm.textContent=C.corto;
  g.append(aro,im,bg,ct,nm);gN.appendChild(g);elN[k]=g;
  g.addEventListener('click',ev=>{ev.stopPropagation();sel(k)});
  g.addEventListener('pointerdown',ev=>arrastre(ev,n))});
let alpha=1;
function tick(){
  W=svg.clientWidth;H=svg.clientHeight;
  if(alpha<=0){pintar();requestAnimationFrame(tick);return}
  const cx=W/2,cy=H/2;
  for(let i=0;i<keys.length;i++){const a=nodes[keys[i]];
    for(let j=i+1;j<keys.length;j++){const b=nodes[keys[j]];
      let dx=b.x-a.x,dy=b.y-a.y,d2=dx*dx+dy*dy;if(d2<1)d2=1;
      const d=Math.sqrt(d2),min=a.r+b.r+26;let f=9000/d2;
      if(d<min)f+=(min-d)*.55;
      const fx=dx/d*f,fy=dy/d*f;a.vx-=fx;a.vy-=fy;b.vx+=fx;b.vy+=fy}}
  LINKS.forEach(l=>{const a=nodes[l.a],b=nodes[l.b];if(!a||!b)return;
    const L=l.f>=3?128:l.f===2?168:205;
    let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,f=(d-L)*.012;
    a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f});
  keys.forEach(k=>{const n=nodes[k];
    n.vx+=(cx-n.x)*.0022;n.vy+=(cy-n.y)*.0030;
    if(n.fijo){n.vx=n.vy=0;return}
    n.vx*=.78;n.vy*=.78;n.x+=n.vx*alpha;n.y+=n.vy*alpha;
    const m=n.r+22;
    n.x=Math.max(m,Math.min(W-m,n.x));n.y=Math.max(m+76,Math.min(H-m-16,n.y))});
  alpha*=.982;
  if(alpha<.02){alpha=0;keys.forEach(k=>{nodes[k].vx=0;nodes[k].vy=0})}
  pintar();requestAnimationFrame(tick)}
function pintar(){
  LINKS.forEach((l,i)=>{const a=nodes[l.a],b=nodes[l.b],el=elL[i];if(!a||!b)return;
    el.setAttribute('x1',a.x);el.setAttribute('y1',a.y);
    el.setAttribute('x2',b.x);el.setAttribute('y2',b.y);
    const t=elE[i];
    if(t.style.display!=='none'){t.setAttribute('x',(a.x+b.x)/2);t.setAttribute('y',(a.y+b.y)/2-6)}});
  keys.forEach(k=>elN[k].setAttribute('transform',`translate(${nodes[k].x},${nodes[k].y})`))}
requestAnimationFrame(tick);
function arrastre(ev,n){ev.preventDefault();svg.classList.add('arrastrando');n.fijo=true;
  const mover=e=>{const p=pt(e);n.x=p.x;n.y=p.y;alpha=Math.max(alpha,.55)};
  const soltar=()=>{n.fijo=false;svg.classList.remove('arrastrando');
    window.removeEventListener('pointermove',mover);window.removeEventListener('pointerup',soltar)};
  window.addEventListener('pointermove',mover);window.addEventListener('pointerup',soltar)}
window.addEventListener('resize',()=>{alpha=Math.max(alpha,.5)});
let zoom=1,px=0,py=0;
function pt(e){const r=svg.getBoundingClientRect();
  return{x:(e.clientX-r.left-px)/zoom,y:(e.clientY-r.top-py)/zoom}}
svg.addEventListener('wheel',e=>{e.preventDefault();
  const r=svg.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
  const z2=Math.max(.5,Math.min(2.2,zoom*(e.deltaY<0?1.12:.89)));
  px=mx-(mx-px)*(z2/zoom);py=my-(my-py)*(z2/zoom);zoom=z2;
  gRoot.setAttribute('transform',`translate(${px},${py}) scale(${zoom})`)},{passive:false});
let filtro=null;const chips=document.getElementById('chips');
Object.keys(ROL).forEach(r=>{
  if(!keys.some(k=>CARDS[k].rol===r))return;
  const b=document.createElement('button');b.className='chip';b.textContent=ROL[r].n;
  b.onclick=()=>{filtro=filtro===r?null:r;
    [...chips.children].forEach(c=>c.classList.remove('act'));
    if(filtro)b.classList.add('act');aplicar()};
  chips.appendChild(b)});
let activo=null;
function aplicar(){
  keys.forEach(k=>{const g=elN[k];g.classList.remove('sel','off');
    if(activo){if(k===activo)g.classList.add('sel');
      else if(!vecinos[activo].some(l=>l.a===k||l.b===k))g.classList.add('off')}
    else if(filtro&&CARDS[k].rol!==filtro)g.classList.add('off')});
  LINKS.forEach((l,i)=>{const el=elL[i],t=elE[i];el.classList.remove('on','off');
    const rel=activo&&(l.a===activo||l.b===activo);
    if(activo){rel?el.classList.add('on'):el.classList.add('off');t.style.display=rel?'':'none'}
    else{t.style.display='none';
      if(filtro&&CARDS[l.a]&&CARDS[l.b]&&CARDS[l.a].rol!==filtro&&CARDS[l.b].rol!==filtro)
        el.classList.add('off')}})}
svg.addEventListener('click',()=>{activo=null;aplicar();vacio()});
const panel=document.getElementById('panel');
function vacio(){
  const peso=k=>vecinos[k].filter(l=>!l.m).length;
  const top=keys.slice().filter(k=>peso(k)>0).sort((a,b)=>peso(b)-peso(a)).slice(0,6);
  panel.innerHTML=`<h3 style="margin-top:0">Cómo se lee</h3>
   <p class="bloq">Cada círculo es una carta y su tamaño depende de las <b>copias</b> que llevas.
   El grosor de la línea marca la fuerza de la sinergia; las
   <b style="color:var(--brasa)">líneas rojas discontinuas</b> son cartas que se estorban.</p>
   <p class="bloq">Pulsa cualquier carta para ver sus conexiones. Puedes arrastrarlas, hacer zoom
   con la rueda y filtrar por función.</p>
   <h3>Los nudos del mazo</h3>
   ${top.map(k=>`<button class="conn" data-k="${encodeURIComponent(k)}">
     <img loading="lazy" src="${IMG(k,'small')}" alt="">
     <span><span class="pill">${peso(k)} conexiones</span>
     <span class="qn">${E(k)}</span></span></button>`).join('')}`;
  enlazar()}
function enlazar(){panel.querySelectorAll('.conn').forEach(b=>
  b.onclick=()=>sel(decodeURIComponent(b.dataset.k)))}
function sel(k){
  if(!CARDS[k])return;
  activo=k;aplicar();
  const C=CARDS[k];
  const conns=vecinos[k].slice().sort((a,b)=>(a.r?1:0)-(b.r?1:0)||b.f-a.f);
  const fila=l=>{const o=l.a===k?l.b:l.a;
    return `<button class="conn" data-k="${encodeURIComponent(o)}">
      <img loading="lazy" src="${IMG(o,'small')}" alt="">
      <span><span class="pill${l.r?' r':''}">${E(l.t)}${l.r?'':' · '+'★'.repeat(l.f)}</span>
      <span class="qn">${E(o)}</span><span class="qd">${l.d}</span></span></button>`};
  const buenas=conns.filter(l=>!l.r&&!l.m),malas=conns.filter(l=>l.r),manas=conns.filter(l=>l.m);
  panel.innerHTML=`<img class="carta-img" src="${IMG(k,'normal')}" alt="">
    <p class="rolcap" style="color:${(ROL[C.rol]||{}).c}">${(ROL[C.rol]||{}).n||''}</p>
    <h2>${E(k)}</h2>
    <p class="meta">${C.copias} copias · ${E(C.coste||C.tipo)} · ${conns.length} conexiones</p>
    ${C.estrategia?`<p class="bloq">${C.estrategia}</p>`:''}
    ${C.evidencia?`<p class="ev">${E(C.evidencia)}</p>`:''}
    ${buenas.length?'<h3>Combina con</h3>'+buenas.map(fila).join(''):''}
    ${malas.length?'<h3 class="r">Se estorba con</h3>'+malas.map(fila).join(''):''}
    ${manas.length?'<h3>Maná</h3>'+manas.map(fila).join(''):''}`;
  panel.scrollTop=0;enlazar()}
vacio();
