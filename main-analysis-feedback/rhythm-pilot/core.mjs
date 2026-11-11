export const FEEDBACK_SCHEMA='rhythm-pilot-feedback/1';
export const safeText=x=>String(x??'').replace(/[\u200b\ufeff]/g,'');
export function validateManifest(m){
 if(m.schema!=='rhythm-audit/1'||!m.id||!Array.isArray(m.cases)||m.cases.length!==12)throw Error('The frozen audit manifest is invalid.');
 const ids=new Set(),songs=new Set(),artists={},sets={};
 for(const c of m.cases){
  if(!c.id||ids.has(c.id)||!c.riff_id||!c.revision||!c.primary?.id||!c.question?.id||!['boundary','grouping','repetition','dialogue','sustain'].includes(c.question.kind))throw Error('Audit question identity is invalid.');
  ids.add(c.id);songs.add(String(c.source_song_id));artists[c.artist]=(artists[c.artist]||0)+1;sets[c.set]=(sets[c.set]||0)+1;
  const options=c.question.options;if(!Array.isArray(options)||options.length<2||!options.some(o=>o.value==='unsure')||new Set(options.map(o=>o.value)).size!==options.length)throw Error('Audit answer choices are invalid.');
  if(['repetition','dialogue'].includes(c.question.kind)&&!c.comparison?.id)throw Error('A relationship question has no exact comparison phrase.');
 }
 if(songs.size!==12||Object.keys(artists).length!==3||Object.values(artists).some(n=>n!==4))throw Error('Audit deck balance differs from the frozen contract.');
 return m;
}
export function binding(c){return {case_id:c.id,question_id:c.question.id,kind:c.question.kind,riff_id:c.riff_id,revision:c.revision,primary:c.primary,comparison:c.comparison??null,context_range_q:c.context_range_q};}
export function newSession(m,hash){return {schema:FEEDBACK_SCHEMA,deck_id:m.id,manifest_sha256:hash,index:0,answers:{},history:[],updated_at:null};}
export function validateSession(raw,m,hash){
 if(!raw||raw.schema!==FEEDBACK_SCHEMA||raw.deck_id!==m.id||raw.manifest_sha256!==hash)throw Error('This backup belongs to a different audit version.');
 const out=newSession(m,hash);out.index=Number.isInteger(raw.index)?Math.max(0,Math.min(m.cases.length-1,raw.index)):0;
 const cases=new Map(m.cases.map(c=>[c.id,c]));
 for(const [id,a]of Object.entries(raw.answers??{})){
  const c=cases.get(id);if(!c||!a||JSON.stringify(a.binding)!==JSON.stringify(binding(c)))throw Error('An answer is not bound to this exact question and phrase.');
  if(a.answer!==''&&!c.question.options.some(o=>o.value===a.answer))throw Error('A backup answer is not one of this question’s choices.');
  if(typeof a.note!=='string'||a.note.length>4900||!Number.isFinite(Date.parse(a.updated_at)))throw Error('A backup answer is invalid.');
  out.answers[id]={binding:binding(c),answer:a.answer,note:a.note,updated_at:a.updated_at,...quality(a,c)};
 }
 // Keep only validated prior answer revisions; never inject arbitrary backup metadata into the UI.
 for(const old of raw.history??[]){const c=cases.get(old?.binding?.case_id);if(c&&JSON.stringify(old.binding)===JSON.stringify(binding(c))&&typeof old.note==='string'&&old.note.length<=4900&&Number.isFinite(Date.parse(old.updated_at))&&(old.answer===''||c.question.options.some(o=>o.value===old.answer)))out.history.push({binding:binding(c),answer:old.answer,note:old.note,updated_at:old.updated_at,...quality(old,c)});}
 for(const [id,a]of Object.entries(out.answers)){const seen=[a,...out.history.filter(x=>x.binding.case_id===id)].map(x=>x.model_revealed_at).filter(Boolean).sort((x,y)=>Date.parse(x)-Date.parse(y));a.model_revealed_at=seen[0]??null;}out.updated_at=raw.updated_at??null;return out;
}
function quality(a,c){
 const confidence=['','low','medium','high'].includes(a.confidence??'')?a.confidence??'':'';
 const context_quality=['','adequate','too_short','rendering_limits','source_problem'].includes(a.context_quality??'')?a.context_quality??'':'';
 const boundary_marks=typeof a.boundary_marks==='string'?a.boundary_marks.slice(0,500):'';
 if(!/^[0-9.,/ \n]*$/.test(boundary_marks))throw Error('Boundary marks must be quarter-note positions.');
 const model_revealed_at=a.model_revealed_at??null;if(model_revealed_at&&!Number.isFinite(Date.parse(model_revealed_at)))throw Error('Invalid model reveal time.');
 return {confidence,context_quality,boundary_marks,model_revealed_at};
}
export function putAnswer(session,c,answer,note,now=new Date().toISOString(),extra={}){
 if(answer!==''&&!c.question.options.some(o=>o.value===answer))throw Error('Invalid answer.');
 const previous=session.answers[c.id],q=quality({...previous,...extra},c);
 if(previous&&(previous.answer!==answer||previous.model_revealed_at!==q.model_revealed_at))session.history.push({...previous});
 session.answers[c.id]={binding:binding(c),answer,note:note.slice(0,4900),updated_at:now,...q};session.updated_at=now;return session;
}
export function mergeSessions(current,incoming){
 const result=structuredClone(current);
 for(const [id,a]of Object.entries(incoming.answers)){
  const old=result.answers[id];
  if(!old||Date.parse(a.updated_at)>Date.parse(old.updated_at)){if(old)result.history.push(old);result.answers[id]=a;}
  else if(JSON.stringify(old)!==JSON.stringify(a))result.history.push(a);
 }
 result.history.push(...incoming.history);for(const [id,a]of Object.entries(result.answers)){const seen=[a,current.answers[id],incoming.answers[id],...result.history.filter(x=>x.binding.case_id===id)].filter(Boolean).map(x=>x.model_revealed_at).filter(Boolean).sort((x,y)=>Date.parse(x)-Date.parse(y));a.model_revealed_at=seen[0]??null;}result.updated_at=new Date().toISOString();return result;
}
export function progress(m,session){
 const out={answered:0,unsure:0,by_kind:{},by_artist:{},by_set:{},reviewed_targets:[]};const targets=new Set();
 for(const c of m.cases){const a=session.answers[c.id];if(!a?.answer)continue;out.answered++;if(a.answer==='unsure')out.unsure++;out.by_kind[c.question.kind]=(out.by_kind[c.question.kind]||0)+1;out.by_artist[c.artist]=(out.by_artist[c.artist]||0)+1;out.by_set[c.set]=(out.by_set[c.set]||0)+1;if(a.answer!=='unsure')for(const t of c.question.coverage_targets??(c.question.field?[c.question.field+'='+c.question.target_value]:[]))targets.add(typeof t==='string'?t:JSON.stringify(t));}
 out.reviewed_targets=[...targets];return out;
}
export async function sha256(bytes){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');}
export async function verifiedJson(path,hash,fetcher=fetch){
 if(typeof path!=='string'||path.startsWith('/')||path.includes('..')||/^[a-z]+:/i.test(path))throw Error('Unexpected audit asset path.');
 const response=await fetcher(path,{cache:'no-cache'});if(!response.ok)throw Error('Could not load audit data ('+response.status+').');
 const bytes=await response.arrayBuffer();if(hash&&await sha256(bytes)!==hash)throw Error('The saved analysis version does not match this audit. Reload and try again.');
 let content=bytes;if(path.split('?')[0].endsWith('.gz')){if(typeof DecompressionStream==='undefined')throw Error('Please use a current Safari, Chrome or Firefox for compressed audit data.');content=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();}
 return JSON.parse(new TextDecoder().decode(content));
}
