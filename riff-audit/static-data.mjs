import {Q} from './timing.mjs';
const cmp=(a,b)=>new Q(a).cmp(b), canon=q=>String(new Q(q));
const clone=value=>structuredClone(value);
function inScope(obj,lo,hi,meter){
 if(obj.source&&!obj.range_q&&obj.onset_q==null&&obj.bar==null)return inScope(obj.source,lo,hi,meter);
 if(obj.range_q)return cmp(obj.range_q[0],hi)<0&&cmp(obj.range_q[1],lo)>0;
 const on=obj.onset_q,off=obj.end_q??obj.written_end_q;
 if(on!=null)return (cmp(on,lo)>=0&&cmp(on,hi)<0)||(off!=null&&cmp(on,lo)<0&&cmp(off,lo)>0);
 let bar=obj.bar; if(bar==null){const match=String(obj.pointer??'').match(/\/measures\/(\d+)/);if(match)bar=Number(match[1])+1;}
 const metric=meter.find(m=>m.bar===bar);
 if(metric)return cmp(metric.start_q,hi)<0&&new Q(metric.start_q).add(metric.span_q).cmp(lo)>0;
 return true;
}
function sameRange(a,b){return Array.isArray(a)&&Array.isArray(b)&&a.length===2&&b.length===2&&a.every((q,i)=>cmp(q,b[i])===0);}
function verifyBinding(pack,record,details){
 if(!record.source_id||pack.source_id!==record.source_id)throw Error('Rhythm export source identity does not match the catalogue record.');
 const projection=pack.projection_receipt?.content_sha256;
 const binding=record.export_binding;
 if(binding&&(binding.record_id!==record.id||!sameRange(binding.range_q,record.range_q)||binding.raw_source_sha256!==pack.source_hash_bindings?.raw_source_sha256||binding.projection_sha256!==projection))throw Error('Catalogue source/range/projection binding is inconsistent with the export.');
 if(record.source_pack){
  const authorized=pack.authorized_records?.[record.id];
  if(!authorized||!sameRange(authorized.range_q,record.range_q))throw Error('Rhythm source pack is not authorized for this catalogue record and original range.');
  if(!projection||projection!==record.source_pack_projection_sha256)throw Error('Rhythm source-pack projection does not match the catalogue binding.');
 }else{
  if(pack.record?.id!==record.id||pack.selection?.record_id!==record.id||!sameRange(pack.range_q,record.range_q)||!sameRange(pack.selection?.range_q,record.range_q))throw Error('Rhythm reference identity or original range does not match the catalogue record.');
  if(!projection||projection!==record.reference_projection_sha256)throw Error('Rhythm reference projection does not match the catalogue binding.');
 }
 if(record.detail_path||Object.keys(details).length){
  if(details.record_id!==record.id||details.source_id!==record.source_id||details.reference_projection_sha256!==record.reference_projection_sha256)throw Error('Structural detail identity or projection does not match the selected reference.');
  if(details.range_q&&!sameRange(details.range_q,record.range_q))throw Error('Structural detail range differs from the original selected riff.');
  if(details.raw_source_sha256&&details.raw_source_sha256!==pack.source_hash_bindings?.raw_source_sha256)throw Error('Structural detail raw-source binding differs from the selected reference.');
  const graph=pack.source_hash_bindings?.graph_sha256s,detailGraph=details.source_hash_bindings?.graph_sha256s;
  if(graph&&detailGraph&&JSON.stringify(graph)!==JSON.stringify(detailGraph))throw Error('Structural detail graph binding does not match the selected reference.');
 }
}
export function selectReference(pack,record,{view_id=null,start_q=null,end_q=null,voices=null,details={}}={}){
 if(!record.available||record.replay_export_status!=='ready')return {available:false,record,events:[],carry_in:[],carry_out:[],views:[],coverage:{neutral_rhythm_eligible:false,pitched_notation_eligible:false},warnings:record.unavailable_reasons??[],replay_export_status:record.replay_export_status};
 verifyBinding(pack,record,details);
 const [lo,hi]=[canon(start_q??record.range_q[0]),canon(end_q??record.range_q[1])];
 if(cmp(lo,record.range_q[0])<0||cmp(hi,record.range_q[1])>0||cmp(lo,hi)>=0)throw Error('Choose an increasing range inside the selected riff.');
 const available=pack.available_voices??[...new Set([...(pack.events??[]).flatMap(e=>e.members??[]),...(pack.carry_in??[])].map(m=>m.voice).filter(Number.isInteger))].sort((a,b)=>a-b);
 const chosen=voices==null?available:[...new Set(voices)].sort((a,b)=>a-b);
 if(!chosen.length||chosen.some(v=>!Number.isInteger(v)||v<0||!available.includes(v)))throw Error('Requested voice is not present in the source.');
 const keepVoice=obj=>obj.voice==null||chosen.includes(obj.voice);
 const views=details.views??pack.views??[];
 const ids=views.map(v=>v.id);view_id??=['verified_nested_0','motif_occurrence_cover','construction_runs'].find(v=>ids.includes(v))??null;
 if(view_id!=null&&!ids.includes(view_id))throw Error('Unknown structural view.');
 const meter=pack.meter_map??[],events=[],carry_in=[],carry_out=[],all=[];
 const seen=new Set();
 function member(m){
  if(!keepVoice(m))return null;const id=m.occurrence??m.id;if(seen.has(id))return null;seen.add(id);
  if(m.onset_q==null)return null;const on=m.onset_q,off=m.tied_end_q;
  if(!((cmp(on,lo)>=0&&cmp(on,hi)<0)||(cmp(on,lo)<0&&(off==null||cmp(off,lo)>0))))return null;
  const n={...m,carry_in:cmp(on,lo)<0,carry_out:off==null||cmp(off,hi)>0};all.push(n);
  if(n.carry_in)carry_in.push(n);if(n.carry_out)carry_out.push(n);return n;
 }
 for(const e of pack.events??[]){const members=(e.members??[]).map(member).filter(m=>m&&!m.carry_in);if(members.length)events.push({...e,members});}
 for(const m of pack.carry_in??[])member(m);
 const scope=obj=>inScope(obj,lo,hi,meter);
 const rests=(pack.explicit_rests??[]).filter(r=>keepVoice(r)&&scope(r));
 const unknown=(pack.unplaced_or_unknown??[]).filter(r=>keepVoice(r.source??r)&&scope(r));
 const grace=(pack.grace_members??[]).filter(g=>keepVoice(g)&&scope(g));
 const masks=(pack.masks??[]).filter(scope),blocking=masks.filter(m=>m.scope!=='grid'||(m.masked_objectives??[]).some(x=>x!=='sixteenth_grid_only'));
 const tempo=pack.tempo_map??[];const atStart=tempo.filter(t=>cmp(t.onset_q,lo)<=0).at(-1);
 const relevantTempo=[...(atStart?[atStart]:[]),...tempo.filter(t=>cmp(t.onset_q,lo)>=0&&cmp(t.onset_q,hi)<0)];
 const tempoUnknown=(pack.tempo_unknown??[]).filter(u=>{if(u.effect_range_q)return cmp(u.effect_range_q[0],hi)<0&&cmp(u.effect_range_q[1],lo)>0;if(!u.range_q)return true;const [a,b]=u.range_q;if(cmp(a,hi)>=0)return false;if(cmp(b,lo)<=0&&tempo.some(t=>cmp(t.onset_q,b)>=0&&cmp(t.onset_q,lo)<=0&&cmp(t.onset_q,a)>0))return false;return true;});
 const clocks=!unknown.length&&!blocking.length&&!grace.length&&all.every(m=>m.clock_known&&m.segments_complete&&m.origin_attack_known===true&&!m.unresolved);
 const tempoKnown=!!atStart&&!tempoUnknown.length&&!relevantTempo.some(t=>t.linear);
 const unsupported=[...new Set(all.flatMap(m=>m.unsupported_synthesis_marks??[]))].sort();
 const coverage={attack_groups:events.length,attack_members:events.reduce((a,e)=>a+e.members.length,0),carry_in_members:carry_in.length,carry_out_members:carry_out.length,explicit_rests:rests.length,exact_clocks_known:clocks,tempo_known:tempoKnown,neutral_rhythm_eligible:clocks&&tempoKnown,pitched_notation_eligible:false,acoustic_fidelity_known:false,unsupported_synthesis_marks:unsupported.length?unsupported:(pack.coverage?.unsupported_synthesis_marks??[]),all_selected_source_members_retained:true,literal_rests_not_acoustic_silence:true};
 const selection={record_id:record.id,view_id,range_q:[lo,hi],voices:chosen,repeat_policy:'written_score_order_no_repeat_expansion',carry_policy:'original_attack_and_full_tie_chain_preserved',context_policy:'strict_subrange_inside_selected_riff',normalizer_version:'public-riff-client-selector/1'};
 return {schema:'public-riff-reference/1',available:true,record,selection,range_q:[lo,hi],events,carry_in,carry_out,explicit_rests:rests,unplaced_or_unknown:unknown,grace_members:grace,masks,blocking_masks:blocking,tempo_map:tempo,tempo_unknown:tempoUnknown,meter_map:meter,available_voices:available,views,hierarchy:(details.hierarchy_by_view?.[view_id]??(details.hierarchy?.view_id===view_id?details.hierarchy:null)??pack.hierarchy_by_view?.[view_id]??null),track_metadata:pack.track_metadata??{name:record.track},coverage,source:pack.source??{},source_hash_bindings:pack.public_provenance??pack.source_hash_bindings??{},projection_receipt:pack.projection_receipt??null,warnings:['Notation replay only. Source recording and acoustic sustain are not reconstructed.','Public excerpt export. Local paths, original score objects and private annotations are not published.','Only the selected riff is available; outside context and generation are not included in this public checkpoint.','Candidate structure is not semantic phrase ground truth.']};
}
const cache=new Map(),pending=new Map();let cacheBytes=0,manifestPromise;
const MAX_FILES=8,MAX_CACHE_BYTES=32*1024*1024;
function safePath(path){if(!/^(?:\.\/)?data\/[A-Za-z0-9_./-]+\.json$/.test(path)||path.includes('..'))throw Error('Invalid exported data address.');return path.replace(/^\.\//,'');}
export const resolveDataURL=(path,base=new URL('.',import.meta.url))=>new URL(path,base);
async function fetchBytes(path){const r=await fetch(resolveDataURL(path),{credentials:'omit'});if(!r.ok){const error=Error(`Export could not load (${r.status}).`);error.status=r.status;throw error;}return new Uint8Array(await r.arrayBuffer());}
async function digest(bytes){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');}
async function exportBytes(path,binding,gzipOnly=false){
 if(gzipOnly&&typeof DecompressionStream!=='function')throw Error('This public player requires gzip decompression support. Update Safari or Chrome to a current version; no uncompressed fallback is published.');
 if(typeof DecompressionStream==='function'&&Number.isSafeInteger(binding.gzip_bytes)){
  let compressed;try{compressed=await fetchBytes(path+'.gz');}catch(e){if(e.status!==404||gzipOnly)throw e;return fetchBytes(path);}
  if(compressed.byteLength!==binding.gzip_bytes)throw Error('Compressed export length does not match its manifest.');
  if(binding.gzip_sha256&&await digest(compressed)!==binding.gzip_sha256)throw Error('Compressed export hash does not match its manifest.');
  const stream=new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip')),reader=stream.getReader(),chunks=[];let size=0;
  try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>(binding.bytes??64*1024*1024)||size>64*1024*1024)throw Error('Export exceeds declared decompression limit.');chunks.push(value);}}catch(e){await reader.cancel();throw e;}
  const result=new Uint8Array(size);let pos=0;for(const part of chunks){result.set(part,pos);pos+=part.byteLength;}return result;
 }
 return fetchBytes(path);
}
async function manifest(){manifestPromise??=fetchBytes('data/manifest.json').then(bytes=>JSON.parse(new TextDecoder().decode(bytes))).catch(e=>{manifestPromise=null;throw e;});return manifestPromise;}
export async function loadJson(path){
 path=safePath(path);if(cache.has(path)){const entry=cache.get(path);cache.delete(path);cache.set(path,entry);return entry.value;}
 if(pending.has(path))return pending.get(path);
 const promise=(async()=>{const index=await manifest(),binding=index.files?.[path];if(!binding?.sha256)throw Error('Export is not listed in the published integrity manifest.');
  if(!globalThis.crypto?.subtle)throw Error('This browser cannot verify the rhythm export. Open the HTTPS page in a current browser.');
  const bytes=await exportBytes(path,binding,index.delivery==='gzip-only'||binding.plain_available===false);if(binding.bytes!=null&&bytes.byteLength!==binding.bytes)throw Error('Published export length does not match its manifest.');
  if(!globalThis.crypto?.subtle)throw Error('This browser cannot verify the rhythm export. Open the HTTPS page in a current browser.');
  const actualHash=await digest(bytes);if(actualHash!==binding.sha256)throw Error('Published export hash does not match its manifest. Reload after deployment finishes.');
  const value=JSON.parse(new TextDecoder().decode(bytes));
  if(bytes.byteLength<=MAX_CACHE_BYTES){while(cache.size&&(cache.size>=MAX_FILES||cacheBytes+bytes.byteLength>MAX_CACHE_BYTES)){const old=cache.keys().next().value;cacheBytes-=cache.get(old).bytes;cache.delete(old);}cache.set(path,{value,bytes:bytes.byteLength});cacheBytes+=bytes.byteLength;}
  return value;
 })().finally(()=>pending.delete(path));pending.set(path,promise);return promise;
}
export const loadCatalog=()=>loadJson('data/catalog.json');
export const cacheStats=()=>({files:cache.size,bytes:cacheBytes,maxFiles:MAX_FILES,maxBytes:MAX_CACHE_BYTES,pending:pending.size});
export async function loadReference(record,options={}){
 if(!record.available||record.replay_export_status!=='ready')return selectReference({},record,options);
 const source=record.source_pack??record.reference_path;if(!source)throw Error('Replay export is not available for this record yet.');
 const index=await manifest(),expected=record.source_pack?record.source_pack_sha256:record.reference_sha256;
 if(!expected||index.files?.[source]?.sha256!==expected)throw Error('Catalogue source path and exported file digest do not match.');
 if(record.detail_path&&(!record.detail_sha256||index.files?.[record.detail_path]?.sha256!==record.detail_sha256))throw Error('Catalogue structural-detail path and exported file digest do not match.');
 const [pack,details]=await Promise.all([loadJson(source),record.detail_path?loadJson(record.detail_path):Promise.resolve({})]);
 return selectReference(pack,record,{...options,details});
}
