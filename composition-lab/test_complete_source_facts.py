"""Source ownership includes false/null/empty/unknown and exact topology."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents,project_documents,validate,ownership_ledger
from check_complete_source_facts import check


class CompleteSourceFactsTests(unittest.TestCase):
    def test_full_unknown_and_empty_typed_fields_have_one_owner(self):
        docs={'metadata.json':{'tracks':[],'unknown':{'a/b~':[None,False,0,0.0,-0.0,{},[],'']},'missing_is_not_null':None}}
        facts=extract_documents(docs)
        self.assertEqual(json.dumps(project_documents(facts)),json.dumps(docs))
        ledger=ownership_ledger(facts)
        self.assertTrue(all('value' not in r for r in ledger))
        self.assertEqual(len({r['fact_ref'] for r in ledger}),len(facts['facts']))
        self.assertIn('metadata.json#/unknown/a~1b~0/0',[r['id'] for r in facts['facts']])
        with tempfile.TemporaryDirectory() as d:
            path=Path(d);(path/'metadata.json').write_text(json.dumps(docs['metadata.json']),encoding='utf-8')
            self.assertEqual(check(path,facts)['status'],'PASS_COMPLETE_CAPTURED_JSON_FACTS')
            changed=deepcopy(facts);next(r for r in changed['facts'] if r.get('value') is False)['value']=0
            self.assertEqual(check(path,changed)['status'],'FAIL')
            with self.assertRaises(ValueError):validate(changed)

    def test_omission_duplicate_order_and_unknown_payload_fail(self):
        original=extract_documents({'metadata.json':{'a':[1,2],'b':{}}})
        for mutate in (lambda d:d['facts'].pop(),lambda d:d['facts'].append(deepcopy(d['facts'][-1])),lambda d:d['facts'][0]['children'].reverse(),lambda d:d['facts'][0].update(hidden_notes=[])):
            changed=deepcopy(original);mutate(changed)
            with self.assertRaises(ValueError):validate(changed)


if __name__=='__main__':unittest.main()
