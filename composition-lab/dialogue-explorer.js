const data=await (await fetch('cases.json')).json();
const manifest=await (await fetch('manifest.json')).json();
const $=s=>document.querySelector(s),svg=$('#roll'),context=$('#context'),focused=$('#focused');
let current,active=context,notes=[],map=[];
const fraction=s=>{const [a,b=1]=String(s).split('/').map(Number);return a/b;};
const pitch=n=>['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B'][((n%12)+12)%12]+(Math.floor(n/12)-1);
const f=s=>String(s)+' quarter-note beats';
function xAt(t){if(!map.length)return 0;for(let i=1;i<map.length;i++)if(t<=map[i].seconds){const a=map[i-1],b=map[i];return a.x+(b.x-a.x)*(t-a.seconds)/(b.seconds-a.seconds);}return 960;}
function secondsAt(q){const x=(fraction(q)-current.base_q_number)/(current.end_q_number-current.base_q_number)*960;for(let i=1;i<map.length;i++)if(x<=map[i].x){const a=map[i-1],b=map[i];return a.seconds+(b.seconds-a.seconds)*(x-a.x)/(b.x-a.x);}return map.at(-1).seconds;}
function setText(id,text){$(id).textContent=text;}
function update(){const x=xAt(active.currentTime);const line=svg.querySelector('.playhead');if(line){line.setAttribute('x1',x);line.setAttribute('x2',x);}for(const n of notes)n.el.classList.toggle('sounding',!active.paused&&active.currentTime>=n.start&&active.currentTime<n.end);}
function seek(t){active.currentTime=Math.max(0,Math.min(t,active.duration||t));update();}
function element(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;}
function load(id){
 for(const a of [context,focused])a.pause();current=data.find(c=>c.id===id);map=current.time_map;
 current.base_q_number=fraction(current.base_q);current.end_q_number=fraction(current.end_q);
 setText('#heading',current.heading);setText('#source',`${current.song} · ${current.track} · bars ${current.start_bar}–${current.end_bar}`);
 setText('#why',current.explanation);setText('#caveat',current.caveat);
 setText('#note-info','Click any note for its pitch, duration and relation to the anchor.');
 context.src=current.id+'.context.wav';focused.src=current.id+'.focused.wav';active=context;
 $('#gp').href=current.id+'.gp';svg.replaceChildren();notes=[];
 const high=Math.max(...current.notes.map(n=>n.pitch)),low=Math.min(...current.notes.map(n=>n.pitch));const height=(high-low+1)*12+30;
 svg.setAttribute('viewBox',`0 0 960 ${height}`);
 const ns='http://www.w3.org/2000/svg';
 for(let p=low;p<=high;p++){const line=document.createElementNS(ns,'line');line.setAttribute('x1','0');line.setAttribute('x2','960');line.setAttribute('y1',(high-p)*12+15);line.setAttribute('y2',(high-p)*12+15);line.setAttribute('stroke','#263f50');svg.append(line);}
 for(const n of current.notes){
  const r=document.createElementNS(ns,'rect'),x=(fraction(n.onset_q)-current.base_q_number)/(current.end_q_number-current.base_q_number)*960;
  const width=(Math.min(fraction(n.onset_q)+fraction(n.duration_q),current.end_q_number)-Math.max(fraction(n.onset_q),current.base_q_number))/(current.end_q_number-current.base_q_number)*960;
  for(const [key,value] of Object.entries({x:Math.max(0,x),y:(high-n.pitch)*12+8,width:Math.max(2,Math.min(width,960-Math.max(0,x))),height:9,fill:({call:'#f6c85f',call_sustain:'#f6c85f',response:'#65c7f7',mixed:'#c79bff',context:'#748998'})[n.role],tabindex:0,role:'button','aria-label':`${pitch(n.pitch)}, ${n.role}, bar ${n.bar}`}))r.setAttribute(key,value);
  r.classList.add('note');const inspect=()=>{setText('#note-info',`${pitch(n.pitch)} · ${n.role.replace('_',' ')} · bar ${n.bar} · fret ${n.fret} · duration ${f(n.duration_q)} · ${current.anchor.length?'interval from anchor: '+current.anchor.map(a=>n.pitch-a).join(', ')+' semitones':'no anchor assigned'}`);seek(n.start);};
  r.onclick=inspect;r.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();inspect();}};svg.append(r);notes.push({...n,el:r});
 }
 const line=document.createElementNS(ns,'line');for(const [k,v] of Object.entries({x1:0,x2:0,y1:0,y2:height,class:'playhead'}))line.setAttribute(k,v);svg.append(line);
 const body=$('#cycles');body.replaceChildren();
 setText('#summary',current.cycles.length?`Anchor: ${current.anchor.map(pitch).join(' + ')}. The table follows ${current.cycles.length} selected exchange${current.cycles.length===1?'':'s'}; the roll also colors their continuation within the excerpt.`:'No exchange assigned by the current rule. This contrast example helps show what is excluded.');
 current.cycles.forEach((c,i)=>{const tr=element('tr'),td=element('td'),button=element('button',`Play ${i+1}`);button.onclick=()=>{seek(secondsAt(c.call.start_q));active.play();};td.append(button);tr.append(td);
  tr.append(element('td',`${c.call.attack_groups} attack${c.call.attack_groups===1?'':'s'} · ${c.call.pitches.map(ps=>ps.map(pitch).join('+')).join(' → ')} · span ${f(c.call.span_q)}`));
  tr.append(element('td',`${c.response.attack_groups} attacks · ${c.response.pitches.map(ps=>ps.map(pitch).join('+')).join(' → ')} · intervals ${c.response.intervals_from_lowest_anchor.map(ps=>ps.join('+')).join(' → ')} semitones · span ${f(c.response.span_q)}`));
  let changes=i===0?'First displayed exchange.':`${c.call.pitch_signature===current.cycles[i-1].call.pitch_signature&&c.call.rhythm_signature===current.cycles[i-1].call.rhythm_signature?'Same call':'Call changes'}; ${c.response.pitch_signature===current.cycles[i-1].response.pitch_signature?'same response pitches':'response pitches change'}; ${c.response.rhythm_signature===current.cycles[i-1].response.rhythm_signature?'same rhythm':'rhythm changes'}.`;
  if(fraction(c.call_sustain_into_response_q)>0)changes+=` Call rings over the answer by ${f(c.call_sustain_into_response_q)}.`;
  if(c.right_censored)changes+=' No clean anchor-only return before a boundary or interruption.';tr.append(element('td',changes));body.append(tr);
 });
 const histogram=h=>Object.entries(h).map(([duration,count])=>`${count} × ${duration} quarter-note beats`).join('; ');
 setText('#exact',current.cycles.length?current.cycles.map((c,i)=>[
  `Exchange ${i+1}`,
  `Call notes: ${c.call.pitches.map(ps=>ps.map(pitch).join(' + ')).join(' → ')}`,
  `Call note lengths: ${histogram(c.call.notated_duration_histogram)}`,
  `Call attack spacing: ${c.call.ioi_q.join(', ')||'single attack'} quarter-note beats`,
  `Response notes: ${c.response.pitches.map(ps=>ps.map(pitch).join(' + ')).join(' → ')}`,
  `Response note lengths: ${histogram(c.response.notated_duration_histogram)}`,
  `Response attack spacing: ${c.response.ioi_q.join(', ')||'single attack'} quarter-note beats`,
  `Response intervals above anchor: ${c.response.intervals_from_lowest_anchor.map(ps=>ps.join(' + ')).join(' → ')} semitones`,
  `Gap before answer: ${f(c.call_to_response_gap_q)}; call sustain overlap: ${f(c.call_sustain_into_response_q)}`,
  `Next anchor return: ${c.anchor_return_period_q===null?'not observed in scope':f(c.anchor_return_period_q)}`,
 ].join('\n')).join('\n\n'):'No exchange assigned. Source notes remain individually inspectable.');
 update();
}
function group(c){if(c.category.startsWith('outside'))return 'outside';if(['minimal','censored'].includes(c.category))return 'edge';return c.category==='regular'?'regular':'variety';}
function filter(kind){const list=kind==='all'?data:data.filter(c=>group(c)===kind);$('#example').replaceChildren(...list.map(c=>{const o=element('option',`${c.heading} — ${c.song}`);o.value=c.id;return o;}));if(list.length)load(list[0].id);}
for(const button of document.querySelectorAll('[data-filter]'))button.onclick=()=>{for(const b of document.querySelectorAll('[data-filter]'))b.setAttribute('aria-pressed',String(b===button));filter(button.dataset.filter);};
$('#example').onchange=e=>load(e.target.value);
for(const audio of [context,focused]){audio.onplay=()=>{for(const other of [context,focused])if(other!==audio)other.pause();active=audio;update();};for(const event of ['timeupdate','seeking','seeked','pause','ended'])audio.addEventListener(event,update);}
function animate(){if(!active.paused)update();requestAnimationFrame(animate);}requestAnimationFrame(animate);
setText('#availability',manifest.unavailable_categories.length?`Not found within the current quality and excerpt limits: ${manifest.unavailable_categories.join(', ')}. No synthetic examples substituted.`:'Every requested example family had an eligible source passage.');
filter('all');
