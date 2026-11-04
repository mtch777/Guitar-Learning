/**
 * Explicit preview policy for a fully muted, continuous tie/legato gesture.
 * Interior pitch-transition clocks remain written; the native mute release cap
 * applies only at the terminal destination. This models duration, not a new
 * palm-muted timbre, and does not change notation or add attacks.
 *
 * The alphaTab prototype dispatcher is installed once per class, but dispatches
 * only for explicitly registered score identities. Unregistered scores execute
 * the original method. Registration is atomic; no model/vendor field is edited.
 */
const POLICY='composition-lab.continuous-mute-terminal-release/1';
const installed=new WeakMap();
const need=(ok,message)=>{if(!ok)throw Error(`Continuous mute playback: ${message}`);};
const owner=n=>n?.beat?.voice?.bar?.staff?.track?.score;

function inventory(score){
 const out=[];
 for(const[ti,t]of score.tracks.entries())for(const[si,s]of t.staves.entries())
 for(const[mi,b]of s.bars.entries())for(const[vi,v]of b.voices.entries())
 for(const[bi,e]of v.beats.entries())for(const[ni,n]of e.notes.entries())
  out.push({note:n,address:[ti,si,mi,vi,bi,ni]});
 return out;
}
function state(note){
 const b=note.beat;
 return [owner(note),b,b.voice,note.string,note.fret,note.realValue,
  note.isPalmMute,note.isDead,note.isStaccato,note.isTieOrigin,note.isTieDestination,
  note.tieOrigin,note.tieDestination,note.slideInType,note.slideOutType,
  note.slideOrigin,note.slideTarget,b.absolutePlaybackStart,b.playbackDuration,
  b.absoluteDisplayStart,b.displayDuration,b.graceType,b.brushType,b.isTremolo,
  b.hasRasgueado,note.trillValue,note.ornament,note.durationPercent,
  JSON.stringify(note.bendPoints?.map(p=>[p.offset,p.value])??null)];
}
function unchanged(before,note){const now=state(note);return before.length===now.length&&before.every((x,i)=>x===now[i]);}

function tempoState(bars){return JSON.stringify(bars.map(b=>({start:b.start,duration:b.calculateDuration(),
 repeat:[b.isRepeatStart,b.isRepeatEnd,b.alternateEndings],directions:b.directions?[...b.directions]:null,
 tempo:b.tempoAutomations.map(a=>[a.ratioPosition,a.value,a.isLinear,a.type])})));}
function tempoContext(at,members){
 const first=members[0].beat,last=members.at(-1).beat,score=owner(members[0]);
 const start=first.absolutePlaybackStart,end=last.absolutePlaybackStart;
 const bars=score.masterBars.slice(first.voice.bar.masterBar.index,last.voice.bar.masterBar.index+1);
 const events=[];
 for(const b of bars){
  need(!b.isRepeatEnd&&!b.alternateEndings&&!b.directions?.size&&
       (b===bars[0]||!b.isRepeatStart),'repeated or redirected continuation tempo needs explicit traversal');
  let prior=-1;
  for(const a of b.tempoAutomations){
   need(Number.isFinite(a.ratioPosition)&&a.ratioPosition>=0&&a.ratioPosition<=1&&a.ratioPosition>=prior,
        'ordered explicit tempo positions required');prior=a.ratioPosition;
   const tick=b.start+b.calculateDuration()*a.ratioPosition;
   if(tick<start||tick>end)continue;
   need(!a.isLinear,'tempo ramp inside continuous mute needs explicit terminal timing');
   need(a.type===at.model.AutomationType.Tempo&&Number.isFinite(a.value)&&a.value>0&&Number.isSafeInteger(tick),
        'finite positive step tempo with integer clock required');
   if(events.length&&events.at(-1).tick===tick)need(events.at(-1).value===a.value,'conflicting tempo declarations');
   else events.push({tick,value:a.value});
  }
 }
 need(members.every(n=>!n.beat.voice.bar.simileMark),'repeated-bar continuation needs explicit traversal');
 return {bars,guard:tempoState(bars),events};
}

function gather(at,score,settings){
 need(score&&Array.isArray(score.tracks),'a finished native score is required');
 const rows=inventory(score),all=new Set(rows.map(r=>r.note)),where=new Map(rows.map(r=>[r.note,r.address]));
 const next=new Map(),incoming=new Map(),unresolved=[];
 for(const{note:n}of rows){
  const tied=n.isTieOrigin||n.tieDestination;
  const slid=n.slideOutType===at.model.SlideOutType.Legato;
  if(!tied&&!slid)continue;
  if(tied&&slid){unresolved.push(n);continue;}
  const d=tied?n.tieDestination:n.slideTarget;
  if(!d||!all.has(d)){unresolved.push(n);continue;}
  const reciprocal=tied?d.isTieDestination&&d.tieOrigin===n:d.slideOrigin===n;
  if(!reciprocal||incoming.has(d)){unresolved.push(n);continue;}
  next.set(n,d);incoming.set(d,n);
 }
 for(const n of unresolved)need(!n.isPalmMute,'ambiguous muted continuation');
 const chains=[],visited=new Set();
 for(const{note:start}of rows){
  if(!next.has(start)||incoming.has(start))continue;
  const members=[];let n=start;
  while(n){need(!members.includes(n),'cyclic continuation');members.push(n);visited.add(n);n=next.get(n);}
  if(!members.some(n=>n.isPalmMute))continue;
  need(members.every(n=>n.isPalmMute),'mixed mute state in a continuous gesture');
  need(members.every(n=>!unresolved.includes(n)),'ambiguous muted continuation');
  for(let i=0;i<members.length;i++){
   const n=members[i],b=n.beat;
   if(i<members.length-1&&n.hasBend){
    need(n.slideOutType!==at.model.SlideOutType.Legato,'simultaneous bend and legato needs explicit pitch-curve coordination');
    if(n.isTieOrigin)need(settings.notation.extendBendArrowsOnTiedNotes===false,
      'tied bend with extendBendArrowsOnTiedNotes needs explicit curve/release coordination');
   }
   need(owner(n)===score&&!b.voice.bar.staff.isPercussion&&!n.isDead&&!n.isStaccato,
        'unsupported dead, staccato or percussion continuation');
   need(!b.graceType&&!b.brushType&&!b.isTremolo&&!b.hasRasgueado&&n.trillValue<0&&!n.ornament&&n.durationPercent===1,
        'unsupported repeated, displaced or grace execution');
   need(Number.isSafeInteger(b.absolutePlaybackStart)&&Number.isSafeInteger(b.playbackDuration)&&b.playbackDuration>0,
        'integer written playback clocks required');
   need(b.absolutePlaybackStart===b.absoluteDisplayStart&&b.playbackDuration===b.displayDuration,
        'independently displaced playback needs a declared continuation clock');
   if(i){
    const previous=members[i-1];
    need(previous.beat.voice.bar.staff===b.voice.bar.staff&&previous.beat.voice.index===b.voice.index&&previous.string===n.string&&
         previous.beat.absolutePlaybackStart+previous.beat.playbackDuration===b.absolutePlaybackStart,
         'continuation must remain contiguous in its voice and string');
    if(previous.tieDestination===n)need(previous.realValue===n.realValue,'tie changes pitch');
   }
  }
  chains.push({members,guards:members.map(state),addresses:members.map(n=>where.get(n)),
   fixedBendClock:members.some(n=>n.hasBend&&n.isTieOrigin),tempo:tempoContext(at,members)});
 }
 for(const n of next.keys())need(visited.has(n)||!n.isPalmMute,'cyclic or ambiguous muted continuation');
 // A dangling destination may have no origin chain at all; do not silently
 // register it as an isolated note whose missing attack is unexplained.
 for(const{note:n}of rows)if(n.isPalmMute&&(n.isTieDestination||n.slideOrigin?.slideOutType===at.model.SlideOutType.Legato))
  need(incoming.has(n)&&visited.has(n),'unresolved muted continuation destination');
 const entries=new WeakMap();
 for(const chain of chains)for(const note of chain.members)entries.set(note,chain);
 return {entries,receipt:Object.freeze({policy:POLICY,continuous_gestures:chains.length,
  interior_notes:chains.reduce((sum,c)=>sum+c.members.length-1,0),
  chains:chains.map(c=>c.addresses.map(a=>[...a])),
  claim:'Continuous written tie/legato timing with native terminal mute release; no acoustic timbre claim.'})};
}

/** Register after loading/finishing the score. Re-register explicitly after edits. */
export function registerContinuousMutePlayback(at,score,settings=new at.Settings()){
 const proto=at?.midi?.MidiFileGenerator?.prototype;
 need(proto&&typeof proto._getNoteDuration==='function','pinned native duration interface unavailable');
 const prepared=gather(at,score,settings); // All refusal precedes dispatcher/registration.
 let installedState=installed.get(proto);
 if(!installedState){
  const original=proto._getNoteDuration,scores=new WeakMap();
  const wrapper=function(note,beatPlayDuration,tempoOnBeatStart){
   const registered=scores.get(owner(note)),chain=registered?.entries.get(note);
   if(!chain){
    if(registered&&note.isPalmMute&&(note.isTieOrigin||note.isTieDestination||
       note.slideOutType===at.model.SlideOutType.Legato||note.slideOrigin?.slideOutType===at.model.SlideOutType.Legato))
      need(false,'unregistered muted continuation appeared; explicitly re-register after editing');
    return original.call(this,note,beatPlayDuration,tempoOnBeatStart);
   }
   need(beatPlayDuration===note.beat.playbackDuration,'runtime beat duration differs from registered written clock');
   need(chain.members.every((n,i)=>unchanged(chain.guards[i],n)),
        'registered continuation changed; explicitly re-register after editing');
   need(chain.tempo.guard===tempoState(chain.tempo.bars),'registered tempo context changed; explicitly re-register');
   if(chain.fixedBendClock)need(this._settings.notation.extendBendArrowsOnTiedNotes===false,
      'registered bend clock setting changed; explicitly re-register');
   const value=original.call(this,note,beatPlayDuration,tempoOnBeatStart);
   const terminal=chain.members.at(-1);
   if(note===terminal)return value;
   let terminalTempo=tempoOnBeatStart;
   for(const event of chain.tempo.events)if(event.tick>note.beat.absolutePlaybackStart&&event.tick<=terminal.beat.absolutePlaybackStart)
    terminalTempo=event.value;
   const end=terminal.beat.absolutePlaybackStart+
      original.call(this,terminal,terminal.beat.playbackDuration,terminalTempo).noteOnly;
   need(end>note.beat.absolutePlaybackStart+beatPlayDuration,'terminal release does not reach the next destination');
   // Native legato and bend timing use noteOnly. Applying an interior mute cap
   // here would shift pitch movement earlier even if note-off were repaired.
   value.noteOnly=beatPlayDuration;
   value.untilTieOrSlideEnd=end-note.beat.absolutePlaybackStart;
   value.letRingEnd=value.untilTieOrSlideEnd;
   return value;
  };
  proto._getNoteDuration=wrapper;
  installedState={original,wrapper,scores};installed.set(proto,installedState);
 }else need(proto._getNoteDuration===installedState.wrapper,'native duration method changed after dispatcher installation');
 installedState.scores.set(score,prepared);return prepared.receipt;
}

export function unregisterContinuousMutePlayback(at,score){
 const proto=at?.midi?.MidiFileGenerator?.prototype;
 return installed.get(proto)?.scores.delete(score)??false;
}
