"""Local-only HTTP UI/API for deterministic six-domain tools and Phase 4 RAG.

No 3rd-party web deps, no telemetry, no public binding, no file uploads.
This web server intentionally does NOT permit autonomous engineering actions.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

from phase5.copilot import run
from phase4.retrieval import load_corpus

WEB = Path(__file__).resolve().parent / 'web'
ASSETS = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/app.js': ('app.js', 'application/javascript; charset=utf-8'),
    '/style.css': ('style.css', 'text/css; charset=utf-8'),
}
MAX_BODY = 8192


def process_payload(payload: object, *, include_demo: bool = False, chunks=None) -> dict:
    """Pure request-to-result path; easy to audit and unit-test offline."""
    if not isinstance(payload, dict):
        return {'status': 'INSUFFICIENT_DATA', 'report': 'Expected JSON object.', 'data': {}, 'citations': []}
    if set(payload) - {'domain', 'fields', 'question'}:
        return {'status': 'INSUFFICIENT_DATA', 'report': 'Unknown API fields.', 'data': {}, 'citations': []}
    return run(payload.get('domain', ''), payload.get('fields', {}),
               question=payload.get('question'), include_demo=include_demo, chunks=chunks)


def make_handler(include_demo=False, corpus=None):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'MfgCopilotLocal/0.1'

        def _headers(self, code: int, mime: str, size: int):
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(size))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
            self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'none'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()

        def _return(self, code: int, body: bytes, mime='application/json; charset=utf-8'):
            self._headers(code, mime, len(body))
            self.wfile.write(body)

        def _json(self, code, obj):
            self._return(code, json.dumps(obj, ensure_ascii=False).encode('utf-8'))

        def _trusted_host(self):
            # Prevent loopback DNS-rebinding requests using an untrusted Host header.
            allowed = {f'127.0.0.1:{self.server.server_port}',
                       f'localhost:{self.server.server_port}'}
            return self.headers.get('Host', '').strip().lower() in allowed

        def do_GET(self):
            if not self._trusted_host():
                self._json(403, {'error': 'Untrusted Host header'})
                return
            path = urlsplit(self.path).path
            if path == '/health':
                self._json(200, {'status': 'OK', 'local_only': True, 'model_autonomy': False,
                                 'demo_enabled': include_demo})
                return
            if path not in ASSETS:
                self._json(404, {'error': 'Not found'})
                return
            filename, content_type = ASSETS[path]
            self._return(200, (WEB / filename).read_bytes(), content_type)

        def do_POST(self):
            if not self._trusted_host():
                self._json(403, {'error': 'Untrusted Host header'})
                return
            if urlsplit(self.path).path != '/api/run':
                self._json(404, {'error': 'Not found'})
                return
            origin = self.headers.get('Origin')
            # Prevent external-origin browser requests even if bound to loopback.
            if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',
                                         f'http://localhost:{self.server.server_port}'):
                self._json(403, {'error': 'Cross-origin requests are not allowed'})
                return
            ctype = self.headers.get('Content-Type', '').split(';')[0].strip().lower()
            if ctype != 'application/json':
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
            result = process_payload(payload, include_demo=include_demo, chunks=corpus)
            self._json(200, result)

    return Handler


def main():
    p = argparse.ArgumentParser(description='Local browser interface; binds only to 127.0.0.1.')
    p.add_argument('--port', type=int, default=8765)
    p.add_argument('--include-demo', action='store_true', help='Enable fictional demo document snippets')
    args = p.parse_args()
    if not 1024 <= args.port <= 65535:
        p.error('Port must be 1024..65535')
    corpus = load_corpus(include_demo=args.include_demo)
    server = HTTPServer(('127.0.0.1', args.port), make_handler(include_demo=args.include_demo, corpus=corpus))
    print(f'Open http://127.0.0.1:{args.port}/ in your browser. Ctrl+C to stop.')
    print(f'Document snippets loaded: {len(corpus)}. Demo sources: {args.include_demo}.')
    print('Local research prototype. No manufacturing action or release authorization.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down local UI.')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
