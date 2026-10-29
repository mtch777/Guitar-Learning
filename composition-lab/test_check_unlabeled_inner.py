from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,realize
from check_unlabeled_inner import inventory,check_options,check
from test_check_inner_voicing import fixture as old_fixture

try:
    import music21
except ImportError:music21=None

def unlabeled_fixture():
    docs,_,target,_,_=old_fixture()
    for name,part in docs.items():
        if not name.startswith('track-'):continue
        for m in part['measures']:
            for v in m.get('voices',[]):
                for b in v.get('beats',[]):
                    if isinstance(b.get('chord'),dict):b['chord'].pop('text',None)
    return docs,target

def ambiguous_fixture():
    tuning=[43,47,50,52,76];ordinary=[48,64,67,69,84];different=[48,52,55,57,84];measures=[]
    for mi in range(10):
        beats=[]
        for bi in range(4):
            values=different if(mi,bi)==(6,0)else ordinary
            beats.append(dict(duration=[1,4],notes=[dict(string=i,fret=p-tuning[i])for i,p in enumerate(values)]))
        measures.append(dict(signature=[4,4],voices=[dict(beats=beats)]))
    docs={'metadata.json':dict(songId=86,revisionId=1,artist='Fixture',title='Ambiguous harmony',tracks=[dict(name='Guitar',instrumentId=25)]),
        'track-0.json':dict(songId=86,revisionId=1,partId=0,instrumentId=25,tuning=tuning,frets=30,measures=measures)}
    return docs,[f'event:86:0:3:0:1:{i}'for i in range(5)]

def run_case(docs,target):
    from unlabeled_inner_voicing import catalog,options,apply
    lower=extract_documents(docs);upper=strip_lower(analyze(lower,declared_chords=True));c=catalog(upper);proposal=options(upper,target[0],c)
    changed=next(o for o in proposal['options']if o['changed']);after=realize(apply(upper,proposal['target'],changed,c))
    return lower,after,proposal,changed

@unittest.skipUnless(music21,'Pinned native oracle unavailable')
class IndependentUnlabeledTests(unittest.TestCase):
    def test_unlabeled_source_positive_and_complete_native_denominator(self):
        docs,target=unlabeled_fixture();before,after,proposal,option=run_case(docs,target)
        r=check_options(before,target[0],proposal);self.assertEqual(r['issues'],[],r)
        actual=check(before,after,target,option);self.assertEqual(actual['status'],'PASS_PROVISIONAL_ALL_ASSUMPTIONS_INNER',actual)
        native=inventory(before);self.assertEqual(len(native['groups']),20)
        self.assertGreater(native['counts']['hypotheses'],0)

    def test_ambiguous_sixth_seventh_keeps_all_support_and_dedups_donors(self):
        docs,target=ambiguous_fixture();before,after,proposal,option=run_case(docs,target)
        self.assertEqual(len(proposal['all_hypothesis_refs']),2)
        self.assertEqual(len(option['support']),2)
        self.assertEqual(option['donor_refs'],sorted(set(option['donor_refs'])))
        r=check_options(before,target[0],proposal);self.assertEqual(r['issues'],[],r)
        self.assertEqual(check(before,after,target,option)['issues'],[])
        missing=deepcopy(proposal);missing['all_hypothesis_refs'].pop()
        self.assertEqual(check_options(before,target[0],missing)['status'],'FAIL')
        missing=deepcopy(option);missing['support'].pop()
        self.assertEqual(check(before,after,target,missing)['status'],'FAIL')

    def test_labels_do_not_supply_hypothesis_votes_or_layout_weights(self):
        docs,target=unlabeled_fixture();a,b,proposal,_=run_case(docs,target)
        labeled=deepcopy(docs)
        # The exact same observed notes gain a matching literal annotation.
        from check_unlabeled_inner import _source
        source=_source(a);group=next(g for g in source['groups']if g['id']==target[0]);h=group['hypotheses'][0]
        from music21 import harmony,pitch
        symbol=harmony.ChordSymbol(root=pitch.Pitch(h['root_pc']),kind=h['kind']).figure
        p,bar,v,beat,_=map(int,target[0].split(':')[2:]);labeled[f'track-{p}.json']['measures'][bar-1]['voices'][v]['beats'][beat].setdefault('chord',{})['text']=symbol
        _,_,other,_=run_case(labeled,target)
        key=lambda data:sorted((tuple(o['pitches']),tuple(o['donor_refs']))for o in data['options']+data['rejected'])
        self.assertEqual(key(proposal),key(other))

    def test_source_provenance_role_counter_and_outside_corruptions_fail(self):
        docs,target=unlabeled_fixture();before,after,proposal,option=run_case(docs,target)
        mutations=[lambda o:o['donor_refs'].append(o['donor_refs'][0]),lambda o:o['support'][0]['roles'][0].update(relative_octaves=True),
            lambda o:o['relationship']['degree_roundtrip'].pop(),lambda o:o['relationship']['edited_set_context']['changed_refs'].pop(),
            lambda o:o['relationship']['checks'][0]['checks']['contact_coverage']['covers'].pop(),
            lambda o:o.update(changed=1),lambda o:o.update(support_class='SOME_ENUMERATED_TARGET_ASSUMPTIONS')]
        for change in mutations:
            bad=deepcopy(option);change(bad);self.assertEqual(check(before,after,target,bad)['status'],'FAIL')
        bad=deepcopy(after);next(f for f in bad['facts']if f['id']=='metadata.json#/title')['value']='forged'
        self.assertEqual(check(before,bad,target,option)['status'],'FAIL')
        missing=deepcopy(proposal);missing['options'].pop()
        self.assertEqual(check_options(before,target[0],missing)['status'],'FAIL')

if __name__=='__main__':unittest.main()
