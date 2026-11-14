const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const noop=()=>{},node={addEventListener:noop,querySelectorAll:()=>[],querySelector:()=>node,setAttribute:noop,append:noop,textContent:'',hidden:false};
const sandbox={console,location:{origin:'http://127.0.0.1:8768'},CSS:{escape:String},document:{querySelector:()=>node,addEventListener:noop},window:{addEventListener:noop},sessionStorage:{getItem:()=>null,setItem(){throw Error('No storage writes');}},setTimeout:()=>1,clearTimeout:noop,setInterval:()=>1,clearInterval:noop,requestAnimationFrame:()=>1,cancelAnimationFrame:noop,Map,Set,URL,Math,JSON,Number,String,Array,Object,Error,Promise};
let code=fs.readFileSync(require('path').join(__dirname,'../static/app.js'),'utf8');
code=code.replace('  init();\n})();',`  globalThis.test={selectedViews,openKontaktChooser,cancelKontaktChooser,confirmKontaktChooser,resultMarkup,Timeline,kontaktPlayer,startKontakt,pollKontakt,currentKontakt,kontaktCapture,kontaktControls,kontaktSettingsMarkup,loadKontaktPresets,setKontaktSetting,set(s){config={stages:[]};state=s;connected=true;editor={key:editorKey(),revision:2,output:s.stages[5].output,selected:[],busy:false};},selection(id,list){stageSelections.set(id,{key:selectionKey(id),selected:list,context:{phrases:state.stages[Number(id)-1].output.phrases}});},timeline(id,t){timelines.set(id,t);},get(){return state;}};\n})();`);
vm.createContext(sandbox);vm.runInContext(code,sandbox);const t=sandbox.test;
const audio={tempo:120,length_beats:8,label:'Reference rhythm Â· E1',notes:[{start_beats:0,duration_beats:1,midi_pitch:28}]};
const state={session_id:'a'.repeat(32),version:7,busy:false,stages:Array.from({length:6},(_,i)=>({id:String(i+1),status:'complete',output:{audio,phrases:[{phrase:1,start_beats:0,length_beats:4},{phrase:2,start_beats:4,length_beats:4}]}}))};
const snapshot=JSON.stringify(state),calls=[];let jobCount=0;
function response(data,ok=true){return {ok,json:async()=>data};}
function ready(capture,job_id='job'+(++jobCount)){return {job_id,status:'ready',capture:{...capture,tempo:120,length_beats:capture.view==='previous'?10:8},audio_url:'/render/audio?job='+job_id,duration_seconds:capture.view==='previous'?7:6,sample_rate:44100,waveform:[[-.1,.1],[-.2,.2],[-.3,.3],[-.4,.4]]};}
(async()=>{
 t.set(state);sandbox.fetch=async(url,options)=>{calls.push({url,options});return response({presets:[{id:'modern-metal-1',label:'Modern Metal 1'},{id:'ready-to-djent',label:'Ready to Djent'},{id:'fake',label:'Not verified'}]});};
 await t.loadKontaktPresets();assert.ok(!t.kontaktControls('1').includes('Not verified'));
 sandbox.fetch=async(url,options)=>{const body=JSON.parse(options.body);calls.push({url,options,body});return response(ready(body));};
 const beforeConfirm=calls.length;t.openKontaktChooser('1');assert.equal(calls.length,beforeConfirm);await t.confirmKontaktChooser('1');assert.equal(calls.length,beforeConfirm+1);assert.equal(t.currentKontakt('1').status,'ready');assert.ok(!t.kontaktControls('1').includes('data-kontakt-confirm'));
 for(let i=1;i<=6;i++){await t.startKontakt(String(i));assert.equal(t.currentKontakt(String(i)).status,'ready');assert.equal(calls.at(-1).body.stage,i);assert.equal(calls.at(-1).body.editor_revision,i===6?2:null);assert.equal(calls.at(-1).body.selected,null);assert.equal(calls.at(-1).options.credentials,'include');}
 const beforeChooser=calls.length;t.openKontaktChooser('1');assert.ok(!t.kontaktControls('1').includes('data-kontakt-confirm'));assert.equal(calls.length,beforeChooser);t.cancelKontaktChooser();assert.ok(!t.kontaktControls('1').includes('data-kontakt-confirm'));assert.equal(calls.length,beforeChooser);
 const cachedCalls=calls.length;await t.startKontakt('1');assert.equal(calls.length,cachedCalls);
 t.selection('2',[2]);t.setKontaktSetting('2','scope','selected');await t.startKontakt('2');assert.deepEqual(calls.at(-1).body.selected,[2]);assert.equal(t.currentKontakt('2').result.capture.length_beats,8);t.openKontaktChooser('2');assert.equal(t.kontaktSettingsMarkup(),'');t.cancelKontaktChooser();
 assert.equal(JSON.stringify(state),snapshot);assert.ok(calls.every(c=>!c.url.includes('generate')&&!c.url.includes(state.session_id)));
 const entry=t.currentKontakt('1'),events={},element={currentTime:1.25,paused:false,ended:false,addEventListener(name,fn){events[name]=fn;},pause(){this.paused=true;events.pause?.();}};let beat;
 t.timeline('1',{progress(n){beat=n;},draw:noop,cursor:null});t.kontaktPlayer.bind(element,'1',entry);assert.equal(t.kontaktPlayer.active,null);events.play();assert.equal(beat,2.5);assert.equal(t.kontaktPlayer.active.element,element);t.kontaktPlayer.stop();assert.equal(element.paused,true);
 const moves=[],ctx={setTransform:noop,clearRect:noop,fillRect:noop,beginPath:noop,moveTo(x,y){moves.push([x,y]);},lineTo:noop,stroke:noop};
 t.Timeline.prototype.drawWaveform.call({waveCanvas:{getContext:()=>ctx},rendered:entry.result,width:300,dpr:1,scale:25,scroller:{scrollLeft:50},cursor:4});assert.ok(moves.some(v=>v[0]===62.5));assert.ok(moves.some(v=>v[0]===50));
 // Previous renders bind each actual previous snapshot, never current or editor output.
 const previousState=JSON.parse(JSON.stringify(state));for(const stage of previousState.stages)stage.previous={output:{audio:{...audio,length_beats:10,notes:[{start_beats:1,duration_beats:2,midi_pitch:60}]},phrases:[]}};
 t.set(previousState);sandbox.fetch=async(url,options)=>{const body=JSON.parse(options.body);calls.push({url,options,body});return response(ready(body));};
 for(let i=1;i<=6;i++){const id=String(i);t.selectedViews[id]='previous';await t.startKontakt(id);const entry=t.currentKontakt(id);assert.equal(entry.status,'ready');assert.equal(entry.length_beats,10);assert.equal(entry.capture.view,'previous');assert.equal(entry.capture.editor_revision,null);assert.equal(entry.capture.selected,null);t.openKontaktChooser(id);assert.equal(t.kontaktControls(id).includes('<select'),id==='6');t.cancelKontaktChooser();const html=t.resultMarkup({id},previousState.stages[i-1]);assert.equal(html.includes('Render in Kontakt'),i>2);assert.ok(html.includes('Previous'));}
 for(let i=1;i<=6;i++)delete t.selectedViews[String(i)];t.set(state);
 // Stale job response cannot attach to another preset/source.
 t.setKontaktSetting('3','preset','ready-to-djent');let finish;sandbox.fetch=()=>new Promise(resolve=>{finish=resolve;});const pending=t.startKontakt('3');const capture={...t.kontaktCapture('3')};t.set({...state,version:8});finish(response(ready(capture)));await pending;assert.equal(t.currentKontakt('3'),undefined);
 // Confirming after the source changed cannot render a different snapshot.
 t.openKontaktChooser('4');const beforeStale=calls.length;t.set({...state,version:9});await t.confirmKontaktChooser('4');assert.equal(calls.length,beforeStale);t.set({...state,version:8});
 // Malformed waveform and mismatched source are rejected, never exposed as ready.
 sandbox.fetch=async(url,options)=>{const body=JSON.parse(options.body);const result=ready(body);result.waveform=[[NaN,1]];return response(result);};await t.startKontakt('4');assert.equal(t.currentKontakt('4').status,'failed');
 sandbox.fetch=async(url,options)=>{const body=JSON.parse(options.body);const result=ready(body);result.capture.version=999;return response(result);};await t.startKontakt('5');assert.equal(t.currentKontakt('5').status,'failed');
 // Queued/running jobs poll status without reissuing start or generation.
 let queuedCapture;const jobCalls=[];
 sandbox.fetch=async(url,options)=>{const body=JSON.parse(options.body);jobCalls.push({url,body});if(url.endsWith('/start')){queuedCapture=body;return response({job_id:'queued-job',status:'queued',capture:{...body,tempo:120,length_beats:8}});}return response(ready(queuedCapture,'queued-job'));};
 await t.startKontakt('1');assert.equal(t.currentKontakt('1').status,'queued');assert.ok(t.kontaktControls('1').includes('Queued'));
 await t.pollKontakt('1',t.currentKontakt('1'));assert.equal(t.currentKontakt('1').status,'ready');assert.deepEqual(jobCalls.at(-1).body,{job_id:'queued-job'});assert.equal(jobCalls.filter(c=>c.url.endsWith('/start')).length,1);
 console.log('Kontakt UI PASS: verified presets, all six immutable captures, selected keep-timeline scope, cache/stale isolation, waveform beat+scroll mapping, native playhead, no autoplay/generation/session mutation.');
})().catch(e=>{console.error(e);process.exitCode=1;});
