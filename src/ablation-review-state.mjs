export const METRICS=[['coherence','Overall coherence'],['melody','Melody continuity'],['harmony','Harmony fit'],['phrasing','Phrase development'],['playability','Playability (if assessable)']];
export const VALUES=new Set(['','1','2','3','4','5','uncertain','absent']);
export const storageKey=version=>'composition-ablation-review:'+version;
export const reviewed=r=>Boolean(r?.coherence);
export function recordReview(previous,patch,{now=new Date().toISOString()}={}){
  const result={...previous,...patch,updatedAt:now};
  for(const [key] of METRICS) if(key in result&&!VALUES.has(result[key])) throw new Error('Invalid rating');
  if(previous?.revealedAt) result.editedAfterReveal=true;
  return result;
}
export function revealReview(previous,now=new Date().toISOString()){
  if(!reviewed(previous)) throw new Error('Record an overall judgment before revealing the method.');
  return {...previous,revealedAt:previous.revealedAt||now,reviewedBeforeReveal:true};
}
export function mergeFeedback(local,incoming,manifest){
  if(incoming.format!=='composition-ablation-feedback-v1'||incoming.version!==manifest.version) throw new Error('This feedback belongs to a different review set.');
  const allowed=new Set(manifest.cases.map(c=>c.id));const result=structuredClone(local);
  for(const [id,r] of Object.entries(incoming.reviews||{})){
    if(!allowed.has(id)) throw new Error('Unknown sketch in feedback.');
    for(const [key] of METRICS) if(r[key]!==undefined&&!VALUES.has(r[key])) throw new Error('Invalid rating in feedback.');
    if(!result[id]||String(r.updatedAt||'')>String(result[id].updatedAt||'')) result[id]={...r,
      ...(result[id]?.revealedAt?{revealedAt:result[id].revealedAt}:{}),
      editedAfterReveal:Boolean(r.editedAfterReveal||result[id]?.editedAfterReveal||result[id]?.revealedAt)};
    else if(r.revealedAt&&!result[id].revealedAt) result[id]={...result[id],revealedAt:r.revealedAt,editedAfterReveal:true};
  }
  return result;
}
export function csvFeedback(manifest,reviews,favorites){
  const fields=['version','case_id','family',...METRICS.map(([k])=>k),'notes','favorite','updatedAt','revealedAt','editedAfterReveal'];
  const quote=value=>'"'+String(value??'').replaceAll('"','""')+'"';
  return [fields,...manifest.cases.map(c=>{const r=reviews[c.id]||{};const row={...r,version:manifest.version,case_id:c.id,family:c.family,favorite:favorites[c.family]===c.id};return fields.map(k=>row[k]??'');})].map(row=>row.map(quote).join(',')).join('\r\n');
}
