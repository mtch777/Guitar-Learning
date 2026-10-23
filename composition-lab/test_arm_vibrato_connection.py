"""Independent raw/category/time coverage for newly encountered source marking."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze
from check_technique_connections import check
from test_contextual_chord_motion import source


class ArmVibratoConnections(unittest.TestCase):
    def test_raw_strings_and_owned_source_time_link(self):
        for value in ('wide','slight'):
            docs=source();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['vibratoWithTremoloBar']=value
            upper=analyze(extract_documents(docs));report=check(docs,upper)
            self.assertEqual(report['status'],'PASS_SOURCE_BACKED_RELATIONSHIPS',report['issues'])
            groups=[g for g in upper['owned_parameters']['technique_declarations']['groups'] if g['field']=='vibratoWithTremoloBar']
            self.assertEqual(len(groups),1);self.assertEqual(groups[0]['parameters'][0]['parameter']['symbol'],value)
            self.assertEqual(groups[0]['owner_ref'],'track-0.json#/measures/0/voices/0/beats/0')
            event=upper['derived_views']['techniques']['tracks'][0]['source_occurrences'][0]
            self.assertTrue(event['source_fact_ref'].startswith(groups[0]['owner_ref']+'/notes/'))
            self.assertEqual((event['onset_q'],event['duration_q']),('0','1'))
            self.assertEqual(report['counts']['vibratoWithTremoloBar_persisted_declarations'],1)

    def test_independent_checker_rejects_wrong_technique_owner(self):
        docs=source();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['vibratoWithTremoloBar']='wide'
        upper=analyze(extract_documents(docs));wrong=deepcopy(upper)
        group=next(g for g in wrong['owned_parameters']['technique_declarations']['groups'] if g['field']=='vibratoWithTremoloBar')
        group['owner_ref']='track-0.json#/measures/0/voices/0/beats/1'
        self.assertEqual(check(docs,wrong)['status'],'FAIL')


if __name__=='__main__':unittest.main()
