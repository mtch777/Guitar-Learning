import {Q,qnum,memberEnd} from '../playback/timing.mjs?v=audio-fix-1';
export function parseDivisions(raw,range){
 const limit=new Q(range[1]).sub(range[0]), values=new Map();
 if(String(raw).length>500)throw Error('Too many divisions. Keep the position list under 500 characters.');
 for(const s of String(raw).trim().split(/[,\s]+/).filter(Boolean)){
  if(!/^(?:\d+(?:\.\d+)?|\d+\/\d+)$/.test(s))throw Error('Use quarter-note positions such as 2, 3.5 or 5/2.');const q=new Q(s);if(q.cmp(0)<=0||q.cmp(limit)>=0)throw Error(`Choose a division above 0 and below ${limit}q.`);
  values.set(String(q),q);
 }
 return [...values.values()].sort((a,b)=>a.cmp(b)).map(String);
}
export function divisionData(raw,range){const offsets=parseDivisions(raw,range);return {schema:'proposed-divisions/1',unit:'quarter_note',origin_q:String(new Q(range[0])),range_q:range.map(String),offsets_q:offsets,positions_q:offsets.map(q=>String(new Q(range[0]).add(q)))};}
export function rollNotes(ref,range){
 const lo=qnum(range[0]),hi=qnum(range[1]),seen=new Set(),notes=[];let omitted=0;
 for(const e of [...(ref.events??[]),{members:ref.carry_in??[]}])for(const m of e.members??[]){
  const id=m.occurrence??m.id??JSON.stringify([m.onset_q??e.onset_q,m.voice,m.pitch]);if(seen.has(id))continue;seen.add(id);
  try{const on=qnum(m.onset_q??e.onset_q),off=qnum(memberEnd(m));if(off<=lo||on>=hi)continue;if(off<=on)throw Error('Invalid hold');
   notes.push({id,on:Math.max(lo,on)-lo,off:Math.min(hi,off)-lo,onset_q:String(new Q(m.onset_q??e.onset_q).sub(range[0])),pitch:Number.isFinite(m.pitch)?m.pitch:null,carry:on<lo});
  }catch{omitted++;}
 }
 return {notes,omitted};
}
const ns='http://www.w3.org/2000/svg',pitchName=n=>['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][((n%12)+12)%12]+(Math.floor(n/12)-1);
export class DivisionRoll{
 constructor({host,scroller,list,status,snap,zoom,undo,onChange,doc=document}){
  Object.assign(this,{host,scroller,list,status,snap,zoom,undo,onChange,doc});this.history=[];this.marks=[];this.snap.value='1/4';this.zoom.value='80';
  snap.onchange=()=>this.draw();zoom.onchange=()=>{const old=this.scale??80,left=scroller.scrollLeft/old;this.draw();scroller.scrollLeft=left*this.scale;};
  undo.onclick=()=>{if(!this.history.length)return;const raw=this.history.pop();this.setMarks(raw);this.onChange(raw);this.status.textContent='Last division edit undone.';};
 }
 load(ref,range,raw=''){this.range=range.map(String);this.length=qnum(new Q(range[1]).sub(range[0]));Object.assign(this,rollNotes(ref,range));this.history=[];this.cursor=null;this.scroller.scrollLeft=0;this.setMarks(raw);}
 clear(){this.range=null;this.host.replaceChildren();this.list.replaceChildren();this.undo.disabled=true;this.status.textContent='Loading piano roll...';}
 setMarks(raw){if(!this.range)return;this.marks=parseDivisions(raw,this.range);this.draw();}
 change(raw){try{const next=parseDivisions(raw,this.range).join(', '),before=this.marks.join(', ');if(next===before)return;this.history.push(before);if(this.history.length>100)this.history.shift();this.setMarks(next);this.onChange(next);this.status.textContent=`${this.marks.length} proposed division${this.marks.length===1?'':'s'}. Included with this example's feedback.`;}catch(e){this.status.textContent=e.message;}}
 add(raw){if(!this.range)return;try{const entries=parseDivisions(raw,this.range);this.change([...this.marks,...entries].join(', '));}catch(e){this.status.textContent=e.message;}}
 toggle(raw){if(this.marks.includes(raw))this.change(this.marks.filter(q=>q!==raw).join(', '));else this.add(raw);}
 atPixel(pixel){let n=(pixel-this.pad)/this.scale;if(n<=0||n>=this.length)return null;
  const nearby=this.marks.map(q=>({q,d:Math.abs(qnum(q)-n)*this.scale})).filter(v=>v.d<=10).sort((a,b)=>a.d-b.d)[0]?.q;if(nearby)return nearby;
  if(this.snap.value==='attacks'){
   const ns=[...new Set(this.notes.filter(n=>!n.carry).map(n=>n.onset_q))].filter(q=>qnum(q)>0&&qnum(q)<this.length);return ns.sort((a,b)=>Math.abs(qnum(a)-n)-Math.abs(qnum(b)-n))[0]??null;
  }
  let q;if(this.snap.value==='free')q=new Q(n.toFixed(3));else {const step=new Q(this.snap.value||'1/4'),count=Math.round(n/step.number());q=new Q(step.n*BigInt(count),step.d);}
  return q.cmp(0)>0&&q.number()<this.length?String(q):null;
 }
 update(state){if(!this.playhead||!this.range)return;const pos=Number(state.position)-qnum(this.range[0]);this.playhead.setAttribute('visibility',Number.isFinite(pos)&&pos>=0&&pos<=this.length?'visible':'hidden');const x=this.pad+pos*this.scale;this.playhead.setAttribute('x1',x);this.playhead.setAttribute('x2',x);}
 draw(){if(!this.range)return;const host=this.host,doc=this.doc,pad=this.pad=48,available=Math.max(220,(this.scroller.clientWidth||330)-pad-20);this.scale=this.zoom.value==='fit'?available/this.length:Number(this.zoom.value||80);const width=Math.max(280,Math.ceil(pad+this.length*this.scale+20));
  const pitches=this.notes.map(n=>n.pitch).filter(Number.isFinite),hi=Math.max(60,...pitches),lo=Math.min(48,...pitches),unknown=this.notes.some(n=>n.pitch===null),rows=hi-lo+1+(unknown?1:0),row=Math.max(7,Math.min(18,260/rows)),top=42,height=Math.ceil(top+rows*row+28);
  const svg=doc.createElementNS(ns,'svg');svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.setAttribute('width',width);svg.setAttribute('height',height);svg.style.width=width+'px';svg.style.height=height+'px';svg.style.maxWidth='none';svg.style.touchAction='pan-x pan-y';svg.setAttribute('tabindex','0');svg.setAttribute('role','group');svg.setAttribute('aria-label','Piano roll: tap a time to add a division; tap an orange division to remove it. Arrow keys move a cursor; Enter toggles a division.');
  const draw=(tag,attrs,label)=>{const e=doc.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,v);if(label!==undefined)e.textContent=label;svg.append(e);return e;};
  draw('rect',{width,height,fill:'#f8fafc'});
  for(let i=0;i<rows;i++){const pitch=hi-i,y=top+i*row,isUnknown=unknown&&i===rows-1;draw('rect',{x:0,y,width,height:row,fill:isUnknown?'#fff4df':[1,3,6,8,10].includes((pitch%12+12)%12)?'#e8edf4':'#f8fafc'});draw('line',{x1:pad,x2:width,y1:y,y2:y,stroke:'#d9e1eb','stroke-width':.5});if(row>=12||pitch%12===0||isUnknown)draw('text',{x:pad-5,y:y+row*.76,'text-anchor':'end','font-size':Math.max(9,Math.min(11,row)),fill:'#52647b'},isUnknown?'?':pitchName(pitch));}
  const gridStep=Math.max(1,2**Math.ceil(Math.log2(38/this.scale)));for(let q=0;q<=this.length;q+=gridStep){const x=pad+q*this.scale;draw('line',{x1:x,x2:x,y1:top-10,y2:height-20,stroke:'#becbdc','stroke-width':q%4===0?1.3:.7});draw('text',{x,y:top-16,'text-anchor':'middle','font-size':11,fill:'#52647b'},'+'+q+'q');}
  for(const n of this.notes){const y=top+(n.pitch===null?rows-1:hi-n.pitch)*row+1;const r=draw('rect',{'data-note-id':n.id,x:pad+n.on*this.scale,y,width:Math.max(2,(n.off-n.on)*this.scale),height:Math.max(4,row-2),rx:2,fill:n.pitch===null?'#a16207':'#3977b9',opacity:n.carry ? .65 : .88});const t=doc.createElementNS(ns,'title');t.textContent=(n.pitch===null?'Unknown pitch':pitchName(n.pitch))+` from +${n.on} to +${n.off}q`;r.append(t);}
  for(const [i,q]of this.marks.entries()){const x=pad+qnum(q)*this.scale;draw('line',{'data-division':q,x1:x,x2:x,y1:5,y2:height-20,stroke:'#c45b00','stroke-width':2.5});draw('rect',{x:x-10,y:0,width:20,height:19,rx:4,fill:'#c45b00'});draw('text',{x,y:14,'text-anchor':'middle','font-size':11,fill:'white'},i+1);}
  if(this.cursor!==null){const x=pad+this.cursor*this.scale;draw('line',{x1:x,x2:x,y1:top-12,y2:height-20,stroke:'#7c3aed','stroke-dasharray':'4 3'});}
  this.playhead=draw('line',{x1:pad,x2:pad,y1:top-10,y2:height-20,stroke:'#0f766e','stroke-width':2,visibility:'hidden'});
  let down;svg.onpointerdown=e=>{if(e.button!==undefined&&e.button!==0)return;down={x:e.clientX,y:e.clientY,scroll:this.scroller.scrollLeft,id:e.pointerId,moved:false};};svg.onpointermove=e=>{if(down&&down.id===e.pointerId&&(Math.hypot(e.clientX-down.x,e.clientY-down.y)>8||Math.abs(this.scroller.scrollLeft-down.scroll)>5))down.moved=true;};svg.onpointercancel=()=>down=null;svg.onpointerleave=()=>down=null;svg.onpointerup=e=>{if(!down||down.id!==e.pointerId)return;const d=down;down=null;if(d.moved||Math.hypot(e.clientX-d.x,e.clientY-d.y)>8||Math.abs(this.scroller.scrollLeft-d.scroll)>5)return;const bounds=svg.getBoundingClientRect(),q=this.atPixel((e.clientX-bounds.left)*width/bounds.width);if(q)this.toggle(q);};
  svg.onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End','Enter',' '].includes(e.key)){e.preventDefault();const step=this.snap.value==='attacks'||this.snap.value==='free' ? .25 : qnum(this.snap.value||'1/4');if(e.key==='Enter'||e.key===' '){const q=this.atPixel(pad+(this.cursor??step)*this.scale);if(q)this.toggle(q);this.svg.focus?.();}else{this.cursor=e.key==='Home'?step:e.key==='End'?this.length-step:Math.max(step,Math.min(this.length-step,(this.cursor??0)+(e.key==='ArrowRight'?step:-step)));this.draw();this.svg.focus?.();this.scroller.scrollLeft=Math.max(0,pad+this.cursor*this.scale-(this.scroller.clientWidth||330)/2);}}};
  host.replaceChildren(svg);this.svg=svg;this.list.replaceChildren();for(const q of this.marks){const b=doc.createElement('button');b.type='button';b.textContent='+'+q+'q  ×';b.setAttribute('aria-label','Remove division at '+q+' quarter notes from excerpt start');b.onclick=()=>this.toggle(q);this.list.append(b);}this.undo.disabled=!this.history.length;
  this.status.textContent=this.marks.length?`${this.marks.length} proposed divisions. Orange lines are yours.`:'No divisions marked yet. Tap the piano roll to add one.';if(unknown)this.status.textContent+=' Unknown pitches appear in the ? row.';if(this.omitted)this.status.textContent+=` ${this.omitted} events with unresolved timing are omitted.`;
 }
}
