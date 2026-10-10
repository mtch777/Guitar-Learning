const AT='https://cdn.jsdelivr.net/npm/@coderline/alphatab@1.8.4/dist/';
const songs=['Cloud Cascade (Tuned Down).gp','Nocturne_ Lost Faith (Tuned Down).gp','Immolation of Night (Tuned Down).gp'];
const $=id=>document.getElementById(id);
const bytes=new Map();let cases=[],filtered=[],position=0,api=null,score=null,loadedSong=null,ready=false,playerIsPlaying=false,loadToken=0,notesTimer=null;
const STORAGE='composition-lab-reviews-v1';
const reviews=(()=>{try{return JSON.parse(localStorage.getItem(STORAGE))||{}}catch{return {}}})();
function save(){try{localStorage.setItem(STORAGE,JSON.stringify(reviews))}catch(e){$('savedLabel').textContent='Browser storage unavailable; export your feedback to preserve it.'}}
function status(s){$('playerStatus').textContent=s}
function songStatus(){const missing=songs.filter(s=>!bytes.has(s));$('fileStatus').textContent=missing.length?'Missing '+missing.length+' file(s)':'✓ All three songs ready'}
function idb(){return new Promise((res,rej)=>{if(!window.indexedDB){rej(Error('IndexedDB unavailable'));return}const r=indexedDB.open('composition-lab-gp',1);r.onupgradeneeded=()=>r.result.createObjectStore('files');r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)})}
async function dbGet(key){const db=await idb();return new Promise((res,rej)=>{const tx=db.transaction('files','readonly');const r=tx.objectStore('files').get(key);r.onsuccess=()=>{db.close();res(r.result)};r.onerror=()=>{db.close();rej(r.error)}})}
async function dbPut(key,value){const db=await idb();return new Promise((res,rej)=>{const tx=db.transaction('files','readwrite');tx.objectStore('files').put(value,key);tx.oncomplete=()=>{db.close();res()};tx.onerror=()=>{db.close();rej(tx.error)}})}
async function dbClear(){const db=await idb();return new Promise((res,rej)=>{const tx=db.transaction('files','readwrite');tx.objectStore('files').clear();tx.oncomplete=()=>{db.close();res()};tx.onerror=()=>{db.close();rej(tx.error)}})}
async function loadFile(song,file){if(!file)return;const data=await file.arrayBuffer();bytes.set(song,data);songStatus();try{await dbPut(song,data)}catch{}if(current()?.song===song)await openSong(song)}
function current(){return filtered[position]}
function reviewFor(c){return reviews[c.id]||{}}
function isReviewed(c){return ['confirmed','rejected','uncertain'].includes(reviewFor(c).label)}
function render(){const c=current();if(!c)return;const kind={motif:'Riff comparison',section_boundary:'Section boundary',chord:'Chord guess'};
 $('count').textContent=`${position+1} / ${filtered.length}`;$('example').value=String(c.id);
 $('heading').textContent=`${kind[c.kind]} · ${c.song.replace(/ \(Tuned Down\)\.gp/,'')}`;
 const bars=c.length||((c.kind==='section_boundary')?4:1);
 $('claim').textContent=c.kind==='motif'?`Does ${c.track} play a related riff at measures ${c.a}–${c.a+bars-1} and ${c.b}–${c.b+bars-1}?`:c.kind==='section_boundary'?`Is measure ${c.a} the start of a noticeably new musical section?`:`Does “${c.hypothesis}” describe the harmony around measure ${c.a}?`;
 $('reviewPrompt').textContent=c.kind==='motif'?'Compare the musical shape, rhythm, and feel of A vs B.':c.kind==='section_boundary'?'Play a few measures before and after the suggested change.':`Listen to the full arrangement; this is only a candidate chord, not a confirmed transcription.`;
 $('evidence').textContent=c.kind==='motif'?`Algorithm distance: ${c.evidence.distance}; pitch shift: ${c.evidence.pitch_shift} semitones.`:c.kind==='section_boundary'?`Novelty score: ${c.evidence.novelty}.`:`Other guesses: ${(c.evidence.alternatives||[]).map(v=>v.name).join(', ')}.`;
 $('playB').disabled=c.kind==='chord';$('playB').textContent=c.kind==='motif'?'▶ Play B':'▶ Play after';$('playA').textContent=c.kind==='motif'?'▶ Play A':c.kind==='section_boundary'?'▶ Play before':'▶ Play chord';
 $('rangeLabels').textContent=c.kind==='motif'?`A: measures ${c.a}–${c.a+bars-1} · B: ${c.b}–${c.b+bars-1}`:c.kind==='section_boundary'?`A: ${Math.max(1,c.a-4)}–${c.a-1} · B: ${c.a}–${c.a+3}`:`Measure ${c.a} (all instruments recommended)`;
 const rev=reviewFor(c);$('notes').value=rev.notes||'';$('savedLabel').textContent=rev.label?`Saved: ${rev.label}`:'Not reviewed';document.querySelectorAll('[data-label]').forEach(b=>b.classList.toggle('selected',b.dataset.label===rev.label));
 const done=cases.filter(isReviewed).length;$('progress').value=done;$('progressLabel').textContent=`${done} of ${cases.length} reviewed · ${cases.length-done} remaining`;
 $('prev').disabled=position===0;$('next').disabled=position===filtered.length-1;
 if(bytes.has(c.song)){openSong(c.song).catch(e=>status('Load failed: '+e.message))}else{status('Load the original .gp song above');$('tab').textContent='Load this song to view its tab.'}
}
function setFilter(){const kind=$('filter').value;const old=current()?.id;filtered=cases.filter(c=>kind==='all'||c.kind===kind);position=Math.max(0,filtered.findIndex(c=>c.id===old));$('example').replaceChildren(...filtered.map(c=>{const o=document.createElement('option');o.value=c.id;o.textContent=`#${c.id} · ${c.song.split(' (')[0]} · ${c.kind} · bar ${c.a}${isReviewed(c)?' ✓':''}`;return o}));render()}
function barRange(c,side){if(c.kind==='motif'){const start=side==='a'?c.a:c.b;return [start,start+(c.length||2)]}if(c.kind==='section_boundary'){return side==='a'?[Math.max(1,c.a-4),c.a]:[c.a,c.a+4]}return [c.a,c.a+1]}
function findTrack(){const c=current();let chosen=score?.tracks.find(t=>t.name===c.track);if(!chosen&&c.kind==='motif')chosen=score?.tracks.find(t=>t.name?.trim()===c.track?.trim());return chosen||score?.tracks.find(t=>t.staves?.[0]?.stringTuning?.tunings?.length)||score?.tracks[0]}
function applyVisibleTracks(){if(!score||!api)return;const target=findTrack();const all=$('partOptions').value==='all'||current().kind==='chord';api.renderTracks(all?score.tracks:[target]);return target}
async function ensureApi(){if(api)return;status('Loading alphaTab…');await new Promise((resolve,reject)=>{if(window.alphaTab){resolve();return}const script=document.createElement('script');script.src=AT+'alphaTab.min.js';script.onload=resolve;script.onerror=()=>reject(Error('alphaTab CDN unavailable'));document.head.append(script)});api=new window.alphaTab.AlphaTabApi($('tab'),{core:{scriptFile:AT+'alphaTab.min.js',fontDirectory:AT+'font/'},display:{scale:0.8},player:{playerMode:'enabledSynthesizer',outputMode:'webAudioScriptProcessor',soundFont:AT+'soundfont/sonivox.sf2',enableCursor:true,enableElementHighlighting:true,scrollMode:'off'}});
 api.scoreLoaded.on(s=>{score=s;applyVisibleTracks();ready=false;status('Tab loaded; preparing playback…')});api.playerReady.on(()=>{ready=true;status('Ready — press Play A or B')});api.playerStateChanged.on(e=>{playerIsPlaying=e.state===1});api.error.on(e=>status('alphaTab error: '+(e.message||e)));
}
async function openSong(name){if(!bytes.has(name))return;await ensureApi();if(loadedSong===name&&score)return;loadedSong=name;ready=false;score=null;api.stop();status('Loading '+name+'…');api.load(bytes.get(name).slice(0));}
function playPart(side){const c=current();if(!c||!score||!api||!ready){status('Wait for song playback to become ready');return}
 const [a,b]=barRange(c,side);const master=score.masterBars;const begin=master?.[a-1],last=master?.[Math.min(b-1,master.length-1)];if(!begin||!last){status('Measures not found in file');return}
 const start=Number(begin.start),end=Number(last.start)+Number(last.calculateDuration?.()||last.duration||0);
 // Prefer next bar's start to avoid depending on master bar duration APIs.
 const next=master[b];const endTick=next?Number(next.start):end;
 if(!Number.isFinite(start)||!Number.isFinite(endTick)||endTick<=start){status('Invalid excerpt timing');return}
 applyVisibleTracks();api.stop();api.playbackSpeed=Number($('speed').value);api.playbackRange={startTick:start,endTick:endTick};api.tickPosition=start;api.play();status(`Playing ${side.toUpperCase()} · bars ${a}–${Math.min(b-1,master.length)}`);
}
function setReview(label){const c=current();if(!c)return;reviews[c.id]={...reviewFor(c),label,notes:$('notes').value,updatedAt:new Date().toISOString()};save();setFilter();}
function download(){const data={format:'composition-lab-review-v1',exportedAt:new Date().toISOString(),totalExamples:cases.length,reviews:Object.entries(reviews).map(([id,v])=>({id:Number(id),...v}))};const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='composition_review_feedback.json';a.click();URL.revokeObjectURL(url)}
async function boot(){cases=await fetch('./cases.json').then(r=>{if(!r.ok)throw Error('Cases JSON not found');return r.json()});$('progress').max=cases.length;
 for(const song of songs){const box=document.createElement('div');box.className='slot';const title=document.createElement('strong');title.textContent=song.replace('.gp','');const input=document.createElement('input');input.type='file';input.accept='.gp';input.setAttribute('aria-label','Load '+song);input.onchange=async()=>{try{await loadFile(song,input.files[0])}catch(e){status(e.message)}};box.append(title,input);$('files').append(box);try{const data=await dbGet(song);if(data)bytes.set(song,data)}catch{}}
 songStatus();$('filter').onchange=setFilter;$('example').onchange=e=>{position=filtered.findIndex(c=>c.id===Number(e.target.value));render()};
 $('playA').onclick=()=>playPart('a');$('playB').onclick=()=>playPart('b');$('pause').onclick=()=>{api?.pause();status('Paused')};$('stop').onclick=()=>{api?.stop();status('Stopped')};
 $('partOptions').onchange=()=>{if(api&&score){api.stop();applyVisibleTracks()}};$('speed').onchange=()=>{if(api)api.playbackSpeed=Number($('speed').value)};
 $('prev').onclick=()=>{if(position>0){position--;render()}};$('next').onclick=()=>{if(position<filtered.length-1){position++;render()}};
 document.querySelectorAll('[data-label]').forEach(b=>b.onclick=()=>setReview(b.dataset.label));$('clearReview').onclick=()=>{const c=current();delete reviews[c.id];save();setFilter()};
 $('notes').oninput=()=>{clearTimeout(notesTimer);notesTimer=setTimeout(()=>{const c=current();reviews[c.id]={...reviewFor(c),notes:$('notes').value,updatedAt:new Date().toISOString()};save()},350)};
 $('export').onclick=download;$('forgetFiles').onclick=async()=>{bytes.clear();loadedSong=null;score=null;api?.stop();try{await dbClear()}catch{}songStatus();status('Local files cleared');$('tab').textContent='Load a song to display its tab.'};setFilter();}
boot().catch(e=>status('Setup failed: '+e.message));