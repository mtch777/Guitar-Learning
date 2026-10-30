"""Independent raw arithmetic and source-lock contrasts for group timing."""
import unittest
from copy import deepcopy
from fractions import Fraction as Q
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize


def source():
    bars=[]
    for seq in ((8,16,16),(16,16,8),(8,16,16)):
        beats=[{'notes':[{'string':0,'fret':3}],'type':t,'duration':[3,3*t]}for t in (*seq,4,4,4)]
        beats[0].update(beamStart=True,velocity='mf');beats[2]['beamStop']=True
        bars.append({'signature':[4,4],'voices':[{'beats':beats}]})
    return {'metadata.json':{'songId':888,'revisionId':1,'tracks':[{'name':'Bass','instrumentId':33}]},'track-0.json':{'songId':888,'revisionId':1,'partId':0,'name':'Bass','instrumentId':33,'tuning':[40],'measures':bars}}


def raw_clocks(documents):
    out={}
    for file,part in documents.items():
        if not file.startswith('track-'):continue
        start=Q(0)
        for mi,bar in enumerate(part['measures']):
            for vi,voice in enumerate(bar['voices']):
                pos=start
                for bi,beat in enumerate(voice['beats']):
                    d=Q(*beat['duration'])*4
                    for ni,n in enumerate(beat['notes']):out[(file,mi,vi,bi,ni)]=(pos,d,n)
                    if not beat.get('graceNote'):pos+=d
            sig=bar['signature'];start+=Q(sig[0]*4,sig[1])
    return out


class IndependentGroupTiming(unittest.TestCase):
    def test_every_permutation_raw_prefix_and_outside_locks(self):
        from itertools import permutations
        docs=source();before=extract_documents(docs);upper=strip_lower(analyze(before,rhythm_groups=True));old=raw_clocks(docs)
        for shares in set(permutations(('1/2','1/4','1/4'))):
            edited=deepcopy(upper);edited['musical_relationships']['groups'][0]['shares']=list(shares);newdocs=project_documents(realize(edited));clock=raw_clocks(newdocs);pos=Q(0)
            for i,s in enumerate(shares):
                key=('track-0.json',0,0,i,0);self.assertEqual(clock[key],(pos,Q(s),old[key][2]));pos+=Q(s)
                beat=newdocs['track-0.json']['measures'][0]['voices'][0]['beats'][i];self.assertEqual(beat['duration'],[3,3*int(4/Q(s))]);self.assertEqual(beat['type'],int(4/Q(s)))
            self.assertEqual({k:v for k,v in old.items()if not(k[1]==0 and k[3]<3)},{k:v for k,v in clock.items()if not(k[1]==0 and k[3]<3)})
            for mi,(a,b)in enumerate(zip(docs['track-0.json']['measures'],newdocs['track-0.json']['measures'])):
                for bi,(x,y)in enumerate(zip(a['voices'][0]['beats'],b['voices'][0]['beats'])):
                    self.assertEqual({k:v for k,v in x.items()if mi!=0 or bi>=3 or k not in('type','duration')},{k:v for k,v in y.items()if mi!=0 or bi>=3 or k not in('type','duration')})

    def test_zero_keeps_nonreduced_fraction_and_field_order(self):
        docs=source();self.assertEqual(project_documents(realize(strip_lower(analyze(extract_documents(docs),rhythm_groups=True)))),docs)
        after=project_documents(realize(strip_lower(analyze(extract_documents(docs),rhythm_groups=True))))
        self.assertEqual(list(after['track-0.json']['measures'][0]['voices'][0]['beats'][0]),list(docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]))

    def test_forged_start_span_and_occurrence_order_refused(self):
        base=strip_lower(analyze(extract_documents(source()),rhythm_groups=True))
        for kind in ('start','span','order','omission','duplicate'):
            upper=deepcopy(base);g=upper['musical_relationships']['groups'][0]
            if kind=='start':g['start_q']='1/4'
            elif kind=='span':g['span_q']='2'
            elif kind=='order':g['members'].reverse()
            elif kind=='omission':g['members'].pop()
            else:g['members'][1]=deepcopy(g['members'][0])
            with self.subTest(kind=kind),self.assertRaises((ValueError,KeyError)):realize(upper)

    def test_same_part_voice_refused_and_plain_reference_exact(self):
        docs=source();docs['track-0.json']['measures'][0]['voices'].append({'beats':[{'rest':True,'notes':[{'rest':True}],'type':1,'duration':[1,1]}]})
        upper=strip_lower(analyze(extract_documents(docs),rhythm_groups=True))
        self.assertFalse(any(g['bar']==1 for g in upper['musical_relationships']['groups']));self.assertEqual(project_documents(realize(upper)),docs)

    def test_policy_population_matches_independent_source_patterns(self):
        from local_group_rhythm import options
        t1=extract_documents(source());upper=analyze(t1,rhythm_groups=True);groups=upper['musical_relationships']['groups'];target=groups[0]['id'];choices=options(t1,target)
        self.assertEqual({tuple(o['shares']):len(o['donor_refs'])for o in choices['options']},{('1/4','1/4','1/2'):1,('1/2','1/4','1/4'):1})
        self.assertEqual(set(choices['witness_pair']),{groups[1]['id'],groups[2]['id']})

if __name__=='__main__':unittest.main()
