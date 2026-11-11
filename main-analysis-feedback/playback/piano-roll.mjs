import {Q,qnum,memberEnd} from './timing.mjs?v=piano-roll-1';

// Drawing uses the same exact rational membership and tie endpoints as playback.
export function rollModel(ref,range){
  const [lo,hi]=range.map(v=>new Q(v)),notes=[],seen=new Set();let unknown=0,unplaced=0;
  if(lo.cmp(hi)>=0)throw Error('Piano-roll range must increase.');
  function add(m,event){
    const start=m.onset_q??event?.onset_q,end=memberEnd(m);
    if(start==null||end==null){unplaced++;return;}
    const on=new Q(start),off=new Q(end);
    if(on.cmp(hi)>=0||off.cmp(lo)<=0)return;
    const id=m.occurrence??m.id??JSON.stringify([String(on),m.voice,m.pitch]);
    if(seen.has(id))return;seen.add(id);
    if(m.pitch==null||!Number.isFinite(Number(m.pitch))){unknown++;return;}
    notes.push({id,pitch:Number(m.pitch),start:qnum(on.cmp(lo)<0?lo:on),end:qnum(off.cmp(hi)>0?hi:off),carryIn:on.cmp(lo)<0,carryOut:off.cmp(hi)>0,voice:m.voice});
  }
  for(const e of ref?.events??[])for(const m of e.members??[])add(m,e);
  for(const m of ref?.carry_in??[])add(m,null);
  const pitches=notes.map(n=>n.pitch),min=Math.max(0,(pitches.length?Math.min(...pitches):48)-2),max=Math.min(127,Math.max(min+11,(pitches.length?Math.max(...pitches):60)+2));
  return {notes,unknown,unplaced,range:[qnum(lo),qnum(hi)],min,max,grace:ref?.grace_members?.length??0};
}
export const pitchName=p=>['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][((p%12)+12)%12]+(Math.floor(p/12)-1);

export class PianoRoll{
  constructor({canvas,scroller,position,readout,notice,zoom,follow,onSeek}){
    Object.assign(this,{canvas,scroller,slider:position,readout,notice,zoom,follow,onSeek});
    this.ctx=canvas.getContext('2d');this.q=0;this.state='stopped';this.left=48;this.top=26;
    zoom.onchange=()=>this.resize();
    follow.onchange=()=>this.draw();
    position.oninput=()=>{if(!this.model)return;const [a,b]=this.model.range,v=Number(position.value);return onSeek(v<=0?this.exactRange[0]:v>=1000?this.exactRange[1]:a+(b-a)*v/1000);};
    canvas.onclick=e=>{if(!this.model)return;const box=canvas.getBoundingClientRect(),x=e.clientX-box.left; if(x<this.left)return;const[a,b]=this.model.range;return onSeek(Math.max(a,Math.min(b,a+(x-this.left)/this.plotWidth*(b-a))));};
    if(typeof ResizeObserver!=='undefined'){this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(scroller);}
  }
  load(ref,range,label){this.exactRange=range.map(String);this.model=rollModel(ref,range);this.label=label;this.q=this.model.range[0];this.state='stopped';this.scroller.scrollLeft=0;this.resize();}
  resize(){if(!this.model||!this.ctx)return;const visible=Math.max(240,this.scroller.clientWidth||640),span=this.model.range[1]-this.model.range[0],windowQ=Number(this.zoom.value)||span;this.width=Math.min(8192,Math.max(visible,this.left+(visible-this.left)*span/windowQ));this.plotWidth=this.width-this.left-10;this.rowHeight=Math.max(5,Math.min(14,260/(this.model.max-this.model.min+1)));this.height=this.top+(this.model.max-this.model.min+1)*this.rowHeight+4;const dpr=Math.min(globalThis.devicePixelRatio||1,2,8192/this.width,8192/this.height,Math.sqrt(4000000/(this.width*this.height)));this.canvas.width=Math.ceil(this.width*dpr);this.canvas.height=Math.ceil(this.height*dpr);this.canvas.style.width=this.width+'px';this.canvas.style.height=this.height+'px';this.ctx.setTransform(dpr,0,0,dpr,0,0);this.draw();}
  update({position,state}){if(!this.model)return;if(Number.isFinite(position))this.q=position;this.state=state;this.draw();}
  draw(){if(!this.model||!this.ctx)return;const c=this.ctx,m=this.model,[a,b]=m.range,x=q=>this.left+(q-a)/(b-a)*this.plotWidth,y=p=>this.top+(m.max-p)*this.rowHeight;
    c.clearRect(0,0,this.width,this.height);c.fillStyle='#f8fafc';c.fillRect(0,0,this.width,this.height);c.font='11px system-ui';c.textBaseline='middle';
    for(let p=m.min;p<=m.max;p++){c.fillStyle=[1,3,6,8,10].includes(p%12)?'#e9edf3':'#f8fafc';c.fillRect(this.left,y(p),this.plotWidth,this.rowHeight);c.strokeStyle='#dbe2eb';c.beginPath();c.moveTo(this.left,y(p));c.lineTo(this.width,y(p));c.stroke();if(this.rowHeight>=10||p%12===0){c.fillStyle='#46576a';c.fillText(pitchName(p),3,y(p)+this.rowHeight/2);}}
    const step=Math.max(1,Math.ceil((b-a)/Math.max(1,this.plotWidth/56)));for(let q=Math.ceil(a/step)*step;q<=b;q+=step){c.strokeStyle='#cbd5e1';c.beginPath();c.moveTo(x(q),this.top);c.lineTo(x(q),this.height);c.stroke();c.fillStyle='#526477';c.fillText(String(Math.round(q*100)/100)+'q',x(q)+3,12);}
    for(const n of m.notes){const active=this.state==='playing'&&this.q>=n.start&&this.q<n.end;c.fillStyle=active?'#f59e0b':'#2463c9';c.fillRect(x(n.start),y(n.pitch)+1,Math.max(2,x(n.end)-x(n.start)),Math.max(2,this.rowHeight-2));if(n.carryIn||n.carryOut){c.strokeStyle='#163e82';c.lineWidth=2;c.strokeRect(x(n.start),y(n.pitch)+1,Math.max(2,x(n.end)-x(n.start)),Math.max(2,this.rowHeight-2));c.lineWidth=1;}}
    const q=Math.max(a,Math.min(b,this.q)),px=x(q);c.strokeStyle='#c02669';c.lineWidth=2;c.beginPath();c.moveTo(px,0);c.lineTo(px,this.height);c.stroke();c.lineWidth=1;
    this.slider.value=String(Math.round((q-a)/(b-a)*1000));this.slider.setAttribute('aria-valuetext','Source quarter '+q.toFixed(2));this.readout.textContent='Source quarter '+q.toFixed(2)+' / '+b.toFixed(2);
    this.notice.textContent=this.label+' · '+m.notes.length+' pitched notes'+(m.unknown?' · '+m.unknown+' unknown pitches not plotted':'')+(m.unplaced?' · '+m.unplaced+' notes with unknown timing not plotted':'')+(m.grace?' · '+m.grace+' grace notes without resolved timing':'')+'. Blue: written notes. Gold: sounding now. Outlined: held across selection edge.';
    this.canvas.setAttribute('aria-label',this.label+'. '+m.notes.length+' written notes, source quarters '+a+' to '+b+'. Use the playback-position slider to seek.');
    if(this.follow.checked){const w=this.scroller.clientWidth||640,left=this.scroller.scrollLeft;if(px>left+w-35||px<left+this.left)this.scroller.scrollLeft=Math.max(0,px-w*.35);}
  }
}
