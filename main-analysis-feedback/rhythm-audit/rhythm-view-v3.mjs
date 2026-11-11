import {qnum,Q} from '../playback/timing.mjs?v=audio-fix-1';
const valueName=q=>({'4':'whole','2':'half','1':'quarter','1/2':'eighth','1/4':'16th','1/8':'32nd','1/16':'64th','3':'dotted half','3/2':'dotted quarter','3/4':'dotted eighth','3/8':'dotted 16th','2/3':'quarter triplet','1/3':'eighth triplet','1/6':'16th triplet','1/12':'32nd triplet'}[String(q)]??`${q}q`);
const qlabel=q=>String(q)+'q';
function el(tag,text='',className=''){const n=document.createElement(tag);n.textContent=text;if(className)n.className=className;return n;}
function sourceNotation(m){const n=m.notation??{};if(n.status==='unavailable'||(!n.value&&!n.base_value))return `unknown notation (${m.written_duration_q??'?'}q duration)`;return n.label??n.display??valueName(m.written_duration_q);}
function marks(m){const a=m.accents;return Array.isArray(a)?a:typeof a==='string'?[a]:a&&typeof a==='object'?Object.entries(a).filter(([,v])=>v).map(([k])=>k):[];}
export function measuredStream(s){
 const groups=s.attacks??[],durations=new Map();for(const a of groups)for(const m of a.members??[]){const k=String(m.written_duration_q??'unknown');durations.set(k,(durations.get(k)??0)+1);}
 const labels=s.summary?.notation_label_counts;const values=labels?Object.entries(labels).map(([name,n])=>`${n} ${name}`).join(', '):[...durations].map(([q,n])=>`${n} × ${q}q`).join(', ');
 const ioi=groups.slice(1).map((a,i)=>String(new Q(a.offset_q).sub(groups[i].offset_q)));
 const runs=[];for(const q of ioi){const last=runs.at(-1);if(last?.q===q)last.count++;else runs.push({q,count:1});}
 return {attack_count:groups.length,member_count:[...durations.values()].reduce((a,b)=>a+b,0),values,ioi,runs};
}
function axisStream(s,label,width=640,target=null){
 const wrap=el('section','','rhythmStream');wrap.append(el('h4',label));
 const facts=measuredStream(s);wrap.append(el('p',`${qlabel(s.duration_q)} long · ${facts.attack_count} attacks · ${facts.member_count} attacked notes`,'rhythmStats'));
 wrap.append(el('p',facts.values?`Written note values: ${facts.values}.`:'No new note attacks in this span.','rhythmValues'));
 const grouping=facts.runs.map(r=>`${r.count} × ${valueName(r.q)}`).join(' → ');
 wrap.append(el('p',grouping?`Attack spacing (duration equivalents): ${grouping}.`:'Attack spacing: fewer than two attacks.','rhythmSpacing'));
 const meter=s.meter??[];if(meter.length)wrap.append(el('p','Source meter: '+[...new Set(meter.map(m=>m.signature?.join('/')??'unknown'))].join(' → ')+`; bars ${meter[0].bar}–${meter.at(-1).bar}. Phrase starts ${String(new Q(s.start_q).sub(meter[0].start_q))}q after bar ${meter[0].bar} begins.`,'rhythmHelp'));
 const total=qnum(s.duration_q),rows=Math.max(1,Math.ceil(total/4));
 const origin=qnum(s.start_q),attacks=s.attacks??[],carry=s.carry_in??[];
 const hasHolds=carry.length>0||attacks.some(a=>(a.members??[]).some(m=>qnum(m.tied_duration_q??m.written_duration_q)>qnum(m.written_duration_q)));const hasGaps=(s.uncovered_intervals_q??[]).length>0;const holdY=86,gapY=hasHolds?118:86,height=98+(hasHolds?32:0)+(hasGaps?28:0);
 for(let row=0;row<rows;row++){
  const lo=row*4,hi=Math.min(total,lo+4),pad=56,scale=(width-pad-16)/4;
  const box=el('div','','rhythmGridScroll');const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  for(const [k,v]of Object.entries({viewBox:`0 0 ${width} ${height}`,width,height,role:'img','aria-label':`${label}, quarter-note positions ${lo} to ${hi}. Blue: written note lengths. Gold: tied continuation. Red marks: explicit source accents. Gaps shown separately.`}))svg.setAttribute(k,String(v));
  svg.style.width=width+'px';svg.style.height=height+'px';svg.style.maxWidth='none';svg.style.flexShrink='0';
  const draw=(tag,attrs,t='')=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(t)n.textContent=t;svg.append(n);return n;};
  const x=q=>pad+(q-lo)*scale;
  draw('rect',{x:pad,y:25,width:(hi-lo)*scale,height:height-40,fill:'#fff'});
  for(let k=0;k<=16;k++){const q=lo+k/4;if(q>hi)break;draw('line',{x1:x(q),x2:x(q),y1:25,y2:height-15,stroke:k%4===0?'#9caebe':'#e4e9f0','stroke-width':k%4===0?1.3:.7});if(k%4===0)draw('text',{x:x(q),y:17,fill:'#344b65','font-size':14,'text-anchor':'middle'},String(q)+'q');}
  for(const bar of meter){const pos=qnum(bar.start_q)-origin;if(pos>=lo&&pos<hi){draw('line',{x1:x(pos),x2:x(pos),y1:24,y2:height-15,stroke:'#485b71','stroke-width':2});draw('text',{x:x(pos)+3,y:height-2,fill:'#485b71','font-size':12},'bar '+bar.bar);}}
  draw('text',{x:2,y:49,fill:'#355b8b','font-size':13},'Notes');if(hasHolds)draw('text',{x:2,y:holdY+12,fill:'#8b6017','font-size':13},'Holds');if(hasGaps)draw('text',{x:2,y:gapY+13,fill:'#677389','font-size':13},'Gaps');
  for(const a of attacks){const at=qnum(a.offset_q);let level=0;const unique=new Set();for(const m of a.members??[]){const dur=qnum(m.written_duration_q??'0'),held=qnum(m.tied_duration_q??m.written_duration_q??'0');const sig=[dur,held,marks(m).join(',')].join(':');if(unique.has(sig))continue;unique.add(sig);const y=34+(level++%3)*15;if(at<hi&&at+dur>lo){const left=Math.max(at,lo),right=Math.min(at+dur,hi);draw('rect',{x:x(left),y,width:Math.max(1,(right-left)*scale),height:11,rx:2,fill:'#216cc1',opacity:level>3?.55:1});if(at>=lo)draw('line',{x1:x(at),x2:x(at),y1:29,y2:79,stroke:'#063e78','stroke-width':1.5});if((right-left)*scale>52)draw('text',{x:x(left)+3,y:y+10,fill:'#fff','font-size':11},String(m.written_duration_q)+'q');}
   if(held>dur&&at+held>lo&&at+dur<hi){const left=Math.max(lo,at+dur),right=Math.min(hi,at+held);draw('rect',{x:x(left),y:holdY,width:Math.max(1,(right-left)*scale),height:16,rx:2,fill:'#c38a28'});}
   if(marks(m).length&&at>=lo&&at<hi)draw('text',{x:x(at)+2,y:27,fill:'#b83940','font-size':16,'font-weight':'bold'},'>');
  }}
  for(const m of carry){const end=qnum(m.end_q??m.tied_end_q??s.start_q)-origin;if(end<=lo)continue;draw('rect',{x:x(lo),y:holdY,width:(Math.min(hi,end)-lo)*scale,height:16,rx:2,fill:'#c38a28'});if((Math.min(hi,end)-lo)*scale>55)draw('text',{x:x(lo)+2,y:holdY+12,fill:'#fff','font-size':12},'held in');}
  for(const gap of s.uncovered_intervals_q??[]){const abs=Array.isArray(gap)?gap:[gap.start_q,gap.end_q];let a=qnum(abs[0])-origin,b=qnum(abs[1])-origin;if(b<=lo||a>=hi)continue;a=Math.max(a,lo);b=Math.min(b,hi);draw('rect',{x:x(a),y:gapY,width:(b-a)*scale,height:16,fill:'#e6eaf0',stroke:'#9ba9b9','stroke-dasharray':'3 3'});if((b-a)*scale>35)draw('text',{x:(x(a)+x(b))/2,y:gapY+13,'text-anchor':'middle',fill:'#5a6575','font-size':12},'gap');}
  if(target?.offset_q!=null){const focus=qnum(target.offset_q);if(focus>=lo&&focus<hi){draw('line',{x1:x(focus),x2:x(focus),y1:24,y2:height-15,stroke:'#ad4d00','stroke-width':3,'stroke-dasharray':'5 3'});wrap.append(el('p',`Review the orange marker at +${target.offset_q}q${target.notation?' ('+target.notation+')':''}.`,'rhythmFocus'));}}
  box.append(svg);wrap.append(box);
 }
 const details=el('details');details.append(el('summary','Exact attacks, lengths and marks'));
 const list=el('ol','','rhythmEvents');for(const a of attacks){const ms=a.members??[];const vals=[...new Set(ms.map(sourceNotation))].join(' + ');const lengths=[...new Set(ms.map(m=>`${m.written_duration_q}q written / ${m.tied_duration_q??m.written_duration_q}q including ties`))].join('; ');const acc=[...new Set(ms.flatMap(marks))];const dynamics=[...new Set(ms.map(m=>m.dynamic).filter(v=>v!=null))];const n=el('li');n.append(el('strong',`At +${a.offset_q}q: ${vals}`),el('span',` ${ms.length} note${ms.length===1?'':'s'}; ${lengths}${acc.length?'; source accent: '+acc.join(', '):''}${dynamics.length?'; written dynamic: '+dynamics.join(', '):''}`));list.append(n);}details.append(list);if(!attacks.length)details.append(el('p','No attacks. Check the hold and gap rows above.'));wrap.append(details);
 return wrap;
}
export function renderRhythm(box,c,e){
 box.replaceChildren();if(!e){box.append(el('p','Rhythm evidence is unavailable. Do not treat a blank diagram as silence.'));return;}
 box.append(el('h3','The rhythm, in quarter-note time'));
 if(e.unplaced_or_unknown?.length||e.grace_members?.length)box.append(el('p',`Incomplete timing evidence: ${e.unplaced_or_unknown?.length??0} unresolved records and ${e.grace_members?.length??0} grace notes. The grid shows only known clocks; a gap can hide unresolved material.`,'rhythmWarning'));
 box.append(el('p','Blue = written note length · Gold = tied or incoming hold · Dashed grey = no known notes sounding · > = written accent','rhythmLegend'));
 box.append(el('p','q = one quarter note. Each row spans four quarters, not necessarily one bar. Positions are measured from the start of each phrase. A and B use the same time scale.','rhythmHelp'));
 const neighbors=e.context?.phrases??[];const at=neighbors.findIndex(p=>p.id===c.primary.id);if(at>=0){const group=el('details');group.append(el('summary','How this phrase sits in the riff'));for(let j=Math.max(0,at-1);j<=Math.min(neighbors.length-1,at+1);j++){const p=neighbors[j],labels=p.summary?.notation_label_counts??{};group.append(el('p',`${j===at?'Selected':j<at?'Previous':'Next'} phrase: ${p.duration_q}q, ${p.summary?.attack_groups??0} attacks. ${Object.entries(labels).map(([k,n])=>n+' '+k).join(', ')||'No new attacked notes'}.`));}group.append(el('p','Use Play context to hear these in source order. These are measured differences, not inferred call/response roles.'));box.append(group);}
 const width=Math.max(300,Math.min(640,Math.floor((box.clientWidth||664)-24)));box.dataset.gridWidth=String(width);
 if(e.comparison)box.append(axisStream(e.comparison,'A · earlier phrase',width));
 box.append(axisStream(e.primary,e.comparison?'B · selected phrase':'Selected phrase',width,c.question?.target_evidence));
 const facts=el('details');facts.append(el('summary','Meter, written rests, accents and data limits'));const s=e.primary;
 const tempo=s.tempo_map??e.context?.tempo_map??[];facts.append(el('p',tempo.length?'Source tempo: '+tempo.map(t=>`${t.quarter_bpm??t.bpm} quarter notes/min at ${t.onset_q}q`).join('; '):'Source tempo is used for playback; see the source excerpt for changes.'));
 const meter=s.meter;facts.append(el('p','Meter: '+(meter?.length?meter.map(m=>`bar ${m.bar}: ${m.signature?.join('/')??'unknown'} (${m.status})`).join('; '):'Not retained in this playback excerpt. The grid does not assume 4/4.')));
 const rests=s.written_rests;facts.append(el('p',Array.isArray(rests)?`${rests.length} written rest record(s). A rest in one voice does not mean all voices are silent.`:'Written rests: unavailable in this evidence. Gaps are computed from known note ends, not assumed written rests.'));
 if(Array.isArray(rests)&&rests.length)facts.append(el('p',rests.map(r=>`${r.onset_q??r.start_q}q: ${r.duration_q??r.end_q??'?'}q${r.voice!=null?', voice '+r.voice:''}`).join('; ')));
 if(s.tie_continuations?.length)facts.append(el('p','Tied notation continuations (not new attacks): '+s.tie_continuations.map(t=>`+${t.offset_q}q: ${t.notation?.label??t.duration_q+'q'}`).join('; ')));
 const accents=(s.attacks??[]).flatMap(a=>(a.members??[]).flatMap(m=>marks(m).map(k=>`+${a.offset_q}q ${k}`)));
 facts.append(el('p',accents.length?'Written accent marks: '+[...new Set(accents)].join('; '):'No explicit accent marks found after checking the source. This does not mean the performance is unaccented.'));

 for(const note of e.limitations??[])facts.append(el('p',String(note)));for(const note of s.limitations??[])facts.append(el('p',String(note)));
 facts.append(el('p','Timing is notated, not a measured live performance. Synthetic playback does not reproduce accent dynamics or guitar articulation. Call/response function is not established by a timing match.'));box.append(facts);
}
