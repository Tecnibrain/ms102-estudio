'use strict';
/* ====== MD-102 Estudio · PWA ====== */
const DATA_URL = 'data/preguntas.json';
const IMG = 'data/img/';
const BOX_DAYS = {1:0, 2:1, 3:3, 4:7, 5:16};   // Leitner
const DAY = 86400000;

let QUESTIONS = [];
let BY_ID = {};
let session = null;

/* ---------- storage ---------- */
const store = {
  get(k, def){ try{ return JSON.parse(localStorage.getItem(k)) ?? def; }catch(e){ return def; } },
  set(k, v){ localStorage.setItem(k, JSON.stringify(v)); }
};
function prog(){ return store.get('ms102_progress', {}); }
function saveProg(p){ store.set('ms102_progress', p); }
function settings(){ return store.get('ms102_settings', {daily:3}); }

function recordAnswer(id, ok){
  const p = prog();
  const r = p[id] || {box:1, correct:0, wrong:0, seen:0};
  r.seen++;
  if(ok){ r.correct++; r.box = Math.min(5, r.box+1); }
  else  { r.wrong++;  r.box = 1; }
  r.last = Date.now();
  p[id] = r;
  saveProg(p);
}

/* ---------- selección de preguntas ---------- */
function isDue(id){
  const r = prog()[id];
  if(!r) return true;
  return (Date.now() - (r.last||0)) >= BOX_DAYS[r.box]*DAY;
}
function pool(temaFilter){
  return QUESTIONS.filter(q => !temaFilter || q.tema === temaFilter);
}
function pickDaily(n, temaFilter){
  const p = prog();
  let cand = pool(temaFilter);
  // 1) vencidas ya vistas (prioriza caja baja y más antiguas)
  const due = cand.filter(q => p[q.id] && isDue(q.id))
                  .sort((a,b)=> (p[a.id].box-p[b.id].box) || ((p[a.id].last||0)-(p[b.id].last||0)));
  // 2) nuevas
  const fresh = shuffle(cand.filter(q => !p[q.id]));
  let out = [...due, ...fresh].slice(0, n);
  if(out.length < n){ // rellenar con cualquiera al azar
    const rest = shuffle(cand.filter(q => !out.includes(q)));
    out = out.concat(rest.slice(0, n - out.length));
  }
  return out;
}
function pickReview(temaFilter){
  const p = prog();
  return shuffle(pool(temaFilter).filter(q => p[q.id] && p[q.id].box <= 2));
}
function shuffle(a){ a=a.slice(); for(let i=a.length-1;i>0;i--){const j=(Math.random()*(i+1))|0;[a[i],a[j]]=[a[j],a[i]];} return a; }

/* ---------- streak / daily state ---------- */
function todayKey(){ const d=new Date(); return d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate(); }
function markDailyDone(){
  const st = store.get('ms102_streak', {count:0, last:null});
  const tk = todayKey();
  if(st.last === tk) return st.count;
  const y = new Date(Date.now()-DAY); const yk = y.getFullYear()+'-'+(y.getMonth()+1)+'-'+y.getDate();
  st.count = (st.last === yk) ? st.count+1 : 1;
  st.last = tk; store.set('ms102_streak', st);
  return st.count;
}
function dailyDoneToday(){ return store.get('ms102_daily',{}).date === todayKey(); }

/* ---------- vistas ---------- */
const V = id => document.getElementById(id);
function show(view){
  ['view-home','view-quiz','view-stats','view-end'].forEach(v=>V(v).classList.add('hidden'));
  V(view).classList.remove('hidden');
  window.scrollTo(0,0);
}

/* ---------- HOME ---------- */
function renderHome(){
  const p = prog();
  const total = QUESTIONS.length;
  const done = Object.keys(p).length;
  const mastered = Object.values(p).filter(r=>r.box>=4).length;
  const pct = total? Math.round(mastered/total*100):0;
  V('h-total').textContent = total;
  V('h-done').textContent = done;
  V('h-streak').textContent = store.get('ms102_streak',{count:0}).count;
  V('ring-pct').textContent = pct+'%';
  const C = 2*Math.PI*52;
  V('ring-fg').style.strokeDashoffset = C - C*pct/100;
  const rev = QUESTIONS.filter(q=>p[q.id]&&p[q.id].box<=2).length;
  V('review-count').textContent = rev? rev+' pendientes' : '';
  V('daily-sub').textContent = dailyDoneToday()? '· ✅ hecho hoy' : '';
  // segment
  const s = settings();
  document.querySelectorAll('#daily-seg button').forEach(b=>b.classList.toggle('on', +b.dataset.n===s.daily));
  // temas
  const sel = V('filter-tema');
  if(sel.options.length<=1){
    [...new Set(QUESTIONS.map(q=>q.tema))].sort().forEach(t=>{
      const o=document.createElement('option'); o.value=t; o.textContent=t; sel.appendChild(o);
    });
  }
}

/* ---------- iniciar sesión de quiz ---------- */
function start(mode){
  const tema = V('filter-tema').value;
  const n = settings().daily;
  let queue;
  if(mode==='daily'){
    const saved = store.get('ms102_daily',{});
    if(saved.date===todayKey() && saved.ids && saved.ids.length){
      queue = saved.ids.map(id=>BY_ID[id]).filter(Boolean);
    }else{
      queue = pickDaily(n, tema);
      store.set('ms102_daily',{date:todayKey(), ids:queue.map(q=>q.id)});
    }
  } else if(mode==='review'){
    queue = pickReview(tema).slice(0, Math.max(n,10));
    if(!queue.length){ alert('¡No tienes preguntas falladas para repasar! 🎉'); return; }
  } else {
    queue = shuffle(pool(tema)).slice(0, Math.max(n,10));
  }
  session = {mode, queue, idx:0, correct:0};
  show('view-quiz');
  renderQuestion();
}

/* ---------- render pregunta ---------- */
function renderQuestion(){
  const q = session.queue[session.idx];
  const total = session.queue.length;
  V('quiz-count').textContent = (session.idx+1)+'/'+total;
  V('progress-fill').style.width = (session.idx/total*100)+'%';
  V('q-footer').classList.add('hidden');
  V('verdict').className='verdict'; V('verdict').textContent='';

  const c = V('q-container');
  let h = `<div class="qcard"><span class="q-id">#${q.id}</span>`+
          `<span class="q-tema">${q.tema}</span>`+
          `<p class="q-stem">${esc(q.stem)}</p>`;
  (q.context_images||[]).forEach(im=> h+=`<img class="q-img" src="${IMG}${im}" alt="tabla">`);

  if(q.type==='mc' && q.options.length){
    const multi = q.correct.length>1;
    if(multi) h+=`<p class="self-ask">Selecciona ${q.correct.length} opciones</p>`;
    h+=`<div class="opts">`;
    q.options.forEach(o=>{
      h+=`<button class="opt" data-k="${o.letter}"><span class="k">${o.letter}</span><span>${esc(o.text)}</span></button>`;
    });
    h+=`</div>`;
    if(multi) h+=`<button class="check-btn" id="check">Comprobar</button>`;
    c.innerHTML=h+`</div>`;
    wireMC(q, multi);
  } else {
    // tipo imagen -> flashcard
    h+=`<button class="reveal-btn" id="reveal">👁️ Ver respuesta</button><div class="ans-wrap" id="answ"></div></div>`;
    c.innerHTML=h;
    V('reveal').onclick=()=>{
      const a=V('answ');
      a.innerHTML=(q.answer_images||[]).map(im=>`<img class="q-img" src="${IMG}${im}" alt="respuesta">`).join('')
        + `<div class="self-ask">¿Respondiste correctamente?<div class="self-btns">
             <button class="self-no" data-ok="0">Fallé</button>
             <button class="self-yes" data-ok="1">Acerté</button></div></div>`;
      V('reveal').style.display='none';
      a.querySelectorAll('[data-ok]').forEach(b=>b.onclick=()=>{
        const ok=b.dataset.ok==='1'; recordAnswer(q.id, ok);
        if(ok) session.correct++;
        verdict(ok); nextEnabled();
      });
    };
  }
}
function wireMC(q, multi){
  const correct = new Set(q.correct);
  const btns=[...document.querySelectorAll('.opt')];
  if(!multi){
    btns.forEach(b=>b.onclick=()=>{
      const ok = correct.has(b.dataset.k);
      btns.forEach(x=>{ x.disabled=true;
        if(correct.has(x.dataset.k)) x.classList.add('correct'); });
      if(!ok) b.classList.add('wrong');
      recordAnswer(q.id, ok); if(ok) session.correct++;
      verdict(ok); nextEnabled();
    });
  }else{
    btns.forEach(b=>b.onclick=()=>{ if(!b.disabled) b.classList.toggle('sel'); });
    V('check').onclick=()=>{
      const sel=new Set(btns.filter(b=>b.classList.contains('sel')).map(b=>b.dataset.k));
      const ok = sel.size===correct.size && [...sel].every(k=>correct.has(k));
      btns.forEach(x=>{ x.disabled=true;
        if(correct.has(x.dataset.k)) x.classList.add('correct');
        else if(x.classList.contains('sel')) x.classList.add('wrong'); });
      V('check').style.display='none';
      recordAnswer(q.id, ok); if(ok) session.correct++;
      verdict(ok); nextEnabled();
    };
  }
}
function verdict(ok){
  const v=V('verdict'); v.textContent = ok?'✅ ¡Correcto!':'❌ Incorrecto';
  v.className='verdict '+(ok?'ok':'bad');
}
function nextEnabled(){
  V('q-footer').classList.remove('hidden');
  V('btn-next').textContent = (session.idx+1>=session.queue.length)?'Finalizar':'Siguiente →';
}
V('btn-next').onclick=()=>{
  session.idx++;
  if(session.idx>=session.queue.length){ endSession(); }
  else renderQuestion();
};

function endSession(){
  V('progress-fill').style.width='100%';
  const {correct,queue,mode}=session;
  const pct=Math.round(correct/queue.length*100);
  let streak=null;
  if(mode==='daily'){ streak=markDailyDone(); store.set('ms102_daily',{date:todayKey(),ids:queue.map(q=>q.id),done:true}); }
  V('end-emoji').textContent = pct>=80?'🏆':pct>=50?'💪':'📚';
  V('end-title').textContent = pct>=80?'¡Excelente!':pct>=50?'¡Buen trabajo!':'¡A seguir practicando!';
  V('end-score').innerHTML = `Acertaste <b>${correct}/${queue.length}</b> (${pct}%)`+
      (streak?`<br>🔥 Racha: ${streak} día${streak>1?'s':''}`:'');
  show('view-end');
}

/* ---------- STATS ---------- */
function renderStats(){
  const p=prog(), total=QUESTIONS.length;
  const done=Object.keys(p).length;
  const mastered=Object.values(p).filter(r=>r.box>=4).length;
  const totC=Object.values(p).reduce((s,r)=>s+r.correct,0);
  const totW=Object.values(p).reduce((s,r)=>s+r.wrong,0);
  const acc = (totC+totW)? Math.round(totC/(totC+totW)*100):0;
  const temas={};
  QUESTIONS.forEach(q=>{ temas[q.tema]=temas[q.tema]||{t:0,m:0}; temas[q.tema].t++;
    if(p[q.id]&&p[q.id].box>=4) temas[q.tema].m++; });
  let h=`<div class="card"><div class="big-num">${Math.round(mastered/total*100)}%</div>
    <div style="color:var(--muted)">dominado (${mastered}/${total})</div></div>
    <div class="card" style="display:flex;gap:20px">
      <div><div class="big-num" style="font-size:28px">${done}</div><small style="color:var(--muted)">respondidas</small></div>
      <div><div class="big-num" style="font-size:28px">${acc}%</div><small style="color:var(--muted)">precisión</small></div>
      <div><div class="big-num" style="font-size:28px">${store.get('ms102_streak',{count:0}).count}</div><small style="color:var(--muted)">🔥 racha</small></div>
    </div><div class="card"><b>Por tema</b>`;
  Object.entries(temas).forEach(([t,v])=>{
    const pc=Math.round(v.m/v.t*100);
    h+=`<div class="tema-row"><span class="name">${t}</span>
        <span class="bar"><i style="width:${pc}%"></i></span><b>${pc}%</b></div>`;
  });
  h+=`</div>`;
  V('stats-body').innerHTML=h;
}

function esc(s){ return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

/* ---------- eventos ---------- */
V('btn-daily').onclick=()=>start('daily');
document.querySelectorAll('.tile').forEach(t=>t.onclick=()=>start(t.dataset.mode));
V('btn-back').onclick=()=>{show('view-home');renderHome();};
V('btn-back2').onclick=()=>{show('view-home');renderHome();};
V('btn-stats').onclick=()=>{renderStats();show('view-stats');};
V('btn-home').onclick=()=>{show('view-home');renderHome();};
V('btn-again').onclick=()=>start(session?session.mode:'practice');
V('btn-reset').onclick=()=>{ if(confirm('¿Borrar todo tu progreso?')){ localStorage.clear(); renderStats(); } };
document.querySelectorAll('#daily-seg button').forEach(b=>b.onclick=()=>{
  const s=settings(); s.daily=+b.dataset.n; store.set('ms102_settings',s); renderHome();
});

/* ---------- init ---------- */
function boot(d){ QUESTIONS=d; d.forEach(q=>BY_ID[q.id]=q); renderHome(); }
function loadOffline(){   // fallback para file:// (sin servidor): usa data/preguntas.js
  if(window.MS102_DATA){ boot(window.MS102_DATA); return; }
  const s=document.createElement('script'); s.src='data/preguntas.js';
  s.onload=()=>window.MS102_DATA?boot(window.MS102_DATA):fail();
  s.onerror=fail; document.head.appendChild(s);
}
function fail(){ V('view-home').innerHTML='<p style="padding:30px">No se pudo cargar el banco de preguntas.</p>'; }
if(window.MS102_DATA){ boot(window.MS102_DATA); }
else fetch(DATA_URL).then(r=>r.json()).then(boot).catch(loadOffline);

if('serviceWorker' in navigator){ navigator.serviceWorker.register('sw.js').catch(()=>{}); }
