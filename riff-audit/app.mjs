import {mountGeneration} from './generation-ui.mjs';
import {Q,qnum,qmin,qmax,compileSchedule,playbackGaps} from './timing.mjs';
import {loadCatalog,loadReference} from './static-data.mjs';
import {ReferencePlayer} from './player.mjs';
import {pitchedLaneGeometry,formatTime} from './review-helpers.mjs';
const $=id=>document.getElementById(id),el=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
const svg=(tag,attrs={},text)=>{const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;};
const state={catalog:null,records:[],lane:'reviewed',limit:100,record:null,ref:null,base:null,view:null,unit:null,loadId:0,plan:null,roll:null};
const text=(id,value)=>$(id).textContent=value,pretty=value=>JSON.stringify(value,null,2),human=s=>String(s??'unknown').replaceAll('_',' ');
const showError=e=>{text('error',e.message??String(e));$('error').hidden=false;};
function hideError(){$('error').hidden=true;}
function identity(r){if(r.origin==='human'&&r.status==='accepted')return 'Human accepted';if(r.origin==='agent_inference'&&r.status==='accepted')return 'Inferred accepted';return human(r.status);}
export function matches(r,{lane='reviewed',search='',identityFilter='all',availability='all'}={}){
 if((lane==='reviewed')!==(r.collection==='reviewed'))return false;
 if(search&&!`${r.artist} ${r.song} ${r.track} ${r.id}`.toLowerCase().includes(search.toLowerCase()))return false;
 if(identityFilter==='riffs'&&!['accepted','riff'].includes(r.status))return false;
 if(identityFilter==='human'&&!(r.origin==='human'&&r.status==='accepted'))return false;
 if(identityFilter==='inferred'&&!(r.origin==='agent_inference'&&r.status==='accepted'))return false;
 if(identityFilter==='uncertain'&&!['unknown','unsure','unresolved'].includes(r.status))return false;
 if(identityFilter==='excluded'&&!['rejected','duplicate','excluded','nonriff'].includes(r.status)&&r.collection!=='automatic_excluded')return false;
 if(availability==='available'&&r.replay_export_status!=='ready')return false;
 if(availability==='pending'&&r.replay_export_status!=='pending')return false;
 if(availability==='missing'&&r.available)return false;
 if(availability==='training'&&!r.model_eligibility?.current_training)return false;
 return true;
}
function renderCatalog(){
 const options={lane:state.lane,search:$('search').value.trim(),identityFilter:$('identityFilter').value,availability:$('availabilityFilter').value};
 const records=state.records.filter(r=>matches(r,options));$('records').replaceChildren();
 for(const r of records.slice(0,state.limit)){
  const b=el('button','record'+(r.replay_export_status!=='ready'?' unavailable':''));b.dataset.id=r.id;b.setAttribute('aria-pressed',String(state.record?.id===r.id));
  b.append(el('strong','',r.song||'Untitled source'),el('small','',`${r.artist} · ${r.track}`),el('small','record-status',`${identity(r)}${recordPending(r)?' · Public export pending':recordOutOfScope(r)?' · Metadata only':!r.available?' · Replay unavailable':''}${r.boundary?.current_capture_human_approved?' · Crop approved':''}`));
  b.onclick=()=>loadRecord(r);$('records').append(b);
 }
 text('resultCount',`${records.length.toLocaleString()} matching ${state.lane==='reviewed'?'reviewed references':'automatic hypotheses'} · ${Math.min(records.length,state.limit)} shown`);
 if(!records.length)$('records').append(el('p','micro','No references match. Try clearing a filter.'));
 $('moreRecords').hidden=records.length<=state.limit;
 $('reviewedLane').setAttribute('aria-pressed',String(state.lane==='reviewed'));$('automaticLane').setAttribute('aria-pressed',String(state.lane==='automatic'));
 text('laneNote',state.lane==='reviewed'?'Identity judgments and crop approvals are separate.':'Overlapping automatic hypotheses. These are not additional independent reviewed riffs.');
 const all=state.records.filter(r=>(r.collection==='reviewed')===(state.lane==='reviewed'));
 text('catalogStats',`${all.filter(r=>r.replay_export_status==='pending').length.toLocaleString()} public exports pending · ${all.filter(r=>['unknown','unsure','unresolved'].includes(r.status)).length.toLocaleString()} uncertain · ${all.filter(r=>['rejected','duplicate','excluded','nonriff'].includes(r.status)||r.collection==='automatic_excluded').length.toLocaleString()} excluded / negative · ${all.filter(r=>!r.available).length.toLocaleString()} unavailable`);
}
function busy(value){$('play').disabled=value||!state.ref?.available;$('stop').disabled=value||!state.ref?.available;$('seek').disabled=value||!state.ref?.available;document.body.dataset.busy=String(value);}
async function loadRecord(record,options={}){
 if(state.record?.id!==record.id){$('voice').value='all';state.base=null;}
 const token=++state.loadId;player.stop();state.ref=null;window.dispatchEvent(new CustomEvent('riff-selection'));$('allowPartial').checked=false;busy(true);hideError();state.record=record;renderCatalog();
 text('artist',record.artist);text('song',record.song);text('sourceLine',record.track);$('reference').hidden=false;$('loading').hidden=true;
 text('playbackStatus','Loading and verifying the source…');
 try{
  const ref=await loadReference(record,{view_id:options.view??null,start_q:options.range?.[0]??null,end_q:options.range?.[1]??null,voices:$('voice').value&&$('voice').value!=='all'?[Number($('voice').value)]:null});if(token!==state.loadId)return;
  state.ref=ref;if(!options.range||!state.base)state.base=ref;state.view=options.view??ref.selection?.view_id??ref.views?.at(-1)?.id;state.unit=options.unit??null;
  renderReference();document.body.dataset.ready='true';window.dispatchEvent(new CustomEvent('riff-selection',{detail:{reference:ref}}));
 }catch(e){if(token===state.loadId){state.ref=null;showError(e);text('playbackStatus','Playback unavailable. No source data was changed.');}}finally{if(token===state.loadId){busy(false);if(state.ref?.available)refreshPlan();}}
}
function auditionReference(){const ref=state.ref;if($('auditionScope').value==='context'&&ref?.context)return {...ref,...ref.context,selection:{...ref.selection,range_q:ref.context.range_q}};return ref;}
function auditionRange(){return auditionReference()?.selection?.range_q??range();}
function range(){return state.ref?.selection?.range_q??state.ref?.range_q??state.record?.range_q;}
function recordPending(r){return r.replay_export_status==='pending';}
function recordOutOfScope(r){return ['out_of_scope','outside_scope'].includes(r.replay_export_status);}
function badge(label,cls=''){return el('span','badge '+cls,label);}
function viewName(v){return ({construction_runs:'Rhythm / gesture units',continuous_untyped:'Untyped region',motif_occurrence_cover:'Verified motif operands',verified_nested_0:'Nested motif operands'})[v.id]??human(v.id);}
function unitName(u){if(u.unit_kind==='verified_motif_operand')return 'Verified motif operand';if(/untyped/.test(u.unit_kind??''))return 'Untyped region';if(/phrase/.test(u.unit_kind??''))return 'Phrase-scale candidate';return `Rhythm / gesture candidate · ${human(u.unit_kind??u.child_kind)}`;}
function activeView(){return(state.base?.views??state.ref?.views??[]).find(v=>v.id===state.view);}
function renderUnits(){
 $('view').replaceChildren();for(const v of state.base?.views??state.ref?.views??[]){const option=el('option','',viewName(v));option.value=v.id;$('view').append(option);}$('view').value=state.view??'';
 $('units').replaceChildren();const units=activeView()?.ordered_units??[];
 for(const [i,u]of units.entries()){
  const b=el('button','unit');b.dataset.unit=u.id;b.setAttribute('aria-pressed',String(state.unit===u.id));b.append(el('strong','',`${i+1}. ${unitName(u)}`),el('small','',`${u.range_q?.join(' → ')} q · ${u.attack_count??'?'} attacks`));
  b.onclick=()=>loadRecord(state.record,{view:state.view,range:u.range_q,unit:u.id});$('units').append(b);
  if(state.unit===u.id){const root=(state.base?.hierarchy?.roots??[]).find(r=>JSON.stringify(r.range_q)===JSON.stringify(u.range_q));
   for(const [j,c]of(root?.children??[]).entries()){
    const child=el('button','unit child');child.append(el('strong','',`↳ ${human(c.child_kind??'rhythm_subunit')} · gesture ${j+1}`),el('small','',`${c.range_q?.join(' → ')} q`));child.onclick=()=>loadRecord(state.record,{view:state.view,range:c.range_q,unit:u.id});$('units').append(child);
   }
  }
 }
 if(!units.length)$('units').append(el('p','micro','No nested view is mapped for this reference. Exact subranges remain available when replay is mapped.'));
 const u=units.find(u=>u.id===state.unit);text('unitDetails',u?`${unitName(u)}. Boundary status: ${human(u.boundary_status)}. ${u.provenance?.kind?`Origin: ${human(u.provenance.kind)}.`:''} Semantic role: unknown.`:'Whole-riff audition. Inner boundaries are evidence-backed candidates, not listener-accepted phrase truth.');
}
function renderReference(){
 const r=state.record,ref=state.ref,rg=range();
 const attribution=[r.attribution_flags,r.attribution_caveats,r.caveats].flatMap(v=>v==null?[]:Array.isArray(v)?v:[v]);$('attributionNotice').hidden=!attribution.length;text('attributionNotice',attribution.length?`Catalogue attribution caveat: ${attribution.map(v=>typeof v==='string'?human(v):pretty(v)).join('; ')}. Artist tags do not establish verified authorship.`:'');$('availabilityNotice').hidden=ref.available;
 text('sourceLine',`${ref.track_metadata?.name??r.track} · ${r.id}`);
 const badges=$('statusBadges');badges.replaceChildren(badge(identity(r),r.status==='accepted'?'positive':'warn'),badge(r.boundary?.current_capture_human_approved?'Crop approved':'Crop not human-approved',r.boundary?.current_capture_human_approved?'positive':'warn'),badge(r.model_eligibility?.current_training?'Current training':'Not current training'),badge(r.split?`Split: ${r.split}`:'Split unknown'));
 if(!ref.available&&recordOutOfScope(r))text('availabilityNotice','Metadata-only: this excluded, negative or uncertain row is outside the identified-riff public audition scope. It remains visible so the catalogue does not hide these judgments.');
 else if(!ref.available&&recordPending(r))text('availabilityNotice','Public replay export is pending for this source-mapped hypothesis. Its status and timing range remain visible; this is not a missing-source or nonriff verdict.');
 else if(!ref.available)text('availabilityNotice',`Replay unavailable: ${(r.unavailable_reasons??ref.unavailable_reasons??[]).join('; ')||'No current source binding.'} This catalogue record has been retained.`);
 text('rangeSummary',rg?`${rg[0]} → ${rg[1]} q`:'Range unavailable');$('rangeStart').value=rg?.[0]??'';$('rangeEnd').value=rg?.[1]??'';
 const selectedVoice=$('voice').value||'all';$('voice').replaceChildren();const allVoice=el('option','','All available voices');allVoice.value='all';$('voice').append(allVoice);for(const voice of ref.available_voices??[]){const option=el('option','',`Voice ${voice}`);option.value=String(voice);$('voice').append(option);}$('voice').value=selectedVoice;
 renderUnits();renderFacts();
 if(ref.available){player.options=settings();player.load(auditionReference(),auditionRange());$('seek').min=String(qnum(auditionRange()[0]));$('seek').max=String(qnum(auditionRange()[1]));refreshPlan();renderRoll();}
 else{state.plan=null;$('roll').replaceChildren();text('playbackStatus',recordPending(r)?'This mapped record is awaiting public rhythm export.':recordOutOfScope(r)?'Metadata-only: outside the identified-riff public audition scope.':'This record remains visible, but has no playable source binding.');}
 soundExplanation();
}
function renderFacts(){
 const ref=state.ref,r=state.record,c=ref.coverage??{};
 const facts=[['Identity judgment',`${identity(r)} · ${human(r.origin)}`],['Crop boundary',r.boundary?.current_capture_human_approved?'Human-approved':human(r.boundary?.confidence)],['Training status',`${r.model_eligibility?.current_training?'Included':'Not included'} · ${r.split??'unknown split'}`],['Source track',ref.track_metadata?.name??r.track],['Exact selected range',(range()??[]).join(' → ')+' quarters'],['Timing coverage',`${c.attack_groups??0} attacks · ${c.attack_members??0} members · ${c.explicit_rests??0} explicit rests`],['Carries',`${c.carry_in_members??0} incoming · ${c.carry_out_members??0} outgoing`],['Source order','Written score order, once. Repeats/endings are retained but not expanded.'],['Timing uncertainty',ref.unplaced_or_unknown?.length?`${ref.unplaced_or_unknown.length} unknown / unplaced source events retained`:'See coverage and source warnings'],['Synthesis',`Written/tied envelopes only. Neutral rhythm only; source pitch and guitar techniques are not published`]];
 $('sourceFacts').replaceChildren();for(const [label,value]of facts){const d=el('div','fact');d.append(el('strong','',label),el('span','',value));$('sourceFacts').append(d);}
 const warnings=[...(ref.warnings??[]),'Written and tied ends are notation, not measured acoustic sustain. This public version uses neutral tones and clicks; original pitches and guitar score details are not published.','At a cropped entrance, incoming holds use a short fade-in without a new attack click. At the loop boundary, holds are truncated; incoming holds are reconstructed on the next cycle.','Only final scheduling and drawing convert rational quarters to floating point. Scheduler assertions use a 1 ns numerical tolerance; browser/audio hardware latency is separate.'];
 if(ref.grace_members?.length)warnings.push(`${ref.grace_members.length} grace members retained; unplaced grace timing is not silently invented.`);
 $('warnings').replaceChildren(...warnings.map(w=>el('li','',typeof w==='string'?w:pretty(w))));
 text('provenance',pretty({source:ref.source,hashes:ref.source_hash_bindings,selection:ref.selection,coverage:ref.coverage,unknowns:ref.unplaced_or_unknown,tempo:ref.tempo_map,boundary:r.boundary}));
}
function settings(){return{mode:$('sound').value,speed:Number($('speed').value),normalized:$('tempoMode').value==='normalized',bpm:Number($('bpm').value),loop:$('loop').checked,allowPartial:$('allowPartial').checked};}
function refreshPlan(){
 const gaps=playbackGaps(auditionReference(),$('sound').value,settings());$('partialNotice').hidden=!gaps.length;text('partialGaps',gaps.join(' '));
 try{state.plan=compileSchedule(auditionReference(),auditionRange(),settings());text('playbackStatus',`${$('auditionScope').value==='context'?'Context audition (excluded from generation evidence) · ':''}${state.plan.duration.toFixed(3)} s · ${state.plan.clicks.length} attacks · ${state.plan.notes.length} held members · ${state.plan.clock.policy}${state.plan.gaps.length?` · ${state.plan.gaps.length} pitch gaps`:''}`);$('play').disabled=!state.ref?.available;}
 catch(e){state.plan=null;$('play').disabled=true;showError(e);}
}
function soundExplanation(){text('soundExplanation',({pitch:'Reference MIDI pitches with a consistent neutral triangle tone. Envelopes follow written/tied duration; guitar techniques are retained as metadata, not acoustically realized.',click:'One short neutral click per source attack time. Chords share one click. Tied continuations and incoming holds do not create clicks.',neutral:'One 220 Hz held envelope per written/tied member. Pitch is intentionally neutral; duration is notation, not acoustic sustain.'})[$('sound').value]);}
function positionLabel(q){const b=auditionReference()?.meter_map?.find(b=>q>=qnum(b.start_q)-1e-8&&q<qnum(b.start_q)+qnum(b.span_q)-1e-8);return b?`Bar ${b.bar} · phase ${(q-qnum(b.start_q)).toFixed(2)} q`:`Quarter ${q.toFixed(2)}`;}
const player=new ReferencePlayer(s=>{text('play',s.state==='playing'?'Ⅱ Pause':'▶ Play reference');$('seek').value=String(s.position);text('position',`${positionLabel(s.position)} · ${s.state}`);document.body.dataset.playback=s.state;const roll=state.roll;if(roll){const x=(s.position-roll.start)*roll.scale+roll.left;roll.head.style.left=x+'px';if(s.state==='playing'&&$('follow').checked){const viewport=$('timelineViewport');if(x<viewport.scrollLeft||x>viewport.scrollLeft+viewport.clientWidth*.8)viewport.scrollLeft=Math.max(0,x-viewport.clientWidth*.2);}}});
function renderRoll(){
 const ref=auditionReference(),rg=auditionRange();if(!ref?.available||!rg)return;
 const start=qnum(rg[0]),end=qnum(rg[1]),span=end-start,left=52,width=Math.max(700,span*48)+left,scale=(width-left)/span;
 const members=[...(ref.events??[]).flatMap(e=>e.members),...(ref.carry_in??[])];const voices=[...new Set(members.map(m=>m.voice).filter(Number.isInteger))].sort((a,b)=>a-b);const rangePitch={low:0,high:Math.max(2,voices.length+1)};const voiceLane=v=>voices.indexOf(v)+1;
 const geom=pitchedLaneGeometry(rangePitch),top=56,height=Math.max(220,geom.height+50),y=p=>top+geom.mapY(p??rangePitch.low)-26,x=q=>left+(qnum(q)-start)*scale;
 const root=svg('svg',{width,height,role:'img','aria-label':'Rhythm timeline with source bars, tempo, voices, held envelopes, rests and candidates'});root.append(svg('rect',{x:0,y:0,width,height,fill:'#14252f'}));
 for(const [i,v]of voices.entries()){const lane=i+1;root.append(svg('rect',{x:left,y:y(lane)-geom.rowSize/2,width:width-left,height:geom.rowSize,fill:i%2?'#152630':'#1b2f3a'}));root.append(svg('text',{x:5,y:y(lane)+4,fill:'#95adb6','font-size':10},`Voice ${v}`));}
 for(const b of ref.meter_map??[]){const a=qnum(b.start_q),z=a+qnum(b.span_q);if(z<=start||a>=end)continue;const bx=x(qmax(b.start_q,rg[0]));root.append(svg('text',{x:bx+5,y:17,fill:'#d5dfdc','font-size':11},`${b.bar} · ${b.signature?.join('/')}${b.pickup?' pickup':''}`));root.append(svg('line',{x1:bx,x2:bx,y1:24,y2:height,stroke:'#4b6269'}));const beat=4/(b.signature?.[1]??4);for(let q=a+beat;q<z-1e-8;q+=beat)if(q>=start&&q<end)root.append(svg('line',{x1:x(String(q)),x2:x(String(q)),y1:40,y2:height,stroke:'#2b424e','stroke-dasharray':'2 4'}));}
 let currentTempo=(ref.tempo_map??[]).filter(t=>qnum(t.onset_q)<=start).at(-1);if(currentTempo)root.append(svg('text',{x:left+4,y:35,fill:'#a4cfb5','font-size':10},`♩ ${currentTempo.quarter_bpm??currentTempo.bpm}`));
 for(const t of ref.tempo_map??[])if(qnum(t.onset_q)>start&&qnum(t.onset_q)<end)root.append(svg('text',{x:x(t.onset_q)+4,y:35,fill:'#a4cfb5','font-size':10},`♩ ${t.quarter_bpm??t.bpm}`));
 for(const u of activeView()?.ordered_units??[]){for(const q of u.range_q??[])if(qnum(q)>=start&&qnum(q)<=end)root.append(svg('line',{x1:x(q),x2:x(q),y1:40,y2:height,stroke:'#b69bd1','stroke-dasharray':'4 5','stroke-opacity':'.55'}));}
 const seen=new Set();for(const m of members){const id=m.occurrence??m.id;if(seen.has(id))continue;seen.add(id);const on=m.onset_q,off=m.tied_end_q??m.written_end_q;if(on==null||off==null)continue;if(new Q(off).cmp(rg[0])<=0||new Q(on).cmp(rg[1])>=0)continue;
  const a=qmax(on,rg[0]),z=qmin(off,rg[1]),carry=new Q(on).cmp(rg[0])<0||new Q(off).cmp(rg[1])>0,cy=y(voiceLane(m.voice)),h=Math.max(4,geom.noteHeight);
  const rect=svg('rect',{x:x(a),y:cy-h/2,width:Math.max(2,x(z)-x(a)-.4),height:h,rx:1,fill:carry?'#4c8d93':'#799aaa',stroke:carry?'#8cddd2':'none',class:'note','data-occurrence':id});
  const detail=`${id} · neutral pitch · voice ${m.voice??'?'} · onset ${on} q · written end ${m.written_end_q} q · tied end ${off} q${carry?' · carries across selection edge':''} · ${'Opaque source member; original score pointer omitted'}`;
  rect.append(svg('title',{},detail));rect.addEventListener('click',()=>text('noteDetails',detail));root.append(rect);
  if(new Q(on).cmp(rg[0])>=0)root.append(svg('line',{x1:x(on),x2:x(on),y1:cy-h/2-2,y2:cy+h/2+2,stroke:'#d2ef9e','stroke-width':2}));
  for(const seg of m.segments??[]){const q=seg.written_end_q;if(q&&new Q(q).cmp(rg[0])>0&&new Q(q).cmp(rg[1])<0)root.append(svg('line',{x1:x(q),x2:x(q),y1:cy-h/2,y2:cy+h/2,stroke:'#ddedf0','stroke-width':.8}));}
 }
 for(const rest of ref.explicit_rests??[]){const a=rest.onset_q??rest.start_q,z=rest.written_end_q??rest.end_q;if(a==null||z==null)continue;const begin=qmax(a,rg[0]),finish=qmin(z,rg[1]);if(begin.cmp(finish)>=0)continue;const rect=svg('rect',{x:x(begin),y:height-18,width:Math.max(2,x(finish)-x(begin)),height:9,fill:'none',stroke:'#bd9f73','stroke-dasharray':'3 2',class:'note'});rect.append(svg('title',{},`Explicit rest ${a} → ${z} q · voice ${rest.voice??'?'}`));rect.addEventListener('click',()=>text('noteDetails',pretty(rest)));root.append(rect);}
 root.addEventListener('click',event=>{if(event.target.closest('.note'))return;const box=root.getBoundingClientRect(),q=start+(event.clientX-box.left-left)/scale;player.seek(Math.min(end,Math.max(start,q))).catch(showError);});
 $('roll').replaceChildren(root);$('roll').style.width=width+'px';const head=el('div','playhead');head.style.left=left+'px';$('roll').append(head);state.roll={start,scale,left,head};
}
$('search').addEventListener('input',()=>{state.limit=100;renderCatalog();});for(const id of ['identityFilter','availabilityFilter'])$(id).onchange=()=>{state.limit=100;renderCatalog();};
$('reviewedLane').onclick=()=>{state.lane='reviewed';state.limit=100;renderCatalog();};$('automaticLane').onclick=()=>{state.lane='automatic';state.limit=100;renderCatalog();};$('moreRecords').onclick=()=>{state.limit+=100;renderCatalog();};
$('view').onchange=()=>{state.view=$('view').value;loadRecord(state.record,{view:state.view});};
$('applyRange').onclick=()=>{try{const a=new Q($('rangeStart').value.trim()),b=new Q($('rangeEnd').value.trim()),whole=state.record.range_q;if(a.cmp(whole[0])<0||b.cmp(whole[1])>0||a.cmp(b)>=0)throw Error('Choose an increasing range inside the selected riff.');loadRecord(state.record,{view:state.view,range:[String(a),String(b)]});}catch(e){showError(e);}};
$('voice').onchange=()=>loadRecord(state.record,{view:state.view,range:range(),unit:state.unit});
$('auditionScope').onchange=()=>{player.stop();$('allowPartial').checked=false;if(state.ref?.available){player.options=settings();player.load(auditionReference(),auditionRange());$('seek').min=String(qnum(auditionRange()[0]));$('seek').max=String(qnum(auditionRange()[1]));refreshPlan();renderRoll();}};
$('wholeRange').onclick=()=>loadRecord(state.record,{view:state.view});
$('play').onclick=()=>{generationUI.stop();if(player.state==='playing')player.pause();else player.play().catch(showError);};$('stop').onclick=()=>player.stop();$('seek').oninput=()=>player.seek(Number($('seek').value)).catch(showError);
for(const id of ['sound','tempoMode','speed','bpm','loop','allowPartial'])$(id).onchange=()=>{hideError();$('bpmLabel').hidden=$('tempoMode').value!=='normalized';player.setOptions(settings()).catch(showError);soundExplanation();if(state.ref?.available)refreshPlan();};
window.addEventListener('pagehide',()=>player.stop());
// Read-only introspection for silent QA and the next integration. No audio auto-start.
const generationUI=mountGeneration({host:document.getElementById('generationPanel'),getReference:()=>state.ref,stopReference:()=>player.stop()});
window.riffAudit={state,player,compileSchedule,loadRecord,generationUI};
try{state.catalog=await loadCatalog();state.records=state.catalog.records;text('reviewedCount',state.catalog.counts.canonical_reviews.toLocaleString());text('automaticCount',state.catalog.counts.automatic.toLocaleString());renderCatalog();const preferred=state.records.find(r=>r.id==='R5-552442-p3-456262334b')??state.records.find(r=>r.available);if(preferred)await loadRecord(preferred);else text('loading','No source records are available.');}catch(e){showError(e);text('loading','The source catalogue could not be opened.');}


