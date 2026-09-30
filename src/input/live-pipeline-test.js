import { measure, summarize, percentile, assess, calibrationVerdict, calibrationSteps } from './gain-calibration.js';
import { trialZip } from './trial-archive.js';
const $=id=>document.getElementById(id),base=new URL(import.meta.env.BASE_URL,location.origin);
const worker=new Worker(new URL('./live-pipeline-worker.js',import.meta.url),{type:'module'});
const openMidi=[27,34,39,44,49,54,58,63],sessionId=crypto.randomUUID();
for(const id of ['string','string2'])for(let s=1;s<=8;s++)$(id).add(new Option(String(s),String(s)));
let manifest,context,stream,source,capture,sink,active=null,trials=[],plan=[],planIndex=0,exportedCount=0,channelAvailable=false;
let gainReference=null,calibration=null,calibrationRun=null,calibrationHistory=[],recentLevels=[],lastFeedbackAt=0;
fetch(new URL('model/gain-reference.json',base)).then(r=>{if(!r.ok)throw Error('Reference unavailable');return r.json();}).then(r=>gainReference=r).catch(()=>{$('calibrationPrompt').textContent='Training level reference unavailable; headroom/noise calibration still works.';});
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
  $('calibrationExport').disabled=!!active||!!calibrationRun||!calibrationHistory.length;
  $('calibrate').disabled=!stream||!channelAvailable||!!active||!!calibrationRun;
  $('calibrationMeasure').disabled=!stream||!channelAvailable||!!active||!!calibrationRun||!calibration||calibration.step>=calibrationSteps.length;
  $('microphone').disabled=!!active||!!calibrationRun||!manifest;
  $('record').disabled=!stream||!channelAvailable||!manifest||!!active||!!calibrationRun||trials.length>=40||($('plan').value!=='manual'&&planIndex>=plan.length);
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
  invalidateCalibration();
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
      if(d.type==='channel-error'){invalidateCalibration();channelAvailable=false;updateReady();$('levels').textContent=`Only ${d.channels} input channel(s). Choose channel 1.`;if(active){active.aborted=true;requestFinish();}return;}
      channelAvailable=true;updateReady();
      $('levels').textContent=`${context?.sampleRate} Hz · `+d.levels.map((l,i)=>`Ch ${i+1}: ${l.rms>0?(20*Math.log10(l.rms)).toFixed(1):'−∞'} dBFS${l.peak>=.999?' · POSSIBLE CLIPPING':''}`).join(' | ');
      observeGain(new Float32Array(d.samples),d.audioTime);
      if(!active||active.finishRequested)return;
      active.blocks++;active.channelCounts.add(d.channels);
      worker.postMessage({type:'frame',id:active.id,samples:d.samples,sequence:d.sequence,audioTime:d.audioTime,receivedWallMs:wall()},[d.samples]);
      if(active.blocks*4096>=active.sampleRate*active.seconds)requestFinish();
    };
    $('microphone').textContent='Disable microphone';await devices();setStatus('Ready. Verify the selected channel responds to your guitar.');updateReady();
  }catch(e){await stop();setStatus(`Input error: ${e.message}`);}
};
$('channel').onchange=()=>{invalidateCalibration();channelAvailable=false;updateReady();capture?.port.postMessage({type:'channel',channel:Number($('channel').value)});};
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
      gainCalibration:calibration?structuredClone(calibration):null,
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
function invalidateCalibration(){
  if(calibrationRun)clearTimeout(calibrationRun.timeout);
  if(calibration)calibration.invalidatedAt=new Date().toISOString();
  calibrationRun=null;calibration=null;recentLevels=[];
  $('calibrationPrompt').textContent='Click “Enable microphone” if input is off, then click “Start / restart calibration”.';
  $('gainFeedback').textContent='No current gain calibration.';lock(false);
}
function calibrationPrompt(){
 const step=calibrationSteps[calibration.step];
 if(!step){$('calibrationPrompt').textContent=`Calibration finished. ${calibration.verdict} If you change the Focusrite gain, click “Start / restart calibration” and repeat the recordings.`;return;}
 const instruction=step.kind==='silence'
  ? 'Mute all strings. Click “Measure next step” to record 3 seconds of silence.'
  : `Prepare string ${step.string}, open (no fret), with a ${step.attack} pick. Click “Measure next step”. Do not play until this line says PLAY NOW.`;
 $('calibrationPrompt').textContent=`${calibration.step?'Previous recording finished. ':''}Recording ${calibration.step+1} of ${calibrationSteps.length}: ${instruction}`;
}
$('calibrate').onclick=()=>{
 calibration={id:crypto.randomUUID(),startedAt:new Date().toISOString(),channel:Number($('channel').value)+1,deviceSettings:stream.getAudioTracks()[0].getSettings(),sampleRate:context.sampleRate,step:0,noiseDb:null,notes:[],complete:false,thresholds:{minimumHeadroomDb:3,minimumNoiseMarginDb:20,onsetRmsDb:-48},audioCorrection:'none'};
 calibrationHistory.push(calibration);calibrationPrompt();updateReady();
};
$('calibrationMeasure').onclick=()=>{
 const step=calibrationSteps[calibration.step];
 calibrationRun={step,blocks:[],startAudioTime:null};lock(true);updateReady();
 $('calibrationPrompt').textContent=step.kind==='silence'?'RECORDING SILENCE — keep all strings muted.':'GET READY — do not play yet.';
 calibrationRun.timeout=setTimeout(()=>{calibrationRun=null;lock(false);updateReady();$('calibrationPrompt').textContent='No complete audio recording arrived. Check the input meter, then click “Measure next step” to try this recording again.';},8000);
};
function observeGain(samples,audioTime){
 const reading=measure(samples),now=wall();recentLevels.push(reading);if(recentLevels.length>12)recentLevels.shift();
 if(now-lastFeedbackAt>400){
  lastFeedbackAt=now;const r=summarize(recentLevels,calibration?.noiseDb??null);
  $('gainMetrics').textContent=`Recent peak ${r.peakDb.toFixed(1)} dBFS · strongest block RMS ${r.loudestBlockRmsDb.toFixed(1)} dBFS`+(r.noiseMarginDb===null?'':` · noise margin ${r.noiseMarginDb.toFixed(1)} dB`);
  if(r.peakDb>-55&&(!calibration||calibration.complete||active))$('gainFeedback').textContent=assess(r,calibration?.noiseDb??null);
 }
 if(!calibrationRun)return;
 const run=calibrationRun;run.startAudioTime??=audioTime;const elapsed=audioTime-run.startAudioTime;
 // Ignore initial half-second for pick cues. Silence uses every full block.
 if(run.step.kind==='note'&&elapsed>=.5)$('calibrationPrompt').textContent=`PLAY NOW — pluck string ${run.step.string} once, open (no fret), with a ${run.step.attack} pick. Let it ring.`;
 if(run.step.kind==='silence'||elapsed>=.5)run.blocks.push(reading);
 if(elapsed<3)return;
 clearTimeout(run.timeout);
 if(run.step.kind==='silence'){
  calibration.noiseDb=percentile(run.blocks.map(b=>b.rmsDb),.9);
  $('gainFeedback').textContent=`Silence floor ${calibration.noiseDb.toFixed(1)} dBFS. Keep gain fixed for the picks.`;
 }else{
  const result={...run.step,...summarize(run.blocks,calibration.noiseDb)};
  const ref=gainReference?.positions[`${result.string}:0:${result.attack}`];
  result.referencePeakDb=ref?.peakDb??null;result.referencePeakDifferenceDb=ref?result.peakDb-ref.peakDb:null;
  calibration.notes.push(result);$('gainFeedback').textContent=assess(result,calibration.noiseDb)+(ref?` Peak is ${Math.abs(result.referencePeakDifferenceDb).toFixed(1)} dB ${result.referencePeakDifferenceDb>=0?'above':'below'} this recorded example (level only).`:' No matching training example.');
 }
 calibration.step++;calibrationRun=null;lock(false);
 if(calibration.step===calibrationSteps.length){calibration.complete=true;calibration.finishedAt=new Date().toISOString();calibration.verdict=calibrationVerdict(calibration.notes);$('gainFeedback').textContent=calibration.verdict;}
 calibrationPrompt();updateReady();
}
$('calibrationExport').onclick=()=>download(new Blob([JSON.stringify({schema:'gain-calibration-v1',sessionId,calibrations:calibrationHistory,reference:gainReference,createdAt:new Date().toISOString()},null,2)],{type:'application/json'}),`gain-calibration-${Date.now()}.json`);
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);}
$('export').onclick=()=>{
  const payload={schema:'live-pipeline-v1',sessionId,createdAt:new Date().toISOString(),userAgent:navigator.userAgent,
    modelManifest:manifest,tuning:openMidi,pageUrl:location.href,
    gainCalibrations:calibrationHistory,activeGainCalibration:calibration,gainReference:gainReference?{schema:gainReference.schema,datasetSha256:gainReference.datasetSha256,count:gainReference.count}:null,
    note:'Paired routes use the same final fusion models. No early actions. Target labels only score outputs. Paired inference adds CPU load. Confidence is diagnostic. This page does not run lesson acceptance.',
    trials:trials.map(({pcm,...t})=>({...t,audioFile:`audio/${t.id}.wav`}))};
  download(trialZip(payload,trials),`live-pipeline-${Date.now()}.zip`);exportedCount=trials.length;
};
$('clear').onclick=()=>{if(exportedCount!==trials.length){setStatus('Export this block before clearing.');return;}if(!confirm('Clear the saved block after checking your downloaded ZIP?'))return;trials=[];exportedCount=0;$('history').replaceChildren();updateReady();setStatus('Saved block cleared. Continue with the next target.');};
window.addEventListener('beforeunload',e=>{if(active||trials.length){e.preventDefault();e.returnValue='';}});
makePlan();devices().catch(()=>{});worker.postMessage({type:'load',baseUrl:new URL('model/fusion3-live',base).href});
