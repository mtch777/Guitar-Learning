// Independent raw-source oracle for reimported native GP. No restoration imports.
const schema='independent-source-grace-check/1';
const rational=(n,d=1n)=>{if(d===0n)throw Error('Zero rational denominator');if(d<0n){n=-n;d=-d;}return[n,d];};
const add=(a,b)=>rational(a[0]*b[1]+b[0]*a[1],a[1]*b[1]);
const eq=(a,b)=>a[0]*b[1]===b[0]*a[1];
const text=a=>{let[n,d]=a,x=n<0n?-n:n,y=d;while(y){const r=x%y;x=y;y=r;}n/=x||1n;d/=x||1n;return d===1n?String(n):`${n}/${d}`;};
function rawQuarter(beat){
  const d=beat.duration;
  if(!Array.isArray(d)||d.length!==2||!d.every(Number.isSafeInteger)||d[0]<=0||d[1]<=0)throw Error('Positive exact source duration required');
  return rational(BigInt(d[0])*4n,BigInt(d[1]));
}
function nativeQuarter(beat){
  if(!Number.isSafeInteger(beat.duration)||beat.duration<=0||!Number.isInteger(beat.dots)||beat.dots<0||beat.dots>8)throw Error('Unsupported native notation duration');
  let n=beat.tupletNumerator,d=beat.tupletDenominator;
  if(n===-1&&d===-1){n=1;d=1;}
  if(!Number.isSafeInteger(n)||!Number.isSafeInteger(d)||n<=0||d<=0)throw Error('Unknown native tuplet convention');
  const power=2n**BigInt(beat.dots);
  return rational(4n*(2n*power-1n)*BigInt(d),BigInt(beat.duration)*power*BigInt(n));
}
function ticks(q){
  const numerator=q[0]*960n;
  if(numerator%q[1]!==0n)throw Error('Unsupported noninteger native tick grid');
  const value=Number(numerator/q[1]);if(!Number.isSafeInteger(value))throw Error('Native tick grid outside exact integer range');return value;
}
function mode(beat){
  const value=beat.graceNote;
  if(value===undefined||value===null||value===false)return 0;
  if(value==='onBeat')return 1;
  if(value==='beforeBeat')return 2;
  throw Error('Unknown source grace declaration');
}
function sourceCapo(raw){
  if(raw.capo===undefined||raw.capo===null)return 0;
  if(!Number.isSafeInteger(raw.capo)||raw.capo<0)throw Error('Unknown source capo declaration');return raw.capo;
}

export function checkSourceGraces(score,parts,types={None:0,OnBeat:1,BeforeBeat:2}){
  const differences=[],witnesses=[],uncheckedPercussion=[],glyphDurationDifferences=[];
  const counts={sourceGraceVoices:0,pitchedGraceVoicesChecked:0,checkedVoiceBeats:0,checkedNotes:0,checkedGraceBeats:0,checkedGraceNotes:0,uncheckedPercussionGraceBeats:0,uncheckedPercussionGraceNotes:0};
  const fail=(code,where,expected,actual)=>differences.push({code,...where,expected:expected??null,actual:actual??null});
  try{
    if(types?.None!==0||types?.OnBeat!==1||types?.BeforeBeat!==2)throw Error('Pinned native grace enum required');
    if(!Array.isArray(parts)||!Array.isArray(score?.tracks)||parts.length!==score.tracks.length)throw Error('Complete source/native track correspondence required');
    for(const[ti,raw]of parts.entries()){
      if(raw.partId!==undefined&&raw.partId!==ti){fail('SOURCE_PART_ADDRESS',{track:ti},ti,raw.partId);continue;}
      const track=score.tracks[ti];
      for(const[mi,measure]of(raw.measures??[]).entries())for(const[vi,voice]of(measure.voices??[]).entries()){
        const source=voice.beats??[],where={track:ti,bar_zero_based:mi,voice:vi};
        if(!Array.isArray(source)){fail('SOURCE_BEAT_ARRAY',where,'array',typeof source);continue;}
        if(raw.instrumentId===1024){
          const graceIndices=source.flatMap((b,i)=>b.graceNote?[i]:[]);if(!graceIndices.length)continue;
          counts.sourceGraceVoices++;
          const notes=graceIndices.reduce((n,i)=>n+(source[i].notes??[]).filter(x=>!x.rest).length,0);
          counts.uncheckedPercussionGraceBeats+=graceIndices.length;counts.uncheckedPercussionGraceNotes+=notes;
          uncheckedPercussion.push({...where,source_beat_indices:graceIndices,source_grace_notes:notes,status:'UNCHECKED_PERCUSSION_DOMAIN'});continue;
        }
        let kinds;try{kinds=source.map(mode);}catch(e){fail('UNKNOWN_SOURCE_GRACE',where,e.message,null);continue;}
        const graceIndices=kinds.flatMap((k,i)=>k?[i]:[]);if(!graceIndices.length)continue;
        counts.sourceGraceVoices++;
        if(!Number.isInteger(raw.instrumentId)||raw.instrumentId<0||raw.instrumentId>127){fail('UNKNOWN_INSTRUMENT_DOMAIN',where,'source program0..127',raw.instrumentId);continue;}
        if(!Array.isArray(track?.staves)||track.staves.length!==1){fail('STAFF_CORRESPONDENCE',where,1,track?.staves?.length);continue;}
        const staff=track.staves[0];
        if(staff.isPercussion||!Array.isArray(raw.tuning)||!raw.tuning.every(Number.isSafeInteger)||JSON.stringify(staff.tuning)!==JSON.stringify(raw.tuning)){
          fail('INSTRUMENT_TUNING',where,raw.tuning,staff.tuning);continue;
        }
        let capo;try{capo=sourceCapo(raw);}catch(e){fail('SOURCE_CAPO',where,e.message,null);continue;}
        if(staff.capo!==capo){fail('CAPO',where,capo,staff.capo);continue;}
        const native=staff.bars?.[mi]?.voices?.[vi]?.beats;
        if(!Array.isArray(native)||native.length!==source.length){fail('FULL_VOICE_BEAT_COUNT',where,source.length,native?.length);continue;}
        const groups=[];
        for(let i=0;i<source.length;i++){
          if(!kinds[i])continue;
          const first=i,kind=kinds[i];while(i+1<source.length&&kinds[i+1])i++;
          if(kinds.slice(first,i+1).some(x=>x!==kind))fail('MIXED_GRACE_GROUP',{...where,beat:first},'homogeneous declared mode',kinds.slice(first,i+1));
          if(i+1===source.length||!(source[i+1].notes??[]).some(n=>!n.rest))fail('UNAVAILABLE_ORDINARY_HOST',{...where,beat:first},'ordinary non-rest host within same bar',null);
          groups.push({first_source_beat:first,last_source_beat:i,host_source_beat:i+1<source.length?i+1:null,source_grace_type:kind});
        }
        let cursor=rational(0n),nativeTotal=0;const beatWitnesses=[];
        for(let bi=0;bi<source.length;bi++){
          const a=source[bi],b=native[bi],loc={...where,beat:bi},sourceRef=`track-${ti}.json#/measures/${mi}/voices/${vi}/beats/${bi}`;
          if(!b||!Array.isArray(b.notes)){fail('NATIVE_BEAT',loc,'native beat with notes',null);continue;}
          counts.checkedVoiceBeats++;
          if(b.index!==bi||b.isEmpty)fail('NATIVE_BEAT_IDENTITY',loc,{index:bi,empty:false},{index:b.index,empty:b.isEmpty});
          if(b.graceType!==kinds[bi])fail('GRACE_MODE',loc,kinds[bi],b.graceType);
          let start;try{start=ticks(cursor);}catch(e){fail('UNSUPPORTED_EXACT_GRID',loc,e.message,null);continue;}
          if(b.displayStart!==start)fail('NOMINAL_ONSET',loc,start,b.displayStart);
          let declared;try{declared=rawQuarter(a);}catch(e){fail('SOURCE_DURATION',loc,e.message,a.duration);continue;}
          if(kinds[bi]){
            counts.checkedGraceBeats++;
            if(b.displayDuration!==0)fail('GRACE_NOMINAL_SPAN',loc,0,b.displayDuration);
            let glyph;try{glyph=nativeQuarter(b);}catch(e){fail('NATIVE_GRACE_NOTATION',loc,e.message,null);}
            if(a.type!==b.duration||(glyph&&!eq(glyph,declared)))glyphDurationDifferences.push({...loc,source_ref:sourceRef,source_type:a.type??null,source_duration_q:text(declared),native_type:b.duration,native_glyph_duration_q:glyph?text(glyph):null,status:'NATIVE_GLYPH_NORMALIZATION_NOT_SOURCE_PARITY'});
          }else{
            let notation;try{notation=nativeQuarter(b);}catch(e){fail('NATIVE_REGULAR_NOTATION',loc,e.message,null);}
            if(notation&&!eq(notation,declared))fail('REGULAR_NOTATION_DURATION',loc,text(declared),text(notation));
            let length;try{length=ticks(declared);}catch(e){fail('UNSUPPORTED_EXACT_GRID',loc,e.message,null);}
            if(length!==undefined&&b.displayDuration!==length)fail('REGULAR_METRIC_DURATION',loc,length,b.displayDuration);
            cursor=add(cursor,declared);
          }
          if(!Number.isSafeInteger(b.displayDuration)||b.displayDuration<0)fail('NATIVE_METRIC_DURATION',loc,'nonnegative exact tick count',b.displayDuration);else nativeTotal+=b.displayDuration;
          const sourceNotes=(a.notes??[]).filter(n=>!n.rest);
          if(sourceNotes.length!==b.notes.length)fail('NOTE_COUNT',loc,sourceNotes.length,b.notes.length);
          const rawKeys=new Map(),nativeKeys=new Map();
          for(let ni=0;ni<sourceNotes.length;ni++){
            const n=sourceNotes[ni];
            if(!Number.isSafeInteger(n.string)||n.string<0||n.string>=raw.tuning.length||!Number.isSafeInteger(n.fret)||n.fret<0){fail('SOURCE_MEMBER',loc,'known integer string/fret',n);continue;}
            const key=`${n.string}:${n.fret}`;
            if(rawKeys.has(key)||[...rawKeys.values()].some(x=>x.string===n.string))fail('AMBIGUOUS_SOURCE_MEMBER',loc,'unique source string and fret',key);
            rawKeys.set(key,n);
          }
          for(const n of b.notes){
            const string=raw.tuning.length-n.string,key=`${string}:${n.fret}`;
            if(!Number.isSafeInteger(string)||!Number.isSafeInteger(n.fret)||nativeKeys.has(key)||[...nativeKeys.values()].some(x=>x.string===n.string))fail('AMBIGUOUS_NATIVE_MEMBER',loc,'unique known native string/fret',key);
            nativeKeys.set(key,n);
          }
          if(JSON.stringify([...rawKeys.keys()].sort())!==JSON.stringify([...nativeKeys.keys()].sort()))fail('NOTE_MEMBERSHIP',loc,[...rawKeys.keys()].sort(),[...nativeKeys.keys()].sort());
          for(const[key,n]of rawKeys){
            const actual=nativeKeys.get(key);if(!actual)continue;counts.checkedNotes++;
            if(kinds[bi]){
              counts.checkedGraceNotes++;
              if(n.ghost!==undefined&&typeof n.ghost!=='boolean')fail('UNKNOWN_SOURCE_GHOST',loc,'boolean/absent',n.ghost);
              else if(actual.isGhost!==(n.ghost===true))fail('GHOST_FLAG',loc,n.ghost===true,actual.isGhost);
            }
          }
          beatWitnesses.push({source_ref:sourceRef,native_index:bi,source_grace_type:kinds[bi],expected_display_start:start,actual_display_start:b.displayStart,actual_display_duration:b.displayDuration,source_member_keys:[...rawKeys.keys()].sort()});
        }
        let expectedTotal;try{expectedTotal=ticks(cursor);}catch(e){fail('UNSUPPORTED_EXACT_VOICE_GRID',where,e.message,null);}
        if(expectedTotal!==undefined&&nativeTotal!==expectedTotal)fail('VOICE_NOMINAL_TOTAL',where,expectedTotal,nativeTotal);
        counts.pitchedGraceVoicesChecked++;
        witnesses.push({...where,source_beat_count:source.length,native_beat_count:native.length,source_regular_duration_q:text(cursor),expected_native_total_ticks:expectedTotal??null,actual_native_total_ticks:nativeTotal,groups,beats:beatWitnesses});
      }
    }
  }catch(error){fail('INVALID_INPUT',{},error.message,null);}
  return {schema,status:differences.length?'FAIL_INDEPENDENT_PITCHED_SOURCE_GRACES':'PASS_INDEPENDENT_PITCHED_SOURCE_GRACES',pitched_scope_status:counts.pitchedGraceVoicesChecked?'CHECKED_PITCHED_GRACE_VOICES':'NO_COVERED_PITCHED_GRACE_VOICES',counts,differences,witnesses,unchecked_percussion:uncheckedPercussion,glyph_duration_differences:glyphDurationDifferences,
    limitations:['Source-grace voices on known pitched programs only; percussion is explicitly unchecked','Original written grace duration/type remains exact in T1; native glyph normalization is reported, not source equality','Zero nominal grace span does not specify performed duration; pinned renderer allocation is not source acoustic truth','Exact one-to-one member/beat scope; no host recovery, missing-note reconstruction, or inferred musical voice','Exact nominal clock domain uses integer ticks at960perquarter; unsupported fractional native grids fail closed']};
}
