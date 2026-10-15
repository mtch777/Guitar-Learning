// Riff comparison listening review. Independent of trainer and audio-analysis code.
const AT = 'https://cdn.jsdelivr.net/npm/@coderline/alphatab@1.8.4/dist/';
const songs = ['Cloud Cascade (Tuned Down).gp','Nocturne_ Lost Faith (Tuned Down).gp','Immolation of Night (Tuned Down).gp'];
const $ = id => document.getElementById(id);
const bytes = new Map();
const STORAGE = 'composition-lab-reviews-v1';
const reviews = (() => { try { return JSON.parse(localStorage.getItem(STORAGE)) || {}; } catch { return {}; } })();
let cases = [], currentIndex = 0, api = null, score = null, loadedSong = null, ready = false;
let loading = null, activeTrack = null, commentsTimer = null;
const current = () => cases[currentIndex];
const currentReview = () => reviews[current()?.id] || {};
const reviewed = c => ['confirmed','rejected','uncertain'].includes(reviews[c.id]?.label);
const updateStatus = value => { $('status').textContent = value; };
function saveReviews() {
  try { localStorage.setItem(STORAGE, JSON.stringify(reviews)); }
  catch { updateStatus('Could not save in this browser. Export your feedback.'); }
}
function dbOpen() {
  return new Promise((resolve, reject) => {
    if (!window.indexedDB) return reject(new Error('Browser file storage not available'));
    const request = indexedDB.open('composition-lab-gp', 1);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains('files')) request.result.createObjectStore('files');
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
async function dbOperation(mode, action) {
  const db = await dbOpen();
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction('files', mode);
      const request = action(tx.objectStore('files'));
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  } finally { db.close(); }
}
const dbGet = name => dbOperation('readonly', store => store.get(name));
const dbPut = (name, data) => dbOperation('readwrite', store => store.put(data, name));
function updateFiles() {
  const available = songs.filter(name => bytes.has(name)).length;
  $('fileStatus').textContent = available + ' of 3 loaded';
  $('fileStatus').classList.toggle('missing', available !== 3);
}
async function ensureApi() {
  if (api) return api;
  if (loading) return loading;
  loading = (async () => {
    updateStatus('Loading guitar playback engine...');
    if (!window.alphaTab) {
      await new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = AT + 'alphaTab.min.js';
        script.onload = resolve;
        script.onerror = () => reject(new Error('alphaTab could not be loaded'));
        document.head.appendChild(script);
      });
    }
    const engine = new window.alphaTab.AlphaTabApi($('tab'), {
      core: { scriptFile: AT+'alphaTab.min.js', fontDirectory: AT+'font/' },
      display: { scale: .8 },
      player: {
        playerMode: 'enabledSynthesizer',
        outputMode: 'webAudioScriptProcessor',
        soundFont: AT+'soundfont/sonivox.sf2',
        enableCursor: true,
        enableElementHighlighting: true,
        scrollMode: 'off'
      }
    });
    api = engine;
    engine.scoreLoaded.on(result => {
      score = result;
      ready = false;
      try { selectOnlyComparedTrack(); }
      catch (error) { updateStatus(error.message); return; }
      updateStatus('Preparing playback...');
    });
    engine.playerReady.on(() => { ready = true; updateStatus('Ready. Play A or B.'); });
    engine.error.on(error => { ready = false; updateStatus('Player error: '+(error?.message || String(error))); });
    return engine;
  })();
  try { return await loading; }
  finally { loading = null; }
}
function selectOnlyComparedTrack() {
  if (!score || !api || !current()) return;
  const targetName = current().track.trim();
  const track = score.tracks.find(t => t.name?.trim() === targetName);
  if (!track) {
    activeTrack = null;
    throw new Error('Cannot find exact instrument "'+targetName+'". Playback blocked to avoid playing the wrong part.');
  }
  // renderTracks is only a rendering operation. Explicit synth mute+solo is essential.
  const others = score.tracks.filter(t => t !== track);
  api.stop();
  api.renderTracks([track]);
  api.changeTrackSolo(score.tracks, false);
  api.changeTrackMute(score.tracks, true);
  api.changeTrackMute([track], false);
  api.changeTrackSolo([track], true);
  activeTrack = track;
}
async function openCurrentSong() {
  const c = current();
  if (!c) return;
  if (!bytes.has(c.song)) {
    ready = false;
    updateStatus('Load "'+c.song+'" above to listen.');
    return;
  }
  await ensureApi();
  if (loadedSong === c.song && score) {
    selectOnlyComparedTrack();
    return;
  }
  loadedSong = c.song;
  score = null; ready = false; activeTrack = null;
  api.stop();
  updateStatus('Loading '+c.song+'...');
  api.load(bytes.get(c.song).slice(0));
}
function render() {
  const c = current();
  if (!c) { updateStatus('No riff comparisons found.'); return; }
  const span = c.length || 2;
  $('counter').textContent = 'Riff '+(currentIndex+1)+' of '+cases.length;
  $('location').textContent = c.song.replace('.gp','')+' · '+c.track;
  $('aLabel').textContent = 'Measures '+c.a+'–'+(c.a+span-1);
  $('bLabel').textContent = 'Measures '+c.b+'–'+(c.b+span-1);
  const done = cases.filter(reviewed).length;
  $('progress').value = done;
  $('progress').max = cases.length;
  $('reviewed').textContent = done+' of '+cases.length+' reviewed';
  $('prev').disabled = currentIndex === 0;
  $('next').disabled = currentIndex === cases.length-1;
  const answer = currentReview();
  $('notes').value = answer.notes || '';
  $('saved').textContent = answer.label ? 'Your answer is saved: '+answer.label : 'Not answered yet';
  document.querySelectorAll('[data-label]').forEach(btn =>
    btn.classList.toggle('selected', btn.dataset.label === answer.label));
  if (api) { api.stop(); api.playbackRange = null; }
  openCurrentSong().catch(error => updateStatus('Load failed: '+error.message));
}
async function play(side) {
  const c = current();
  if (!c) return;
  if (!api || !score || !ready) {
    updateStatus('Song is still loading. Please try again.');
    return;
  }
  try {
    selectOnlyComparedTrack();
    if (!activeTrack || activeTrack.name?.trim() !== c.track.trim())
      throw new Error('Incorrect instrument selected');
    const startMeasure = side === 'a' ? c.a : c.b;
    const endMeasureExclusive = startMeasure + (c.length || 2);
    const master = score.masterBars;
    if (!master || startMeasure < 1 || endMeasureExclusive > master.length+1)
      throw new Error('Invalid measure range in source file');
    const first = master[startMeasure-1];
    const after = master[endMeasureExclusive-1];
    const last = master[endMeasureExclusive-2];
    const startTick = Number(first?.start);
    const endTick = after ? Number(after.start) :
      Number(last?.start) + Number(last?.calculateDuration?.() || last?.duration);
    if (!Number.isFinite(startTick) || !Number.isFinite(endTick) || endTick <= startTick)
      throw new Error('Could not determine the excerpt timing');
    api.playbackSpeed = Number($('speed').value);
    api.playbackRange = {startTick, endTick};
    api.tickPosition = startTick;
    if (!api.play()) throw new Error('Audio engine is not ready to play');
    updateStatus('Playing only '+activeTrack.name+' · measures '+startMeasure+'–'+(endMeasureExclusive-1));
  } catch(error) { updateStatus('Playback failed: '+error.message); }
}
function setAnswer(value) {
  const c = current();
  if (!c) return;
  reviews[c.id] = {...currentReview(), label:value, notes:$('notes').value, updatedAt:new Date().toISOString()};
  saveReviews();
  render();
}
function exportReviews() {
  const payload = {format:'composition-lab-review-v1', exportedAt:new Date().toISOString(),
    reviewType:'riff-comparison', totalExamples:cases.length,
    reviews:cases.filter(c => reviews[c.id]).map(c => ({id:c.id,...reviews[c.id]}))};
  const blob = new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob), link=document.createElement('a');
  link.href=url; link.download='riff_review_feedback.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
}
async function boot() {
  const response=await fetch('./cases.json');
  if (!response.ok) throw new Error('Comparison examples are unavailable');
  const source=await response.json();
  cases=source.filter(c => c.kind === 'motif');
  // Remove comparison duplicates where the two stereo rhythm guitars use the same bar references.
  const used = new Set();
  cases=cases.filter(c => {
    const key=[c.song,c.a,c.b,c.length].join('|');
    if (used.has(key)) return false;
    used.add(key); return true;
  });
  for (const song of songs) {
    try { const data=await dbGet(song); if(data)bytes.set(song,data); } catch {}
  }
  updateFiles();
  $('files').addEventListener('change', async event => {
    for (const file of event.target.files || []) {
      const song=songs.find(s => s.toLowerCase() === file.name.toLowerCase());
      if (!song) continue;
      const data=await file.arrayBuffer();
      bytes.set(song,data);
      try { await dbPut(song,data); } catch {}
    }
    updateFiles();
    openCurrentSong().catch(error => updateStatus(error.message));
  });
  $('playA').onclick=()=>play('a'); $('playB').onclick=()=>play('b');
  $('stop').onclick=()=>{api?.stop(); updateStatus('Stopped');};
  $('speed').onchange=()=>{if(api)api.playbackSpeed=Number($('speed').value);};
  $('prev').onclick=()=>{if(currentIndex>0){currentIndex--;render();}};
  $('next').onclick=()=>{if(currentIndex<cases.length-1){currentIndex++;render();}};
  document.querySelectorAll('[data-label]').forEach(btn => btn.onclick=()=>setAnswer(btn.dataset.label));
  $('notes').oninput=()=>{
    clearTimeout(commentsTimer);
    // Capture the ID at input time so moving next cannot attach remarks to a different riff.
    const id=current()?.id, contents=$('notes').value;
    commentsTimer=setTimeout(()=>{
      if(id===undefined)return;
      reviews[id]={...reviews[id],notes:contents,updatedAt:new Date().toISOString()};
      saveReviews();
    },350);
  };
  $('export').onclick=exportReviews;
  render();
}
boot().catch(error => updateStatus('Setup failed: '+error.message));
