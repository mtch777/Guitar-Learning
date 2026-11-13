/* UI only: all selections, scores, musical data and eligibility come from the engine. */
'use strict';
(() => {
  const $ = s => document.querySelector(s);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const copy = value => value == null ? value : JSON.parse(JSON.stringify(value));
  let config = null, state = null, drafts = {}, requestBusy = false, polling = null, connected = false;
  let responseSerial=0, generationEpoch=0, minimumVersion=0, versionSession=null;
  const selectedViews = {}, timelines = new Map();
  const saveResults=new Map();
  const saveKey=(stage,version,identity=state?.session_id)=>`${identity||''}:${stage}:${version}`;
  const githubFolder='https://github.com/mtch777/Guitar-Learning/tree/generated-midi/generated-midi';
  const stagesNode = $('#steps'), noticeNode = $('#notice');
  const stable = value => JSON.stringify(canonical(value));
  function canonical(value){if(Array.isArray(value))return value.map(canonical);if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])]));return value;}
  function readPath(obj,path){return path.split('.').reduce((o,k)=>o?.[k],obj);}
  function writePath(obj,path,value){const keys=path.split('.');let at=obj;for(const key of keys.slice(0,-1))at=at[key]??(at[key]={});at[keys.at(-1)]=value;}
  const idOf = stage => String(stage.id);
  const stageState = id => state?.stages?.find(s => String(s.id) === String(id));
  const isBusy = () => requestBusy || !!state?.busy;
  const finalStage = id => config?.stages?.findIndex(s => idOf(s) === String(id)) === config.stages.length - 1;
  function notify(message, retry = false) {
    noticeNode.hidden = !message;
    noticeNode.textContent = message || '';
    if (retry) {
      const button = document.createElement('button'); button.textContent = '↻ Reconnect';
      button.addEventListener('click', () => config ? refresh(true) : init()); noticeNode.append(document.createElement('br'), button);
    }
  }
  async function api(url, options = {}) {
    const response = await fetch(url, {credentials:'same-origin',cache:'no-store', ...options});
    let data;
    try { data = await response.json(); } catch { throw Error('The generator returned an unreadable response.'); }
    if (!response.ok) {const error=Error(data.error || data.message || `Request failed (${response.status}).`);error.loading=!!data.loading;throw error;}
    return data;
  }
  function saveDrafts() {
    try { sessionStorage.setItem('riff-walkthrough-drafts', JSON.stringify({session:state?.session_id, drafts})); } catch {}
  }
  function initDrafts() {
    let stored;
    try { stored = JSON.parse(sessionStorage.getItem('riff-walkthrough-drafts')); } catch {}
    for (const stage of config.stages) {
      const id = idOf(stage), current = stageState(id);
      const defaults = stage.defaults || Object.fromEntries((stage.parameters || []).map(p => [p.key, p.default]));
      drafts[id] = copy(current?.applied && Object.keys(current.applied).length ? current.applied : defaults);
      if (stored?.session === state?.session_id && stored.drafts?.[id]) drafts[id] = {...drafts[id], ...stored.drafts[id]};
    }
  }
  function isDirty(id) {
    const stage = config.stages.find(s => idOf(s) === id), ss = stageState(id);
    const actual = ss?.applied && Object.keys(ss.applied).length ? ss.applied : stage.defaults || {};
    return stable(drafts[id]) !== stable(actual);
  }
  function displayStatus(ss) {
    if (!ss) return '';
    const value = String(ss.status || '').toLowerCase();
    if(value==='running' && ss.output?.progress && Number.isFinite(ss.output.progress.completed) && Number.isFinite(ss.output.progress.total))return `${ss.output.progress.completed} / ${ss.output.progress.total} phrases`;
    return ({empty:'',pending:'Waiting',queued:'Waiting',running:'Generating…',complete:'',completed:'',ready:'',blocked:'Stopped',error:'Failed',stale:'Waiting',invalidated:'Waiting'})[value] ?? value;
  }
  function parameterMarkup(stage) {
    const id = idOf(stage); let lastGroup = null;
    const content = (stage.parameters || []).map(p => {
      let heading = '';
      if (p.group && p.group !== lastGroup) { lastGroup=p.group; heading=`<div class="param-group">${esc(({field_weights:'Field weights',opening_weights:'Opening / independent fit',context_weights:'Contextual fit',tier_weights:'Matching tiers',fit_weights:'Reference fit',details:'Reproducibility'})[p.group]||p.group)}</div>`; }
      const name = `param-${id}-${p.key}`, value = readPath(drafts[id],p.key) ?? p.default ?? '';
      const disabled = isBusy() ? ' disabled' : '';
      const common = `id="${esc(name)}" data-stage="${esc(id)}" data-key="${esc(p.key)}"${disabled}`;
      let field;
      if (p.type === 'select' || p.options) {
        field = `<select ${common}>${(p.options || []).map(option => {
          const v = typeof option==='object' ? option.value : option;
          const label = typeof option==='object' ? option.label : option;
          return `<option value="${esc(v)}"${String(v)===String(value)?' selected':''}>${esc(label)}</option>`;
        }).join('')}</select>`;
      } else if (p.type === 'boolean' || p.type === 'checkbox') {
        field = `<input type="checkbox" ${common}${value?' checked':''}>`;
      } else {
        const numeric = ['number','integer','float','range'].includes(p.type);
        field = `<input type="${numeric?'number':'text'}" ${common} value="${esc(value)}"${numeric?' inputmode="decimal"':''}${p.min!=null?` min="${esc(p.min)}"`:''}${p.max!=null?` max="${esc(p.max)}"`:''}${p.step!=null?` step="${esc(p.step)}"`:numeric?' step="any"':''}${p.required||numeric?' required':''}>`;
      }
      return heading+`<label class="param-field${p.type==='checkbox'||p.type==='boolean'?' checkbox':''}" for="${esc(name)}"><span>${esc(p.label || p.key)}</span>${field}</label>`;
    }).join('');
    if (!content) return '';
    return `<details class="params" data-details="params-${esc(id)}"${config.stages.indexOf(stage)===0&&!stageState(id)?.output?' open':''}><summary>Parameters <span class="draft-tag"${isDirty(id)?'':' hidden'}>Not applied</span></summary><div class="param-grid">${content}</div></details>`;
  }
  function summaryMarkup(summary) {
    if (summary == null) return '';
    if (typeof summary === 'string') return `<p class="summary-text">${esc(summary)}</p>`;
    if (Array.isArray(summary)) return `<p class="summary-text">${summary.map(esc).join(' · ')}</p>`;
    return `<dl class="summary-grid">${Object.entries(summary).map(([k,v])=>`<div class="summary-item"><dt>${esc(k)}</dt><dd${typeof v==='string'&&v.startsWith('riff:')?` class="identifier" title="${esc(v)}"`:''}>${esc(typeof v==='object'?JSON.stringify(v):typeof v==='number'?(/similarity/i.test(k)?`${v.toFixed(1)}%`:formatNumber(v)):v)}</dd></div>`).join('')}</dl>`;
  }
  function repeatLabel(value) {
    if(value==null)return '';
    const tokens=Array.isArray(value)?value:String(value).split(';');
    return tokens.map(v=>String(v).trim()).filter(v=>/^\d+$/.test(v)).join(', ');
  }
  function phraseMarkup(phrases,id) {
    if (!phrases?.length) return '';
    const chips=`<div class="phrase-list">${phrases.map(p=>{
      const exact=repeatLabel(p.repeat),rhythm=repeatLabel(p.rhythm_repeat);
      return `<div class="phrase-chip"><span class="beats">${p.length_beats!=null?`${esc(formatNumber(p.length_beats))} beats`:''}</span><strong>${esc(p.phrase ?? p.phrase_number ?? '')}</strong>${p.role?` · ${esc(p.role)}`:''}${p.texture?`<div class="dim">${esc(p.texture)}</div>`:''}${p.copy_from!=null?`<div class="dim">Copied from ${esc(p.copy_from)}</div>`:''}${exact?`<div class="dim">Notes + timing: ${esc(exact)}</div>`:''}${rhythm?`<div class="dim">Rhythm: ${esc(rhythm)}</div>`:''}</div>`;
    }).join('')}</div>`;
    return phrases.length>1?`<details class="evidence phrase-details" data-details="phrases-${esc(id)}"><summary>Phrases (${phrases.length})</summary>${chips}</details>`:chips;
  }
  function audioAvailable(output) { return !!output?.audio?.notes?.length; }
  function saveableAudio(id,ss) {
    const a=ss?.output?.audio;
    if(!a || a.unavailable || a.reason || !Array.isArray(a.notes) || !Number.isFinite(a.length_beats) || a.length_beats<=0 || a.tempo!==120)return false;
    if(!a.notes.every(n=>Number.isFinite(n.start_beats)&&n.start_beats>=0&&Number.isFinite(n.duration_beats)&&n.duration_beats>0&&Number.isInteger(n.midi_pitch)&&n.midi_pitch>=0&&n.midi_pitch<=127&&n.start_beats+n.duration_beats<=a.length_beats+1e-8))return false;
    return ss.status==='complete' || (String(id)==='5' && ss.status==='blocked' && !!ss.output.blocker && typeof a.label==='string' && a.label.startsWith('Partial') && a.notes.length>0);
  }
  const selectiveRegenerationEnabled=false;
  let editor=null,editorSerial=0;
  const editorKey=()=>`${state?.session_id||''}:${state?.version}`;
  function currentEditor(){return editor?.key===editorKey()&&stageState('6')?.status==='complete'?editor:null;}
  function editorReady(){return !isBusy()&&connected&&stageState('6')?.status==='complete'&&selectedViews['6']!=='previous';}
  function reviewOutput(){return currentEditor()?.output||stageState('6')?.output;}
  async function editorRequest(action,payload){
    const endpoint=new URL(location.origin);endpoint.port='8769';endpoint.pathname='/editor/'+action;
    const r=await fetch(endpoint.href,{method:'POST',credentials:'include',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const result=await r.json();if(!r.ok)throw Error(result.error||'The edit could not be completed.');return result;
  }
  async function openEditor(){
    if(!editorReady())return null;
    if(currentEditor())return currentEditor();
    const key=editorKey(),serial=++editorSerial;
    editor={key,busy:true,revision:0,selected:[],mode:'both',plan:null,output:null};render();
    try{
      const result=await editorRequest('open',{version:state.version});
      if(serial!==editorSerial||key!==editorKey())return null;
      if(result.source_version!==state.version||!Number.isInteger(result.revision)||!result.output?.audio)throw Error('The editor returned an invalid result.');
      Object.assign(editor,{revision:result.revision,output:result.output,busy:false});return editor;
    }catch(e){if(serial===editorSerial&&key===editorKey()){editor=null;notify(e.message);}return null;}
    finally{render();}
  }
  async function togglePhrase(number){
    if(!editorReady()||currentEditor()?.busy)return;
    const e=await openEditor();if(!e||e!==currentEditor()||e.busy)return;
    if(!e.output.phrases?.some(p=>Number(p.phrase)===number))return;
    e.selected=e.selected.includes(number)?e.selected.filter(n=>n!==number):[...e.selected,number].sort((a,b)=>a-b);e.plan=null;e.saved=null;render();
  }
  function setEditorMode(mode){if(!selectiveRegenerationEnabled)return;const e=currentEditor();if(!e||e.busy||!['rhythm','pitches','both'].includes(mode))return;e.mode=mode;e.plan=null;render();}
  async function editorAction(action,full=false){
    if(action!=='save'&&!selectiveRegenerationEnabled)return;
    if(!editorReady())return;const e=await openEditor();if(!e||e!==currentEditor()||e.busy)return;
    if(!full&&!e.selected.length)return;if(action==='regenerate'&&!e.plan)return;
    const key=e.key,serial=++editorSerial,revision=e.revision;
    const payload={version:state.version,revision,selected:full?null:[...e.selected]};
    if(action!=='save')payload.mode=e.mode;
    e.busy=true;render();
    try{
      const result=await editorRequest(action,payload);
      if(serial!==editorSerial||key!==editorKey()||e!==currentEditor())return;
      if(action==='plan'){
        if(!Array.isArray(result.affected)||!Array.isArray(result.rhythm_affected)||!Array.isArray(result.pitch_affected))throw Error('The affected phrase list could not be verified.');
        e.plan=result;
      }else if(action==='regenerate'){
        if(result.source_version!==payload.version||!Number.isInteger(result.revision)||result.revision<=revision||!result.output?.audio)throw Error('The edit returned an invalid revision.');
        player.stop();e.revision=result.revision;e.output=result.output;e.plan=null;e.saved=null;
      }else{
        if(result.saved!==true||result.editor_revision!==revision||!result.file_url?.startsWith('https://github.com/mtch777/Guitar-Learning/blob/generated-midi/generated-midi/')||result.folder_url!==githubFolder)throw Error('The save destination could not be verified.');
        e.saved={...result,selected:payload.selected,revision};notify('Saved '+(full?'full':'selected')+' MIDI to GitHub.');
      }
    }catch(error){if(serial===editorSerial&&key===editorKey()){if(action==='regenerate')e.plan=null;notify(error.message);}}
    finally{if(e===currentEditor())e.busy=false;render();}
  }
  function editorMarkup(output){
    const e=currentEditor(),selected=e?.selected||[],busy=!!e?.busy||isBusy();
    const buttons=(output.phrases||[]).map(p=>`<button type="button" data-phrase-select="${Number(p.phrase)}" aria-pressed="${selected.includes(Number(p.phrase))}"${busy?' disabled':''}>${selected.includes(Number(p.phrase))?'✓ ':''}${Number(p.phrase)}</button>`).join(' ');
    let html=`<section aria-label="Phrase editor"><p>Select phrases${selectiveRegenerationEnabled?' · Review edits leave earlier steps unchanged.':''}</p><div role="group" aria-label="Phrases">${buttons}</div>`;
    if(e?.revision>0)html+=`<p>Edited · revision ${e.revision}</p>`;
    if(e?.busy)html+='<p role="status">Working…</p>';
    if(selected.length){
      html+=`<p>Selected: ${selected.join(', ')}</p><button data-editor-action="save"${busy?' disabled':''}>💾 Save selected MIDI</button><p>Selected MIDI joins phrases in original order and clips holds at selection edges.</p>`;
      if(selectiveRegenerationEnabled){
        html+=`<label>Regenerate <select data-editor-mode${busy?' disabled':''}>${[['rhythm','Rhythm'],['pitches','Pitches'],['both','Both']].map(([v,l])=>`<option value="${v}"${(e?.mode||'both')===v?' selected':''}>${l}</option>`).join('')}</select></label> <button data-editor-action="plan"${busy?' disabled':''}>Check affected phrases</button>`;
        if(e?.plan)html+=`<p>Will regenerate: ${esc(e.mode)} · phrases ${e.plan.affected.map(esc).join(', ')}<br>Rhythm: ${e.plan.rhythm_affected.map(esc).join(', ')||'none'} · Pitches: ${e.plan.pitch_affected.map(esc).join(', ')||'none'}</p><button data-editor-action="regenerate"${busy?' disabled':''}>🎲 Regenerate affected phrases</button>`;
      }
    }
    if(e?.saved?.file_url)html+=`<p>Saved revision ${e.saved.revision} · <a href="${esc(e.saved.file_url)}" target="_blank" rel="noopener noreferrer">${e.saved.selected?'Selected MIDI':'Full MIDI'}</a></p>`;
    return html+'</section>';
  }
  function resultMarkup(stage, ss) {
    const id=idOf(stage), usePrevious=selectedViews[id]==='previous' && !!ss?.previous;
    const previous=ss?.previous?.output ?? ss?.previous;
    const output=usePrevious ? previous : id==='6'?(currentEditor()?.output||ss?.output):ss?.output;
    let html='';
    if (previous) html+=`<div class="compare" role="group" aria-label="Result version"><button data-action="view" data-stage="${esc(id)}" data-view="current" aria-pressed="${!usePrevious}">Current</button><button data-action="view" data-stage="${esc(id)}" data-view="previous" aria-pressed="${!!usePrevious}">Previous</button></div>`;
    if (!output) {
      const status=String(ss?.status || '').toLowerCase();
      const message = ['running','queued','pending','stale','invalidated'].includes(status) ? (status==='running'?'Generating…':'Waiting for earlier steps.') : ss?.error || ss?.blocker || (config.stages.indexOf(stage)===0?'':'Generate an earlier step to begin.');
      return html+(message?`<p class="empty">${esc(message)}</p>`:'');
    }
    html+=summaryMarkup(output.summary);
    if (output.blocker) html+=`<div class="blocker">${esc(output.blocker)}</div>`;
    if (audioAvailable(output)) {
      const active=player.active?.stage===id && player.active?.view===(usePrevious?'previous':'current');
      html+=`<div class="audio-section"><div class="audio-toolbar"><button class="play-button" data-action="play" data-stage="${esc(id)}"${isBusy()?' disabled':''} aria-label="${active?'Stop':'Play'} ${esc(output.audio.label || '')}${usePrevious?' previous result':''}">${active?'■ Stop':'▶ Play'}</button><span class="audio-label">${esc(output.audio.label || 'Audio')}${usePrevious?' · Previous':''}</span><span class="audio-clock" data-clock="${esc(id)}">${active?'0:00 / ':''}${formatTime(duration(output.audio))}</span></div><div class="timeline" data-timeline="${esc(id)}"><div class="timeline-scroll"><div class="timeline-track"></div></div><canvas aria-label="Note timing and playback position" role="img"></canvas></div></div>`;
    } else if(output.audio?.unavailable || output.audio?.reason) html+=`<p class="empty">${esc(output.audio.unavailable || output.audio.reason)}</p>`;
    if(id==='6'&&!usePrevious&&ss?.status==='complete')html+=editorMarkup(output);
    html+=phraseMarkup(output.phrases,id);
    const evidence={...(output.details || {})};
    const applied=usePrevious?(ss.previous.applied || undefined):ss.applied;
    if (applied && Object.keys(applied).length) evidence['Applied parameters']=applied;
    if (Object.keys(evidence).length) html+=`<details class="evidence" data-details="evidence-${esc(id)}"><summary>Details</summary><pre>${esc(JSON.stringify(evidence,null,2))}</pre></details>`;
    if (!usePrevious && !isBusy() && !currentEditor()?.busy && saveableAudio(id,{...ss,output})) {
      const saved=id==='6'&&currentEditor()?.revision>0?null:saveResults.get(saveKey(id,state.version));
      html+=`<button type="button" data-save-midi="${esc(id)}" data-version="${state.version}" ${saved?.pending?'disabled':''}>${saved?.pending?'Saving…':ss.status==='blocked'?'💾 Save partial MIDI':'💾 Save MIDI'}</button> <a href="${githubFolder}" target="_blank" rel="noopener noreferrer">🔗 Folder</a>`;
      if(saved?.file_url)html+=`<p>Saved v${state.version} · <a href="${esc(saved.file_url)}" target="_blank" rel="noopener noreferrer">MIDI</a></p>`;
    }
    return html;
  }
  const markupCache = new Map();
  function render() {
    if (!config || !state) return;
    for(const [index,stage] of config.stages.entries()) {
      const id=idOf(stage), ss=stageState(id) || {}, status=displayStatus(ss);
      const old=stagesNode.querySelector(`[data-step="${CSS.escape(id)}"]`);
      const prevOK=index===0 || ['complete','completed','ready'].includes(stageState(config.stages[index-1].id)?.status);
      const disabled=isBusy() || !!currentEditor()?.busy || !connected || !prevOK;
      const markup=`<section class="step ${esc(ss.status || '')}" data-step="${esc(id)}"><div class="step-head"><div class="step-heading"><span class="step-number">${index+1}</span><div><h2>${esc(stage.title)}</h2>${status?`<div class="status ${['error','blocked'].includes(ss.status)?'bad':''}">${ss.status==='running'?'<span class="busy-dot"></span>':''}${esc(status)}</div>`:''}</div></div>${!finalStage(id)?`<button class="primary" data-action="generate" data-stage="${esc(id)}"${disabled?' disabled':''}${!prevOK?' title="Generate an earlier step first"':''}>🎲 Generate</button>`:''}</div>${parameterMarkup(stage)}<div class="result">${resultMarkup(stage,ss)}</div></section>`;
      if(old && markupCache.get(id)===markup)continue;
      const opened={}; if(old)for(const d of old.querySelectorAll('details'))opened[d.dataset.details]=d.open;
      const oldTimeline=timelines.get(id),scroll=oldTimeline?.scroller.scrollLeft || 0;
      oldTimeline?.destroy();timelines.delete(id);
      const template=document.createElement('template');template.innerHTML=markup;const element=template.content.firstElementChild;
      if(old)old.replaceWith(element);else stagesNode.append(element);
      markupCache.set(id,markup);
      for(const d of element.querySelectorAll('details'))if(d.dataset.details in opened)d.open=opened[d.dataset.details];
      const prev=selectedViews[id]==='previous',out=prev?(ss?.previous?.output??ss?.previous):id==='6'?(currentEditor()?.output||ss?.output):ss?.output;
      const el=element.querySelector('[data-timeline]');
      if(el && out?.audio){const t=new Timeline(el,out.audio,out.audio.phrases || (/reference/i.test(out.audio.label || '')?[]:out.phrases || []),id==='6'&&!prev?togglePhrase:null);timelines.set(id,t);t.scroller.scrollLeft=scroll;t.draw();}
    }
    $('#connection').textContent=!connected?'Disconnected':isBusy()?'Generating…':'';
  }
  function formatNumber(n){const v=Number(n);return Number.isFinite(v)?String(Math.round(v*1000)/1000):String(n);}
  function formatTime(seconds){seconds=Math.max(0,Number(seconds)||0);return `${Math.floor(seconds/60)}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;}
  function duration(a){return (a.notes||[]).reduce((end,n)=>Math.max(end,Number(n.start_beats)+Number(n.duration_beats)),Number(a.length_beats)||0)*60/(Number(a.tempo)||120);}
  function getOutput(id){const s=stageState(id);return selectedViews[id]==='previous'?(s?.previous?.output??s?.previous):String(id)==='6'?(currentEditor()?.output||s?.output):s?.output;}
  async function generate(id){
    if(isBusy() || currentEditor()?.busy || !connected)return;
    const index=config.stages.findIndex(s=>idOf(s)===id);
    const affected=new Set(config.stages.slice(index).map(idOf));
    const inputs=[...stagesNode.querySelectorAll('input,select')].filter(input=>affected.has(input.dataset.stage));
    for(const input of inputs){if(!input.checkValidity()){input.closest('details').open=true;input.reportValidity();return;}}
    player.stop();notify('');requestBusy=true;generationEpoch++;responseSerial++;clearTimeout(polling);
    const params=copy(drafts);
    for(const earlier of config.stages.slice(0,index))params[idOf(earlier)]=copy(stageState(earlier.id)?.applied || earlier.defaults || {});
    for(let i=index;i<config.stages.length;i++){
      const s=stageState(config.stages[i].id);if(!s)continue;
      if(s.output)s.previous={output:copy(s.output),applied:copy(s.applied)};
      s.output=null;s.status=i===index?'running':'queued';selectedViews[String(s.id)]='current';
    }
    render();
    try{
      const accepted=await api('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({stage:typeof config.stages[index].id==='number'?Number(id):id,params})});
      if(Number.isFinite(accepted.version)){versionSession=state.session_id;minimumVersion=Math.max(minimumVersion,accepted.version);}
      requestBusy=false; await refresh();
    }catch(error){
      requestBusy=false;notify(error.message);await refresh(false,true);
    }
  }
  async function refresh(manual=false,keepNotice=false){
    clearTimeout(polling);if(requestBusy)return;
    const serial=++responseSerial,epoch=generationEpoch;let received=false;
    try{
      const next=await api('/api/state');received=true;
      if(serial!==responseSerial || epoch!==generationEpoch)return;
      if(next.session_id===versionSession && Number(next.version)<minimumVersion){polling=setTimeout(()=>refresh(),250);return;}
      if(state && (next.version!==state.version || next.session_id!==state.session_id))player.stop();
      if(next.session_id!==versionSession){versionSession=next.session_id;minimumVersion=Number(next.version)||0;}
      else minimumVersion=Math.max(minimumVersion,Number(next.version)||0);
      const reconnected=!connected;connected=true;state=next;
      if((manual||reconnected)&&!keepNotice)notify('');
      render();
      if(state.busy)polling=setTimeout(()=>refresh(),1000);
    }catch(error){
      if(serial!==responseSerial || epoch!==generationEpoch)return;
      connected=false;requestBusy=false;player.stop();
      notify(received?'The generator responded, but this result could not be displayed. Reconnect to retry.':'Cannot reach the generator. Your last displayed result is retained; reconnect to check its status.',true);
      $('#connection').textContent='Disconnected';
      for(const b of stagesNode.querySelectorAll('[data-action="generate"]'))b.disabled=true;
      for(const a of stagesNode.querySelectorAll('.export'))a.remove();
      polling=setTimeout(()=>refresh(),5000);
    }
  }
  class Timeline{
    constructor(el,audio,phrases,onSelect=null){
      this.el=el;this.audio=audio;this.phrases=phrases;this.canvas=el.querySelector('canvas');this.scroller=el.querySelector('.timeline-scroll');this.track=el.querySelector('.timeline-track');
      this.length=audio.notes.reduce((end,n)=>Math.max(end,Number(n.start_beats)+Number(n.duration_beats)),Math.max(Number(audio.length_beats)||0,1));this.cursor=null;
      const pitches=audio.notes.map(n=>Number(n.midi_pitch)).filter(Number.isFinite);this.lo=pitches.reduce((v,p)=>Math.min(v,p),127)-1;this.hi=pitches.reduce((v,p)=>Math.max(v,p),0)+1;
      this.scrollHandler=()=>this.draw();this.scroller.addEventListener('scroll',this.scrollHandler,{passive:true});
      this.selectHandler=event=>{if(!onSelect)return;const r=this.scroller.getBoundingClientRect();const beat=(event.clientX-r.left+this.scroller.scrollLeft)/this.scale;const p=this.phrases.find(p=>beat>=Number(p.start_beats)&&beat<Number(p.start_beats)+Number(p.length_beats));if(p&&(!this.pointerStart||Math.abs(event.clientX-this.pointerStart.x)<6&&Math.abs(this.scroller.scrollLeft-this.pointerStart.scroll)<6))onSelect(Number(p.phrase));};
      this.downHandler=event=>{this.pointerStart={x:event.clientX,scroll:this.scroller.scrollLeft};};
      this.scroller.addEventListener('pointerdown',this.downHandler);this.scroller.addEventListener('click',this.selectHandler);
      this.selectable=!!onSelect;
      this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(el);this.resize();
    }
    resize(){const w=this.el.clientWidth,h=this.el.clientHeight-18,dpr=Math.min(window.devicePixelRatio||1,2);this.canvas.width=Math.round(w*dpr);this.canvas.height=Math.round(h*dpr);this.canvas.style.height=h+'px';this.width=w;this.height=h;this.dpr=dpr;this.scale=Math.max(25,w/this.length);this.track.style.width=Math.max(w,this.length*this.scale)+'px';this.draw();}
    draw(){
      const c=this.canvas.getContext('2d'),w=this.width,h=this.height;if(!w)return;c.setTransform(this.dpr,0,0,this.dpr,0,0);c.clearRect(0,0,w,h);const offset=this.scroller.scrollLeft;const x=b=>b*this.scale-offset;
      if(this.selectable)for(const p of this.phrases){if(currentEditor()?.selected.includes(Number(p.phrase))){c.fillStyle='rgba(130,180,90,.22)';c.fillRect(x(Number(p.start_beats)),18,Number(p.length_beats)*this.scale,h-18);}}
      c.font='10px system-ui';c.textBaseline='top';
      for(let beat=Math.max(0,Math.floor(offset/this.scale));beat<=(offset+w)/this.scale;beat++){
        c.strokeStyle=beat%4===0?'#354333':'#233020';c.lineWidth=1;c.beginPath();c.moveTo(Math.round(x(beat))+.5,18);c.lineTo(Math.round(x(beat))+.5,h);c.stroke();
        if(beat%4===0){c.fillStyle='#8b9c87';c.fillText(String(beat),x(beat)+4,3);}
      }
      const range=Math.max(3,this.hi-this.lo),noteHeight=Math.min(14,Math.max(3,(h-28)/range));
      for(const n of this.audio.notes){
        const start=Number(n.start_beats),end=start+Number(n.duration_beats),left=x(Math.max(0,start)),right=x(Math.min(this.length,end));if(right<0||left>w)continue;
        const pitch=Number(n.midi_pitch);if(!Number.isFinite(pitch))continue;
        const y=24+(this.hi-pitch)/range*(h-35);c.fillStyle=n.placeholder?'#8c9787':'#bbdf8c';c.globalAlpha=.82;
        c.fillRect(left,y,Math.max(2,right-left-1),noteHeight);c.globalAlpha=1;
      }
      for(const p of this.phrases){const start=Number(p.start_beats);if(!Number.isFinite(start)||start<=0)continue;const xx=x(start);if(xx<0||xx>w)continue;c.strokeStyle='#77966b';c.setLineDash([3,4]);c.beginPath();c.moveTo(xx,20);c.lineTo(xx,h);c.stroke();c.setLineDash([]);}
      if(this.cursor!=null){c.strokeStyle='#c2c7c0';c.lineWidth=2;c.beginPath();c.moveTo(x(this.cursor),0);c.lineTo(x(this.cursor),h);c.stroke();}
    }
    progress(beat){this.cursor=beat;const pos=beat*this.scale;const left=this.scroller.scrollLeft;if(pos>left+this.width*.82 || pos<left)this.scroller.scrollLeft=Math.max(0,pos-this.width*.25);this.draw();}
    destroy(){this.scroller.removeEventListener('pointerdown',this.downHandler);this.scroller.removeEventListener('click',this.selectHandler);this.resizeObserver.disconnect();this.scroller.removeEventListener('scroll',this.scrollHandler);}
  }
  const player={
    context:null,active:null,nodes:new Set(),timer:null,frame:null,token:0,
    stop(){this.token++;clearInterval(this.timer);cancelAnimationFrame(this.frame);for(const n of this.nodes){try{n.stop();}catch{}}this.nodes.clear();const old=this.active;this.active=null;if(old){const t=timelines.get(old.stage);if(t){t.cursor=null;t.draw();}const b=stagesNode.querySelector(`[data-action="play"][data-stage="${CSS.escape(old.stage)}"]`);if(b){b.textContent='▶ Play';b.setAttribute('aria-label','Play');}const clock=stagesNode.querySelector(`[data-clock="${CSS.escape(old.stage)}"]`);if(clock)clock.textContent=formatTime(old.duration);}},
    async play(id){
      const view=selectedViews[id] || 'current';if(this.active?.stage===id && this.active?.view===view){this.stop();return;}
      this.stop();const token=this.token;const output=getOutput(id);if(!audioAvailable(output))return;
      try{
        if(!this.context){const AC=window.AudioContext||window.webkitAudioContext;if(!AC)throw Error('Audio playback is unavailable in this browser.');this.context=new AC();this.gain=this.context.createGain();this.gain.gain.value=.22;this.compressor=this.context.createDynamicsCompressor();this.compressor.threshold.value=-15;this.compressor.ratio.value=8;this.gain.connect(this.compressor);this.compressor.connect(this.context.destination);const real=new Float32Array(9),imag=new Float32Array(9);for(let i=1;i<9;i++)imag[i]=1/(i*i*.4+i*.6);this.wave=this.context.createPeriodicWave(real,imag);}
        await this.context.resume();if(token!==this.token)return;if(this.context.state!=='running')throw Error('Audio is paused by the browser. Tap Play again.');
        const a=output.audio;
        if(a.notes.some(n=>n.midi_pitch==null || !Number.isFinite(Number(n.midi_pitch)) || Number(n.midi_pitch)<0 || Number(n.midi_pitch)>127 || !Number.isFinite(Number(n.start_beats)) || !Number.isFinite(Number(n.duration_beats)) || Number(n.duration_beats)<=0))throw Error('Audio contains an invalid note. Playback stopped.');
        const seconds=60/(Number(a.tempo)||120),notes=a.notes.map(n=>({start:Math.max(0,Number(n.start_beats))*seconds,end:(Number(n.start_beats)+Number(n.duration_beats))*seconds,pitch:Number(n.midi_pitch)})).filter(n=>Number.isFinite(n.pitch)&&n.end>n.start).sort((a,b)=>a.start-b.start);
        if(!notes.length)throw Error('There are no playable notes in this result.');
        const start=this.context.currentTime+.06,total=duration(a);this.active={stage:id,view,start,duration:total};let next=0;
        const schedule=()=>{if(token!==this.token)return;const ahead=this.context.currentTime-start+.25;while(next<notes.length&&notes[next].start<ahead){const note=notes[next++],osc=this.context.createOscillator(),gain=this.context.createGain(),on=start+note.start,off=start+note.end;osc.setPeriodicWave(this.wave);osc.frequency.value=440*Math.pow(2,(note.pitch-69)/12);const span=off-on,attack=Math.min(.008,span*.2),release=Math.min(.012,span*.3);gain.gain.setValueAtTime(0,on);gain.gain.linearRampToValueAtTime(.45,on+attack);gain.gain.setValueAtTime(.45,off-release);gain.gain.linearRampToValueAtTime(0,off);osc.connect(gain);gain.connect(this.gain);osc.start(on);osc.stop(off+.02);this.nodes.add(osc);osc.onended=()=>{this.nodes.delete(osc);osc.disconnect();gain.disconnect();};}};
        schedule();this.timer=setInterval(schedule,60);
        const b=stagesNode.querySelector(`[data-action="play"][data-stage="${CSS.escape(id)}"]`);if(b){b.textContent='■ Stop';b.setAttribute('aria-label','Stop playback');}
        const t=timelines.get(id);if(t)t.scroller.scrollLeft=0;
        const update=()=>{if(token!==this.token)return;const elapsed=Math.max(0,this.context.currentTime-start);timelines.get(id)?.progress(elapsed/seconds);const clock=stagesNode.querySelector(`[data-clock="${CSS.escape(id)}"]`);if(clock)clock.textContent=`${formatTime(elapsed)} / ${formatTime(total)}`;if(elapsed>=total+.05){this.stop();return;}this.frame=requestAnimationFrame(update);};update();
      }catch(error){this.stop();notify(error.message);}
    }
  };
  stagesNode.addEventListener('input',event=>{
    const input=event.target;if(input.hasAttribute?.('data-editor-mode')){setEditorMode(input.value);return;}if(!input.dataset.key)return;const id=input.dataset.stage,key=input.dataset.key;
    writePath(drafts[id],key,input.type==='checkbox'?input.checked:input.type==='number'?(input.value===''?'':Number(input.value)):input.value);
    const tag=input.closest('.params').querySelector('.draft-tag');tag.hidden=!isDirty(id);saveDrafts();
  });
  function midiText(buffer,version){
    const bytes=new Uint8Array(buffer);
    if(bytes.length<14 || String.fromCharCode(...bytes.slice(0,4))!=='MThd')throw Error('The export is not a MIDI file.');
    let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
    return JSON.stringify({type:'riff-midi',version,filename:`riff-${version}.mid`,base64:btoa(binary)});
  }
  function showMidiText(text,version){
    document.querySelector('#midi-copy-panel')?.remove();
    const panel=document.createElement('section');panel.id='midi-copy-panel';panel.className='notice';
    const label=document.createElement('p');label.textContent=`MIDI v${version}. Copy this text and paste it in the chat.`;
    const area=document.createElement('textarea');area.readOnly=true;area.value=text;area.rows=4;area.style.width='100%';area.setAttribute('aria-label','Exact MIDI export text');
    const button=document.createElement('button');button.type='button';button.textContent='📋 Copy text';
    const close=document.createElement('button');close.type='button';close.textContent='✕';close.setAttribute('aria-label','Close MIDI text');close.addEventListener('click',()=>panel.remove());
    button.addEventListener('click',()=>{area.focus();area.select();area.setSelectionRange(0,area.value.length);let copied=false;try{copied=document.execCommand('copy');}catch{}label.textContent=`MIDI v${version}. `+(copied?'Copied. Paste it in the chat.':'Select all and copy the text, then paste it in the chat.');});
    panel.append(label,area,button,close);document.querySelector('main').prepend(panel);panel.scrollIntoView({block:'start'});area.focus();area.select();
  }
  function previousSessionReference(){
    try{const value=JSON.parse(sessionStorage.getItem('riff-walkthrough-drafts'));return /^[A-Za-z0-9_-]{32}$/.test(value?.session||'') && value.session!==state?.session_id?value.session:null;}catch{return null;}
  }
  async function saveGithub(stage,version,previous=null){
    const identity=previous||state?.session_id,key=saveKey(stage,version,identity);if(saveResults.get(key)?.pending)return;
    saveResults.set(key,{pending:true});render();
    try{
      const endpoint=new URL(location.origin);endpoint.port='8769';endpoint.pathname=previous?'/recover':'/save';
      const response=await fetch(endpoint.href,{method:'POST',credentials:'include',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify(previous?{session_id:previous}:{stage:Number(stage),version:Number(version)})});
      const result=await response.json();if(!response.ok || result.saved!==true)throw Error(result.error||'GitHub save was not confirmed.');
      if(!result.file_url?.startsWith('https://github.com/mtch777/Guitar-Learning/blob/generated-midi/generated-midi/') || result.folder_url!==githubFolder)throw Error('The save destination could not be verified.');
      saveResults.set(key,result);notify(`Saved ${previous?'previous session ':identity!==state?.session_id?'earlier session ':''}MIDI v${result.version} to GitHub.`);
    }catch(error){saveResults.delete(key);notify(error.message==='Failed to fetch'?'Cannot reach the MIDI save service. Nothing was confirmed saved.':error.message);}
    render();
  }
  function renderRecovery(){
    if(document.querySelector('#previous-save'))return;
    if(!previousSessionReference())return;
    const panel=document.createElement('section');panel.id='previous-save';panel.className='notice';
    const button=document.createElement('button');button.type='button';button.textContent='💾 Save previous result';
    const link=document.createElement('a');link.href=githubFolder;link.target='_blank';link.rel='noopener noreferrer';link.textContent=' 🔗 Folder';
    button.addEventListener('click',async()=>{const previous=previousSessionReference();if(!previous){notify('No previous session reference is available.');return;}button.disabled=true;await saveGithub('6','previous',previous);button.disabled=false;});
    panel.append(button,link);document.querySelector('main').prepend(panel);
  }
  stagesNode.addEventListener('click',async event=>{
    const phrase=event.target.closest('[data-phrase-select]');if(phrase){if(!phrase.disabled)await togglePhrase(Number(phrase.dataset.phraseSelect));return;}
    const edit=event.target.closest('[data-editor-action]');if(edit){if(!edit.disabled)await editorAction(edit.dataset.editorAction);return;}
    const saveMidi=event.target.closest('[data-save-midi]');
    if(saveMidi){if(!saveMidi.disabled){if(saveMidi.dataset.saveMidi==='6'&&currentEditor()?.revision>0)await editorAction('save',true);else await saveGithub(saveMidi.dataset.saveMidi,Number(saveMidi.dataset.version));}return;}
    const copyMidi=event.target.closest('[data-copy-midi]');
    if(copyMidi){
      if(copyMidi.disabled)return;copyMidi.disabled=true;
      const version=Number(copyMidi.dataset.version),stage=copyMidi.dataset.copyMidi;
      try{const response=await fetch(`/api/midi?stage=${encodeURIComponent(stage)}&version=${encodeURIComponent(version)}`,{credentials:'same-origin',cache:'no-store'});if(!response.ok)throw Error('MIDI is unavailable for this result.');showMidiText(midiText(await response.arrayBuffer(),version),version);}catch(error){notify(error.message);}finally{copyMidi.disabled=false;}
      return;
    }
    const download=event.target.closest('.export');
    if(download){
      event.preventDefault();if(download.getAttribute('aria-disabled')==='true')return;
      download.setAttribute('aria-disabled','true');
      try{const response=await fetch(download.href,{credentials:'same-origin',cache:'no-store'});if(!response.ok){const error=await response.json();throw Error(error.error || 'MIDI is unavailable for this result.');}const blob=await response.blob();const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=`riff-${state.version}.mid`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}catch(error){notify(error.message);}finally{download.removeAttribute('aria-disabled');}
      return;
    }
    const button=event.target.closest('[data-action]');if(!button||button.disabled)return;const id=button.dataset.stage;
    if(button.dataset.action==='generate')generate(id);
    if(button.dataset.action==='play')player.play(id);
    if(button.dataset.action==='view'){player.stop();selectedViews[id]=button.dataset.view;render();}
  });
  document.addEventListener('visibilitychange',()=>{if(document.hidden)player.stop();else if(config)refresh();});
  window.addEventListener('pagehide',()=>player.stop());
  async function init(){
    clearTimeout(polling);const serial=++responseSerial,epoch=generationEpoch;
    try{
      const nextConfig=await api('/api/config'),nextState=await api('/api/state');
      if(serial!==responseSerial || epoch!==generationEpoch)return;
      config=nextConfig;state=nextState;versionSession=state.session_id;minimumVersion=Number(state.version)||0;
      connected=true;notify('');initDrafts();render();renderRecovery();if(state.busy)polling=setTimeout(()=>refresh(),1000);
    }catch(error){
      if(serial!==responseSerial || epoch!==generationEpoch)return;
      connected=false;if(error.loading){$('#connection').textContent='Loading dataset…';notify('');polling=setTimeout(init,1500);}else{$('#connection').textContent='Disconnected';notify(error.message || 'Cannot reach the generator.',true);}
    }
  }
  init();
})();
