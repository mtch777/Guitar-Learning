"""Evaluate the additive pass against sealed source-supported seeds, privately."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'songsterr_automation/songsterr_api'))
from build_pedal_evidence_review import support_regions
from pedal_expansion import expand_phrases


def evaluate(report,analyses):
    lookup={(s['song_id'],s['part_id'],s['section_start']):s for s in analyses}
    results=[];counts=Counter()
    for song in report['songs']:
        for track in song['tracks']:
            seeds=[];rows=track['rows'];byid={n['occurrence']:n for n in rows}
            for section in sorted({n['section_start'] for n in rows}):
                a=lookup.get((song['song_id'],track['part_id'],section))
                if not a or not a['accepted']:continue
                for i,r in enumerate(support_regions(a,rows,track.get('sustain_relationships',{}).get('chains',[]))):
                    seeds.append(dict(r,id=f'{section}:{i}',roles={k:v for k,v in a['roles'].items() if k in r['members']},
                        members=sorted(r['members']),return_members=sorted(r['return_members'])))
            if not seeds:continue
            snapshot=deepcopy(seeds)
            phrases=expand_phrases(rows,seeds,sustain_chains=track.get('sustain_relationships',{}).get('chains',[]))
            assert seeds==snapshot,'Seed mutation'
            mapped={ident:r for r in phrases for ident in r['seed_ids']}
            assert len(mapped)==len(seeds),'Lost or duplicated seed'
            for s in seeds:
                r=mapped[s['id']]
                assert set(s['members'])<=set(r['members'])
                assert all(r['roles'][i]==role for i,role in s['roles'].items()),'Original highlight changed'
            for r in phrases:
                for c in r['added_cycles']:
                    assert set(c['call_members']+c['response_members'])<=byid.keys()
                    assert all(not byid[i]['tie_destination'] for i in c['call_members']+c['response_members'])
                    assert max(F(byid[i]['onset_q']) for i in c['call_members'])<min(F(byid[i]['onset_q']) for i in c['response_members'])
                    assert F(c['response_start_q'])<F(c['return_q'])
                    assert all(r['roles'][i]=='call' for i in c['call_members'])
                    assert all(r['roles'][i]=='response' for i in c['response_members'])
                assert set(r['members'])<=byid.keys()
                counts[r['direction']]+=1
                counts['original_disjoint_groups']+=len(r['original_bounds'])
                counts['added_exchanges']+=len(r['added_cycles'])
            counts['input_seeds']+=len(seeds);counts['output_phrases']+=len(phrases);counts['tracks']+=1
            results.append(dict(song_id=song['song_id'],part_id=track['part_id'],seeds=seeds,phrases=phrases))
    return dict(counts=dict(counts),tracks=results)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['report','analyses','out']:p.add_argument(name,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private output only')
    algorithm=Path(__file__).with_name('pedal_expansion.py');before=hashlib.sha256(algorithm.read_bytes()).hexdigest()
    result=evaluate(json.loads(a.report.read_text(encoding='utf-8')),json.loads(a.analyses.read_text(encoding='utf-8')))
    assert before==hashlib.sha256(algorithm.read_bytes()).hexdigest(),'Code changed during evaluation'
    result['algorithm_sha256']=before
    result['detector_sha256']=hashlib.sha256(algorithm.with_name('pedal_evidence.py').read_bytes()).hexdigest()
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='tracks'}))
