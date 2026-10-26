"""Independent denominator and translated-witness corruption regressions."""
from copy import deepcopy
import unittest
from test_joint_fingering import documents
from source_fact_tier1 import extract_documents
from voicing_register import inventory
from family_policy import catalog as transform, options
from check_family_policy import check, normalized_units


def production(docs):
    cat=transform(inventory(extract_documents(docs),'joint_source_fingering'),docs)
    rows=[]
    for unit in cat['units']:
        if unit['refusal_reasons']:continue
        out=options(cat,unit['id'])
        rows.append({k:out[k]for k in ('target_ref','status','levels','rejected','options')})
    return cat,rows


class FamilyPolicyOracleTests(unittest.TestCase):
    def test_all_source_units_contexts_and_complete_options(self):
        docs=documents();cat,rows=production(docs)
        report=check(docs,cat,rows)
        self.assertEqual(report['status'],'PASS_INDEPENDENT_POLICY',report)
        self.assertGreater(report['accepted_donor_links'],0)

    def test_missing_unit_donor_duplicate_and_corrupt_context(self):
        docs=documents();base,rows=production(docs)
        for mode in ('unit','duplicate','context','donor','choice','geometry'):
            cat=deepcopy(base);reported=deepcopy(rows)
            if mode=='unit':cat['units'].pop()
            elif mode=='duplicate':cat['units'].append(deepcopy(cat['units'][0]))
            elif mode=='context':cat['units'][0]['family_context_key']='{}'
            elif mode=='geometry':cat['units'][0]['source_geometry']['tuning'][0]+=1
            elif mode=='donor':next(c for r in reported for c in r['options'])['donor_refs'].pop()
            elif mode=='choice':next(r for r in reported if r['options'])['options'].pop()
            with self.subTest(mode=mode):self.assertEqual(check(docs,cat,reported)['status'],'FAIL_INDEPENDENT_POLICY')

    def test_pitch_wrap_duplicates_and_source_order(self):
        for shift in (0,1,5,11):
            docs=documents();part=docs['track-0.json']
            for bar in part['measures']:
                for note in bar['voices'][0]['beats'][0]['notes']:note['fret']+=shift
            cat,rows=production(docs)
            self.assertEqual(check(docs,cat,rows)['status'],'PASS_INDEPENDENT_POLICY')
        docs=documents()
        for bar in docs['track-0.json']['measures']:
            notes=bar['voices'][0]['beats'][0]['notes'];notes.reverse()
        cat,rows=production(docs);self.assertEqual(check(docs,cat,rows)['status'],'PASS_INDEPENDENT_POLICY')

    def test_open_crossing_and_declared_bound_refusals(self):
        docs=documents();cat,rows=production(docs)
        # Source fixture includes an open-string donor and a higher-register
        # occurrence: translation must preserve open/closed execution status.
        reasons={r['reason']for row in rows for r in row['rejected']}
        self.assertIn('OPEN_STRING_STATUS_CHANGED',reasons)
        docs['track-0.json']['frets']=5
        cat,rows=production(docs);r=check(docs,cat,rows)
        self.assertEqual(r['status'],'PASS_INDEPENDENT_POLICY',r)
        self.assertIn('INVALID_TRANSLATED_OR_SOURCE_FRET',{e['reason']for row in rows for e in row['rejected']})

    def test_independent_context_equivariance_and_duplicate_members(self):
        docs=documents();part=docs['track-0.json']
        for bar in part['measures']:
            notes=bar['voices'][0]['beats'][0]['notes']
            notes[1]['fret']=part['tuning'][notes[0]['string']]+notes[0]['fret']-part['tuning'][notes[1]['string']]
        original=normalized_units(docs)[0]
        for shift in range(12):
            moved=deepcopy(docs)
            for bar in moved['track-0.json']['measures']:
                for note in bar['voices'][0]['beats'][0]['notes']:note['fret']+=shift
            rows=normalized_units(moved)[0]
            for before,after in zip(original,rows):
                self.assertEqual(before.get('family_context_key'),after.get('family_context_key'))
                self.assertEqual(before.get('family_full_context_key'),after.get('family_full_context_key'))
                self.assertEqual(before['member_refs'],after['member_refs'])
            cat,reported=production(moved)
            self.assertEqual(check(moved,cat,reported)['status'],'PASS_INDEPENDENT_POLICY')

    def test_uncoupled_source_spelling_refusal_is_authenticated(self):
        for value in ([],[0,4,1]):
            docs=documents()
            docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['spn']=value
            cat,rows=production(docs)
            self.assertIn('SOURCE_PITCH_DECLARATION_NOT_COUPLED',cat['units'][0]['refusal_reasons'])
            self.assertEqual(check(docs,cat,rows)['status'],'PASS_INDEPENDENT_POLICY')
            cat['units'][0]['refusal_reasons'].remove('SOURCE_PITCH_DECLARATION_NOT_COUPLED')
            self.assertEqual(check(docs,cat,rows)['status'],'FAIL_INDEPENDENT_POLICY')
        docs=documents();notes=docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes']
        notes[0]['spn']=[];notes[0]['bend']={'tone':100,'points':[]}
        cat,rows=production(docs)
        self.assertEqual(check(docs,cat,rows)['status'],'PASS_INDEPENDENT_POLICY')

    def test_active_other_part_context_is_not_dropped(self):
        docs=documents();part=deepcopy(docs['track-0.json'])
        part['partId']=1;part['instrumentId']=25
        for bar in part['measures']:
            bar['voices'][0]['beats'][0]['notes']=[dict(string=5,fret=1)]
        docs['track-1.json']=part
        docs['metadata.json']['tracks'].append(dict(name='Other',instrumentId=25))
        before=normalized_units(docs)[0]
        docs['track-1.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret']=2
        after=normalized_units(docs)[0]
        a=next(row for row in before if row['part_id']==0)
        b=next(row for row in after if row['id']==a['id'])
        self.assertNotEqual(a['family_context_key'],b['family_context_key'])
        cat,rows=production(docs)
        self.assertEqual(check(docs,cat,rows)['status'],'PASS_INDEPENDENT_POLICY')


if __name__=='__main__':unittest.main()
