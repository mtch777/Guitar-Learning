import {GeneratorClient} from './generation-runtime/client.mjs';
import {ReferencePlayer} from './player.mjs';
import {Q,compileSchedule} from './timing.mjs';
export function generationPayload(reference,{seed,extent,bpm}){
 if(!reference?.available||!reference.selection?.range_q)throw Error('Select a playable reference range first.');
 if(!/^-?\d{1,19}$/.test(seed)||BigInt(seed)<-(2n**63n)||BigInt(seed)>=2n**63n)throw Error('Seed must be a signed 64-bit integer.');
 const length=new Q(extent);if(length.cmp('0')<=0)throw Error('Length must be positive quarters.');
 const tempo=Number(bpm);if(!Number.isFinite(tempo)||tempo<20||tempo>400)throw Error('Choose 20–400 quarter BPM.');
 return {reference_json:JSON.stringify(reference),request_json:JSON.stringify({extent_q:String(length),meter:[4,4],start_phase_q:'0',tempo_bpm:tempo}),seed_decimal:BigInt(seed).toString(),rules_json:'{}'};
}
export function outcomeAudition(outcome){
 if(outcome.status!=='result'||!outcome.result?.player_json)return null;
 const ref=JSON.parse(outcome.result.player_json),range=ref.selection.range_q;
 const plan=compileSchedule(ref,range,{mode:'neutral',speed:1,normalized:false,loop:false,allowPartial:false});
 return {ref,range,plan};
}
function save(text,name){const url=URL.createObjectURL(new Blob([text],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);}
export function mountGeneration({host,getReference,stopReference,clientFactory=options=>new GeneratorClient(options)}){
 host.replaceChildren();const make=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;return e;};
 const heading=make('h3','Generate from this selection');host.append(heading,make('p','Experimental selected-reference constructor, not a trained semantic phrase model. It uses measured timing plus explicit authored priors. No target melody or guitar rendering.'));
 host.append(make('p','First use downloads about 14 MB of browser runtime. Jobs and results stay in this tab only: download results before leaving. Every outcome remains visible, including failures and rejected or partial raw results.'));
 const controls=make('div');controls.className='range-row';
 const field=(title,value)=>{const label=make('label',title),input=make('input');input.value=value;input.type='text';label.append(input);controls.append(label);return input;};
 const seed=field('Exact seed','1109'),extent=field('Output quarters (4/4)','16'),bpm=field('Quarter BPM','120');
 const run=make('button','Generate selected rhythm'),cancel=make('button','Cancel');run.className='primary';cancel.disabled=true;controls.append(run,cancel);host.append(controls);
 const progress=make('p','Choose a reference or subrange above, then Generate.');progress.setAttribute('role','status');const results=make('div');host.append(progress,results);
 const client=clientFactory({onProgress:m=>{progress.textContent=m.status==='loading'?'Loading verified browser runtime…':'Generating from the frozen selection…';}});
 const generatedPlayer=new ReferencePlayer();let active=false;const jobs=[];
 const stop=()=>generatedPlayer.stop();cancel.onclick=()=>client.cancel();
 run.onclick=async()=>{
  if(active)return;let payload,ref;try{ref=getReference();payload=generationPayload(ref,{seed:seed.value.trim(),extent:extent.value.trim(),bpm:bpm.value.trim()});}catch(e){progress.textContent=e.message;return;}
  const job={schema:'rhythm-pages-session-job/1',created_at:new Date().toISOString(),reference_label:ref.record?.id??ref.selection.record_id,selection:structuredClone(ref.selection),payload,outcome:null};jobs.push(job);
  active=true;run.disabled=true;cancel.disabled=false;stop();stopReference();
  const card=make('section');card.className='source-details';card.append(make('h4',`Seed ${payload.seed_decimal} | ${job.reference_label} | ${ref.selection.range_q.join(' to ')} q`));const status=make('p','Running…');card.append(status);results.prepend(card);
  try{
   job.outcome=await client.generate(payload);const out=job.outcome;
   status.textContent=out.status==='result'?`${out.result.summary.status} | ${out.result.summary.attacks} attacks | assessment: ${out.result.summary.assessment}`:`${out.status}: ${out.error?.message??'No complete raw output returned.'}`;
   let audition=null;try{audition=outcomeAudition(out);}catch(e){card.append(make('p','Audition unavailable: '+e.message));}
   if(audition){const play=make('button','Play generated rhythm'),end=make('button','Stop');play.onclick=()=>{stopReference();stop();generatedPlayer.options={mode:'neutral',speed:1,normalized:false,loop:false,allowPartial:false};generatedPlayer.load(audition.ref,audition.range);generatedPlayer.play().catch(e=>{progress.textContent=e.message;});};end.onclick=stop;card.append(play,end,make('p',`${audition.plan.duration.toFixed(2)} s, including natural held-note tails. No automatic playback.`));}
   else card.append(make('p','No complete playable clock returned. Raw evidence is retained, not replaced or retried.'));
   const download=make('button','Download complete job');download.onclick=()=>save(JSON.stringify(job,null,2),`rhythm-job-${payload.seed_decimal}-${jobs.indexOf(job)+1}.json`);card.append(download);
   if(out.result?.raw_json){const raw=make('button','Download raw result');raw.onclick=()=>save(out.result.raw_json,`rhythm-raw-${payload.seed_decimal}.json`);card.append(raw);}
   const details=make('details'),summary=make('summary','Outcome evidence'),pre=make('pre');pre.textContent=out.status==='result'?JSON.stringify({summary:out.result.summary,projection:out.result.projection_receipt,assessment:JSON.parse(out.result.assessment_json),runtime:out.runtime_receipt},null,2):JSON.stringify(out,null,2);details.append(summary,pre);card.append(details);
   progress.textContent='Finished. This result remains tied to its original selected range even if you navigate elsewhere.';
  }catch(e){job.outcome={status:'failed',error:{message:e.message}};status.textContent='Failed: '+e.message;progress.textContent='Generation failed; no successful result is claimed.';}
  finally{active=false;run.disabled=false;cancel.disabled=true;}
 };
 window.addEventListener('riff-selection',stop);
 window.addEventListener('pagehide',()=>{stop();client.dispose();});
 return {stop,available:true,jobs,dispose(){stop();client.dispose();}};
}

