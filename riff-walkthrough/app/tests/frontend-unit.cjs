const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const noop=()=>{};
const node={addEventListener:noop,querySelectorAll:()=>[],querySelector:()=>node,setAttribute:noop,append:noop,textContent:'',hidden:false};
const sandbox={console,location:{origin:'http://127.0.0.1:8768'},btoa:value=>Buffer.from(value,'binary').toString('base64'),CSS:{escape:String},document:{querySelector:()=>node,addEventListener:noop},window:{addEventListener:noop},sessionStorage:{getItem:()=>null,setItem:noop},setTimeout,clearTimeout,setInterval,clearInterval,requestAnimationFrame:()=>1,cancelAnimationFrame:noop,Map,Set,URL,Math,JSON,Number,String,Array,Object,Error,Promise};
let code=fs.readFileSync(require('path').join(__dirname,'../static/app.js'),'utf8');
code=code.replace('  init();\n})();',`  globalThis.test={saveGithub,previousSessionReference,midiText,player,refresh,repeatLabel,phraseMarkup,get(){return {state,connected};},invalidate(version){generationEpoch++;responseSerial++;versionSession=state.session_id;minimumVersion=version;},cancelPoll(){clearTimeout(polling);},stable,readPath,writePath,formatNumber,summaryMarkup,parameterMarkup,resultMarkup,isDirty,formatTime,duration,set(c,s,d){config=c;state=s;drafts=d;connected=true;}};\n})();`);
vm.createContext(sandbox);vm.runInContext(code,sandbox);const t=sandbox.test;
assert.notEqual(t.stable({weights:{a:1}}),t.stable({weights:{a:2}}));
assert.equal(t.stable({b:2,a:{y:3,x:4}}),t.stable({a:{x:4,y:3},b:2}));
const nested={fit:{a:1}};t.writePath(nested,'fit.a',0);assert.equal(t.readPath(nested,'fit.a'),0);
assert.equal(t.formatTime(60.2),'1:00');assert.equal(t.formatNumber(2.333333),'2.333');
assert.equal(t.duration({length_beats:8,tempo:120,notes:[{start_beats:7,duration_beats:2}]}),4.5);
assert.ok(t.summaryMarkup({name:'<script>'}).includes('&lt;script&gt;'));
const config={stages:[{id:'1',defaults:{artist:'all'},parameters:[]},{id:'2',defaults:{weights:{a:1}},parameters:[{key:'weights.a',label:'A',type:'number',default:1,min:0,step:.25}]}]};
const state={version:1,stages:[{id:'1',status:'complete',output:{}},{id:'2',status:'complete',applied:{weights:{a:1}},output:{summary:{score:0},can_export:false}}]};
t.set(config,state,{'1':{artist:'all'},'2':{weights:{a:0}}});
assert.equal(t.isDirty('2'),true);const html=t.parameterMarkup(config.stages[1]);assert.ok(html.includes('value="0"'));assert.ok(html.includes('required'));assert.ok(html.includes('Not applied'));assert.ok(!html.includes(' open>'));
const result=t.resultMarkup(config.stages[1],state.stages[1]);assert.ok(!result.includes('data-save-midi'));
state.stages[1].output.can_export=true;assert.ok(t.resultMarkup(config.stages[1],state.stages[1]).includes('data-save-midi'));
state.stages[1].output={audio:{notes:[],unavailable:'Carry-in notes need mapping'}};assert.ok(t.resultMarkup(config.stages[1],state.stages[1]).includes('Carry-in notes need mapping'));
assert.equal(t.repeatLabel('none among comparable phrases; unknown comparisons: 2'),'');
assert.equal(t.repeatLabel('2; 4; unknown comparisons: 6'),'2, 4');
const phraseHTML=t.phraseMarkup([{phrase:1,length_beats:4,repeat:'2; unknown comparisons: 4',rhythm_repeat:'2'},{phrase:2,length_beats:4,repeat:'1'}],'2');
assert.ok(phraseHTML.includes('Phrases (2)'));assert.ok(phraseHTML.includes('Notes + timing: 2'));assert.ok(phraseHTML.includes('Rhythm: 2'));assert.ok(!phraseHTML.includes('unknown comparisons'));assert.ok(!phraseHTML.includes(' open'));
assert.ok(t.summaryMarkup({Similarity:44.512649}).includes('44.5%'));
const midi=Buffer.from('4d546864000000060000000103c04d54726b0000000400ff2f00','hex');
const beforeCopy=t.stable(t.get().state),exportText=JSON.parse(t.midiText(Uint8Array.from(midi).buffer,2));
assert.equal(exportText.version,2);assert.equal(exportText.filename,'riff-2.mid');assert.equal(exportText.type,'riff-midi');
assert.deepEqual(Buffer.from(exportText.base64,'base64'),midi);assert.equal(t.stable(t.get().state),beforeCopy);
assert.throws(()=>t.midiText(Uint8Array.from([1,2,3]).buffer,2),/not a MIDI/);
const exportState={id:'2',status:'complete',applied:{},output:{can_export:true}};
assert.ok(t.resultMarkup(config.stages[1],exportState).includes('data-save-midi="2"'));
assert.ok(t.resultMarkup(config.stages[1],exportState).includes('data-version="1"'));
console.log('MIDI text checks passed: exact byte roundtrip, captured version, invalid response rejection, no session state changes.');
console.log('Frontend unit checks passed: nested drafts, safe labels, compact phrase topology, export gating, unavailable audio, numeric/time formatting.');
const fixtureRoot=process.env.QA_FIXTURES || require('path').join(__dirname,'../qa');
if (fs.existsSync(fixtureRoot+'/stage12_actual.json') && fs.existsSync(fixtureRoot+'/stage3_contextual.json')) {
const pair=JSON.parse(fs.readFileSync(fixtureRoot+'/stage12_actual.json'));
const rhythm=JSON.parse(fs.readFileSync(fixtureRoot+'/stage3_contextual.json'));
const realConfig={stages:Array.from({length:6},(_,i)=>({id:String(i+1),parameters:[],defaults:{}}))};
const realState={version:4,stages:[pair.seed,pair.scaffold,rhythm].map((output,i)=>({id:String(i+1),status:'complete',applied:{},output}))};
t.set(realConfig,realState,{'1':{},'2':{},'3':{}});
for(let i=0;i<3;i++){
 const html=t.resultMarkup(realConfig.stages[i],realState.stages[i]);
 assert.ok(html.includes('▶ Play'));assert.ok(html.includes('E1'));
 assert.ok(!html.includes('undefined'));assert.ok(!html.includes('NaN'));assert.ok(!html.includes('data-save-midi'));
}
console.log('Actual stage 1–3 artifacts render labels, audio controls and details without undefined/NaN or false MIDI export.');

} else {
 console.log('SKIP actual stage 1–3 artifact rendering: private QA fixtures are not present. Set QA_FIXTURES to their directory to run this check.');
}

(async()=>{
 const requestLog=[];const previous='a'.repeat(32),stored=JSON.stringify({session:previous,drafts:{}});
 sandbox.sessionStorage.getItem=()=>stored;
 t.set({stages:[]},{session_id:'b'.repeat(32),version:1,busy:false,stages:[]},{});
 assert.equal(t.previousSessionReference(),previous);
 sandbox.fetch=async(url,options)=>{requestLog.push({url,options});return {ok:true,json:async()=>({saved:true,version:2,file_url:'https://github.com/mtch777/Guitar-Learning/blob/generated-midi/generated-midi/riff-test.mid',folder_url:'https://github.com/mtch777/Guitar-Learning/tree/generated-midi/generated-midi'})};};
 await t.saveGithub('6',2);
 assert.equal(requestLog[0].url,'http://127.0.0.1:8769/save');assert.equal(requestLog[0].options.credentials,'include');
 assert.deepEqual(JSON.parse(requestLog[0].options.body),{stage:6,version:2});
 await t.saveGithub('6','previous',previous);
 assert.equal(requestLog[1].url,'http://127.0.0.1:8769/recover');assert.deepEqual(JSON.parse(requestLog[1].options.body),{session_id:previous});
 assert.equal(sandbox.sessionStorage.getItem(),stored);assert.equal(t.get().state.version,1);
 assert.ok(requestLog.every(r=>!r.url.includes(previous)&&!r.url.includes('/api/generate')));
 let finishSave;sandbox.fetch=()=>new Promise(resolve=>{finishSave=resolve;});
 t.set({stages:[]},{session_id:'c'.repeat(32),version:3,busy:false,stages:[]},{});
 const delayedSave=t.saveGithub('6',3);
 t.set({stages:[]},{session_id:'d'.repeat(32),version:3,busy:false,stages:[]},{});
 finishSave({ok:true,json:async()=>({saved:true,version:3,file_url:'https://github.com/mtch777/Guitar-Learning/blob/generated-midi/generated-midi/riff-test.mid',folder_url:'https://github.com/mtch777/Guitar-Learning/tree/generated-midi/generated-midi'})});await delayedSave;
 const complete={id:'6',status:'complete',output:{can_export:true}};
 assert.ok(!t.resultMarkup({id:'6'},complete).includes('Saved v3'));
 t.set({stages:[]},{session_id:'c'.repeat(32),version:3,busy:false,stages:[]},{});
 assert.ok(t.resultMarkup({id:'6'},complete).includes('Saved v3'));
 sandbox.sessionStorage.getItem=()=>null;
 console.log('GitHub save checks passed: local-only endpoint, captured version, unchanged generation/session/storage, previous identifier absent from URL.');
 const oscillators=[],envelopes=[];
 const parameter=()=>({value:0,setValueAtTime(v,t){this.events.push([v,t]);},linearRampToValueAtTime(v,t){this.events.push([v,t]);},events:[]});
 class AudioContext {
  constructor(){this.currentTime=0;this.state='running';this.destination={};}
  async resume(){}
  createGain(){const g={gain:parameter(),connect:noop,disconnect:noop};envelopes.push(g.gain);return g;}
  createDynamicsCompressor(){return {threshold:{},ratio:{},connect:noop};}
  createPeriodicWave(real,imag){assert.ok(imag[2]>0);return {};}
  createOscillator(){const o={frequency:{value:0},connect:noop,disconnect:noop,setPeriodicWave:noop,start(t){this.started=t;},stop(t){this.stopped=t;}};oscillators.push(o);return o;}
 }
 sandbox.window.AudioContext=AudioContext;
 const output={audio:{label:'Rhythm · E1',tempo:120,length_beats:.1,notes:[{start_beats:0,duration_beats:.001,midi_pitch:28},{start_beats:0,duration_beats:.05,midi_pitch:28}]}};
 t.set({stages:[{id:'1',defaults:{},parameters:[]}]},{version:1,stages:[{id:'1',status:'complete',output}]},{'1':{}});
 await t.player.play('1');
 assert.equal(oscillators.length,2);assert.ok(Math.abs(oscillators[0].frequency.value-41.2034446)<.00001);
 assert.equal(t.player.nodes.size,2);
 for(const env of envelopes.slice(1)){const times=env.events.map(x=>x[1]);for(let i=1;i<times.length;i++)assert.ok(times[i]>=times[i-1]);}
 t.player.stop();assert.equal(t.player.nodes.size,0);assert.equal(t.player.active,null);
 console.log('Audio scheduling checks passed: harmonic E1, simultaneous notes retained, tiny-note envelopes monotonic, stop clears all voices. This is scheduler QA, not audible-device verification.');
 const pending=[];sandbox.fetch=()=>new Promise(resolve=>pending.push(resolve));
 const reply=value=>({ok:true,json:async()=>value});
 t.set({stages:[]},{session_id:'test',version:1,busy:false,stages:[]},{});
 const oldRequest=t.refresh();
 t.invalidate(2); // The same epoch/version barrier used when a Generate response is accepted.
 const newRequest=t.refresh();
 pending[1](reply({session_id:'test',version:2,busy:false,stages:[]}));await newRequest;
 pending[0](reply({session_id:'test',version:1,busy:false,stages:[]}));await oldRequest;
 assert.equal(t.get().state.version,2);
 const olderSameVersion=t.refresh(),newerSameVersion=t.refresh();
 pending[3](reply({session_id:'test',version:2,busy:false,stages:[],marker:'new'}));await newerSameVersion;
 pending[2](reply({session_id:'test',version:2,busy:false,stages:[],marker:'old'}));await olderSameVersion;
 assert.equal(t.get().state.marker,'new');
 const backward=t.refresh();pending[4](reply({session_id:'test',version:1,busy:false,stages:[]}));await backward;t.cancelPoll();assert.equal(t.get().state.version,2);
 console.log('Refresh race checks passed: delayed pre-generation response rejected; later request wins at same version; lower versions cannot restore stale results.');

})().catch(e=>{console.error(e);process.exitCode=1;});
