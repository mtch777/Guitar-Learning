export const rational=x=>{const [a,b='1']=String(x).split('/');return Number(a)/Number(b)};
export function sourceStringIndex(count,gpString){return gpString>0&&gpString<=count?count-gpString:null;}
export function joinDifferences(row,event){
 if(!row)return ['missing occurrence'];
 const out=[];
 for(const [label,a,b] of [['pitch',row.midi,event.pitch],['source string index',row.string,event.sourceString],['fret',row.fret,event.fret]])if(a!==b)out.push(label);
 if(Math.abs(rational(row.bar_offset_q)-event.localQ)>1e-7)out.push('onset within bar');
 if(Math.abs(rational(row.duration_q)-event.durationQ)>1e-7)out.push('written duration');
 return out;
}
export function playbackPosition(tick,playedBar,sourceHeader){
 return {barIndex:playedBar.masterBar.index,localQ:(tick-playedBar.start)/960,sourceQ:sourceHeader?rational(sourceHeader.start_q)+(tick-playedBar.start)/960:null};
}

export function linkedAnalysis(track,ids){const output=[];const contains=v=>typeof v==='string'?ids.has(v):!!v&&typeof v==='object'&&Object.values(v).some(contains);function walk(v,path){if(!v||typeof v!=='object')return;if(Array.isArray(v)){v.forEach((item,i)=>{if(item&&typeof item==='object'&&contains(item))output.push({path:`${path}.${i}`,data:item});});return;}if(Object.values(v).some(x=>typeof x==='string'&&ids.has(x))){output.push({path,data:v});return;}for(const[k,x]of Object.entries(v))walk(x,`${path}.${k}`);}for(const[k,v]of Object.entries(track||{}))if(k!=='rows'&&k!=='raw_note')walk(v,k);return output;}
