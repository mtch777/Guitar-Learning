"""Coverage is an audited disposition, not an inference from raw storage."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

folder=Path(__file__).parent/'songsterr_automation/songsterr_api'
sys.path.insert(0,str(folder))
spec=importlib.util.spec_from_file_location('coverage_audit',folder/'audit_api_coverage.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)


class ApiCoverageTests(unittest.TestCase):
    def test_presence_counts_include_false_zero_null_and_empty_arrays(self):
        docs=[('metadata',dict(aiGenerated=False,isJunk=None,views=0,tracks=[]),'private-song-a',None),
              ('metadata',dict(aiGenerated=True,tracks=[dict(isVocalTrack=False)]),'private-song-b',None)]
        report,private=a.scan_documents(docs);rows={r['path']:r for r in report['fields']}
        self.assertEqual(rows['metadata.aiGenerated']['present_count'],2)
        self.assertEqual(rows['metadata.aiGenerated']['truthy_value_count'],1)
        self.assertEqual(rows['metadata.isJunk']['nonnull_count'],0)
        self.assertEqual(rows['metadata.views']['truthy_value_count'],0)
        self.assertEqual(rows['metadata.tracks']['present_count'],2)
        self.assertEqual(rows['metadata.tracks[]']['present_count'],1)
        self.assertEqual(rows['metadata.tracks[].isVocalTrack']['parent_denominator'],1)
        self.assertEqual(len(private['sources']),2)

    def test_nested_parent_denominators_and_distinct_source_coverage(self):
        data=dict(measures=[dict(voices=[dict(beats=[dict(notes=[dict(hp=True),dict(hp=False),dict(fret=2)])])]),
                            dict(voices=[dict(beats=[dict(notes=[dict(fret=3)])])])])
        report,_=a.scan_documents([('track',data,'song','track0'),('track',data,'song','track1')])
        row=next(r for r in report['fields'] if r['path']==a.N+'.hp')
        self.assertEqual((row['present_count'],row['parent_denominator']),(4,8))
        self.assertEqual(row['presence_percent'],50)
        self.assertEqual(row['entries_with_field'],1)
        self.assertEqual(row['track_responses_with_field'],2)

    def test_unknown_child_is_not_covered_by_analyzed_parent(self):
        data=dict(measures=[dict(voices=[dict(beats=[dict(notes=[dict(bend=dict(points=[dict(position=0,tone=0,newCurveParameter=99)]))])])])])
        report,_=a.scan_documents([('track',data,'song','track0')])
        unknown=a.N+'.bend.points[].newCurveParameter'
        self.assertEqual(report['review_required_paths'],[unknown])
        row=next(r for r in report['fields'] if r['path']==unknown)
        self.assertEqual(row['status'],'retained_only')
        self.assertTrue(row['review_required'])

    def test_new_native_mechanics_and_partial_curve_support_are_explicit(self):
        rules=a.registry()
        self.assertEqual(rules[a.B+'.brushStroke']['status'],'analyzed')
        self.assertEqual(rules[a.B+'.brushStroke.direction']['status'],'analyzed')
        self.assertEqual(rules[a.N+'.bend.points[].position']['status'],'analyzed')
        self.assertEqual(rules[a.N+'.bend.points[].precisePosition']['status'],'analyzed')
        self.assertEqual(rules[a.N+'.bend.points[].vibrato']['status'],'analyzed')
        self.assertEqual(rules[a.B+'.tremoloBar']['status'],'analyzed')
        self.assertEqual(rules[a.B+'.tremoloBar.points[].tone']['status'],'analyzed')

    def test_timeline_is_now_modeled_but_unused_catalog_copies_are_not(self):
        rules=a.registry()
        self.assertEqual(rules['track.automations.tempo[].bpm']['analysis_level'],'step_tempo_timeline')
        self.assertEqual(rules['track.automations.tempo[].bpm']['status'],'analyzed')
        self.assertEqual(rules['metadata.tracks[].instrumentId']['status'],'retained_only')
        self.assertEqual(rules['track.instrumentId']['status'],'analyzed')
        self.assertEqual(rules['track.revisionId']['status'],'analyzed')
        self.assertEqual(rules['metadata.revisionId']['status'],'analyzed')

    def test_public_report_has_no_response_values_or_private_source_identity(self):
        secret='PRIVATE_SCORE_OR_ANNOTATION_VALUE'
        docs=[('metadata',dict(songId=987654321,title=secret,author=dict(name=secret)),'PRIVATE_SONG_ID',None),
              ('track',dict(name=secret),'PRIVATE_SONG_ID','PRIVATE_TRACK_ID')]
        report,private=a.scan_documents(docs)
        public=json.dumps(report)+a.markdown(report)
        for token in (secret,'987654321','PRIVATE_SONG_ID','PRIVATE_TRACK_ID'):self.assertNotIn(token,public)
        self.assertIn('PRIVATE_SONG_ID',json.dumps(private))
        self.assertEqual(sum(report['status_counts'].values()),report['observed_paths'])
        self.assertEqual(len(report['analyzer_sha256']),64)

    def test_declared_marker_rules_follow_current_analyzer_constants(self):
        rules=a.registry()
        for base,fields in [(a.N,a.NOTE_FIELDS),(a.B,a.BEAT_FIELDS)]:
            for field in fields:
                self.assertEqual(rules[base+'.'+field]['status'],'analyzed')
                self.assertTrue(any(name in rules[base+'.'+field]['code_evidence'] for name in ('summary','source_semantics')))


if __name__=='__main__':unittest.main()
