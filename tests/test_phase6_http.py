"""Loopback dashboard regression, with no cloud or model needed."""
from http.client import HTTPConnection
from http.server import HTTPServer
import json
import threading
import unittest
from phase5.web_app import make_handler


class Phase6HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(('127.0.0.1', 0), make_handler(include_demo=False, corpus=[]))
        cls.port=cls.server.server_port
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, *, host=None, origin=None, payload=None, content_type=None, length=None):
        connection=HTTPConnection('127.0.0.1',self.port,timeout=5)
        headers={'Host':host or f'127.0.0.1:{self.port}'}
        if origin is not None:
            headers['Origin']=origin
        if content_type:
            headers['Content-Type']=content_type
        body=None
        if payload is not None:
            body=json.dumps(payload).encode('utf-8')
        if length is not None:
            body=b'x'*length
            headers['Content-Length']=str(length)
        connection.request(method,path,body=body,headers=headers)
        reply=connection.getresponse()
        raw=reply.read()
        status=reply.status
        response_headers=dict(reply.getheaders())
        connection.close()
        return status,json.loads(raw.decode('utf-8')) if 'json' in response_headers.get('Content-Type','') else raw,response_headers

    def test_health_and_security_headers(self):
        code,obj,headers=self.request('GET','/health')
        self.assertEqual(code,200)
        self.assertTrue(obj['local_only'])
        self.assertEqual(headers.get('X-Frame-Options'),'DENY')
        self.assertEqual(headers.get('Cross-Origin-Resource-Policy'),'same-origin')

    def test_forbidden_host_header(self):
        code,_,_=self.request('GET','/health',host='evil.example')
        self.assertEqual(code,403)

    def test_legitimate_quality_request(self):
        data={'domain':'quality','fields':{'nominal':'20.00','measured':'20.03','tolerance':'0.05','unit':'mm'}}
        code,obj,_=self.request('POST','/api/run',payload=data,content_type='application/json')
        self.assertEqual(code,200)
        self.assertEqual(obj['data']['decision'],'PASS')

    def test_untrusted_origin_refused(self):
        data={'domain':'quality','fields':{'nominal':'20.00','measured':'20.03','tolerance':'0.05','unit':'mm'}}
        code,_,_=self.request('POST','/api/run',payload=data,content_type='application/json',origin='https://evil.example')
        self.assertEqual(code,403)

    def test_json_content_type_required(self):
        code,_,_=self.request('POST','/api/run',payload={'domain':'quality'},content_type='text/plain')
        self.assertEqual(code,415)

    def test_payload_size_cap(self):
        code,_,_=self.request('POST','/api/run',content_type='application/json',length=8193)
        self.assertEqual(code,413)

    def test_document_query_abstains_by_default(self):
        code,obj,_=self.request('POST','/api/run',content_type='application/json',
          payload={'domain':'knowledge','question':'What does ISO 9001 require for release?'})
        self.assertEqual(code,200)
        self.assertEqual(obj['status'],'NO_VERIFIED_SOURCE')

if __name__=='__main__':
    unittest.main()
