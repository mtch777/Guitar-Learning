"""Source-backed positive and adversarial checks, independent of detector code."""
from copy import deepcopy
import unittest
from test_connected_tier2 import documents
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze
from check_technique_connections import check


class TechniqueConnectionCheckTests(unittest.TestCase):
    def case(self):
        docs=documents();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[0]['velocity']='mf';beats[0]['notes'][0].update(vibrato=True,ghost=True,harmonic='natural',harmonicFret=12)
        upper=analyze(extract_documents(docs));return docs,upper

    def test_persisted_flags_harmonics_curve_and_inherited_dynamics(self):
        docs,upper=self.case();result=check(docs,upper)
        self.assertEqual(result['issues'],[])
        self.assertEqual(result['counts']['vibrato_persisted_declarations'],1)
        self.assertEqual(result['counts']['harmonic_persisted_declarations'],1)
        self.assertIn('dynamic_inherited_explicit',result['examples'])

    def test_unknown_beat_invalidates_history_and_note_override_does_not_replace_it(self):
        docs=documents();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[0]['velocity']='mf';beats[1]['velocity']='unrecognized';beats[2]['notes'][0]['velocity']='f'
        upper=analyze(extract_documents(docs));result=check(docs,upper)
        self.assertEqual(result['status'],'PASS_SOURCE_BACKED_RELATIONSHIPS')
        states=upper['derived_views']['techniques']['tracks'][0]['dynamics']
        self.assertEqual([d['known'] for d in states],[True,False,True,False])
        self.assertEqual(states[-1]['marking_origin'],dict(bar=1,voice=0,beat=1))

    def test_omissions_and_duplicates_fail_independent_denominators(self):
        docs,original=self.case()
        for kind in ('track','effect','dynamic','occurrence','parameter'):
            for duplicate in (False,True):
                upper=deepcopy(original);tracks=upper['derived_views']['techniques']['tracks']
                if kind=='track':items=tracks
                elif kind=='effect':items=upper['owned_parameters']['technique_declarations']['groups']
                elif kind=='parameter':items=upper['owned_parameters']['technique_declarations']['groups'][0]['parameters']
                else:items=tracks[0]['dynamics' if kind=='dynamic' else 'source_occurrences']
                if duplicate:items.append(deepcopy(items[0]))
                else:items.pop()
                self.assertEqual(check(docs,upper)['status'],'FAIL',(kind,duplicate))

    def test_corrupt_persisted_flag_curve_and_history_detected(self):
        docs,original=self.case()
        for field in ('vibrato','bend','dynamic'):
            upper=deepcopy(original)
            if field=='dynamic':upper['derived_views']['techniques']['tracks'][0]['dynamics'][1]['marking_origin']['beat']=2
            else:
                group=next(g for g in upper['owned_parameters']['technique_declarations']['groups'] if g['field']==field)
                parameter=group['parameters'][0]['parameter']
                if field=='vibrato':parameter['symbol']=False
                else:parameter['normalized']='99'
            self.assertEqual(check(docs,upper)['status'],'FAIL')


if __name__=='__main__':unittest.main()
