import { trialZip } from './trial-archive.js';
const $=id=>document.getElementById(id),base=new URL(import.meta.env.BASE_URL,location.origin);
const worker=new Worker(new URL('./live-pipeline-worker.js',import.meta.url),{type:'module'});
const openMidi=[27,34,39,44,49,54,58,63],sessionId=crypto.randomUUID();
for(const id of ['string','string2'])for(let s=1;s<=8;s++)$(id).add(new Option(String(s),String(s)));
let manifest,context,stream,source,capture,sink,active=null,trials=[],plan=[],planIndex=0,exportedCount=0,channelAvailable=false;
const wall=()=>performance.timeOrigin+performance.now();
function setStatus(s){$('status').textContent=s;}
function planTarget(){
  if($('plan').value==='manual')return;
  const t=plan[planIndex];if(!t)return;
  for(const k of ['string','fret','attack','repeat'])$(k).value=t[k];$('kind').value='single';refreshTarget();
}
function makePlan(){
  plan=[];planIndex=0;
  const full=$('plan').value==='full';
  for(let string=1;string<=8;string++)for(const fret of full?[0,5,12,19,24]:[0,12,24])
    for(const attack of full?['soft','normal','hard']:['normal'])for(let repeat=1;repeat<=(full?2:1);repeat++)plan.push({string,fret,attack,repeat});
  planTarget();refreshTarget();
}
function refreshTarget(){
  const kind=$('kind').value;$('second').hidden=!['transition','overlap'].includes(kind);
  $('target').textContent=kind==='silence'?'Remain silent for this trial':`String ${$('string').value} · fret ${$('fret').value} · ${$('attack').value}`;
  $('progress').textContent=$('plan').value==='manual'?'Manual target':`Planned target ${planIndex+1} of ${plan.length}`;
}
function lock(on){for(const id of ['device','channel','plan','kind','string','fret','attack','repeat','string2','fret2','next','clear','export'])$(id).disabled=on;}
function updateReady(){
  $('record').disabled=!stream||!channelAvailable||!manifest||!!active||trials.length>=40||($('plan').value!=='manual'&&planIndex>=plan.length);
  $('export').disabled=!!active||!trials.length;$('clear').disabled=!!active||!trials.length;
  $('saved').textContent=`${trials.length} saved trial(s) · ${Math.round(trials.reduce((n,t)=>n+t.pcm.byteLength,0)/1048576)} MB audio`;
}
function target(){
  const position=(s,f)=>{const string=Number($(s).value),fret=Number($(f).value);if(!Number.isInteger(fret)||fret<0||fret>24)throw Error('Fret must be 0–24');return {string,fret,midi:openMidi[string-1]+fret};};
  const first=position('string','fret'),kind=$('kind').value;
  const positions=kind==='silence'?[]:kind==='repeated'?[first,first]:['transition','overlap'].includes(kind)?[first,position('string2','fret2')]:[first];
  return {kind,positions,attack:$('attack').value,repeat:Number($('repeat').value)};
}
async function devices(){
  const selected=$('device').value,items=await navigator.mediaDevices.enumerateDevices();
  $('device').replaceChildren(new Option('System default',''));
  items.filter(d=>d.kind==='audioinput').forEach((d,i)=>$('device').add(new Option(d.label||`Input ${i+1}`,d.deviceId)));
  if([...$('device').options].some(o=>o.value===selected))$('device').value=selected;
}
async function stop(){
  if(active&&!active.finishRequested){active.aborted=true;requestFinish();}
  stream?.getTracks().forEach(t=>t.stop());source?.disconnect();capture?.disconnect();sink?.disconnect();
  if(context)await context.close();stream=null;context=null;channelAvailable=false;$('microphone').textContent='Enable microphone';
  if(!active)setStatus('Microphone off');updateReady();
}
$('microphone').onclick=async()=>{
  if(stream){await stop();return;}
  try{
    if(!window.AudioWorkletNode)throw Error('Use a browser with AudioWorklet support');
    stream=await navigator.mediaDevices.getUserMedia({audio:{deviceId:$('device').value?{exact:$('device').value}:undefined,
      channelCount:{ideal:2},echoCancellation:false,noiseSuppression:false,autoGainControl:false},video:false});
    context=new AudioContext({sampleRate:44100});await context.resume();
    await context.audioWorklet.addModule(new URL('live-pipeline-capture.js',base).href);
    capture=new AudioWorkletNode(context,'live-pipeline-capture',{processorOptions:{channel:Number($('channel').value)}});
    sink=context.createGain();sink.gain.value=0;source=context.createMediaStreamSource(stream);
    source.connect(capture);capture.connect(sink);sink.connect(context.destination);
    capture.port.onmessage=({data:d})=>{
      if(d.type==='channel-error'){channelAvailable=false;updateReady();$('levels').textContent=`Only ${d.channels} input channel(s). Choose channel 1.`;if(active){active.aborted=true;requestFinish();}return;}
      channelAvailable=true;updateReady();
      $('levels').textContent=`${context?.sampleRate} Hz · `+d.levels.map((l,i)=>`Ch ${i+1}: ${l.rms>0?(20*Math.log10(l.rms)).toFixed(1):'−∞'} dBFS${l.peak>=.99?' · CLIPPING':''}`).join(' | ');
      if(!active||active.finishRequested)return;
      active.blocks++;active.channelCounts.add(d.channels);
      worker.postMessage({type:'frame',id:active.id,samples:d.samples,sequence:d.sequence,audioTime:d.audioTime,receivedWallMs:wall()},[d.samples]);
      if(active.blocks*4096>=active.sampleRate*active.seconds)requestFinish();
    };
    $('microphone').textContent='Disable microphone';await devices();setStatus('Ready. Verify the selected channel responds to your guitar.');updateReady();
  }catch(e){await stop();setStatus(`Input error: ${e.message}`);}
};
$('channel').onchange=()=>{channelAvailable=false;updateReady();capture?.port.postMessage({type:'channel',channel:Number($('channel').value)});};
$('device').onchange=async()=>{if(stream){await stop();setStatus('Input changed. Enable microphone again.');}};
$('plan').onchange=()=>{makePlan();updateReady();};
for(const id of ['kind','string','fret','attack','repeat','string2','fret2'])$(id).onchange=refreshTarget;
$('kind').onchange=()=>{if($('kind').value!=='single')$('plan').value='manual';refreshTarget();updateReady();};
$('next').onclick=()=>{if(planIndex<plan.length-1){planIndex++;planTarget();}updateReady();};
$('record').onclick=()=>{
  if(!stream||active||!manifest)return;
  try{
    const t=target(),id=crypto.randomUUID();
    active={id,target:t,sampleRate:context.sampleRate,seconds:6,blocks:0,channelCounts:new Set(),
      startedAt:new Date().toISOString(),startedWallMs:wall(),channel:Number($('channel').value)+1,
      deviceSettings:stream.getAudioTracks()[0].getSettings(),cues:[],renderedEvents:[],aborted:false};
    worker.postMessage({type:'start',id,sampleRate:context.sampleRate});lock(true);updateReady();setStatus('Stay quiet…');
    const cue=(message,at)=>setTimeout(()=>{if(active?.id===id&&!active.finishRequested){active.cues.push({message,wallMs:wall()});setStatus(message);}},at);
    cue(t.kind==='silence'?'SILENCE · keep input quiet':'PLAY NOW · first pluck',1000);
    if(t.positions.length===2)cue(t.kind==='overlap'?'PLAY SECOND · leave the first ringing':'PLAY SECOND · mute the first, then pluck',3000);
    active.timeout=setTimeout(()=>{if(active?.id===id&&!active.finishRequested){active.aborted=true;requestFinish();setStatus('Audio stopped arriving; saving incomplete trial.');}},12000);
  }catch(e){active=null;lock(false);updateReady();setStatus(e.message);}
};
function requestFinish(){if(!active||active.finishRequested)return;active.finishRequested=true;clearTimeout(active.timeout);setStatus('Capture finished · processing…');worker.postMessage({type:'finish',id:active.id});}
worker.onmessage=({data:d})=>{
  if(d.type==='ready'){manifest=d.manifest;$('model').textContent='Models ready · estimated-pitch fusion bundle';$('microphone').disabled=false;setStatus('Enable microphone to begin.');updateReady();return;}
  if(d.type==='error'){setStatus(`Trial error: ${d.message}`);if(active){active.error=d.message;active.aborted=true;requestFinish();}return;}
  if(!active||active.id!==d.id)return;
  if(d.type==='progress')for(const event of d.events)active.renderedEvents.push({route:event.route,eventIndex:active.renderedEvents.filter(e=>e.route===event.route).length,
    receivedWallMs:wall(),workerDecisionWallMs:event.workerDecisionWallMs});
  if(d.type==='finished'){
    const saved={...active,channelCounts:[...active.channelCounts],report:d.report,pcm:new Float32Array(d.pcm),finishedWallMs:wall()};
    delete saved.timeout;trials.push(saved);const tr=$('history').insertRow();
    const label=saved.target.positions.map(p=>`S${p.string} F${p.fret}`).join(' → ')||'silence';
    for(const value of [trials.length,label,saved.target.kind,saved.blocks,saved.aborted?'incomplete':'saved'])tr.insertCell().textContent=value;
    active=null;lock(false);if($('plan').value!=='manual'){planIndex++;if(planIndex<plan.length)planTarget();}
    updateReady();setStatus(trials.length>=40?'Block full. Export, then clear saved trials.':'Trial saved. Predictions stay hidden; export the ZIP for analysis.');
  }
};
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);}
$('export').onclick=()=>{
  const payload={schema:'live-pipeline-v1',sessionId,createdAt:new Date().toISOString(),userAgent:navigator.userAgent,
    modelManifest:manifest,tuning:openMidi,pageUrl:location.href,
    note:'Paired routes use the same final fusion models. No early actions. Target labels only score outputs. Paired inference adds CPU load. Confidence is diagnostic. This page does not run lesson acceptance.',
    trials:trials.map(({pcm,...t})=>({...t,audioFile:`audio/${t.id}.wav`}))};
  download(trialZip(payload,trials),`live-pipeline-${Date.now()}.zip`);exportedCount=trials.length;
};
$('clear').onclick=()=>{if(exportedCount!==trials.length){setStatus('Export this block before clearing.');return;}if(!confirm('Clear the saved block after checking your downloaded ZIP?'))return;trials=[];exportedCount=0;$('history').replaceChildren();updateReady();setStatus('Saved block cleared. Continue with the next target.');};
window.addEventListener('beforeunload',e=>{if(active||trials.length){e.preventDefault();e.returnValue='';}});
makePlan();devices().catch(()=>{});worker.postMessage({type:'load',baseUrl:new URL('model/fusion3-live',base).href});
