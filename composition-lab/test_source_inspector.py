import csv,io,json,tempfile,unittest
from pathlib import Path
from email.message import Message
from build_source_inspector import build,digest
from serve_source_inspector import make_handler

class SourceInspectorTests(unittest.TestCase):
    def test_builder_preserves_song_object_gp_bytes_and_allowlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);corpus=root/'corpus';corpus.mkdir();raw=corpus/'raw';raw.mkdir();(raw/'track-2.json').write_text('{"partId":2}')
            gp=corpus/'score.gp';gp.write_bytes(b'unchanged-gp')
            song=dict(song_id=1,title='fixture',tracks=[dict(part_id=2,rows=[dict(onset_q='1/3',raw_note={'fret':0})])])
            (corpus/'relationships-v2.json').write_text(json.dumps(dict(songs=[song])))
            with (corpus/'catalog.csv').open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=['song_id','song','artist','revision','gp_file','raw_source_folder']);writer.writeheader();writer.writerow(dict(song_id=1,song='fixture',artist='test',revision=2,gp_file=str(gp),raw_source_folder=str(raw)))
            alpha=root/'alpha';alpha.mkdir()
            for name in ('alphaTab.min.js','alphaTab.worker.min.mjs','alphaTab.worklet.min.mjs'):(alpha/name).write_text('fixture')
            for name in ('font','soundfont'):(alpha/name).mkdir()
            out=root/'local-artifacts'/'bundle';out.parent.mkdir();result=build(corpus,alpha,out)
            self.assertEqual(result['available'],1);self.assertEqual((out/'songs/1/source.gp').read_bytes(),gp.read_bytes());self.assertEqual(json.loads((out/'songs/1/stored.json').read_text()),song)
            entry=json.loads((out/'catalog.json').read_text())[0];self.assertEqual(entry['gp_sha256'],digest(gp))
            allowed=json.loads((out/'served-files.json').read_text());self.assertNotIn('served-files.json',allowed);self.assertIn('source_inspector_logic.mjs',allowed)
            with self.assertRaises(ValueError):build(corpus,alpha,out)

    def test_server_denies_unlisted_and_traversal_even_inside_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'index.html').write_text('review');(root/'secret.json').write_text('private');(root/'served-files.json').write_text('["index.html"]')
            cls=make_handler(root).func
            for path in ('/secret.json','/served-files.json','/../index.html'):
                h=cls.__new__(cls);h.directory=str(root);h.path=path;h.command='GET';h.request_version='HTTP/1.1';h.requestline='GET '+path+' HTTP/1.1';h.headers=Message();h.wfile=io.BytesIO();h.log_message=lambda *args:None
                self.assertIsNone(h.send_head());self.assertIn(b'404',h.wfile.getvalue().split(b'\r\n',1)[0])

if __name__=='__main__':unittest.main()
