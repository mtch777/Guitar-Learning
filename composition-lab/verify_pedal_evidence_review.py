"""Audit every private piano-roll note against authoritative source occurrences."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib,json
from pathlib import Path


def verify_review(report, directory, corpus):
    catalogue=json.loads((directory/'catalogue.json').read_text(encoding='utf-8'))
    jobs=json.loads((directory/'render-index.json').read_text(encoding='utf-8'))
    songs={s['song_id']:s for s in report['songs']};counts=Counter();scores=set()
    for entry in catalogue['cases']:
        detail=json.loads((directory/'cases'/(entry['id']+'.json')).read_text(encoding='utf-8'))
        song=songs[entry['song_id']];track=next(t for t in song['tracks'] if t['part_id']==entry['part_id'])
        byid={n['occurrence']:n for n in track['rows']}
        all_notes={}
        for i,window in enumerate(detail['windows']):
            lo,hi=F(window['base_q']),F(window['end_q'])
            assert lo<hi
            if i:assert detail['windows'][i-1]['end_q']==window['base_q'],'Gap between audio parts'
            expected={n['occurrence']:n for n in track['rows'] if n['midi'] is not None
                      and F(n['onset_q'])<hi and F(n['onset_q'])+F(n['duration_q'])>lo}
            observed={n['id']:n for n in window['notes']}
            assert len(observed)==len(window['notes']),'Duplicate note in a window'
            assert expected.keys()==observed.keys(),'Missing or extra source occurrence'
            for ident,n in observed.items():
                original=expected[ident]
                assert n['pitch']==original['midi'] and n['bar']==original['bar']
                assert F(n['onset_q'])==F(original['onset_q'])
                assert F(n['duration_q'])==F(original['duration_q'])
                assert n['tied']==original['tie_destination']
                if ident in all_notes:assert all_notes[ident]==n,'Inconsistent overlap note'
                all_notes[ident]=n
            if window['playable']:
                assert window['id'] in jobs
                assert len(jobs[window['id']])==2
                assert abs(window['time_map'][-1]['seconds']-window['seconds'])<1e-8
            else:counts['unavailable_audio_parts']+=1
            counts['windows']+=1;counts['note_displays']+=len(observed)
        for cycle in detail['after_cycles']:
            assert set(cycle['call_members']+cycle['response_members'])<=all_notes.keys(),'Evidence outside displayed source'
            assert max(F(byid[i]['onset_q']) for i in cycle['call_members'])<min(F(byid[i]['onset_q']) for i in cycle['response_members'])
        if entry['song_id'] not in scores:
            source=corpus/str(entry['song_id'])/'score.gp';copy=directory/'scores'/f"{entry['song_id']}.gp"
            assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(copy.read_bytes()).digest()
            scores.add(entry['song_id'])
        counts['cases']+=1
    counts['unchanged_source_scores']=len(scores)
    result=dict(counts);(directory/'source-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['report','directory','corpus']:p.add_argument(n,type=Path)
    a=p.parse_args();print(json.dumps(verify_review(json.loads(a.report.read_text(encoding='utf-8')),a.directory,a.corpus)))
