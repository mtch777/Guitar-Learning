const INTERVALS = [0,4,7];
const ALTER = {'♯':1,'♭':-1};
const XML_ESCAPE = value => String(value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

export function writtenChord(chord) {
  if (!chord || !Array.isArray(chord.notes) || chord.notes.length!==3) {
    throw new TypeError('Major triad requires three spelled pitches.');
  }
  return chord.notes.map((name,i)=>{
    const midi=60+chord.root+INTERVALS[i];
    const step=name[0], accidental=name.slice(1);
    if (!'CDEFGAB'.includes(step) || !Object.prototype.hasOwnProperty.call(ALTER,accidental) && accidental!=='') {
      throw new RangeError('Unsupported written pitch '+name);
    }
    return {midi,step,alter:ALTER[accidental]||0,octave:Math.floor(midi/12)-1,accidental};
  });
}

function noteXML(pitch,chordMember=false) {
  const alter = pitch.alter ? '<alter>'+pitch.alter+'</alter>' : '';
  const accidental = pitch.alter ? '<accidental>'+(pitch.alter>0?'sharp':'flat')+'</accidental>' : '';
  return '<note>'+(chordMember?'<chord/>':'')+
    '<pitch><step>'+pitch.step+'</step>'+alter+'<octave>'+pitch.octave+'</octave></pitch>'+
    '<duration>1920</duration><type>whole</type>'+accidental+'</note>';
}

export function buildTriadMusicXML(chords) {
  if (!Array.isArray(chords) || !chords.length) throw new TypeError('At least one major triad is required.');
  const head=`<?xml version="1.0" encoding="utf-8"?>
<score-partwise version="4.0">
<work><work-title>Major Triads</work-title></work>
<movement-title>Major Triads</movement-title>
<part-list><score-part id="P1"><part-name>Piano</part-name><part-abbreviation>Pno.</part-abbreviation></score-part></part-list>
<part id="P1">`;
  const measures=chords.map((chord,index)=>{
    const attributes=index===0 ?
      '<attributes><divisions>480</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>' : '';
    const label='<direction placement="above"><direction-type><words font-weight="bold" font-size="12">'+XML_ESCAPE(chord.name)+'</words></direction-type></direction>';
    return '<measure implicit="no" number="'+(index+1)+'">'+attributes+label+
      writtenChord(chord).map((pitch,i)=>noteXML(pitch,i>0)).join('')+'</measure>';
  });
  return head+measures.join('')+'</part></score-partwise>';
}