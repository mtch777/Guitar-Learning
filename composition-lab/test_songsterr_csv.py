import csv
import json
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('csv_capture',Path(__file__).parent/'songsterr_automation/songsterr_api/download_csv.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class SongsterrCsvTests(unittest.TestCase):
    def test_source_inventory_excludes_dead_note_pitch_and_grace_duration(self):
        src=Path(__file__).parent/'songsterr_automation/songsterr_api/analyze_corpus_sources.py'
        spec=importlib.util.spec_from_file_location('raw_inventory',src);inventory=importlib.util.module_from_spec(spec);spec.loader.exec_module(inventory)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'1';folder.mkdir()
            (folder/'metadata.json').write_text(json.dumps(dict(songId=1,revisionId=2,title='Fixture',artist='Fixture')))
            raw=dict(partId=0,instrumentId=30,tuning=[41,40],measures=[dict(signature=[2,4],voices=[dict(beats=[
                dict(duration=[1,32],graceNote=True,notes=[dict(string=0,fret=3)]),
                dict(duration=[1,4],notes=[dict(string=0,fret=0,hp=True),dict(string=1,fret=0)]),
                dict(duration=[1,4],notes=[dict(string=0,dead=True),dict(string=1,fret=0)])])])])
            (folder/'track-0.json').write_text(json.dumps(raw))
            track=inventory.analyze(root)['songs'][0]['tracks'][0]
            self.assertEqual(track['counts']['note_segments'],4);self.assertEqual(track['counts']['grace_beats'],1)
            self.assertEqual(track['coattack_groups']['close_interval_texture'],1)
            self.assertEqual(track['coattack_groups']['double_stop'],1)

    def test_id_dedup_preserves_alternate_versions_and_csv_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'input.csv'
            with p.open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=['Song','URL']);w.writeheader()
                for name,url in [('Song','https://www.songsterr.com/a/wsa/song-tab-s123t0'),('same selected track','https://www.songsterr.com/a/wsa/song-tab-s123t2'),('alternate','https://www.songsterr.com/a/wsa/song-tab-s124')]:w.writerow(dict(Song=name,URL=url))
            found=module.selections(p)
            self.assertEqual(list(found),[123,124]);self.assertEqual([r['csv_row'] for r in found[123]],[1,2])

    def test_eight_string_bridge_retains_every_note_without_mutating_source(self):
        try:import guitarpro as gp
        except ImportError:self.skipTest('PyGuitarPro available in corpus environment')
        source=gp.Song();track=source.tracks[0]
        track.strings=[gp.GuitarString(i,70-i*5) for i in range(1,9)]
        beat=gp.Beat(track.measures[0].voices[0],status=gp.BeatStatus.normal)
        beat.notes=[gp.Note(beat,string=i,value=i,type=gp.NoteType.normal) for i in range(1,9)]
        track.measures[0].voices[0].beats=[beat]
        bridge,mapping=module.split_for_gp5(source)
        self.assertEqual(len(bridge.tracks),2);self.assertEqual(len(source.tracks[0].strings),8)
        restored=[]
        for t,m in zip(bridge.tracks,mapping):
            self.assertLessEqual(len(t.strings),7)
            for n in t.measures[0].voices[0].beats[0].notes:restored.append((m['source_strings'][n.string-1],n.value))
        self.assertEqual(sorted(restored),[(i,i) for i in range(1,9)])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bridge.gp5';gp.write(bridge,str(p),version=(5,1,0));r=gp.parse(str(p))
            self.assertEqual(sum(len(b.notes) for t in r.tracks for m in t.measures for v in m.voices for b in v.beats),8)
            restored=module.restore_bridge(r,mapping)
            self.assertEqual(len(restored.tracks),1)
            self.assertEqual(sorted((n.string,n.value) for n in restored.tracks[0].measures[0].voices[0].beats[0].notes),[(i,i) for i in range(1,9)])


if __name__=='__main__':unittest.main()
