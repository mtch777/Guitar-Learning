import copy,json
from pathlib import Path
import unittest
from unittest.mock import patch
from corpus_composer import learn,generate


def fixture():
    tracks=[];raw={}
    for ti,(name,program,base) in enumerate([('Rhythm',30,40),('Lead',30,52),('Bass',34,28)]):
        rows=[]
        for bar in (1,2):
            for beat,step in enumerate((0,2,4,5)):
                rows.append(dict(occurrence=f'{ti}:{bar}:{beat}',voice=0,bar=bar,string=0,fret=step,midi=base+step,
                    tie_destination=False,onset_q=str((bar-1)*4+beat),duration_q='1',section_start=1))
        tracks.append(dict(part_id=ti,name=name,guitar_or_bass=True,temporal_relationships_eligible=True,rows=rows))
        raw[ti]=dict(instrumentId=program,tuning=[base],capo=0)
    song=dict(song_id=1,artist='Artist',ai_generated=False,is_junk=False,provisional_partition='development',
        candidate_work_family='a',notation_hash='a',tracks=tracks,
        timeline=dict(tempo=[dict(onset_q='0',quarter_bpm='137')]),
        shared_layout=[dict(bar=b,start_q=str((b-1)*4),span_q='4',signature=[4,4]) for b in (1,2)])
    return dict(songs=[song]),raw


def model_for(report,raw):
    def read(path,**kwargs):return json.dumps(raw[int(path.stem.split('-')[-1])])
    with patch.object(Path,'read_text',read):return learn(report,Path('private'),'Artist')


class ComposerTests(unittest.TestCase):
    def test_aligned_patterns_share_observed_bar_across_roles(self):
        report,raw=fixture();model=model_for(report,raw)
        a,plan=generate(model,8,23,aligned_patterns=True)
        b,_=generate(model,8,23,aligned_patterns=True)
        self.assertEqual(a,b)
        bybar={}
        for row in plan['sources']:
            bybar.setdefault(row['bar'],set()).add((row['training_song'],row['training_bar']))
            role=plan['roles'][row['track']]
            source=next(p for records in model['parts'][role].values() for p in records
                if (p['song_id'],p['part_id'],p['bar'])==(row['training_song'],row['training_part'],row['training_bar']))
            actual=a['tracks'][row['track']]['measures'][row['bar']-1]['voices'][0]
            self.assertEqual([(e['duration_q'],len(e['notes'])) for e in actual],
                [(e['duration_q'],len(e['intervals'])) for e in source['events']])
        self.assertTrue(bybar)
        self.assertTrue(all(len(s)==1 for s in bybar.values()))
        default,_=generate(model,8,23)
        explicit,_=generate(model,8,23,aligned_patterns=False)
        self.assertEqual(default,explicit)

    def test_train_only_deterministic_playable_generation(self):
        report,raw=fixture();model=model_for(report,raw)
        a,plan=generate(model,8,23);b,_=generate(model,8,23)
        self.assertEqual(a,b);self.assertEqual(len(a['tracks']),3)
        self.assertEqual(a['tempo_bpm'],'137')
        held=copy.deepcopy(report['songs'][0]);held.update(song_id=2,candidate_work_family='b',notation_hash='b',provisional_partition='held_out')
        held['tracks'][0]['rows'][0]['midi']=99;report['songs'].append(held)
        self.assertEqual(model,model_for(report,raw))

    def test_rejected_bar_cannot_contribute_roots(self):
        report,raw=fixture()
        # First two attacks overlap, so the entire first training bar is rejected.
        report['songs'][0]['tracks'][0]['rows'][1]['onset_q']='1/2'
        model=model_for(report,raw)
        seq=next(s for s in model['source_sequences'] if s['part_id']==0)['roots']
        self.assertTrue(all(int(n['onset_q'])>=4 for n in seq))
        self.assertEqual(model['excluded']['ambiguous_bar'],1)

    def test_recurrence_distinguishes_different_contours_with_same_rhythm(self):
        report,raw=fixture();rows=report['songs'][0]['tracks'][1]['rows']
        rows[5]['midi'],rows[6]['midi']=rows[6]['midi'],rows[5]['midi']
        model=model_for(report,raw)
        plan=next(p for p in model['plans'] if p['role']=='melody')
        self.assertEqual(plan['sequence'],[0,1])

    def test_unobserved_transition_across_section_is_not_learned(self):
        report,raw=fixture();rows=report['songs'][0]['tracks'][1]['rows']
        for n in rows[4:]:n['section_start']=2;n['midi']+=10
        model=model_for(report,raw)
        steps=next(iter(model['parts']['melody'].values()))[0]['root_steps']
        self.assertNotIn('5',steps) # 57 -> 62 section boundary is not a continuous step.

    def test_tie_origin_and_destination_bars_are_excluded_together(self):
        report,raw=fixture();track=report['songs'][0]['tracks'][0]
        track['sustain_relationships']=dict(chains=[dict(origin='0:1:3',members=['0:1:3','0:2:0'])])
        # Keep a third bar so the required role still has eligible training data.
        song=report['songs'][0];song['shared_layout'].append(dict(bar=3,start_q='8',span_q='4',signature=[4,4]))
        third=[dict(n,occurrence='third-'+n['occurrence'],bar=3,onset_q=str(8+i)) for i,n in enumerate(track['rows'][:4])]
        track['rows'].extend(third)
        model=model_for(report,raw)
        self.assertTrue(all(p['bar']==3 for ps in model['parts']['harmony'].values() for p in ps))


if __name__=='__main__':unittest.main()
