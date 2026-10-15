import unittest
from copy import deepcopy
from fractions import Fraction as F
from learned_phrase_adapter import token_time,view,encode,decode,encoder_tokens,make_score,examples
from benchmarks.learned_organization import Grammar,unique
from benchmarks.learned_phrase_chain import mask_motif
from test_phrase_experiments import fixture


def vocab():
    tokens=['Bar_None','TimeSig_4/4','Position_0.0','Position_0.5','Position_1.0','Position_3.5',
        'Duration_0.5','Duration_1.0','Duration_4.0','Pitch_60','Pitch_62','BOS','EOS','CA_False','SEP']
    return {t:i+1 for i,t in enumerate(tokens)}


class AdapterTests(unittest.TestCase):
    def test_unknown_time_is_rejected_not_dropped(self):
        with self.assertRaises(ValueError):token_time(F(1,3),vocab(),'Position')
        token,error=token_time(F(1,3),{'Position_0.33':1},'Position')
        self.assertEqual(token,'Position_0.33');self.assertEqual(error,F(1,300))

    def test_time_alias_matches_upstream_float_spelling(self):
        self.assertEqual(token_time(0,{'Position_0':1,'Position_0.0':2},'Position'),('Position_0.0',F(0)))

    def test_attack_projection_audits_loss_and_preserves_source(self):
        track=fixture()['tracks'][0]
        for m in track['measures'][:2]:
            original=deepcopy(m['voices'][0][0]);original['duration_q']='1/2'
            m['voices']=[[dict(original,local_onset_q=str(F(i,2)),notes=[dict(original['notes'][0],tie={'destination':'true'})] if i==1 else deepcopy(original['notes'])) for i in range(4)]]
        frozen=deepcopy(track);notes,audit=view(track,0)
        self.assertEqual(len(notes),6);self.assertEqual(audit['tie_continuations_excluded'],2)
        self.assertEqual(track,frozen)

    def test_decode_rejects_overlaps_incomplete_notes_and_overfull_bars(self):
        for tokens in [
            ['Bar_None','Position_3.5','Pitch_60','Duration_1.0'],
            ['Bar_None','Position_0.0','Pitch_60'],
            ['Bar_None','Position_0.0','Pitch_60','Duration_1.0','Position_0.5','Pitch_62','Duration_0.5']]:
            with self.assertRaises(ValueError):decode(tokens)

    def test_exact_triplet_decode_and_native_score(self):
        notes=decode(['BOS','Bar_None','TimeSig_4/4','Position_0.0','Pitch_60','Duration_0.33','EOS'])
        self.assertEqual(notes[0]['duration'],F(1,3))
        track=fixture()['tracks'][0];score=make_score(notes,track)
        self.assertEqual(score['tracks'][0]['program'],track['program'])
        self.assertEqual(sum(F(e['duration_q']) for e in score['tracks'][0]['measures'][0]['voices'][0]),4)

    def test_grammar_prevents_overlap_and_pads_no_harmony_rules(self):
        v=vocab();g=Grammar(v,60,62)
        self.assertEqual(g.allowed([v['BOS']]),[v['Bar_None']])
        seq=[v[t] for t in ['BOS','Bar_None','TimeSig_4/4','Position_3.5','Pitch_60']]
        self.assertEqual(g.allowed(seq),[v['Duration_0.5']])
        self.assertEqual(g.allowed(seq+[v['Duration_0.5']]),[v['Bar_None']])

    def test_target_not_in_encoder_and_content_dedup(self):
        self.assertNotIn('PL_12',encoder_tokens(['Pitch_60']))
        a=dict(context=['a'],target=['b']);b=dict(context=['a'],target=['c'])
        self.assertEqual(len(unique([a,deepcopy(a),b])),2)

    def test_refiner_masks_match_released_tokenizer_filtering(self):
        tokens=['BOS','Bar_None','Position_0.0','Pitch_60','Duration_1.0','EOS']
        pitch,control=mask_motif(tokens,'pitch')
        self.assertEqual(control,'COR_PITCH_MASK');self.assertNotIn('Pitch_60',pitch)
        timing,control=mask_motif(tokens,'duration')
        self.assertEqual(control,'COR_DURATION_MASK');self.assertEqual(timing,['Bar_None','Pitch_60'])


if __name__=='__main__':unittest.main()
