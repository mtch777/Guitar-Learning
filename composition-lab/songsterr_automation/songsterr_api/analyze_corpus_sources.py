"""Source-notation inventory, independent of GP conversion and AI judgments."""
from collections import Counter
from fractions import Fraction as F
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from technique_analysis import classify_group
from pedal_patterns import detect_bursts


def analyze(root):
    songs=[]
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or not (folder/'metadata.json').exists():continue
        meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'));tracks=[]
        for file in sorted(folder.glob('track-*.json')):
            part=json.loads(file.read_text(encoding='utf-8'));program=part.get('instrumentId');counts=Counter();groups=Counter();rows=[];order=0;offset=F(0);signature=[4,4];section='Unannotated';section_start=1
            guitar=program is not None and 24<=program<=39
            for mi,m in enumerate(part.get('measures',[])):
                signature=m.get('signature') or signature
                marker=m.get('marker')
                if marker:section=str(marker);section_start=mi+1
                for vi,v in enumerate(m.get('voices',[])):
                    local=F(0)
                    for bi,b in enumerate(v.get('beats',[])):
                        duration=F(*b['duration'])*4 if b.get('duration') else F(0)
                        if b.get('graceNote'):counts['grace_beats']+=1;continue
                        active=[];counts['beats']+=1
                        for ni,n in enumerate(b.get('notes',[])):
                            if n.get('rest'):continue
                            counts['note_segments']+=1;counts['attacks']+=not bool(n.get('tie'))
                            for field in ('hp','bend','slide','leftHandVibrato','vibrato','wideVibrato','harmonic','dead','ghost'):
                                if n.get(field):counts['note_marker:'+field]+=1
                            if any(n.get(k) or b.get(k) for k in ('leftHandVibrato','vibrato','wideVibrato')):counts['vibrato_marked_note_segments']+=1
                            tuning=part.get('tuning',[]);string=n.get('string');fret=n.get('fret')
                            if not guitar or not isinstance(string,int) or not isinstance(fret,(int,float)) or not 0<=string<len(tuning):continue
                            order+=1
                            row=dict(occurrence=f'{part.get("partId",file.stem)}:{mi+1}:{vi}:{bi}:{ni}',order=order,bar=mi+1,section=section,section_start=section_start,voice=vi,onset_q=str(offset+local),duration_q=str(duration),midi=tuning[string]+fret+(part.get('capo') or 0),string=string,fret=fret,tie_destination=bool(n.get('tie')),pitch_effects=bool(n.get('bend') or n.get('harmonic') or b.get('tremoloBar')))
                            if n.get('dead'):row['midi']=None
                            rows.append(row);active.append(row)
                        if guitar:groups.update(classify_group(active))
                        local+=duration
                offset+=F(4*signature[0],signature[1])
            candidates=detect_bursts(rows) if guitar else []
            burst_lengths=Counter(length for c in candidates for i,length in enumerate(c['burst_attack_counts']) if i%2==0)
            tracks.append(dict(part_id=part.get('partId'),name=part.get('name') or part.get('instrument'),program=program,guitar_or_bass=guitar,counts=dict(counts),coattack_groups=dict(groups),pedal_burst_candidates=len(candidates),observed_anchor_burst_lengths=dict(burst_lengths)))
        songs.append(dict(song_id=meta['songId'],revision_id=meta['revisionId'],title=meta.get('title'),artist=meta.get('artist'),tracks=tracks))
    return dict(schema='songsterr-source-technique-inventory-v1',songs=songs,
                limitations=['Written notation, not recorded performance','Marker absence is not proof of technique absence','Dyads/chords are simultaneous attacks on distinct strings; sounding bend/harmonic intervals unresolved','Overlapping pedal candidates are not verified musical functions or independent examples','No artist-feel or generative-quality judgment'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();report=analyze(a.corpus);a.out.write_text(json.dumps(report,indent=2));print(json.dumps(dict(songs=len(report['songs']),tracks=sum(len(s['tracks']) for s in report['songs']))))
