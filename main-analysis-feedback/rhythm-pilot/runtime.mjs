import {DivisionRoll,parseDivisions} from './divisions.mjs?v=1';
import {renderRhythm,measuredStream} from '../rhythm-audit/rhythm-view-v3.mjs?v=3';
import {ReferencePlayer} from '../playback/player.mjs?v=audio-fix-1';
import {Fretboard} from '../playback/fretboard.mjs?v=mapped-filters-1';
import {renderPhraseShapes} from '../playback/shapes.mjs?v=mapped-filters-1';
import {Q,qnum,memberEnd,compileSchedule} from '../playback/timing.mjs?v=audio-fix-1';
import {validateManifest,newSession,validateSession,putAnswer,mergeSessions,progress,verifiedJson} from './core.mjs?v=2';
const $=id=>document.getElementById(id),panel=$('rhythmAudit');
let clipNotice='',pairPlayback=false;
let evidence,legacyDeck,legacyRaw=null,previousDeck,previousRaw=null;let priorArchives=[];
let deck,session,storageKey,hash=panel.dataset.manifestSha,storageError='',rawRecovery=null,loadEpoch=0,playEpoch=0,loaded=null,currentIndex=0,queue=null,playingSide='phrase',previousPlayerState='stopped';
const cache=new Map();
// Repair legacy display encoding only; never change source IDs or answer bindings.
const cp=new TextDecoder('windows-1252'),utf=new TextDecoder('utf-8',{fatal:true}),cpBytes=new Map(Array.from({length:256},(_,i)=>[cp.decode(Uint8Array.of(i)),i]));
function text(value){let s=String(value??'');for(let p=0;p<2;p++){let a=Array.from(s),out='',changed=false;for(let i=0;i<a.length;i++){const b=cpBytes.get(a[i]),n=b>=194&&b<=223?2:b>=224&&b<=239?3:b>=240&&b<=244?4:0,bs=a.slice(i,i+n).map(x=>cpBytes.get(x));if(n&&bs.length===n&&bs.slice(1).every(x=>x>=128&&x<=191)){try{out+=utf.decode(Uint8Array.from(bs));i+=n-1;changed=true;continue;}catch{}}out+=a[i];}s=out;if(!changed)break;}return s.replace(/[\u200b\ufeff]/g,'');}
const current=()=>deck.cases[currentIndex];
const span=p=>`${p.start_q}\u2013${p.end_q} quarter notes`;
const player=new ReferencePlayer(state=>{
 if(playingSide!=='sound test'){board?.update(state);divisionRoll?.update(state);}$('auditPause').disabled=!['playing','paused'].includes(state.state);$('auditPause').textContent=state.state==='paused'?'Resume':'Pause';
 if(['starting','playing','paused'].includes(state.state))$('auditAudioStatus').textContent=state.state==='paused'&&state.contextState!=='running'?'Audio interrupted. Tap Resume to restart audio. '+clipNotice:`${state.state==='paused'?'Paused':state.state==='starting'?'Starting':'Playing'} ${playingSide}. ${clipNotice}`;
 const ended=previousPlayerState==='playing'&&state.state==='stopped';previousPlayerState=state.state;
 if(ended&&playingSide==='sound test'){restoreAfterSoundTest();$('auditAudioStatus').textContent='Sound test finished. If you heard nothing, check media volume and Bluetooth/output routing. '+clipNotice;return;}
 if(ended){if(queue){const next=queue;queue=null;Promise.resolve().then(()=>{if(next.epoch===playEpoch)return startSide(next.side,next.epoch);}).catch(e=>{if(next.epoch===playEpoch)showPlaybackError(e);});}else $('auditAudioStatus').textContent='Playback stopped. '+clipNotice;}
});
let board=new Fretboard({canvas:$('auditRoll'),scroller:$('auditRollScroll'),position:$('auditPosition'),readout:$('auditReadout'),notice:$('auditNotice'),follow:$('auditFollow'),onSeek:async value=>{if(!loaded||playingSide==='sound test')return;queue=null;const epoch=++playEpoch;try{await player.seek(value);}catch(e){if(epoch===playEpoch)showPlaybackError(e);}}});
let divisionRoll=new DivisionRoll({host:$('auditDivisionCanvas'),scroller:$('auditDivisionScroll'),list:$('auditDivisionList'),status:$('auditDivisionStatus'),snap:$('auditDivisionSnap'),zoom:$('auditDivisionZoom'),undo:$('auditDivisionUndo'),onChange:raw=>{$('auditBoundaryMarks').value=raw;$('auditMarkError').textContent='';save();}});
$('auditDivisionAdd').onclick=()=>{divisionRoll.add($('auditDivisionExact').value);};
$('auditDivisionExact').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();$('auditDivisionAdd').click();}};
function restoreAfterSoundTest(){
 if(playingSide!=='sound test')return;playingSide='phrase';
 if(loaded){const side=current().comparison?'A':'B';clipNotice=describePlan(preview(side));selectSide(side);$('auditPosition').disabled=false;}
}
function stop(){queue=null;pairPlayback=false;++playEpoch;player.stop();restoreAfterSoundTest();$('auditAudioStatus').textContent='Playback stopped. '+clipNotice;}
function showPlaybackError(e){queue=null;player.stop();restoreAfterSoundTest();$('auditAudioStatus').textContent='Playback unavailable: '+text(e.message);}
function setMode(audit){stop();window.dispatchEvent(new Event('rhythm-audit-mode'));document.body.classList.toggle('audit-mode',audit);panel.hidden=!audit;$('auditReturn').hidden=audit;if(audit){board.resize();divisionRoll.draw();redrawRhythm(true);}}
$('auditBrowse').onclick=()=>setMode(false);$('auditReturn').onclick=()=>setMode(true);
function persist(){
 if(storageError){$('auditSaveStatus').textContent=storageError+' Your current answers are kept in this tab. Download them before closing.';$('auditSaveStatus').dataset.error='true';return false;}
 try{localStorage.setItem(storageKey,JSON.stringify(session));$('auditSaveStatus').dataset.error='false';$('auditSaveStatus').textContent=session.answers[current().id]?.answer?'Answer saved in this browser.':session.answers[current().id]?.boundary_marks?'Divisions saved in this browser.':session.answers[current().id]?.note?'Note saved in this browser.':'Choose an answer, or mark your divisions.';return true;}
 catch(e){storageError='Browser storage is unavailable or full.';return persist();}
}
function save(answer){const c=current(),old=session.answers[c.id];if(answer==='marked'&&!safeBoundaryMarks()&&!$('auditNote').value.trim()){$('auditMarkError').textContent='Enter boundary positions or describe them in your note before saving Marked.';return;}putAnswer(session,c,answer??old?.answer??'',$('auditNote').value,new Date().toISOString(),{confidence:$('auditConfidence').value,context_quality:$('auditContextQuality').value,boundary_marks:safeBoundaryMarks()});persist();renderAnswers();renderProgress();updateReveal();}
function button(label,fn){const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=fn;return b;}
function renderAnswers(){const c=current(),a=session.answers[c.id];$('auditAnswers').replaceChildren(...c.question.options.map(o=>{const b=button(o.label,()=>save(o.value));b.setAttribute('aria-pressed',String(a?.answer===o.value));return b;}));}
function renderProgress(){
 const p=progress(deck,session);$('auditCount').textContent=`${p.answered} of ${deck.cases.length} answered${p.unsure?' \xb7 '+p.unsure+' unsure':''}`;$('auditProgress').value=p.answered;
 $('auditSets').replaceChildren(...[...new Set(deck.cases.map(c=>c.set))].map(n=>{const b=button(`Set ${n} | ${p.by_set[n]||0}/${deck.cases.filter(c=>c.set===n).length}`,()=>loadCase(deck.cases.findIndex(c=>c.set===n)));b.setAttribute('aria-current',String(current().set===n));return b;}));
 $('auditDots').replaceChildren(...deck.cases.map((c,i)=>({c,i})).filter(x=>x.c.set===current().set).map(({c,i})=>{const b=button(String(i+1),()=>loadCase(i));b.setAttribute('aria-label',`Example ${i+1}${session.answers[c.id]?.answer?', answered':''}`);b.setAttribute('aria-current',String(i===currentIndex));b.dataset.answered=String(!!session.answers[c.id]?.answer);return b;}));
 const box=$('auditCoverageBody');box.replaceChildren();const add=s=>{const n=document.createElement('p');n.textContent=s;box.append(n);};
 add(Object.entries({boundary:'Phrase boundaries',grouping:'Grouping / accents',repetition:'Repetition / development',dialogue:'Call and response',sustain:'Rest / sustain function'}).map(([k,n])=>`${n}: ${p.by_kind[k]||0}/${deck.cases.filter(c=>c.question.kind===k).length}`).join(' | '));
 add(['Invent Animate','Currents','ERRA'].map(a=>`${a}: ${p.by_artist[a]||0}/4`).join(' | '));
 add(deck.coverage?.summary??'12-item balanced pilot, not comprehensive validation or a population accuracy estimate.');
 add('Next: revise questions using this pilot, then expand to 60 development judgments, 12 per dimension. Reserve new songs for a separate later check.');
 if(deck.coverage?.remaining_presence?.length)add('Not yet covered: '+deck.coverage.remaining_presence.join(', '));
 const pending=deck.cases.filter(c=>!session.answers[c.id]?.answer||session.answers[c.id].answer==='unsure');add(`${pending.length} questions still need a definite judgment. Export includes the exact questions, tags and unanswered cases for follow-up.`);
}
async function asset(meta){if(!meta?.path||!meta.sha256)throw Error('Required saved data has no verified binding.');const k=meta.path+':'+meta.sha256;if(!cache.has(k))cache.set(k,verifiedJson(meta.path,meta.sha256).catch(e=>{cache.delete(k);throw e;}));return cache.get(k);}
function verifyPhrase(result,p){if(p.components?.length){let cursor=new Q(p.start_q);for(const part of p.components){verifyPhrase(result,part);if(cursor.cmp(part.start_q)!==0)throw Error('Combined rhythm span has a gap or overlap.');cursor=new Q(part.end_q);}if(cursor.cmp(p.end_q)!==0)throw Error('Combined rhythm span end differs.');return p;}const found=result.phrases?.find(x=>x.id===p.id);if(!found||found.start_q!==p.start_q||found.end_q!==p.end_q)throw Error('Phrase boundaries differ from this audit version.');return found;}
function sidePhrase(side){return side==='A'?current().comparison:current().primary;}
function selectSide(side,context=false){const c=current(),p=sidePhrase(side);context=context||blindBoundary();const range=context?(c.context_range_q??loaded.ref.range_q):[p.start_q,p.end_q];playingSide=context?'captured riff context':c.comparison?side:'phrase';player.load(loaded.ref,range);board.load(loaded.ref,range,playingSide,loaded.geometry,'target',blindBoundary()?range:[p.start_q,p.end_q]);renderPhraseShapes($('auditShapeCards'),$('auditShapeNotice'),loaded.shapes,p,document);$('auditPairIdentity').textContent=blindBoundary()?`Continuous excerpt: ${c.context_range_q[0]} to ${c.context_range_q[1]}q in the song. Mark positions relative to excerpt start. Model cuts are hidden.`:c.comparison?`A: phrase ${c.comparison.ordinal??''}, ${span(c.comparison)} \xb7 B: phrase ${c.primary.ordinal??''}, ${span(c.primary)}.`:`Selected span: ${span(p)}. Context is the available captured riff, not the whole song.`;if(loaded.geometryError)$('auditNotice').textContent+=' '+loaded.geometryError;if(loaded.shapesError)$('auditShapeNotice').textContent=loaded.shapesError;}
function describePlan(plan){
 const sounding=plan.mode==='click'?plan.clicks.length:plan.mode==='neutral'?plan.notes.length:plan.notes.filter(n=>!n.percussion?Number.isFinite(n.pitch)&&n.pitch!==null:!n.carry_in).length;
 const omitted=plan.mode==='pitch'?plan.notes.length-sounding:0;
 return `${plan.duration.toFixed(2)} seconds. `+(!sounding?'Silent in this playback mode: no playable events in this selection. Play context to hear the surrounding notes. ':plan.duration<.5?'Very short phrase; use Play context for a longer listen. ':'')+(omitted?`${omitted} notes without usable pitches are omitted in source-pitch mode. `:'')+(plan.gaps.length?`Partial notation preview: ${sounding} playable notes${omitted?', '+omitted+' notes without pitches omitted':''}. Unresolved timing and grace notes are omitted, never guessed. `:'');
}
function preview(side,context=false){context=context||blindBoundary();const c=current(),p=sidePhrase(side);return compileSchedule(loaded.ref,context?(c.context_range_q??loaded.ref.range_q):[p.start_q,p.end_q],{mode:$('auditMode').value||'neutral',normalized:false,speed:Number($('auditSpeed').value||1),allowPartial:true});}
async function startSide(side,epoch,context=false){context=context||blindBoundary();if(!loaded||epoch!==playEpoch)return;clipNotice=describePlan(preview(side,context));selectSide(side,context);await player.setOptions({mode:$('auditMode').value||'neutral',normalized:false,loop:!pairPlayback&&!context&&$('auditLoop').checked,allowPartial:true,speed:Number($('auditSpeed').value||1),timbre:$('auditTone').value||'bright'});if(epoch!==playEpoch)return;await player.play();}
async function play(side,context=false,pair=false){if(!loaded)return;stop();const epoch=playEpoch;const unlocked=player.unlock();$('auditAudioStatus').textContent='Starting audio...';pairPlayback=pair;if(pair)queue={side:'B',epoch};try{await unlocked;if(epoch===playEpoch)await startSide(side,epoch,context);}catch(e){if(epoch===playEpoch)showPlaybackError(e);}}
$('auditPlay').onclick=()=>play(current().comparison?'A':'B');$('auditPlayB').onclick=()=>play('B');$('auditPair').onclick=()=>play('A',false,true);$('auditContext').onclick=()=>play('B',true);$('auditStop').onclick=()=>stop();
$('auditPause').onclick=async()=>{const epoch=playEpoch;try{if(player.state==='playing')player.pause();else if(player.state==='paused')await player.play();}catch(e){if(epoch===playEpoch)showPlaybackError(e);}};
$('auditNote').oninput=()=>save();
$('auditConfidence').onchange=()=>save();$('auditContextQuality').onchange=()=>save();$('auditBoundaryMarks').oninput=()=>{try{validBoundaryMarks();divisionRoll.setMarks($('auditBoundaryMarks').value);$('auditMarkError').textContent='';save();}catch(e){$('auditMarkError').textContent=e.message;}};
for(const id of ['auditMode','auditSpeed','auditLoop'])$(id).onchange=()=>{stop();if(loaded){clipNotice=describePlan(preview(current().comparison?'A':'B'));$('auditAudioStatus').textContent='Playback setting changed. Tap Play. '+clipNotice;}};
$('auditTone').onchange=()=>{stop();$('auditAudioStatus').textContent='Tone changed. Tap Play. '+clipNotice;};
$('auditSoundTest').onclick=async()=>{
 stop();const epoch=playEpoch;clipNotice='Sound test: a short 440 Hz tone, not part of the source phrase. If silent, raise media volume and check Bluetooth/output routing.';playingSide='sound test';$('auditPosition').disabled=true;const unlocked=player.unlock();$('auditAudioStatus').textContent='Starting sound test...';
 try{await unlocked;if(epoch!==playEpoch)return;player.load({tempo_map:[{onset_q:'0',quarter_bpm:120}],events:[{onset_q:'0',members:[{id:'sound-test',onset_q:'0',written_end_q:'1',pitch:69}]}]},['0','1']);await player.setOptions({mode:'pitch',speed:1,normalized:false,allowPartial:true,loop:false,timbre:$('auditTone').value||'bright'});if(epoch!==playEpoch)return;await player.play();if(epoch!==playEpoch||player.state!=='playing')return;$('auditAudioStatus').textContent='Sound test playing. If silent, raise media volume and check Bluetooth/output routing.';}catch(e){if(epoch===playEpoch)showPlaybackError(e);}
};
$('auditPrevious').onclick=()=>loadCase(currentIndex-1);$('auditNext').onclick=()=>{if(currentIndex<deck.cases.length-1)loadCase(currentIndex+1);else{$('auditCoverage').open=true;$('auditCoverage').scrollIntoView({behavior:'smooth',block:'center'});}};
function setPlaybackDisabled(value){for(const id of ['auditPlay','auditPlayB','auditPair','auditContext','auditPosition'])$(id).disabled=value;}
function renderTimeline(c,ref){
 const box=$('auditTimeline');box.replaceChildren();if(!ref)return;if(blindBoundary())c={...c,primary:{start_q:c.context_range_q[0],end_q:c.context_range_q[1]},comparison:null};
 const [lo,hi]=ref.range_q.map(qnum),width=Math.max(320,Math.min(620,box.clientWidth||620)),height=126,pad=18,x=q=>pad+(q-lo)/(hi-lo)*(width-pad*2);
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.setAttribute('width',width);svg.setAttribute('height',height);svg.setAttribute('role','img');svg.setAttribute('aria-label','Selected phrase boundaries within the captured riff. Blue marks the phrase, purple marks earlier comparison A. Vertical marks are note attacks; horizontal lines are holds.');
 const draw=(tag,attrs,label='')=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(label)n.textContent=label;svg.append(n);return n;};
 draw('rect',{x:0,y:0,width,height,fill:'#f8fafc'});
 for(const [p,label,color]of [[c.primary,c.comparison?'B':'Phrase','#155ac0'],...(c.comparison?[[c.comparison,'A','#7c3aed']]:[])]){
  const a=x(qnum(p.start_q)),b=x(qnum(p.end_q));draw('rect',{x:a,y:27,width:Math.max(1,b-a),height:67,fill:color,opacity:.1});draw('line',{x1:a,x2:a,y1:22,y2:99,stroke:color,'stroke-width':2});draw('line',{x1:b,x2:b,y1:22,y2:99,stroke:color,'stroke-width':2});draw('text',{x:(a+b)/2,y:15,'text-anchor':'middle',fill:color,'font-size':12},label);}
 const seen=new Set();for(const e of [...(ref.events??[]),{members:ref.carry_in??[]}])for(const m of e.members??[]){if(seen.has(m.id))continue;seen.add(m.id);try{const on=qnum(m.onset_q??e.onset_q),off=qnum(memberEnd(m));if(off<=lo||on>=hi)continue;const y=41+(Number(m.pitch??60)%8)*6;draw('line',{x1:x(Math.max(lo,on)),x2:x(Math.min(hi,off)),y1:y,y2:y,stroke:'#546b84','stroke-width':3});if(on>=lo)draw('line',{x1:x(on),x2:x(on),y1:34,y2:90,stroke:'#546b84',opacity:.35});}catch{}}
 for(const [q,anchor]of [[lo,'start'],[hi,'end']])draw('text',{x:x(q),y:117,'text-anchor':anchor,fill:'#536476','font-size':11},q+'q');box.append(svg);
}

function renderComparison(ev){
 const box=$('auditComparison'),answered=!!session?.answers[current().id]?.answer;box.hidden=!ev.comparison||!answered;$('auditPairDetails').hidden=box.hidden;if(box.hidden){box.textContent='';return;}
 const sig=s=>(s.attacks??[]).map(a=>a.offset_q).join('|');
 const holds=s=>(s.attacks??[]).map(a=>a.offset_q+':'+[...new Set((a.members??[]).map(m=>m.tied_duration_q??m.written_duration_q))].sort().join(',')).join('|')+';carry:'+JSON.stringify((s.carry_in??[]).map(m=>String(new Q(m.tied_end_q??m.end_q??s.start_q).sub(s.start_q))).sort());
 const a=ev.comparison,b=ev.primary,equal=String(a.duration_q)===String(b.duration_q),attacks=equal&&sig(a)===sig(b),same=attacks&&holds(a)===holds(b);
 box.textContent=`Measured comparison: A ${a.duration_q}q / ${(a.attacks??[]).length} attacks; B ${b.duration_q}q / ${(b.attacks??[]).length} attacks. `+(!equal?'Phrase lengths differ. ':attacks?'Relative attack positions match. ':'Relative attack positions differ. ')+(same?'Known tied-note lengths also match. ':attacks?'Known tied-note lengths differ. ':'')+'This is measured source structure, not a learned call-and-response label.';
 const q=current().question;if(q.kind==='relation'){$('auditModelAnswer').textContent='Measured timing, not a musical verdict: '+(same?'Same attacks and holds':attacks?'Same attacks, different holds':'Different attack timing');}
}



function blindBoundary(){return !!deck&&current().question.kind==='boundary'&&!session?.answers[current().id]?.model_revealed_at;}
function safeBoundaryMarks(){try{return validBoundaryMarks();}catch(e){$('auditMarkError').textContent=e.message;return session.answers[current().id]?.boundary_marks??'';}}
function validBoundaryMarks(){const raw=$('auditBoundaryMarks').value.trim();parseDivisions(raw,current().context_range_q);return raw;}
function updateReveal(){
 if(!deck||!session)return;const c=current(),a=session.answers[c.id];$('auditReveal').disabled=!a?.answer;$('auditModel').hidden=!a?.model_revealed_at;
 $('auditReveal').textContent=a?.model_revealed_at?'Model has been revealed':'Reveal model after answering';
 $('auditRevealStatus').textContent=a?.model_revealed_at?'Later edits are recorded as made after model reveal.':'Your first judgment is saved before you see the model.';
 $('auditShapes').hidden=blindBoundary();$('auditFretboard').hidden=blindBoundary();if(loaded){const ev=evidence?.cases.find(x=>x.id===c.id);if(ev)renderComparison(ev);}
 if(a?.model_revealed_at){const ev=evidence?.cases.find(x=>x.id===c.id);const cuts=(ev?.context?.phrases??[]).slice(1).map(p=>String(new Q(p.start_q).sub(c.context_range_q[0]))).filter(v=>qnum(v)>0&&qnum(v)<qnum(new Q(c.context_range_q[1]).sub(c.context_range_q[0])));$('auditModelAnswer').textContent=c.question.kind==='boundary'?'Model cuts inside this excerpt: '+(cuts.length?cuts.map(x=>'+'+x+'q').join(', '):'none')+'. These are hypotheses, not correct answers.':c.question.model_note??c.question.model_label??'No musical verdict is established for this question.';$('auditModelExplanation').textContent=c.question.explanation??'';}
}
function renderVisibleRhythm(box,c,ev){
 if(blindBoundary()){
  const stream=ev.context?.stream;if(!stream)throw Error('Continuous context evidence is missing.');
  renderRhythm(box,{...c,primary:stream,comparison:null,question:{...c.question,target_evidence:null}},{...ev,primary:stream,comparison:null,context:{...ev.context,phrases:[]}});
  for(const n of box.querySelectorAll('h4'))n.textContent='Continuous excerpt (model cuts hidden)';
 }else renderRhythm(box,c,ev);
}
$('auditReveal').onclick=()=>{const c=current(),a=session.answers[c.id];if(!a?.answer||a.model_revealed_at)return;putAnswer(session,c,a.answer,a.note,new Date().toISOString(),{...a,model_revealed_at:new Date().toISOString()});persist();updateReveal();if(loaded){redrawRhythm(true);renderTimeline(c,loaded.ref);if(player.state==='stopped')selectSide(c.comparison?'A':'B');}};

let rhythmResizeTimer;
function redrawRhythm(force=false){
 if(!loaded||!evidence||panel.hidden)return;const box=$('auditRhythm');const width=Math.max(300,Math.min(640,Math.floor((box.clientWidth||664)-24)));
 if(!force&&Number(box.dataset.gridWidth)===width)return;
 const opened=Array.from(box.querySelectorAll?.('details')??[]).map(d=>d.open);const ev=evidence.cases.find(x=>x.id===current().id);renderVisibleRhythm(box,current(),ev);Array.from(box.querySelectorAll?.('details')??[]).forEach((d,i)=>d.open=!!opened[i]);
}
window.addEventListener('resize',()=>{clearTimeout(rhythmResizeTimer);rhythmResizeTimer=setTimeout(()=>{redrawRhythm();divisionRoll.draw();},80);});
window.addEventListener('orientationchange',()=>{clearTimeout(rhythmResizeTimer);rhythmResizeTimer=setTimeout(()=>{redrawRhythm();divisionRoll.draw();},120);});

async function loadCase(i){
 if(!deck||i<0||i>=deck.cases.length)return;stop();const epoch=++loadEpoch;loaded=null;divisionRoll.clear();currentIndex=i;session.index=i;const c=current(),a=session.answers[c.id];
 $('auditTitle').textContent=text(c.artist)+' / '+text(c.title);$('auditType').textContent=`Set ${c.set} \xb7 Example ${i+1} of ${deck.cases.length} \xb7 ${({boundary:'Phrase boundaries',grouping:'Grouping / perceived accents',repetition:'Repetition / development',dialogue:'Call and response',sustain:'Rest / sustain function'})[c.question.kind]}`;
 $('auditSource').textContent='Source part '+text(c.part??'unknown');$('auditQuestion').textContent=c.question.text;$('auditHint').textContent=c.question.hint??'';$('auditNote').value=a?.note??'';$('auditConfidence').value=a?.confidence??'';$('auditContextQuality').value=a?.context_quality??'';$('auditBoundaryMarks').value=a?.boundary_marks??'';$('auditMarkError').textContent='';$('auditMode').value=c.question.kind==='sustain'&&c.playback_quality?.unknown_pitch_members?'neutral':'pitch';$('auditBoundaryWrap').hidden=false;updateReveal();
 $('auditModelAnswer').textContent='No musical verdict established. This question needs your judgment.';$('auditModelExplanation').textContent=c.question.explanation??'';$('auditModel').open=false;$('auditShapes').open=false;
 $('auditRhythm').replaceChildren();$('auditComparison').hidden=true;$('auditPairDetails').hidden=true;$('auditPairDetails').open=false;clipNotice='';$('auditPartial').checked=true;$('auditPartialWrap').hidden=true;renderTimeline(c);$('auditPlay').textContent=c.comparison?'Play A':'Play phrase';$('auditPlayB').hidden=!c.comparison;$('auditPair').hidden=!c.comparison;$('auditPrevious').disabled=i===0;$('auditNext').textContent=i===deck.cases.length-1?'Review progress':deck.cases[i+1]?.set!==c.set?'Next set':'Next example';
 $('auditContextAdvice').textContent='Start with the surrounding context, then use the isolated excerpt if useful.';$('auditAudioStatus').textContent='Loading verified phrase data\u2026';$('auditPairIdentity').textContent='';$('auditShapeCards').replaceChildren();$('auditShapeNotice').textContent='';$('auditNotice').textContent='';$('auditReadout').textContent='';board.model=null;board.ctx.clearRect(0,0,board.canvas.width,board.canvas.height);setPlaybackDisabled(true);renderAnswers();renderProgress();persist();
 try{
  const result=await asset(c.assets.result??c.assets.analysis),ref=await asset(c.assets.playback);if(epoch!==loadEpoch)return;
  if(result.id!==c.riff_id||result.revision!==c.revision||ref.id!==c.riff_id||String(ref.binding?.song_id)!==String(c.source_song_id))throw Error('Source identity differs from the frozen deck.');
  verifyPhrase(result,c.primary);if(c.comparison)verifyPhrase(result,c.comparison);
  for(const p of [c.primary,c.comparison].filter(Boolean)){if(new Q(p.start_q).cmp(ref.range_q[0])<0||new Q(p.end_q).cmp(ref.range_q[1])>0)throw Error('The phrase is outside the saved audio excerpt.');}
  let geometry=null,shapes=null,geometryError='',shapesError='';
  try{geometry=await asset(c.assets.fretboard);if(geometry.id!==c.riff_id||geometry.revision!==c.revision||geometry.playback_sha256!==c.assets.playback.sha256)throw Error('Fretboard source binding differs.');}catch(e){geometry=null;geometryError='Fretboard unavailable: '+e.message;}
  try{shapes=await asset(c.assets.shapes);if(shapes.id!==c.riff_id||shapes.revision!==c.revision||shapes.result_sha256!==(c.assets.result??c.assets.analysis).sha256)throw Error('Shape source binding differs.');}catch(e){shapes=null;shapesError='Shapes unavailable: '+e.message;}
  if(epoch!==loadEpoch)return;loaded={result,ref,geometry,shapes,geometryError,shapesError};divisionRoll.load(ref,c.context_range_q,a?.boundary_marks??'');$('auditDivisionOrigin').textContent=`Time runs left to right, pitch runs upward. +0q is the excerpt start (source ${c.context_range_q[0]}q). Each mark proposes a split across the selected part, not a change to the notes. Model cuts are not shown on this roll.`;const ev=evidence.cases.find(x=>x.id===c.id);if(!ev||ev.revision!==c.revision)throw Error('Rhythm evidence differs from this source revision.');renderVisibleRhythm($('auditRhythm'),c,ev);renderComparison(ev);renderTimeline(c,ref);selectSide(c.comparison?'A':'B');setPlaybackDisabled(false);updateReveal();
  const labels=c.comparison?[['A',c.comparison],['B',c.primary]]:[['phrase',c.primary]];
  const descriptions=[];let partial=false;
  for(const [label]of labels){const plan=preview(label==='A'?'A':'B');partial ||= plan.gaps.length>0;descriptions.push((c.comparison?label+': ':'')+describePlan(plan));}
  const first=preview(c.comparison?'A':'B'),silent=first.mode==='click'?!first.clicks.length:!first.notes.length;
  $('auditPlay').textContent=blindBoundary()?'Play excerpt':silent?'Play silent span':c.comparison?'Play A':partial?'Play available notation':'Play phrase';
  $('auditContext').textContent=blindBoundary()?'Play full excerpt':c.question.kind==='dialogue'?'Play dialogue in context':'Play context first';const short=labels.some(([side])=>preview(side==='A'?'A':'B').duration<1),missing=c.playback_quality?.unknown_pitch_members??0;$('auditContextAdvice').textContent=c.question.kind==='sustain'&&missing?`Rhythm + holds is recommended for this pause/hold judgment: it includes every known attack and hold. The highlighted gesture has complete timing and pitches. Optional source-pitch context omits ${missing} notes with unknown pitches later in the wider excerpt, outside the target.`:short?'These isolated gestures are under a second. Start with context; isolated playback is only an optional close-up.':'Start with the surrounding context, then compare the isolated gestures if useful.';
  clipNotice=descriptions.join(' ');$('auditAudioStatus').textContent=clipNotice+' Playback starts when you press Play.';

 }catch(e){if(epoch!==loadEpoch)return;$('auditAudioStatus').textContent='Data unavailable: '+e.message+' You can choose Unsure and continue.';}
}
$('auditExport').onclick=()=>{
 const payload={...session,exported_at:new Date().toISOString(),source_snapshot:deck.source_snapshot,deck,progress:progress(deck,session),unreadable_previous_storage:rawRecovery,legacy_archive:{manifest_sha256:deck.legacy_manifest_sha256,deck:legacyDeck,raw_saved_feedback:legacyRaw},previous_rhythm_archive:{manifest_sha256:deck.previous_manifest_sha256,deck:previousDeck,raw_saved_feedback:previousRaw},prior_archives:priorArchives,rhythm_evidence:{path:deck.evidence.path,sha256:deck.evidence.sha256}};
 const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='rhythm-audit-'+deck.id+'-'+new Date().toISOString().slice(0,10)+'.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);$('auditBackupStatus').textContent='Backup download started. Send that JSON file to dot when you want the answers reviewed.';
};
$('auditImport').onclick=()=>$('auditImportFile').click();$('auditImportFile').onchange=async()=>{const file=$('auditImportFile').files?.[0];if(!file)return;try{if(file.size>10000000)throw Error('Backup is too large.');const raw=JSON.parse(await file.text());if([deck.legacy_manifest_sha256,deck.previous_manifest_sha256].includes(raw.manifest_sha256))throw Error('This backup is from an earlier review version. It has not been overwritten or counted toward revised questions. Keep it; the new deck saves answers separately.');const incoming=validateSession(raw,deck,hash);session=mergeSessions(session,incoming);persist();await loadCase(currentIndex);$('auditBackupStatus').textContent='Backup merged. Newer answers were kept; earlier versions remain in the export history.';}catch(e){$('auditBackupStatus').textContent='Backup not restored: '+e.message;}$('auditImportFile').value='';};
window.addEventListener('pagehide',()=>stop());
async function init(){try{
 deck=validateManifest(await verifiedJson('rhythm-pilot/manifest.json',hash));evidence=await verifiedJson(deck.evidence.path,deck.evidence.sha256);if(evidence.source_selection_sha256!==deck.source_selection_sha256||evidence.cases.length!==deck.cases.length)throw Error('Rhythm evidence binding is invalid.');legacyDeck=await verifiedJson('rhythm-audit/manifest.json',deck.legacy_manifest_sha256);previousDeck=await verifiedJson(deck.previous_manifest_path,deck.previous_manifest_sha256);try{previousRaw=localStorage.getItem('rhythm-audit:'+deck.previous_manifest_sha256);}catch{}try{legacyRaw=localStorage.getItem('rhythm-audit:'+deck.legacy_manifest_sha256);}catch{}$('auditLegacy').textContent='12-example pilot. Answer before revealing the model. Earlier review answers stay separate and unchanged.';storageKey='rhythm-pilot:'+hash;session=newSession(deck,hash);
 try{const raw=localStorage.getItem(storageKey);if(raw){try{session=validateSession(JSON.parse(raw),deck,hash);}catch(e){rawRecovery=raw;storageError='An earlier save could not be read, so it has not been overwritten.';}}}catch(e){storageError='Browser storage is unavailable.';}
 $('auditSampling').textContent=typeof deck.sampling==='string'?deck.sampling:JSON.stringify(deck.sampling);$('auditProgress').max=deck.cases.length;for(const v of [1,2,3]){try{const path=v===1?'rhythm-audit/manifest.json':`rhythm-audit/manifest-v${v}.json`,response=await fetch(path),bytes=await response.arrayBuffer(),d=JSON.parse(new TextDecoder().decode(bytes)),h=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');priorArchives.push({manifest_sha256:h,deck_id:d.id,raw_saved_feedback:localStorage.getItem('rhythm-audit:'+h)});}catch{}}
 $('auditVersion').textContent='Deck '+deck.id+' \xb7 Snapshot '+(deck.source_snapshot?.index_sha256??deck.source_snapshot?.files?.find(f=>f.path==='index.json')?.sha256??'').slice(0,12)+' \xb7 Answers are tied to this exact version.';
 $('auditLoadStatus').textContent='';$('auditContent').hidden=false;await loadCase(session.index);
 }catch(e){$('auditLoadStatus').textContent='Audit could not load: '+e.message+' Use Browse all phrases while this is unavailable.';$('auditLoadStatus').dataset.error='true';}}
export const ready=init();
