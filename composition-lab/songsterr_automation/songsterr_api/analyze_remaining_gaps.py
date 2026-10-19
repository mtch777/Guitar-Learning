"""Fast corpus audit of additive slide, unpitched-tie and local timing details.

Private source-located evidence is separate from public aggregate counts.
Independent interval/set checks use the validator, never production classifiers.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

from analyze_relationships import occurrences
from source_relationship_details import relationship_details
from source_semantics import layout, rests
from validate_technique_analysis import labels as independent_labels


def analyze(corpus):
    counts=Counter();statuses=Counter();types=Counter();groups=Counter();errors=[];evidence=[]
    def check(ok,kind,location):
        counts[kind+'_checked']+=1
        if not ok:
            counts['failed_checks']+=1
            if len(errors)<50:errors.append(dict(kind=kind,location=location))
    for folder in sorted(corpus.iterdir()):
        if not (folder/'metadata.json').exists():continue
        counts['entries']+=1
        meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8-sig'))
        files=sorted(folder.glob('track-*.json'),key=lambda p:int(p.stem.split('-')[-1]))
        parts=[json.loads(p.read_text(encoding='utf-8-sig')) for p in files]
        headers,shared=layout(parts)
        for i,part in enumerate(parts):
            counts['tracks']+=1
            rows,grace,_,warnings=occurrences(part,headers)
            warnings+=rests(part,headers)[1]
            identity=[]
            for key,expected in [('songId',meta['songId']),('revisionId',meta['revisionId']),('partId',int(files[i].stem.split('-')[-1]))]:
                if key in part and part[key]!=expected:identity.append(dict(reason='mismatched_'+key))
            catalog=(meta.get('tracks') or [])
            flags=catalog[i] if i<len(catalog) else {}
            program=part.get('instrumentId')
            guitar=isinstance(program,int) and 24<=program<=39 and not flags.get('isVocalTrack') and not flags.get('isEmpty')
            invalid=bool(warnings or shared or identity)
            details=relationship_details(part,headers,rows,grace,warnings,[*shared,*identity],recover_groups=guitar and invalid)
            counts['details_tracks_processed']+=1
            if not guitar:continue
            counts['guitar_bass_tracks']+=1
            lookup={r['occurrence']:r for r in rows+grace}
            if invalid:
                counts['globally_timing_excluded_guitar_tracks']+=1
                counts['bars_in_excluded_guitar_tracks']+=len(part.get('measures',[]))
                counts['safe_bars_in_excluded_guitar_tracks']+=sum(r['end_bar']-r['start_bar']+1 for r in details['local_timing']['all_voice_regions'])
            for event in details['slides']['events']:
                statuses[event['status']]+=1;types[event['type']]+=1
                if event['status']!='resolved_written_target':continue
                a,b=lookup[event['origin']],lookup[event['destination']]
                chain=[a,*[lookup[x] for x in event['tied_members']]]
                check(a['string']==b['string'] and a['voice']==b['voice'] and b['midi'] is not None and a['midi'] is not None
                      and a['fret']!=b['fret'] and not b['tie_destination']
                      and F(a['onset_q'])+sum((F(r['duration_q']) for r in chain),F(0))==F(b['onset_q'])
                      and event['interval_semitones']==b['midi']-a['midi'] and event['timing_eligible'],
                      'slide_endpoint',[folder.name,part.get('partId'),event['occurrence']])
            for link in details['unpitched_ties']['links']:
                a,b=lookup[link['origin']],lookup[link['destination']]
                check(a['raw_note'].get('dead') is True and b['raw_note'].get('dead') is True and b['tie_destination']
                      and a['midi'] is None and b['midi'] is None and a['voice']==b['voice'] and a['string']==b['string']
                      and a['fret']==b['fret'] and F(a['onset_q'])+F(a['duration_q'])==F(b['onset_q'])
                      and link['sounding_pitch'] is None,'unpitched_link',[folder.name,part.get('partId'),link['destination']])
            counts['unpitched_links']+=len(details['unpitched_ties']['links'])
            counts['unpitched_unresolved']+=len(details['unpitched_ties']['unresolved'])
            for group in details['recovered_coattack_groups']:
                notes=[r for r in rows if r['onset_q']==group['onset_q'] and not r['tie_destination']]
                check(set(group['members'])=={r['occurrence'] for r in notes} and set(group['labels'])==independent_labels(notes),
                      'local_coattack',[folder.name,part.get('partId'),group['onset_q']])
                region=details['local_timing']['all_voice_regions'][group['timing_region']]
                check(all(F(region['start_q'])<=F(r['onset_q'])<F(r['onset_q'])+F(r['duration_q'])<=F(region['end_q']) for r in notes),
                      'local_timing_boundary',[folder.name,part.get('partId'),group['onset_q']])
                groups.update(group['labels'])
            evidence.append(dict(song_id=meta['songId'],part_id=part.get('partId'),details=details))
    counts.setdefault('failed_checks',0)
    source=Path(__file__)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,*[source.with_name(n) for n in
            ('source_slides.py','source_semantics.py','source_timing_regions.py','source_relationship_details.py')]]}
    public=dict(schema='source-analysis-repair-pass2-v1',counts=dict(counts),slide_status_counts=dict(statuses),
                slide_type_counts=dict(types),recovered_coattack_label_counts=dict(groups),implementation_sha256=hashes,
                limitations=['Notation relationships, not performed sound or artist intent',
                             'Additive local output does not enable existing whole-track detectors or artist-profile eligibility',
                             'Grace order and tied-origin slide candidates remain explicit unknowns'])
    return public,dict(tracks=evidence,errors=errors)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--aggregate',type=Path,required=True)
    args=p.parse_args()
    if 'local-artifacts' not in args.out.resolve().parts:p.error('Source evidence must remain in local-artifacts')
    public,private=analyze(args.corpus)
    args.out.write_text(json.dumps(private,separators=(',',':')),encoding='utf-8')
    args.aggregate.write_text(json.dumps(public,indent=2),encoding='utf-8')
    print(json.dumps(public))
    raise SystemExit(bool(public['counts'].get('failed_checks')))
