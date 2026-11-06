import {normalizeEvents, toEventScore, qValue} from './riff-event-score.js';
import {buildShapeTimeline, playbackShapeFrame} from './riff-shapes.js';

const ALPHATAB_ROOT = 'https://cdn.jsdelivr.net/npm/@coderline/alphatab@1.8.4/dist/';
const INTERVALS = ['1','♭2','2','♭3','3','4','♭5','5','♭6','6','♭7','7'];
const ARTISTS = ['Invent Animate','Currents','ERRA'];

export function riffPhrases(result) {
  if (!Number.isFinite(qValue(result?.duration_q)) || qValue(result.duration_q)<=0) throw new Error('The composer returned no exact riff duration.');
  const phrases = result?.phrases ?? result?.sections;
  if (!Array.isArray(phrases) || !phrases.length) throw new Error('The composer returned no phrase plan.');
  let end = 0;
  for (const phrase of phrases) {
    const start = qValue(phrase.offset_q), length = qValue(phrase.length_q);
    if (!Number.isFinite(start) || !Number.isFinite(length) || length <= 0 || Math.abs(start-end)>1e-8) {
      throw new Error('The phrase plan has a gap or overlap.');
    }
    end = start+length;
  }
  if (Math.abs(end-qValue(result.duration_q))>1e-8) throw new Error('The phrase plan does not cover the whole riff.');
  return phrases;
}

export function barPosition(score, quarter) {
  const bars = score?.bar_map || [];
  const index = bars.findIndex(b => quarter >= b.onset && quarter < b.onset+b.span);
  return {current: index < 0 ? bars.length : index+1, total: bars.length};
}

function loadAlphaTab() {
  if (window.alphaTab) return Promise.resolve(window.alphaTab);
  return new Promise((resolve,reject) => {
    // The narrow chained-slide correction uses the verified 1.8.4 native API.
    // Its private method names are retained only in the unminified bundle.
    const script=document.createElement('script'); script.src=`${ALPHATAB_ROOT}alphaTab.js`;
    script.onload=()=>window.alphaTab?resolve(window.alphaTab):reject(new Error('Player did not initialize.'));
    script.onerror=()=>reject(new Error('Could not load the guitar player. Check your connection and try again.'));
    document.head.append(script);
  });
}

export function mountBuilder() {
  const $=id=>document.getElementById(id);
  let artists=['Invent Animate'], mode='Aeolian', result=null, phrases=[], api=null, at=null;
  let worker=null, requestId=0, terminalRequest=-1, busy=false, ready=false, playing=false, speed=1, quarter=0;
  let timeout=null, playerPromise=null, shapeTimeline={spans:[],issues:[]}, shownSpan;
  let pendingLoad=null, acceptedNative=null, recovering=false;
  let activeCells=new Map(), labelCells=[];
  const status=(message,error=false)=>{$('status').textContent=message;$('status').classList.toggle('error',error);};
  const duration=()=>result?.score.duration_q || 0;
  function transport() {
    $('play').disabled=busy||!ready; $('stop').disabled=busy||!ready;
    $('play').textContent=playing?'❚❚ Pause':'▶ Play';
    $('download').disabled=busy||!result; $('seek').disabled=busy||!ready;
    for (const button of $('section-playback').querySelectorAll('button')) button.disabled=busy||!ready;
  }
  function setBusy(value) {
    busy=value; document.body.setAttribute('aria-busy',String(value));
    for (const button of document.querySelectorAll('[aria-label="Generate a riff"] button')) button.disabled=value;
    $('generate').textContent=value?'Generating…':'Generate riff'; transport();
  }
  function fail(error) {clearTimeout(timeout);setBusy(false);status(error?.message||String(error),true);}
  function recoverPlayer(error) {
    const rollback=Boolean(pendingLoad&&acceptedNative);pendingLoad=null;ready=false;
    if (rollback) {
      recovering=true;
      try {api.stop();api.load(acceptedNative);} catch {recovering=false;}
    }
    fail(error);
  }
  function position(value) {
    quarter=Math.max(0,Math.min(duration(),value));$('seek').value=String(quarter);
    const bars=barPosition(result?.score,quarter);
    $('position').textContent=`Bar ${bars.current} / ${bars.total}`;
    for (const button of $('section-playback').querySelectorAll('button')) {
      const p=phrases[Number(button.dataset.index)];
      button.setAttribute('aria-pressed',String(quarter>=qValue(p.offset_q)&&quarter<qValue(p.offset_q)+qValue(p.length_q)));
    }
    drawActive();
  }
  function createFretboard() {
    const board=$('fretboard');board.replaceChildren();activeCells=new Map();labelCells=[];shownSpan=undefined;
    board.append(document.createElement('div'));
    for (let fret=1;fret<=24;fret++) {
      const cell=document.createElement('div');cell.className='fret-number';cell.textContent=fret;board.append(cell);
    }
    for (let string=0;string<8;string++) {
      const open=result.score.tuning_high_to_low[string];
      const label=document.createElement('div');label.className='string-label';label.textContent=INTERVALS[(open-4+120)%12];
      label.title='Open string interval relative to E';board.append(label);labelCells.push(label);
      for (let fret=1;fret<=24;fret++) {
        const cell=document.createElement('div');cell.className='cell';
        const marker=document.createElement('span');marker.className='marker';marker.textContent=INTERVALS[(open+fret-4+120)%12];
        cell.title=`Fret ${fret} · ${marker.textContent}`;cell.dataset.baseTitle=cell.title;
        cell.append(marker);board.append(cell);activeCells.set(`${string}:${fret}`,cell);
      }
    }
    drawActive();
  }
  function drawActive() {
    if (!result) return;
    const frame=playbackShapeFrame(shapeTimeline,result.score,quarter),span=frame.span;
    if (span!==shownSpan) {
      shownSpan=span;const color=span?.color||'blue';
      $('fretboard').dataset.shapeColor=color;$('current-shape').dataset.color=color;
      for (const cell of activeCells.values()) {cell.classList.remove('shape-outline','shape-extension','shape-tapped');cell.title=cell.dataset.baseTitle;}
      for (const contact of span?.contacts||[]) {
        const cell=activeCells.get(contact.key);if(!cell)continue;cell.classList.add('shape-outline');
        if(contact.displayRole==='extension')cell.classList.add('shape-extension');
        if(contact.displayRole==='tapped')cell.classList.add('shape-tapped');
        cell.title+=` · ${contact.roles.join(' / ')}`;
      }
      const names={single_contact_context:'One fretted contact',open_string_only:'Open strings',tapped_context_only:'Tapping',no_fretted_contact:'No fretted shape'};
      const label=!span?(quarter>=duration()?'End of riff':'Shape unavailable'):span.status!=='available'?'Shape unavailable'
        :span.kind==='shape_window'?`Shape ${span.shapeNumber}`:names[span.kind]||'Shape unavailable';
      $('current-shape').textContent=span?`Phrase ${span.sectionIndex+1} · ${label}`:label;
      $('shape-legend').textContent=`Outline: ${span?.outlineKind==='reference_shape'?'reference shape':'this phrase’s positions'} · dotted: extensions · dashed: tapping · filled: current notes. Blue/orange marks a shape change; open strings light gray.`;
    }
    for (const cell of activeCells.values()) cell.classList.remove('active');
    for (const label of labelCells) label.classList.remove('open');
    for (const note of frame.activeContacts) activeCells.get(`${note.string}:${note.fret}`)?.classList.add('active');
    for (const string of frame.openStrings) labelCells[string]?.classList.add('open');
  }
  async function ensurePlayer() {
    if(api)return;if(playerPromise)return playerPromise;
    playerPromise=(async()=>{
      at=await loadAlphaTab();api=new at.AlphaTabApi($('score'),{
        core:{scriptFile:`${ALPHATAB_ROOT}alphaTab.js`,fontDirectory:`${ALPHATAB_ROOT}font/`},display:{scale:0.8},
        player:{playerMode:'enabledSynthesizer',outputMode:'webAudioScriptProcessor',soundFont:`${ALPHATAB_ROOT}soundfont/sonivox.sf2`,enableCursor:true,enableUserInteraction:false,scrollMode:'off'}
      });
      api.error.on(recoverPlayer);
      api.scoreLoaded.on(()=>{ready=false;transport();});
      api.playerReady.on(()=>{
        if(pendingLoad) {
          if(api.score&&api.score!==pendingLoad.native)return;
          const next=pendingLoad;
          const previous={result,phrases,shapeTimeline};
          try {
            result=next.candidate;phrases=next.phrases;shapeTimeline=next.timeline;
            presentResult();
            acceptedNative=next.native;pendingLoad=null;recovering=false;
            clearTimeout(timeout);setBusy(false);status('Ready. Play the whole riff or click a phrase.');
          } catch(error) {
            result=previous.result;phrases=previous.phrases;shapeTimeline=previous.shapeTimeline;
            presentResult();recoverPlayer(error);return;
          }
        } else if(recovering) recovering=false;
        ready=Boolean(result);api.playbackSpeed=speed;transport();
      });
      api.playerStateChanged.on(args=>{playing=args.state===1;transport();});
      api.playerPositionChanged.on(args=>position(Number(args.currentTick||0)/960));
    })().catch(error=>{playerPromise=null;throw error;});return playerPromise;
  }
  function showPlan() {
    $('pattern-details').replaceChildren();$('section-playback').replaceChildren();
    for (const [index,phrase] of phrases.entries()) {
      const name=String(phrase.label||phrase.role||`Phrase ${index+1}`);
      const button=document.createElement('button');button.type='button';button.dataset.index=String(index);
      button.textContent=`▶ ${index+1} · ${name.replaceAll('_',' ')}`;
      button.addEventListener('click',()=>{if(!ready||busy)return;api.pause();api.tickPosition=qValue(phrase.offset_q)*960;position(qValue(phrase.offset_q));api.play();});
      $('section-playback').append(button);
      const detail=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');
      summary.textContent=`Phrase ${index+1} · ${qValue(phrase.length_q)} beats · ${name.replaceAll('_',' ')}`;
      pre.textContent=JSON.stringify(phrase,null,2);detail.append(summary,pre);$('pattern-details').append(detail);
    }
    const summary=result.summary||result.plan?.summary;
    $('riff-summary').textContent=typeof summary==='string'?summary:`${phrases.length} phrases · ${duration()} beats · click any phrase to play from it`;
    if (result.plan) {
      const detail=document.createElement('details'),heading=document.createElement('summary'),pre=document.createElement('pre');
      heading.textContent='How the phrases relate';pre.textContent=JSON.stringify(result.plan,null,2);detail.append(heading,pre);$('pattern-details').prepend(detail);
    }
  }
  function presentResult() {
    $('result').hidden=!result;if(!result)return;
    $('result-title').textContent=`E ${result.request.mode} · ${result.tempo} BPM`;
    $('seek').max=String(duration());showPlan();createFretboard();position(0);
  }
  function getWorker() {
    if(worker)return worker;
    worker=new Worker(new URL('./riff-builder-worker.js',import.meta.url),{type:'module'});
    worker.onerror=error=>{
      worker?.terminate();worker=null;
      if(terminalRequest!==requestId)fail(new Error(error.message||'Composer could not start.'));
    };
    worker.onmessage=async({data})=>{
      if(data.id!==requestId||data.id===terminalRequest)return;
      if(data.type==='status')status(data.message);
      if(data.type==='error'){terminalRequest=data.id;fail(new Error(data.message));return;}
      if(data.type!=='result')return;
      terminalRequest=data.id;
      clearTimeout(timeout);const candidate=data.result;
      if(candidate.status!=='generated') {
        const message=candidate.message||'These choices did not produce a complete riff. Generate again to try another.';
        fail(new Error(`${message}${result?' Your previous riff is still available.':''}`));return;
      }
      try {
        const candidatePhrases=riffPhrases(candidate);candidate.score=normalizeEvents(candidate);
        const timeline=buildShapeTimeline(candidate);
        if(timeline.issues.length)throw new Error('The generated fretboard data is incomplete. Your previous riff is retained.');
        await ensurePlayer();
        if(data.id!==requestId)return;
        const native=toEventScore(at,candidate,`E ${candidate.request.mode} · Drop E riff`);
        pendingLoad={candidate,phrases:candidatePhrases,timeline,native};
        timeout=setTimeout(()=>recoverPlayer(new Error('The guitar player could not load this riff. Your previous result is retained.')),60000);
        ready=false;playing=false;api.stop();status('Loading guitar sound…');api.load(native);api.playbackSpeed=speed;
      } catch(error) {if(pendingLoad)recoverPlayer(error);else fail(error);}
    };return worker;
  }
  function generate() {
    if(busy)return;if(!artists.length){status('Select at least one reference artist.',true);return;}
    const seed=crypto.getRandomValues(new Uint32Array(1))[0];
    const request={artists:ARTISTS.filter(a=>artists.includes(a)),mode,seed};
    api?.stop();playing=false;setBusy(true);requestId++;status('Finding related phrase material…');
    timeout=setTimeout(()=>{worker?.terminate();worker=null;requestId++;fail(new Error('Composer took too long. Your previous riff is still available; try generating again.'));},180000);
    getWorker().postMessage({id:requestId,request,assetBase:new URL('riff-builder/',document.baseURI).href});
  }
  $('artists').addEventListener('click',event=>{
    const button=event.target.closest('[data-artist]');if(!button||busy)return;const artist=button.dataset.artist;
    artists=artists.includes(artist)?artists.filter(a=>a!==artist):[...artists,artist];button.setAttribute('aria-pressed',String(artists.includes(artist)));
  });
  $('modes').addEventListener('click',event=>{
    const button=event.target.closest('[data-mode]');if(!button||busy)return;mode=button.dataset.mode;
    for(const other of $('modes').querySelectorAll('button'))other.setAttribute('aria-pressed',String(other===button));
  });
  $('generate').addEventListener('click',generate);
  $('play').addEventListener('click',()=>{if(ready&&!busy)api.playPause();});
  $('stop').addEventListener('click',()=>{api?.stop();position(0);});
  $('speeds').addEventListener('click',event=>{
    const button=event.target.closest('[data-speed]');if(!button)return;speed=Number(button.dataset.speed);if(api)api.playbackSpeed=speed;
    for(const other of $('speeds').querySelectorAll('button'))other.setAttribute('aria-pressed',String(other===button));
  });
  $('seek').addEventListener('input',()=>{if(api&&ready){api.tickPosition=Number($('seek').value)*960;position(Number($('seek').value));}});
  $('download').addEventListener('click',()=>{
    if(!result)return;const blob=new Blob([JSON.stringify(result,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download=`drop-e-${result.request.mode.toLowerCase()}-riff-${new Date().toISOString().replace(/[:.]/g,'-')}.json`;
    link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  transport();
}
