import {Q} from './timing.mjs?v=piano-roll-1';
const GROUPS=[['core_contacts','Core'],['extension_contacts','Extension'],['tapped_contacts','Tap'],['held_contacts','Held'],['carry_in_contacts','Carry-in']];
export function phraseShapeModel(data,phrase){
 if(!data||data.schema!=='main-analysis-shapes/1'||data.status==='unavailable')return {status:'unavailable',cards:[]};
 if(JSON.stringify(data.target_tuning)!==JSON.stringify([64,59,55,50,45,40,35,28]))return {status:'mismatch',cards:[]};
 const entry=data.phrases?.find(p=>p.id===phrase.id);
 if(!entry||entry.start_q!==phrase.start_q||entry.end_q!==phrase.end_q)return {status:'mismatch',cards:[]};
 const shapes=new Map((data.shapes||[]).map(s=>[s.id,s]));
 if(shapes.size!==(data.shapes||[]).length)return {status:'mismatch',cards:[]};
 const cards=[];
 for(const match of entry.shapes||[]){
  const shape=shapes.get(match.shape_id);if(!shape||!Array.isArray(match.occurrence_ids)||!match.occurrence_ids.length)return {status:'mismatch',cards:[]};
  let lo,hi;try{const a=new Q(shape.start_q),b=new Q(shape.end_q),p=new Q(phrase.start_q),q=new Q(phrase.end_q);lo=a.cmp(p)>0?a:p;hi=b.cmp(q)<0?b:q;if(lo.cmp(hi)>=0||lo.cmp(match.overlap_q[0])!==0||hi.cmp(match.overlap_q[1])!==0)return {status:'mismatch',cards:[]};}catch{return {status:'mismatch',cards:[]};}
  const contacts=new Map();
  for(const [key,label] of GROUPS)for(const point of shape[key]||[]){
   if(!Number.isInteger(point.string)||point.string<1||point.string>8||!Number.isInteger(point.fret)||point.fret<0||point.fret>48)return {status:'mismatch',cards:[]};
   const k=point.string+':'+point.fret;if(!contacts.has(k))contacts.set(k,{string:point.string,fret:point.fret,kinds:[]});contacts.get(k).kinds.push(label);
  }
  cards.push({...shape,overlap_q:[String(lo),String(hi)],witness_count:new Set(match.occurrence_ids).size,contacts:[...contacts.values()]});
 }
 return {status:cards.length?'available':'none',cards};
}
function diagram(doc,card){
 const svg=doc.createElementNS('http://www.w3.org/2000/svg','svg'),contacts=card.contacts;
 const frets=contacts.map(p=>p.fret),lo=frets.length?Math.min(...frets):0,hi=frets.length?Math.max(...frets):0;
 const cell=34,left=36,top=34,row=27,width=Math.max(300,left+(hi-lo+1)*cell+10),height=top+8*row+10;
 const node=(tag,attrs={},text='')=>{const n=doc.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(text)n.textContent=text;svg.append(n);return n;};
 svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.setAttribute('width',width);svg.setAttribute('height',height);svg.setAttribute('role','img');svg.setAttribute('aria-label','Phrase shape. '+contacts.map(p=>`String ${p.string}, fret ${p.fret}: ${p.kinds.join(', ')}`).join('; '));
 node('rect',{x:left,y:top-10,width:width-left-5,height:8*row,fill:'#f1f5f9'});
 for(let f=lo;f<=hi;f++){const x=left+(f-lo+.5)*cell;node('text',{x,y:17,'text-anchor':'middle',fill:'#334155','font-size':12},f===0?'Open':String(f));node('line',{x1:x+cell/2,x2:x+cell/2,y1:top-10,y2:height-20,stroke:'#94a3b8'});}
 for(let string=1;string<=8;string++){const y=top+(string-.5)*row;node('text',{x:16,y:y+4,'text-anchor':'middle',fill:'#334155','font-size':11},'S'+string);node('line',{x1:left,x2:width-5,y1:y,y2:y,stroke:'#94a3b8'});}
 for(const p of contacts){const x=left+(p.fret-lo+.5)*cell,y=top+(p.string-.5)*row,core=p.kinds.includes('Core'),tap=p.kinds.includes('Tap');node('circle',{cx:x,cy:y,r:10,fill:core?'#2563eb':tap?'#9333ea':'#fff',stroke:core?'#1d4ed8':tap?'#7e22ce':'#c87400','stroke-width':2});
  if(p.kinds.includes('Extension')&&(core||tap))node('circle',{cx:x+9,cy:y-9,r:4,fill:'#c87400',stroke:'#fff','stroke-width':1});
  if(tap&&core)node('circle',{cx:x,cy:y,r:13,fill:'none',stroke:'#9333ea','stroke-width':2});
  if(p.kinds.includes('Held')||p.kinds.includes('Carry-in'))node('circle',{cx:x,cy:y,r:14,fill:'none',stroke:'#64748b','stroke-dasharray':'3 2','stroke-width':2});
 }
 return svg;
}
export function renderPhraseShapes(container,notice,data,phrase,doc=globalThis.document){
 container.replaceChildren();const model=phraseShapeModel(data,phrase);
 const messages={unavailable:'Shape data unavailable.',mismatch:'Shape data changed. Reload the page.',none:'No shapes detected.'};
 if(model.status!=='available'){notice.textContent=messages[model.status];return model;}
 notice.textContent='Blue: core · Orange: extension · Purple: tap · Dashed: held notes';
 for(const [i,card] of model.cards.entries()){
  const article=doc.createElement('article');article.setAttribute('class','shapeCard');
  const title=doc.createElement('h4');title.textContent='Shape '+(i+1);article.append(title);
  const scroll=doc.createElement('div');scroll.setAttribute('class','shapeDiagram');scroll.append(diagram(doc,card));article.append(scroll);
  container.append(article);
 }
 return model;
}
