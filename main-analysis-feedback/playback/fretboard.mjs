import {Q,qnum,memberEnd} from './timing.mjs?v=piano-roll-1';

const names=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const pc=p=>((p%12)+12)%12;
export function fretboardModel(ref,range,geometry,basis='target',phraseRange=range){
  const [lo,hi]=range.map(v=>new Q(v));
  if(lo.cmp(hi)>=0)throw Error('Fretboard range must increase.');
  const [phraseLo,phraseHi]=phraseRange.map(v=>new Q(v));
  if(phraseLo.cmp(phraseHi)>=0)throw Error('Phrase range must increase.');
  const wholeRiff=lo.cmp(phraseLo)!==0||hi.cmp(phraseHi)!==0;
  const model={notes:[],contacts:[],range:[qnum(lo),qnum(hi)],basis,unknown:0,unplaced:ref?.unplaced_or_unknown?.length??0,grace:ref?.grace_members?.length??0,unknownCarry:geometry?.unknown_carry_count??0,available:false};
  const count=geometry?.string_counts?.[basis];
  model.wholeRiff=wholeRiff;model.phraseRange=[String(phraseLo),String(phraseHi)];
  if(!['source','target'].includes(basis)||geometry?.schema!=='main-analysis-fretboard/1'||!Number.isInteger(count)||count<1||count>24||!Array.isArray(geometry.notes))return model;
  model.available=true;model.stringCount=count;
  // Identity joins only. Coordinates are never derived from pitch or tuning.
  const lookup=new Map(),duplicates=new Set();
  for(const n of geometry.notes){if(lookup.has(n.id))duplicates.add(n.id);lookup.set(n.id,n);}
  const seen=new Set(),contacts=new Map();
  function add(m,event,carry=false){
    const id=m.id;if(id==null||seen.has(id))return;seen.add(id);
    const onset=m.onset_q??event?.onset_q,end=memberEnd(m);
    let on,off;try{on=new Q(onset);off=new Q(end);}catch{model.unplaced++;return;}
    if(off.cmp(lo)<=0||on.cmp(hi)>=0)return;
    if(off.cmp(on)<=0){model.unplaced++;return;}
    const point=lookup.get(id)?.[basis];
    if(duplicates.has(id)||point?.coordinate_valid!==true||!Number.isInteger(point.string)||point.string<1||point.string>count||!Number.isInteger(point.fret)||point.fret<0||point.fret>48){model.unknown++;return;}
    const pitch=point.pitch==null||!Number.isFinite(Number(point.pitch))?null:Number(point.pitch);
    const n={id,pitch,string:point.string,fret:point.fret,onset_q:String(on),start:qnum(on.cmp(lo)<0?lo:on),end:qnum(off.cmp(hi)>0?hi:off),carryIn:carry||on.cmp(lo)<0,carryOut:off.cmp(hi)>0,voice:m.voice};
    // Ownership follows the original attack, never its clipped or tied interval.
    n.inPhrase=on.cmp(phraseLo)>=0&&on.cmp(phraseHi)<0;
    n.context=wholeRiff&&!n.inPhrase;
    // The player auditions original source pitches even when geometry is mapped.
    n.sourceAudible=m.pitch!=null&&Number.isFinite(Number(m.pitch));
    model.notes.push(n);const key=n.string+':'+n.fret;
    if(!contacts.has(key))contacts.set(key,{string:n.string,fret:n.fret,notes:[]});contacts.get(key).notes.push(n);
  }
  for(const e of ref?.events??[])for(const m of e.members??[])add(m,e);
  for(const m of ref?.carry_in??[])add(m,null,true);
  model.contacts=[...contacts.values()];return model;
}

export function contactAppearance(contact){
  const selected=contact.notes.filter(n=>!n.context),context=contact.notes.filter(n=>n.context);
  const note=selected[0]??context[0];
  return {note,mixed:selected.length>0&&context.length>0,contextOnly:!selected.length,
    color:!selected.length?'#6b7280':note.pitch==null?'#7c3aed':`hsl(${pc(note.pitch)*30} 62% 33%)`};
}

export class Fretboard{
  constructor({canvas,scroller,position,readout,notice,follow,onSeek}){
    Object.assign(this,{canvas,scroller,slider:position,readout,notice,follow,onSeek});
    this.ctx=canvas.getContext('2d');this.q=0;this.state='stopped';this.left=48;this.top=42;this.rowHeight=42;
    follow.onchange=()=>this.draw();
    position.oninput=()=>{if(!this.model)return;const[a,b]=this.model.range,v=Number(position.value);if(!Number.isFinite(v))return;return onSeek(v<=0?this.exactRange[0]:v>=1000?this.exactRange[1]:a+(b-a)*v/1000);};
    canvas.onclick=e=>this.seekContact(e);
    if(typeof ResizeObserver!=='undefined'){this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(scroller);}
  }
  load(ref,range,label,geometry,basis='target',phraseRange=range){
    this.exactRange=range.map(String);this.phraseRange=phraseRange;this.model=fretboardModel(ref,range,geometry,basis,phraseRange);this.label=label;this.q=this.model.range[0];this.state='stopped';this.scroller.scrollLeft=0;this.resize();
  }
  resize(){
    if(!this.model||!this.ctx)return;
    const frets=this.model.notes.map(n=>n.fret);
    this.minFret=frets.length?Math.min(...frets):0;this.maxFret=frets.length?Math.max(...frets):0;
    const columns=this.maxFret-this.minFret+1,visible=Math.max(240,Math.min(8192,this.scroller.clientWidth||640));
    this.cellWidth=Math.max(36,Math.min(72,(visible-this.left-12)/columns));
    this.width=Math.max(visible,this.left+columns*this.cellWidth+12);this.plotWidth=this.width-this.left;
    this.height=this.model.available?this.top+this.model.stringCount*this.rowHeight+14:120;
    const dpr=Math.min(globalThis.devicePixelRatio||1,2,8192/this.width,8192/this.height,Math.sqrt(3900000/(this.width*this.height)));
    this.canvas.width=Math.floor(this.width*dpr);this.canvas.height=Math.floor(this.height*dpr);this.canvas.style.width=this.width+'px';this.canvas.style.height=this.height+'px';this.ctx.setTransform(dpr,0,0,dpr,0,0);this.draw();
  }
  x(fret){return this.left+(fret-this.minFret+.5)*this.cellWidth;}
  y(string){return this.top+(string-.5)*this.rowHeight;}
  active(n){return n.sourceAudible&&this.state==='playing'&&this.q>=n.start&&this.q<n.end;}
  seekContact(e){
    if(!this.model?.available)return;const box=this.canvas.getBoundingClientRect(),x=(e.clientX-box.left)*this.width/(box.width||this.width),y=(e.clientY-box.top)*this.height/(box.height||this.height);
    const contact=this.model.contacts.find(p=>Math.abs(this.x(p.fret)-x)<=Math.min(20,this.cellWidth/2)&&Math.abs(this.y(p.string)-y)<=20);if(!contact)return;
    const[a,b]=this.model.range,nearest=[...contact.notes].sort((u,v)=>Math.abs(qnum(u.onset_q)-this.q)-Math.abs(qnum(v.onset_q)-this.q)||u.start-v.start)[0];
    const on=new Q(nearest.onset_q);return this.onSeek(on.cmp(this.exactRange[0])<=0?this.exactRange[0]:on.cmp(this.exactRange[1])>=0?this.exactRange[1]:nearest.onset_q);
  }
  update({position,state}){if(!this.model)return;if(Number.isFinite(position))this.q=position;if(state!=null)this.state=state;this.draw();}
  draw(){
    if(!this.model||!this.ctx)return;const c=this.ctx,m=this.model,[a,b]=m.range;
    c.clearRect(0,0,this.width,this.height);c.fillStyle='#f8fafc';c.fillRect(0,0,this.width,this.height);c.font='12px system-ui';c.textAlign='center';c.textBaseline='middle';
    if(m.available){
      c.fillStyle='#edf2f7';c.fillRect(this.left,this.top,this.cellWidth*(this.maxFret-this.minFret+1),m.stringCount*this.rowHeight);
      for(let f=this.minFret;f<=this.maxFret;f++){
        const x=this.x(f);c.fillStyle='#334155';c.fillText(f===0?'0 open':String(f),x,20);c.strokeStyle=f===0?'#334155':'#94a3b8';c.lineWidth=f===0?3:1;c.beginPath();c.moveTo(x+this.cellWidth/2,this.top);c.lineTo(x+this.cellWidth/2,this.height-14);c.stroke();
      }
      for(let s=1;s<=m.stringCount;s++){const y=this.y(s);c.fillStyle='#334155';c.fillText('S'+s,20,y);c.strokeStyle='#64748b';c.lineWidth=1+(s-1)/m.stringCount;c.beginPath();c.moveTo(this.left,y);c.lineTo(this.x(this.maxFret)+this.cellWidth/2,y);c.stroke();}
      for(const p of m.contacts){
        const active=p.notes.filter(n=>this.active(n)),appearance=contactAppearance(p);
        const n=appearance.note,x=this.x(p.fret),y=this.y(p.string);
        c.beginPath();c.arc(x,y,14,0,Math.PI*2);c.fillStyle=appearance.mixed?'#6b7280':appearance.color;c.fill();
        if(appearance.mixed){c.beginPath();c.arc(x,y,10,0,Math.PI*2);c.fillStyle=appearance.color;c.fill();}
        if(active.length){c.strokeStyle='#f59e0b';c.lineWidth=4;c.beginPath();c.arc(x,y,18,0,Math.PI*2);c.stroke();}
        c.fillStyle='#fff';c.font='bold 11px system-ui';c.fillText(n.pitch==null?'X':names[pc(n.pitch)],x,y);
        if(p.notes.length>1){c.fillStyle='#1e293b';c.font='9px system-ui';c.fillText('×'+p.notes.length,x+11,y-17);}
      }
    }else{c.fillStyle='#475569';c.fillText('Fretboard geometry unavailable',this.width/2,55);}
    const q=Math.max(a,Math.min(b,this.q));this.slider.value=String(Math.round((q-a)/(b-a)*1000));this.slider.setAttribute('aria-valuetext','Source quarter '+q.toFixed(2));this.readout.textContent=Math.round((q-a)/(b-a)*100)+'%';
    const warnings=[m.unknown?m.unknown+' notes with missing or invalid coordinates not plotted':'',m.unplaced?m.unplaced+' unresolved or unplaced notes not plotted':'',m.grace?m.grace+' grace notes without resolved timing':'',m.unknownCarry?m.unknownCarry+' incoming holds with unknown geometry':''].filter(Boolean);
    this.notice.textContent=(!m.available?'Fretboard unavailable.':m.wholeRiff?'Color: selected phrase · Gray: rest of riff':'')+(warnings.length?' '+warnings.join('; ')+'.':'');
    this.canvas.setAttribute('aria-label',this.label+'. Gold ring: sounding note. X: unknown/dead pitch. '+this.notice.textContent+' Source quarters '+a+' to '+b+'. '+m.contacts.map(p=>'String '+p.string+', '+(p.fret===0?'open':'fret '+p.fret)+', '+p.notes.length+' notes'+(m.wholeRiff?', '+p.notes.filter(n=>!n.context).length+' selected phrase, '+p.notes.filter(n=>n.context).length+' context':'')+(p.notes.some(n=>this.active(n))?', sounding':'')).join('; ')+'. Use the playback-position slider to seek.');
    if(this.follow.checked&&this.state==='playing'){const n=m.notes.find(n=>this.active(n));if(n){const x=this.x(n.fret),w=this.scroller.clientWidth||640,left=this.scroller.scrollLeft;if(x>left+w-24||x<left+24)this.scroller.scrollLeft=Math.max(0,Math.min(this.width-w,x-w/2));}}
  }
}
