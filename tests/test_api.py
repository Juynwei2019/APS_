import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
import app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.original=app.DB
        app.DB=Path(cls.temp.name)/'data'/'aps.db'
        app.initialize()
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        app.DB=cls.original
        cls.temp.cleanup()

    def request(self,path,body=None):
        request=Request(self.url+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        with urlopen(request) as response:
            return json.loads(response.read())

    def test_save_reload_schedule(self):
        data=self.request('/api/sample')
        data['orders'][0]['quantity']=3
        self.assertTrue(self.request('/api/data',data)['saved'])
        self.assertEqual(self.request('/api/data'),data)
        app.initialize()
        self.assertEqual(self.request('/api/data'),data)
        windows=data['resources'][0]['windows']
        result=self.request('/api/schedule',{'start':windows[0]['start'],'end':windows[-1]['end']})
        self.assertEqual(len(result['operations']),4)
        self.assertTrue(all(op['status']=='scheduled' for op in result['operations']))

    def test_bad_input_keeps_saved_data(self):
        before=self.request('/api/data')
        bad=json.loads(json.dumps(before));bad['orders'][0]['quantity']=0
        with self.assertRaises(HTTPError) as error:self.request('/api/data',bad)
        self.assertEqual(error.exception.code,400)
        self.assertEqual(self.request('/api/data'),before)

    def test_assets_and_not_found(self):
        for path in ('/','/app.js','/style.css'):
            with urlopen(self.url+path) as response:
                self.assertEqual(response.status,200)
                self.assertGreater(len(response.read()),100)
        with self.assertRaises(HTTPError) as error:urlopen(self.url+'/../app.py')
        self.assertEqual(error.exception.code,404)

    def test_cross_origin_write_rejected(self):
        request=Request(self.url+'/api/data',data=b'{}',headers={'Origin':'http://other.example'})
        with self.assertRaises(HTTPError) as error:urlopen(request)
        self.assertEqual(error.exception.code,403)
