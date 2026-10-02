"""Local APS development server, Python standard library only."""
import argparse
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from scheduler import schedule, validate
from sample import sample_data

ROOT = Path(__file__).parent
DB = ROOT / 'data' / 'aps.db'


def initialize():
    DB.parent.mkdir(exist_ok=True)
    with sqlite3.connect(DB) as db:
        db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)')
        db.execute('INSERT OR IGNORE INTO state VALUES (1, ?)', (json.dumps(sample_data()),))


def read_data():
    with sqlite3.connect(DB) as db:
        return json.loads(db.execute('SELECT payload FROM state WHERE id=1').fetchone()[0])


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, mime='application/json; charset=utf-8'):
        payload = json.dumps(body, ensure_ascii=False).encode() if mime.startswith('application/json') else body
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == '/api/data':
            return self.respond(200, read_data())
        if self.path == '/api/sample':
            return self.respond(200, sample_data())
        files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if self.path not in files:
            return self.respond(404, {'error': '找不到頁面'})
        filename, mime = files[self.path]
        self.respond(200, (ROOT / 'static' / filename).read_bytes(), mime)

    def do_POST(self):
        if self.path not in ('/api/data', '/api/schedule'):
            return self.respond(404, {'error': '找不到 API'})
        if self.headers.get('Origin') and self.headers['Origin'] != 'http://' + self.headers.get('Host', ''):
            return self.respond(403, {'error': '不允許跨來源寫入'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 1000000:
                return self.respond(413, {'error': '請求大小超出限制'})
            body = json.loads(self.rfile.read(size))
            if self.path == '/api/schedule':
                return self.respond(200, schedule(read_data(), body['start'], body['end'], body.get('rule', 'priority')))
            validate(body)
            with sqlite3.connect(DB) as db:
                db.execute('UPDATE state SET payload=? WHERE id=1', (json.dumps(body),))
            self.respond(200, {'saved': True})
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            self.respond(400, {'error': str(exc)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8000, type=int)
    args = parser.parse_args()
    initialize()
    print(f'APS listening on {args.host}:{args.port}', flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
