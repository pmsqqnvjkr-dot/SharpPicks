import json
import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO

_flask_app = None
_flask_ready = threading.Event()
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')

def _load_flask_app():
    global _flask_app
    try:
        from app import app
        _flask_app = app
        _flask_ready.set()
        print("[wsgi] Flask app loaded successfully", flush=True)
    except Exception as e:
        print(f"[wsgi] Error loading Flask app: {e}", flush=True)
        _flask_ready.set()

def _start_flask_loader():
    t = threading.Thread(target=_load_flask_app, daemon=True)
    t.start()

class HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/' or self.path == '/health':
            if not _flask_ready.is_set():
                self._send_json(200, {'status': 'starting'})
                return
            if _flask_app is None:
                self._send_json(500, {'status': 'error'})
                return

            accept = self.headers.get('Accept', '')
            if self.path == '/' and 'text/html' in accept:
                self._serve_index()
                return
            self._send_json(200, {'status': 'ok'})
            return

        if _flask_ready.is_set() and _flask_app is not None:
            self._proxy_to_flask()
            return

        self._send_json(503, {'status': 'loading'})

    def do_POST(self):
        if _flask_ready.is_set() and _flask_app is not None:
            self._proxy_to_flask()
            return
        self._send_json(503, {'status': 'loading'})

    def do_PUT(self):
        self.do_POST()

    def do_DELETE(self):
        self.do_POST()

    def do_PATCH(self):
        self.do_POST()

    def do_OPTIONS(self):
        self.do_POST()

    def _send_json(self, code, data):
        body = json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_index(self):
        try:
            index_path = os.path.join(_static_dir, 'index.html')
            with open(index_path, 'rb') as f:
                html = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html)))
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(html)
        except Exception:
            self._send_json(200, {'status': 'ok'})

    def _proxy_to_flask(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''

        environ = {
            'REQUEST_METHOD': self.command,
            'PATH_INFO': self.path.split('?')[0],
            'QUERY_STRING': self.path.split('?')[1] if '?' in self.path else '',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '5000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.input': BytesIO(body),
            'wsgi.errors': sys.stderr,
            'wsgi.url_scheme': 'https',
            'wsgi.multithread': True,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            'CONTENT_TYPE': self.headers.get('Content-Type', ''),
            'CONTENT_LENGTH': str(content_length),
            'REMOTE_ADDR': self.client_address[0],
            'HTTP_HOST': self.headers.get('Host', 'localhost'),
        }

        for key, value in self.headers.items():
            key_upper = key.upper().replace('-', '_')
            if key_upper not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                environ[f'HTTP_{key_upper}'] = value

        response_started = []
        response_headers = []

        def start_response(status, headers, exc_info=None):
            response_started.append(status)
            response_headers.extend(headers)

        try:
            result = _flask_app(environ, start_response)
            response_body = b''.join(result)
            if hasattr(result, 'close'):
                result.close()

            status_code = int(response_started[0].split(' ')[0])
            self.send_response(status_code)
            for header_name, header_value in response_headers:
                self.send_header(header_name, header_value)
            self.end_headers()
            self.wfile.write(response_body)
        except Exception as e:
            self._send_json(500, {'error': str(e)})


def main():
    port = int(os.environ.get('PORT', 5000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"[wsgi] Server listening on port {port}", flush=True)

    _start_flask_loader()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == '__main__':
    main()
