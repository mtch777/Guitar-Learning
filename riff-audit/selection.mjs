// Counts are selectable occurrences, not unique songs or independently verified phrases.
export const kindLabels={whole:'Whole riff',verified_motif_operand:'Motif candidate',untyped_remainder:'Unclassified part',pitched_line:'Single-note line',distinct_pitch_chord:'Chord gesture',connected_articulation_line:'Connected-note gesture',palm_muted_line:'Palm-muted line',unpitched_or_unknown:'Unpitched / unknown',continuous_untyped:'Unclassified part'};
export const kindLabel=k=>kindLabels[k]??k.replaceAll('_',' ');
export function selectionEntries(records,index,styles={}){
 const ready=records.filter(r=>r.available&&r.replay_export_status==='ready'&&['accepted','riff'].includes(r.status));const byId=new Map(ready.map(r=>[r.id,r]));
 const sourceStyles=r=>styles[r.id]?.style_ids?.length?styles[r.id].style_ids:['unlabeled'];
 return [...ready.map(record=>({id:record.id,record,scope:'whole',kind:'whole',sourceStyle:sourceStyles(record),range:record.range_q})),...(index.parts??[]).filter(p=>byId.has(p.record_id)).map(p=>({...p,id:`${p.record_id}/${p.view}/${p.unit}`,record:byId.get(p.record_id),scope:'part',sourceStyle:sourceStyles(byId.get(p.record_id))}))];
}
export function matchesSelection(e,filters={},omit){return Object.entries(filters).every(([k,v])=>k===omit||!v||v==='all'||(k==='search'?`${e.record.artist} ${e.record.song} ${e.record.track} ${e.record.id}`.toLowerCase().includes(v.toLowerCase()):(Array.isArray(e[k])?e[k].includes(v):(e[k]??e.record[k])===v)));}
export function facetCounts(entries,filters,key){const counts=new Map();for(const e of entries)if(matchesSelection(e,filters,key)){const values=e[key]??e.record[key];for(const value of Array.isArray(values)?values:[values])counts.set(value,(counts.get(value)??0)+1);}return [...counts].sort((a,b)=>String(a[0]).localeCompare(String(b[0])));}
export function randomSelection(entries,random=Math.random,previousId){const pool=entries.length>1?entries.filter(e=>e.id!==previousId):entries;return pool.length?pool[Math.min(pool.length-1,Math.floor(random()*pool.length))]:null;}
