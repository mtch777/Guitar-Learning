const ALPHATAB_ROOT = 'https://cdn.jsdelivr.net/npm/@coderline/alphatab@1.8.4/dist/';
import {normalizeEvents, toEventScore} from './riff-event-score.js';
const INTERVALS = ['1','♭2','2','♭3','3','4','♭5','5','♭6','6','♭7','7'];
export function fraction(value) { const [a, b = '1'] = String(value).split('/'); return Number(a) / Number(b); }

// Adapt the composer's written score without selecting or changing any notes.
export function toNativeScore(at, source, title = 'Drop E riff') {
  const m = at.model, score = new m.Score();
  score.title = title; score.artist = 'Original Drop E composition';
  const track = new m.Track(); score.addTrack(track); track.name = 'Drop E 8 string';
  track.playbackInfo.program = 30;
  const staff = new m.Staff(); track.addStaff(staff);
  staff.stringTuning.tunings = [...source.tuning_high_to_low];
  staff.showStandardNotation = false; staff.showTablature = true;
  for (const [barIndex, sourceBar] of source.bars.entries()) {
    const master = new m.MasterBar();
    master.timeSignatureNumerator = source.meter[0]; master.timeSignatureDenominator = source.meter[1];
    if (!barIndex) master.tempoAutomations.push(m.Automation.buildTempoAutomation(false, 0, source.tempo, 2));
    score.addMasterBar(master);
    const bar = new m.Bar(); staff.addBar(bar); const voice = new m.Voice(); bar.addVoice(voice);
    for (const sourceBeat of sourceBar) {
      const beat = new m.Beat(); voice.addBeat(beat);
      beat.duration = sourceBeat.type; beat.dots = sourceBeat.dots || 0; beat.isEmpty = false;
      beat.dynamics = m.DynamicValue[(sourceBeat.velocity || 'mf').toUpperCase()];
      for (const sourceNote of sourceBeat.notes) {
        const note = new m.Note();
        note.string = source.tuning_high_to_low.length - sourceNote.string;
        note.fret = sourceNote.fret;
        note.isPalmMute = Boolean(sourceBeat.palmMute);
        note.isHammerPullOrigin = Boolean(sourceNote.hp);
        note.accentuated = sourceNote.accentuated || 0;
        note.dynamics = beat.dynamics;
        beat.addNote(note);
      }
    }
  }
  score.finish(new at.Settings());
  return score;
}

function loadAlphaTab() {
  if (window.alphaTab) return Promise.resolve(window.alphaTab);
  return new Promise((resolve, reject) => {
    const script = document.createElement('script'); script.src = `${ALPHATAB_ROOT}alphaTab.min.js`;
    script.onload = () => window.alphaTab ? resolve(window.alphaTab) : reject(new Error('Player did not initialize.'));
    script.onerror = () => reject(new Error('Could not load the guitar player. Check your connection and Generate again.'));
    document.head.append(script);
  });
}

export function mountBuilder() {
  const $ = id => document.getElementById(id);
  const styleNames = {arpeggio:'Arpeggio', chordal:'Chord', melodic:'Melodic', pedal:'Pedal', rhythmic:'Rhythmic', other:'Other'};
  const focusNames = {single:'Mostly single notes', interval:'Mostly intervals', triad:'Mostly triads', chord:'Mostly chords', mixed:'Mixed'};
  let sections = [{style:'arpeggio', focus:'single', length_q:'8', seed:0}];
  let artists = ['Invent Animate'], mode = 'Aeolian', result = null, api = null, at = null;
  let worker = null, requestId = 0, busy = false, ready = false, playing = false, speed = 1, q = 0, playerPromise = null;
  let timeout = null, activeCells = new Map(), labelCells = [], scoreLoad = 0, lastRequest = null, availability = null;
  const status = (message, error = false) => { $('status').textContent = message; $('status').classList.toggle('error', error); };
  const duration = () => result?.score.duration_q || 0;
  function transport() {
    $('play').disabled = busy || !ready; $('stop').disabled = busy || !ready;
    $('play').textContent = playing ? '❚❚ Pause' : '▶ Play';
    $('download').disabled = busy || !result; $('seek').disabled = busy || !ready;
    for (const b of $('section-playback').querySelectorAll('button')) b.disabled = busy || !ready;
  }
  function setBusy(value) {
    busy = value; document.body.setAttribute('aria-busy', String(value));
    for (const element of document.querySelectorAll('[aria-label="Generate a riff"] button, [aria-label="Generate a riff"] input, [aria-label="Generate a riff"] select')) element.disabled = value;
    $('generate').textContent = value ? 'Generating…' : 'Generate riff';
    if (!value) renderSections();
    transport();
  }
  function fail(error) {
    clearTimeout(timeout); setBusy(false);
    status(error?.message || String(error), true);
  }
  function updatePosition(value) {
    q = Math.max(0, Math.min(duration(), value)); $('seek').value = String(q);
    const bars = Math.ceil(duration() / 4);
    $('position').textContent = `Bar ${Math.min(bars, Math.floor(q / 4) + 1)} / ${bars}`;
    for (const button of $('section-playback').querySelectorAll('button')) {
      const s = result.sections[Number(button.dataset.index)];
      button.setAttribute('aria-pressed', String(q >= fraction(s.offset_q) && q < fraction(s.offset_q) + fraction(s.length_q)));
    }
    drawActive();
  }
  function createFretboard() {
    const board = $('fretboard'); board.replaceChildren(); activeCells = new Map(); labelCells = [];
    board.append(document.createElement('div'));
    for (let fret = 1; fret <= 24; fret++) { const cell = document.createElement('div'); cell.className = 'fret-number'; cell.textContent = fret; board.append(cell); }
    const score = result.score;
    for (let string = 0; string < 8; string++) {
      const label = document.createElement('div'); label.className = 'string-label';
      label.textContent = INTERVALS[(score.tuning_high_to_low[string] - 4 + 120) % 12];
      label.title = 'Open string interval relative to E'; board.append(label); labelCells.push(label);
      for (let fret = 1; fret <= 24; fret++) {
        const cell = document.createElement('div'); cell.className = 'cell';
        const marker = document.createElement('span'); marker.className = 'marker';
        marker.textContent = INTERVALS[(score.tuning_high_to_low[string] + fret - 4 + 120) % 12];
        cell.title = `Fret ${fret} · ${marker.textContent}`; cell.append(marker); board.append(cell); activeCells.set(`${string}:${fret}`, cell);
      }
    }
    for (const note of score.notes) activeCells.get(`${note.string}:${note.fret}`)?.classList.add('used');
    drawActive();
  }
  function drawActive() {
    if (!result) return;
    for (const cell of activeCells.values()) cell.classList.remove('active');
    for (const cell of labelCells) cell.classList.remove('open');
    for (const note of result.score.notes) {
      if (q < note.start || q >= note.end || q >= duration()) continue;
      if (note.fret === 0) labelCells[note.string]?.classList.add('open');
      else activeCells.get(`${note.string}:${note.fret}`)?.classList.add('active');
    }
  }
  function renderSections() {
    $('sections').replaceChildren();
    sections.forEach((section, index) => {
      const row = document.createElement('div'); row.className = 'section-row';
      const number = document.createElement('strong'); number.textContent = `${index + 1}`; row.append(number);
      for (const [key, names, label] of [['style',styleNames,'Style'],['focus',focusNames,'Focus'],['length_q',{'4':'1 bar','8':'2 bars','16':'4 bars'},'Length']]) {
        const holder = document.createElement('label'); holder.textContent = label;
        const select = document.createElement('select'); select.setAttribute('aria-label', `Section ${index + 1} ${label.toLowerCase()}`);
        for (const [value, text] of Object.entries(names)) {
          const option = document.createElement('option'); option.value = value;
          const hasRefs=key==='style'?artists.some(a=>Object.values(availability?.rhythms[a]?.[value]||{}).some(n=>n>0)):key==='focus'?artists.some(a=>availability?.rhythms[a]?.[section.style]?.[value]>0):true;
          option.textContent = text + (availability&&!hasRefs?' · no labelled refs':''); select.append(option);
        }
        select.value = section[key]; select.disabled = busy;
        select.addEventListener('change', () => {section[key] = select.value; status('Section changed. Generate to apply it.'); renderSections();});
        holder.append(select); row.append(holder);
      }
      const fresh = document.createElement('button'); fresh.textContent = '↻ New version'; fresh.title = 'Regenerate only this section'; fresh.disabled = busy || !sameSettings();
      fresh.addEventListener('click', () => generate(index)); row.append(fresh);
      const remove = document.createElement('button'); remove.textContent = '×'; remove.setAttribute('aria-label', `Remove section ${index + 1}`); remove.disabled = busy || sections.length === 1;
      remove.addEventListener('click', () => {sections.splice(index,1); renderSections(); status('Section removed. Generate to apply it.');}); row.append(remove);
      if(availability){
        const hasRhythm=artists.some(a=>availability.rhythms[a]?.[section.style]?.[section.focus]>0);
        const hasShape=artists.some(a=>availability.palettes[a]?.[section.style]?.[mode]>0);
        if(!hasRhythm||!hasShape){const hint=document.createElement('p');hint.className='small availability-hint';hint.textContent=!hasRhythm?'No labelled rhythm material for this artist/style/focus yet.':'No labelled shape palette fits this style and mode yet.';row.append(hint);}
      }
      $('sections').append(row);
    });
  }
  function settings() {return {artists:['Invent Animate','Currents','ERRA'].filter(a=>artists.includes(a)),mode,tempo:Number($('tempo').value),seed:1,sections:sections.map(s=>({...s}))};}
  function sameSettings() {return Boolean(lastRequest) && JSON.stringify(settings()) === JSON.stringify(lastRequest);}
  async function ensurePlayer() {
    if (api) return;
    if (playerPromise) return playerPromise;
    playerPromise = (async () => {
      at = await loadAlphaTab();
      api = new at.AlphaTabApi($('score'), {
        core: {scriptFile: `${ALPHATAB_ROOT}alphaTab.min.js`, fontDirectory: `${ALPHATAB_ROOT}font/`}, display: {scale: 0.8},
        player: {playerMode:'enabledSynthesizer',outputMode:'webAudioScriptProcessor',soundFont:`${ALPHATAB_ROOT}soundfont/sonivox.sf2`,enableCursor:true,enableUserInteraction:false,scrollMode:'off'}
      });
      api.error.on(error=>{ready=false; transport(); fail(error);});
      api.scoreLoaded.on(() => {ready=false; transport();});
      api.playerReady.on(() => {ready=true; api.playbackSpeed=speed; transport(); status('Ready. Play the riff or click a section.');});
      api.playerStateChanged.on(args => {playing=args.state===1; transport();});
      api.playerPositionChanged.on(args => updatePosition(Number(args.currentTick || 0)/960));
    })().catch(error=>{playerPromise=null; throw error;});
    return playerPromise;
  }
  function showPatterns() {
    $('pattern-details').replaceChildren(); $('section-playback').replaceChildren();
    result.sections.forEach((s,index)=>{
      const b=document.createElement('button'); b.type='button'; b.dataset.index=String(index); b.textContent=`▶ ${index+1} · ${styleNames[sections[index].style]}`;
      b.addEventListener('click',()=>{if(!ready||busy)return; api.pause(); api.tickPosition=fraction(s.offset_q)*960; updatePosition(fraction(s.offset_q)); api.play();});
      $('section-playback').append(b);
      const h=document.createElement('h3'); h.textContent=`Section ${index+1} · ${styleNames[sections[index].style]}`;
      const p=document.createElement('p'); p.className='small';
      const notes=result.score.notes.filter(n=>n.start>=fraction(s.offset_q)&&n.start<fraction(s.offset_q)+fraction(s.length_q));
      const frets=notes.filter(n=>n.fret>0).map(n=>n.fret);
      const attacks=new Set(notes.map(n=>n.start)).size;
      p.textContent=`${fraction(s.length_q)/4} bars · ${attacks} attacks · ${frets.length?`frets ${Math.min(...frets)}–${Math.max(...frets)}`:'open strings'} · ${s.distinct_pattern_count || s.blocks?.length || 0} rhythm patterns`;
      const detail=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');
      summary.textContent='Reference patterns and checks'; pre.textContent=JSON.stringify(s,null,2); detail.append(summary,pre);
      $('pattern-details').append(h,p,detail);
    });
    const note=document.createElement('p'); note.className='small'; note.textContent='Style tags describe the source riffs. Generated sections use their patterns; local style recognition and musical quality still need listening.'; $('pattern-details').append(note);
  }
  function getWorker() {
    if(worker)return worker;
    worker=new Worker(new URL('./riff-builder-worker.js',import.meta.url),{type:'module'});
    worker.onerror=error=>{worker?.terminate();worker=null;fail(new Error(error.message||'Composer could not start.'));};
    worker.onmessage=async({data})=>{
      if(data.id!==requestId)return;
      if(data.type==='status')status(data.message);
      if(data.type==='error')fail(new Error(data.message));
      if(data.type==='result') {
        clearTimeout(timeout);
        if(data.result.status!=='generated') {
          const descriptions=data.result.sections.filter(s=>s.status!=='generated').map(s=>{
            const reason=s.refusals?.at(-1)?.reason || 'no matching choice';
            const messages={no_admitted_rhythm_templates:'No rhythm material matches this artist/style/focus.',no_mode_compatible_shape_palette:'No compatible shape palette for this mode and style.',whole_units_cannot_fill_requested_length:'The available complete patterns cannot fill this length.',bounded_realization_search_exhausted:'No new pitch choice found within the current search.',bounded_realization_or_section_novelty_search_exhausted:'No complete new pitch choice found within the current search.'};
            return `Section ${s.index+1}: ${messages[reason] || reason.replaceAll('_',' ')}`;
          });
          fail(new Error(`No complete riff for this selection. ${descriptions.slice(0,3).join(' ')}${result?' Your previous riff is still available.':''}`)); return;
        }
        const candidate=data.result;
        try {
          candidate.score=normalizeEvents(candidate);
          await ensurePlayer();
          const native=toEventScore(at,candidate,`E ${mode} · Drop E riff`);
          result=candidate; lastRequest=structuredClone(candidate.request || settings());
          $('result').hidden=false; $('result-title').textContent=`E ${mode} · ${candidate.tempo} BPM`;
          $('seek').max=String(duration()); showPatterns(); createFretboard(); updatePosition(0);
          ready=false; playing=false; scoreLoad++; api.stop(); api.load(native); api.playbackSpeed=speed;
          setBusy(false); status('Loading guitar sound…');
        } catch(error) {fail(error);}
      }
    };
    return worker;
  }
  function generate(onlyIndex=null) {
    const tempo=Number($('tempo').value);
    if(!Number.isInteger(tempo)||tempo<80||tempo>200){status('Choose a whole-number tempo from 80 to 200 BPM.',true);return;}
    if(!artists.length){status('Select at least one reference artist.',true);return;}
    if(onlyIndex===null) sections.forEach(s=>s.seed++); else sections[onlyIndex].seed++;
    const request=settings(); api?.stop(); playing=false; setBusy(true); requestId++; status('Finding reference patterns…');
    timeout=setTimeout(()=>{worker?.terminate();worker=null;requestId++;fail(new Error('Composer took too long. Try a shorter section or another selection.'));},180000);
    getWorker().postMessage({id:requestId,request,assetBase:new URL('riff-builder/',document.baseURI).href});
  }
  $('artists').addEventListener('click',event=>{const b=event.target.closest('[data-artist]');if(!b||busy)return;const a=b.dataset.artist;artists=artists.includes(a)?artists.filter(x=>x!==a):[...artists,a];b.setAttribute('aria-pressed',String(artists.includes(a)));renderSections();});
  $('modes').addEventListener('click',event=>{const b=event.target.closest('[data-mode]');if(!b||busy)return;mode=b.dataset.mode;for(const x of $('modes').querySelectorAll('button'))x.setAttribute('aria-pressed',String(x===b));renderSections();});
  $('tempo').addEventListener('input',renderSections);
  $('add-section').addEventListener('click',()=>{if(sections.length>=12){status('This version supports up to 12 sections.',true);return;}sections.push({style:'pedal',focus:'single',length_q:'8',seed:0});renderSections();});
  $('generate').addEventListener('click',()=>generate());
  $('play').addEventListener('click',()=>{if(ready&&!busy)api.playPause();});
  $('stop').addEventListener('click',()=>{api?.stop();updatePosition(0);});
  $('speeds').addEventListener('click',event=>{const b=event.target.closest('[data-speed]');if(!b)return;speed=Number(b.dataset.speed);if(api)api.playbackSpeed=speed;for(const x of $('speeds').querySelectorAll('button'))x.setAttribute('aria-pressed',String(x===b));});
  $('seek').addEventListener('input',()=>{if(api&&ready){api.tickPosition=Number($('seek').value)*960;updatePosition(Number($('seek').value));}});
  $('download').addEventListener('click',()=>{
    if(!result)return;
    const blob=new Blob([JSON.stringify(result,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download=`drop-e-${lastRequest.mode.toLowerCase()}-riff.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  renderSections();transport();
  fetch(new URL('riff-builder/availability.json',document.baseURI)).then(r=>r.ok?r.json():null).then(data=>{if(data){availability=data;renderSections();}}).catch(()=>{});
}
if(typeof document!=='undefined')mountBuilder();
