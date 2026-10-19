import copy,json,math,unittest
from conditional_harmony_steps import fit,distribution,score,evaluate,validate_rows


def rows(families=('a','b','c'),repeat=6):
    out=[]
    for si,family in enumerate(families,1):
        for i in range(repeat):
            for register,step in ((0,12),(12,-12),(6,0)):
                out.append(dict(family=family,song_id=si,part_id=0,onset_q=str(len(out)),origin_register=register,voicing_span=0,step=step,destination_register=register+step))
    return out

class ConditionalStepTests(unittest.TestCase):
    def test_context_signal_unknown_backoff_and_json_roundtrip(self):
        data=rows();model=fit(data)
        ps,support=distribution(model,0,0);self.assertGreater(ps[139],model['global_probs'][139]);self.assertGreater(support['mass'],0)
        fallback,support=distribution(model,99,99);self.assertEqual(fallback,model['global_probs']);self.assertIsNone(support)
        serialized=json.loads(json.dumps(model));self.assertEqual(distribution(model,0,0)[0],distribution(serialized,0,0)[0]);self.assertEqual(distribution(model,0,0)[1]['mass'],distribution(serialized,0,0)[1]['mass'])
    def test_family_weight_and_shuffle_keep_marginal_support(self):
        data=rows();normal=fit(data);control=fit(data,True)
        self.assertEqual(normal['global_probs'],control['global_probs'])
        for key in normal['contexts']:self.assertAlmostEqual(normal['contexts'][key]['mass'],control['contexts'][key]['mass'])
        self.assertEqual(fit(data,True),control)
    def test_score_independently_matches_vector_definition(self):
        train=rows(('a','b'));held=rows(('c',),1);held=[dict(held[0],song_id=3)]
        model=fit(train);report=score(held,model);ps,_=distribution(model,0,0);index=held[0]['step']+127
        self.assertAlmostEqual(report['nll'],-math.log(ps[index]));self.assertAlmostEqual(report['brier'],sum((p-int(i==index))**2 for i,p in enumerate(ps)))
        self.assertAlmostEqual(report['below_open_probability'],sum(ps[:127]));self.assertAlmostEqual(report['destination_register_TV'],1-ps[index])
    def test_leakage_duplicate_and_source_identity_refused(self):
        data=rows();model=fit(data)
        with self.assertRaisesRegex(ValueError,'leaked'):score(data,model)
        with self.assertRaisesRegex(ValueError,'Duplicate'):validate_rows(data+[copy.deepcopy(data[0])])
        alias=copy.deepcopy(data[0]);alias['onset_q']='0/1'
        with self.assertRaisesRegex(ValueError,'Duplicate'):validate_rows(data+[alias])
        bad=copy.deepcopy(data);bad[0]['destination_register']+=1
        with self.assertRaisesRegex(ValueError,'Invalid'):fit(bad)
    def test_family_separated_synthetic_signal_passes_frozen_screen(self):
        result=evaluate(rows());self.assertEqual(result['families'],3);self.assertTrue(result['predeclared_operational_gate_pass'])
        self.assertEqual(result['family_NLL_wins_against_both'],3)
    def test_large_song_does_not_outweigh_other_family(self):
        a=[dict(family='a',song_id=1,part_id=0,onset_q=str(i),origin_register=0,voicing_span=0,step=12,destination_register=12) for i in range(100)]
        b=[dict(family='b',song_id=2,part_id=0,onset_q='0',origin_register=12,voicing_span=0,step=-12,destination_register=0)]
        model=fit(a+b)
        self.assertAlmostEqual(model['global_probs'][139],model['global_probs'][115])

if __name__=='__main__':unittest.main()
