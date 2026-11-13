import json
from http.server import HTTPServer
import threading
import unittest
from urllib.request import Request, urlopen

from api.run import handler


class VercelApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(('127.0.0.1', 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/api/run'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_health(self):
        with urlopen(self.url, timeout=2) as response:
            payload = json.loads(response.read())
        self.assertEqual(payload['status'], 'OK')
        self.assertTrue(payload['model_loaded'])
        self.assertEqual(payload['model'], 'steel-rf-2026-11-14')
        self.assertTrue(payload['demo_documents'])

    def test_quality_calculation(self):
        body = json.dumps({
            'domain': 'quality',
            'fields': {'nominal': '20', 'measured': '20.03', 'tolerance': '0.05', 'unit': 'mm'},
        }).encode()
        request = Request(self.url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read())
        self.assertEqual(payload['status'], 'CALCULATED')
        self.assertEqual(payload['data']['decision'], 'PASS')

    def test_fictional_document_retrieval_is_explicit(self):
        body = json.dumps({
            'domain': 'knowledge',
            'question': 'What identifiers belong in an inspection record for traceability?',
        }).encode()
        request = Request(self.url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read())
        self.assertEqual(payload['source_provenance'], 'fictional_demo')
        self.assertTrue(payload['citations'])

    def test_natural_language_assistant(self):
        body = json.dumps({
            'prompt': 'Check quality: nominal=20 measured=20.03 tolerance=0.05 unit=mm',
        }).encode()
        request = Request(self.url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read())
        self.assertEqual(payload['status'], 'CALCULATED')
        self.assertEqual(payload['data']['decision'], 'PASS')
        self.assertEqual(payload['assistant']['routed_domain'], 'quality')


if __name__ == '__main__':
    unittest.main()
