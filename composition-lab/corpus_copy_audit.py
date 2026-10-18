"""Known-corpus relative attack-window audit; never an originality verdict.

Includes attack spacing, individual sounding lengths and simultaneous pitch sets.
Unknown/dead pitches split streams. Tied destinations do not create attacks.
All source-derived locations and hashes are private artifacts.
"""
from collections import defaultdict,Counter
from fractions import Fraction as F
import argparse,hashlib,json
from pathlib import Path


def source_streams(report):
    out=[];excluded=Counter()
    for song in report['songs']:
        for track in song['tracks']:
            if not track.get('guitar_or_bass'):continue
            if not track.get('temporal_relationships_eligible'):
                excluded['temporal_tracks']+=1;continue
            tails={c['origin']:c['end_q'] for c in track.get('sustain_relationships',{}).get('chains',[])}
            lanes=defaultdict(lambda:defaultdict(list))
            for n in track['rows']:
                if not n['tie_destination']:lanes[n['voice']][F(n['onset_q'])].append(n)
            for voice,groups in lanes.items():
                stream=[]
                def flush():
                    if stream:out.append(dict(song_id=song['song_id'],part_id=track['part_id'],voice=voice,
                        partition=song['provisional_partition'],events=stream.copy()))
                    stream.clear()
                for q,notes in sorted(groups.items()):
                    if any(n['midi'] is None for n in notes):flush();continue
                    stream.append(dict(q=str(q),notes=sorted((n['midi'],str(F(tails.get(n['occurrence'],q+F(n['duration_q'])))-q)) for n in notes),
                        members=[n['occurrence'] for n in notes]))
                flush()
    return out,dict(excluded)


def generated_streams(score):
    result=[]
    for ti,track in enumerate(score['tracks']):
        lanes=defaultdict(list)
        for m in track['measures']:
            for vi,voice in enumerate(m['voices']):
                for e in voice:
                    if e['notes']:lanes[vi].append(dict(q=e['onset_q'],notes=sorted((n['midi'],str(F(e['duration_q']))) for n in e['notes'])))
        result.extend(dict(track=ti,voice=v,events=events) for v,events in lanes.items())
    return result


def fingerprint(events):
    anchor=events[0]['notes'][0][0];q=F(events[0]['q'])
    signature=tuple((str(F(e['q'])-q),tuple((str(F(str(p))-F(str(anchor))),str(F(d))) for p,d in e['notes'])) for e in events)
    digest=hashlib.sha256(json.dumps(signature,separators=(',',':')).encode()).hexdigest()
    constant=len({tuple(p for p,d in e['notes']) for e in events})==1
    return digest,constant


def audit(report,directory,lengths=(8,16,32)):
    streams,excluded=source_streams(report);indexes={n:defaultdict(list) for n in lengths}
    for stream in streams:
        events=stream['events']
        for length,index in indexes.items():
            for start in range(len(events)-length+1):
                key,_=fingerprint(events[start:start+length])
                if len(index[key])<3:index[key].append(dict(song_id=stream['song_id'],part_id=stream['part_id'],voice=stream['voice'],partition=stream['partition'],members=events[start]['members']))
    outputs=[];music_hashes=defaultdict(list);openings=defaultdict(list)
    for path in sorted(directory.glob('*.expected.json')):
        score=json.loads(path.read_text(encoding='utf-8'));candidate=generated_streams(score);counts={n:Counter() for n in lengths};examples=[];example_counts=Counter()
        music_hash=hashlib.sha256(json.dumps(candidate,sort_keys=True,separators=(',',':')).encode()).hexdigest();music_hashes[music_hash].append(path.name)
        for lane in candidate:
            if len(lane['events'])>=8:openings[(lane['track'],lane['voice'],fingerprint(lane['events'][:8])[0])].append(path.name)
        for lane in candidate:
            for length,index in indexes.items():
                for start in range(len(lane['events'])-length+1):
                    key,constant=fingerprint(lane['events'][start:start+length]);counts[length]['windows']+=1
                    if key in index:
                        counts[length]['constant_voicing_matches' if constant else 'varied_voicing_matches']+=1
                        bucket=(length,constant)
                        if example_counts[bucket]<12:
                            window=lane['events'][start:start+length];pitch_sets=[tuple(p for p,d in e['notes']) for e in window]
                            examples.append(dict(track=lane['track'],voice=lane['voice'],start_q=lane['events'][start]['q'],length=length,constant_voicing=constant,
                                distinct_pitch_sets=len(set(pitch_sets)),minimum_pitch_changes=sum(min(a)!=min(b) for a,b in zip(pitch_sets,pitch_sets[1:])),
                                distinct_written_lengths=len({str(F(d)) for e in window for p,d in e['notes']}),sources=index[key]));example_counts[bucket]+=1
        outputs.append(dict(file=path.name,counts={str(n):dict(c) for n,c in counts.items()},examples=examples))
    return dict(schema='known-corpus-relative-copy-audit-v1',source_streams=len(streams),excluded=excluded,outputs=outputs,
        identical_generated_music=[names for names in music_hashes.values() if len(names)>1],
        shared_relative_harmony_openings=[names for (track,voice,key),names in openings.items() if track==0 and len(names)>1],
        shared_relative_track_openings=[dict(track=track,voice=voice,files=names) for (track,voice,key),names in openings.items() if len(names)>1],
        limitations=['Supplied corpus only, not a musical originality/copyright determination.',
            'SHA256 relative pitch/timing/length windows; articulation, effects and expression excluded.',
            'Constant repeated voicings are reported separately; common chugs are not automatically rejected.',
            'Source attack streams exclude unknown/dead events and honor resolved tied lengths.',
            'Within-voice attack membership with sustain lengths, not complete sounding texture or cross-voice matching.'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('report','directory','out'):p.add_argument(n,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private source-location output only')
    result=audit(json.loads(a.report.read_text(encoding='utf-8')),a.directory)
    a.out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    totals=Counter()
    for r in result['outputs']:
        for n,c in r['counts'].items():
            for k,v in c.items():totals[n+':'+k]+=v
    print(json.dumps(dict(outputs=len(result['outputs']),counts=dict(totals),identical_generated_music=result['identical_generated_music'],shared_openings=result['shared_relative_harmony_openings'])))
