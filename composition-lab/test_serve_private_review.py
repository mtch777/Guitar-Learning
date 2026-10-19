import io,tempfile,unittest
from pathlib import Path
from email.message import Message
from serve_review_bundle import handler


class PrivateReviewServerTests(unittest.TestCase):
    def request(self,root,path,range_=None):
        cls=handler(root);h=cls.__new__(cls);h.path=path;h.command='GET';h.request_version='HTTP/1.1';h.requestline='GET '+path+' HTTP/1.1';h.headers=Message();h.wfile=io.BytesIO();h.log_message=lambda *args:None
        if range_:h.headers['Range']=range_
        stream=h.send_head()
        if stream:
            with stream:h.copyfile(stream,h.wfile)
        headers,body=h.wfile.getvalue().split(b'\r\n\r\n',1)
        return headers.decode(),body

    def test_audio_ranges_and_unrelated_files_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'assets').mkdir();(root/'index.html').write_text('review');(root/'assets/a.wav').write_bytes(bytes(range(100)));(root/'secret.json').write_text('private')
            headers,body=self.request(root,'/assets/a.wav','bytes=10-19')
            self.assertIn('206',headers);self.assertIn('Content-Range: bytes 10-19/100',headers);self.assertEqual(body,bytes(range(10,20)))
            headers,body=self.request(root,'/assets/a.wav','bytes=-4');self.assertEqual(body,bytes(range(96,100)))
            for path in ('/secret.json','/assets/../secret.json','/assets/%2e%2e/secret.json','/assets/'):
                headers,body=self.request(root,path);self.assertIn('404',headers)
            headers,body=self.request(root,'/assets/a.wav','bytes=999-');self.assertIn('416',headers)


if __name__=='__main__':unittest.main()
