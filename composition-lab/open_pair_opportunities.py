"""Rejoin accepted eligible open-string opportunities without inventing labels."""
import argparse,json
from pathlib import Path
from collections import Counter,defaultdict
from copy import deepcopy
from fractions import Fraction as F
from performance_opportunities import opportunities
from artist_profiles import stable_hash
from engine_contract import sha
from analyze_relationships import hopo


def join(report,baseline,artist):
    events,_=opportunities(report)
    training=[e for e in events if e['partition']=='development' and not e['flagged']]
    if stable_hash(training)!=baseline['training_sha256']:
        raise ValueError('Accepted analysis does not reproduce baseline training events')
    selected=[e for e in events if e['artist']==artist and not e['flagged'] and e['known'][0] in ('hammer_on_from_open','pull_off_to_open')]
    tracks={};song_ids=set()
    for song in report['songs']:
        if song['song_id'] in song_ids:raise ValueError('Duplicate source song')
        song_ids.add(song['song_id'])
        for track in song['tracks']:
            key=(song['song_id'],track['part_id'])
            if key in tracks:raise ValueError('Duplicate source track')
            tracks[key]=track
    groups=defaultdict(list)
    for e in selected:groups[e['song_id'],e['part_id']].append(e)
    joined=[];seen=set();counts=defaultdict(Counter)
    for key,es in groups.items():
        track=tracks[key];rows=track['rows'];lookup={n['occurrence']:n for n in rows}
        if len(lookup)!=len(rows):raise ValueError('Duplicate source occurrence')
        marked=deepcopy(rows)
        for n in marked:n['effects']=list(set(n['effects'])|{'hp'})
        pairs,_=hopo(marked,track.get('grace_rows',[]));byorigin=defaultdict(list)
        for pair in pairs:byorigin[pair['origin']].append(pair)
        for e in es:
            if len(e['members'])!=1:raise ValueError('Unique origin required')
            origin=e['members'][0];choices=[p for p in byorigin[origin] if p['direction']+'_'+p['context']==e['known'][0]]
            if len(choices)!=1:raise ValueError('Ambiguous or missing eligible pair')
            pair=choices[0];a,b=lookup[origin],lookup[pair['destination']];ident=(*key,origin,pair['destination'])
            if ident in seen:raise ValueError('Duplicate eligible pair')
            seen.add(ident)
            if (a['voice']!=b['voice'] or a['string']!=b['string'] or a['midi'] is None or b['midi'] is None
                or a['tie_destination'] or b['tie_destination'] or F(a['onset_q'])+F(a['duration_q'])!=F(b['onset_q'])
                or F(a['duration_q'])<=0 or F(b['duration_q'])<=0):
                raise ValueError('Unresolved pair identity/clock/pitch')
            correct=(a['fret']==0 and b['fret']>0) if e['known'][0]=='hammer_on_from_open' else (a['fret']>0 and b['fret']==0)
            if not correct:raise ValueError('Pair direction/open endpoint differs')
            joined.append(dict(e,origin=origin,destination=b['occurrence'],origin_fret=a['fret'],destination_fret=b['fret'],
                fret_distance=abs(b['fret']-a['fret']),origin_duration_q=a['duration_q'],destination_duration_q=b['duration_q'],
                origin_onset_q=a['onset_q'],destination_onset_q=b['onset_q'],voice=a['voice'],string=a['string']))
            counts[e['partition'],e['known'][0]]['eligible']+=1
            counts[e['partition'],e['known'][0]]['marked' if e['labels'] else 'unmarked']+=1
    if not joined or len(joined)!=len(selected):raise ValueError('Nonempty complete reconciliation required')
    return dict(schema='joined-existing-open-pair-opportunities-v1',all_existing_opportunities_joined=True,
        duplicate_or_unknown_joins=0,counts=[dict(partition=k[0],feature=k[1],**v) for k,v in sorted(counts.items())],events=joined,
        limitations=['Inherited exclusion reasons are uncounted, not zero.','Unmarked is a notation negative, not physical performance truth.'])


def run(report_path,baseline_path,output,artist):
    report_path,baseline_path,output=map(Path,(report_path,baseline_path,output))
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private output required')
    seals={str(p):sha(p) for p in (report_path,baseline_path)}
    result=join(json.loads(report_path.read_text(encoding='utf-8')),json.loads(baseline_path.read_text(encoding='utf-8')),artist)
    if seals!={str(p):sha(p) for p in (report_path,baseline_path)}:raise ValueError('Input changed during join')
    result.update(source=dict(path=str(report_path.resolve()),sha256=seals[str(report_path)]),baseline_model_sha256=seals[str(baseline_path)],join_code_sha256=sha(__file__))
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,separators=(',',':'))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('report','baseline','output'):parser.add_argument(name,type=Path)
    parser.add_argument('--artist',required=True);args=parser.parse_args()
    result=run(args.report,args.baseline,args.output,args.artist)
    print(json.dumps(dict(joined=len(result['events']),counts=result['counts'])))
