"""Serverless CPU workbench endpoint for the hosted research demo."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlsplit

from phase4.retrieval import load_corpus
from phase5.web_app import process_payload

MAX_BODY = 8192
CORPUS = load_corpus(include_demo=True)


class handler(BaseHTTPRequestHandler):
    """Vercel Python Function entrypoint."""

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if urlsplit(self.path).path != '/api/run':
            self._json(404, {'error': 'Not found'})
            return
        self._json(200, {
            'status': 'OK',
            'runtime': 'serverless_cpu',
            'model_loaded': True,
            'model': 'steel-rf-2026-11-14',
            'training_data': 'observed_public_manufacturing_records',
            'demo_documents': True,
        })

    def do_POST(self) -> None:
        if urlsplit(self.path).path != '/api/run':
            self._json(404, {'error': 'Not found'})
            return
        if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            self._json(415, {'error': 'Content-Type must be application/json'})
            return
        try:
            size = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            size = -1
        if not 0 < size <= MAX_BODY:
            self._json(413, {'error': 'Request must be 1..8192 bytes'})
            return
        try:
            payload = json.loads(self.rfile.read(size))
        except (ValueError, UnicodeDecodeError):
            self._json(400, {'error': 'Invalid JSON'})
            return
        result = process_payload(payload, include_demo=True, chunks=CORPUS)
        self._json(200, result)
