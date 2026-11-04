// alphaTab resolves a HopoOrigin to the next written note, even if that note
// merely continues the origin's tied hold. Recover its fresh target only after
// proving the complete contiguous same-string chain. No notes/flags/velocities
// are changed. This is paired-preview routing, not standalone GP fidelity.
const need = (ok, message) => {if (!ok) throw Error(`HP through ties: ${message}`);};
function inventory(score) {
  const rows=[], lanes=new Map(), byNote=new Map();
  for(const[ti,t]of score.tracks.entries())for(const[si,s]of t.staves.entries())
  for(const[mi,b]of s.bars.entries())for(const[vi,v]of b.voices.entries())
  for(const[bi,beat]of v.beats.entries())for(const[ni,n]of beat.notes.entries()) {
    const row={n,staff:s,beat,address:[ti,si,mi,vi,bi,ni]},key=`${ti}:${si}:${vi}:${n.string}`;
    rows.push(row);byNote.set(n,row);if(!lanes.has(key))lanes.set(key,[]);row.lane=lanes.get(key);row.lane.push(row);
  }
  return {rows,byNote};
}
function plan(score) {
  const {rows,byNote}=inventory(score), plans=[],claimed=new Set();
  for(const row of rows) {
    const origin=row.n;
    if(!origin.isHammerPullOrigin)continue;
    if(!origin.tieDestination) {
      need(!origin.hammerPullDestination?.isTieDestination,'HP targets a tied tail without its origin continuation link');
      continue;
    }
    const members=[origin], first=origin.tieDestination;
    let current=origin;
    while(current.tieDestination) {
      const next=current.tieDestination,r=byNote.get(next),prior=byNote.get(current);
      need(r&&!members.includes(next),'missing or cyclic tied continuation');
      need(next.isTieDestination&&next.tieOrigin===current,'nonreciprocal tie');
      need(r.lane===row.lane&&!r.staff.isPercussion&&!next.isDead&&!current.isDead&&next.realValue===origin.realValue&&next.fret===origin.fret,'mixed pitch, string, voice or kind in tie');
      need(!r.beat.graceType&&!prior.beat.graceType&&prior.beat.absolutePlaybackStart===prior.beat.absoluteDisplayStart&&r.beat.absolutePlaybackStart===r.beat.absoluteDisplayStart&&
        prior.beat.absoluteDisplayStart+prior.beat.displayDuration===r.beat.absoluteDisplayStart,'tie is not written and performed contiguous');
      need(row.lane[row.lane.indexOf(prior)+1]===r,'intervening same-string contact');
      need(!next.isHammerPullOrigin&&!next.slideOutType&&!current.slideOutType&&!next.isLeftHandTapped,'mixed continuation gesture');
      members.push(next);current=next;
    }
    const tail=byNote.get(current),targetRow=row.lane[row.lane.indexOf(tail)+1],target=targetRow?.n;
    need(target&&!target.isTieDestination&&!target.isDead&&!targetRow.beat.graceType&&target.realValue!==origin.realValue,'missing fresh pitched HP target');
    need(tail.beat.absoluteDisplayStart+tail.beat.displayDuration===targetRow.beat.absoluteDisplayStart&&
      targetRow.beat.absoluteDisplayStart===targetRow.beat.absolutePlaybackStart,'HP target has gap, overlap or displaced playback');
    need(!claimed.has(target),'conflicting HP targets');claimed.add(target);
    need(origin.hammerPullDestination===first||origin.hammerPullDestination===target,'unexpected existing HP target');
    need(target.hammerPullOrigin===null||target.hammerPullOrigin===origin,'conflicting incoming HP target');
    need(origin.hammerPullDestination===first ? first.hammerPullOrigin===origin&&target.hammerPullOrigin===null : first.hammerPullOrigin===null&&target.hammerPullOrigin===origin,'nonreciprocal existing HP binding');
    for(const n of members.slice(1))need(n.hammerPullOrigin===null||n===first&&n.hammerPullOrigin===origin,'conflicting incoming tie HP binding');
    plans.push({origin,first,target,members,rows:members.map(n=>byNote.get(n)),targetRow});
  }
  return plans;
}

// Export authentication is independent of the native target search: the raw
// same-string source sequence must be origin -> every tied member -> fresh note.
export function checkSourceHammerPullThroughTies(score,parts) {
  const plans=plan(score),sourceLanes=new Map();
  const key=(ti,vi,string)=>`${ti}:${vi}:${string}`;
  for(const[ti,part]of parts.entries())for(const[mi,m]of part.measures.entries())
  for(const[vi,v]of(m.voices||[]).entries())for(const[bi,b]of(v.beats||[]).entries())for(const n of(b.notes||[])) {
    if(n.rest)continue;const k=key(ti,vi,n.string);if(!sourceLanes.has(k))sourceLanes.set(k,[]);
    sourceLanes.get(k).push({n,b,address:[ti,0,mi,vi,bi]});
  }
  for(const item of plans) {
    const expected=[...item.rows,item.targetRow],sourceRows=[];
    for(const r of expected) {
      const[ti,si,mi,vi,bi]=r.address,part=parts[ti],v=part?.measures[mi]?.voices[vi],b=v?.beats[bi];
      need(si===0&&part.instrumentId!==1024&&v?.beats.length===r.beat.voice.beats.length&&b&&!b.graceNote,'source/native ordinary occurrence correspondence');
      const candidates=(b.notes||[]).filter(n=>!n.rest&&n.string===r.staff.tuning.length-r.n.string);
      need(candidates.length===1,'ambiguous source member identity');
      const n=candidates[0],d=b.duration;
      need(n.fret===r.n.fret&&!n.dead&&Array.isArray(d)&&d.length===2&&d.every(x=>Number.isSafeInteger(x)&&x>0)&&
        BigInt(d[0])*3840n===BigInt(d[1])*BigInt(r.beat.displayDuration),'source pitch/duration identity');
      sourceRows.push({n,b,address:[ti,si,mi,vi,bi]});
    }
    need(sourceRows[0].n.hp===true,'source origin lacks HP declaration');
    need(sourceRows.slice(1,-1).every(r=>r.n.tie===true&&!r.n.hp),'source continuation is not a plain written tie');
    need(!sourceRows.at(-1).n.tie,'source target is not fresh');
    const first=sourceRows[0],lane=sourceLanes.get(key(first.address[0],first.address[3],first.n.string));
    const index=lane.findIndex(r=>r.n===first.n);
    need(index>=0&&sourceRows.every((r,i)=>lane[index+i]?.n===r.n),'native target differs from complete source same-string sequence');
  }
  return {checkedChains:plans.length,chains:plans.map(p=>({origin:p.rows[0].address,ties:p.rows.slice(1).map(r=>r.address),target:p.targetRow.address})),scope:'Source-authenticated written HP routing through tied holds; no acoustic technique claim'};
}

export function restoreHammerPullThroughTies(score) {
  const plans=plan(score); // All conflicts refuse before any mutation.
  let restored=0;
  for(const p of plans) {
    if(p.origin.hammerPullDestination===p.target)continue;
    p.origin.hammerPullDestination=p.target;p.target.hammerPullOrigin=p.origin;
    p.first.hammerPullOrigin=null;restored++;
  }
  return {restoredChains:restored,checkedChains:plans.length,scope:'HP playback routing only; written flags, notes, dynamics and slur layout retained'};
}
