from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import tempfile,unittest
from source_bass_evidence import extract_bass_features
from check_source_bass_evidence import check


def observation(i,a,b,mask,previous=None):return dict(id=i,mask=mask,previous_mask=previous,sequence=0,start_q=a,end_q=b)
def event(ident,a,d,p,**extra):return dict(id=ident,onset_q=a,duration_q=d,pitch=p,**extra)


class SourceBassTests(unittest.TestCase):
    def test_inversions_unisons_sustain_tie_and_halfopen(self):
        events=[event('C','0','2',60),event('E','0','1',52),event('G','0','2',67),event('Eunison','0','1',52),event('Etie','1','1',52,source_tied='1')]
        rows=[observation(0,'0','1',145),observation(1,'1','2',145,145)]
        result=extract_bass_features('piece',rows,events)
        self.assertEqual(result[0]['lowest_pc'],4);self.assertEqual(result[0]['lowest_note_refs'],['E','Eunison'])
        self.assertEqual(result[1]['lowest_note_refs'],['Etie']);self.assertIn('C',result[1]['active_note_refs'])
        self.assertEqual(result[0]['status'],'KNOWN')

    def test_unknown_is_not_known_minimum_rest_and_zero_grace(self):
        events=[event('known','0','1',60),event('unknown','0','1',None),event('grace','1','0',30)]
        result=extract_bass_features('piece',[observation(0,'0','1',1),observation(1,'1','2',0)],events)
        self.assertEqual(result[0]['status'],'UNRESOLVED');self.assertIsNone(result[0]['lowest_midi']);self.assertFalse(result[0]['lowest_note_refs'])
        self.assertEqual(result[1]['status'],'EMPTY');self.assertFalse(result[1]['active_note_refs'])

    def test_transposition_split_invariance_no_mutation_or_target_input(self):
        events=[event('bass','0','1',48),event('other','0','1',64)];before=deepcopy(events)
        original=extract_bass_features('piece',[observation(0,'0','1',17)],events)[0]
        split=extract_bass_features('piece',[observation(0,'0','1/2',17),observation(1,'1/2','1',17,17)],events)
        self.assertTrue(all((r['lowest_midi'],r['lowest_note_refs'])==(original['lowest_midi'],original['lowest_note_refs'])for r in split));self.assertEqual(events,before)
        moved=[dict(e,pitch=e['pitch']+2)for e in events]
        self.assertEqual(extract_bass_features('piece',[observation(0,'0','1',68)],moved)[0]['lowest_pc'],2)
        bad=observation(0,'0','1',17);bad['target']={'state':0}
        with self.assertRaises(ValueError):extract_bass_features('piece',[bad],events)

    def test_duplicate_bad_mask_internal_change_and_boolean_pitch_refused(self):
        rows=[observation(0,'0','1',1)];events=[event('note','0','1',60)]
        for bad in (events+events,[dict(events[0],pitch=True)]):
            with self.assertRaises(ValueError):extract_bass_features('piece',rows,bad)
        with self.assertRaises(ValueError):extract_bass_features('piece',[dict(rows[0],mask=2)],events)
        with self.assertRaises(ValueError):extract_bass_features('piece',rows,events+[event('mid','1/2','1/2',64)])

    def test_independent_tsv_checker_missing_changed_and_boolean_witness(self):
        with tempfile.TemporaryDirectory()as directory:
            d=Path(directory);notes=d/'notes.tsv';measures=d/'measures.tsv'
            notes.write_text('mc\tmc_onset\tduration\tmidi\n1\t0\t1/4\t48\n1\t0\t1/4\t64\n',encoding='utf-8')
            measures.write_text('mc\tact_dur\n1\t1/4\n',encoding='utf-8')
            rows=[observation(0,'0','1',17)];features=extract_bass_features('p',rows,[event('note-row:0','0','1',48),event('note-row:1','0','1',64)])
            self.assertEqual(check('p',rows,notes,measures,features)['status'],'PASS_RAW_SOURCE_BASS_FEATURES')
            for bad in ([],[dict(features[0],lowest_midi=60)],[dict(features[0],observation_ref=False)],[dict(features[0],lowest_note_refs=[])]):
                self.assertEqual(check('p',rows,notes,measures,bad)['status'],'FAIL')

    def test_independent_raw_checker_catches_hidden_same_pc_reattack(self):
        with tempfile.TemporaryDirectory()as directory:
            d=Path(directory);notes=d/'notes.tsv';measures=d/'measures.tsv'
            notes.write_text('mc\tmc_onset\tduration\tmidi\n1\t0\t1/8\t48\n1\t1/8\t1/8\t60\n',encoding='utf-8')
            measures.write_text('mc\tact_dur\n1\t1/4\n',encoding='utf-8')
            row=observation(0,'0','1',1)
            fake=dict(piece='p',observation_ref=0,start_q='0',end_q='1',status='KNOWN',lowest_midi=48,lowest_pc=0,lowest_note_refs=['note-row:0'],active_note_refs=['note-row:0'],unknown_note_refs=[])
            result=check('p',[row],notes,measures,[fake])
            self.assertEqual(result['status'],'FAIL');self.assertIn('Raw note boundary inside fixed observation cell',result['issues'])


if __name__=='__main__':unittest.main()
