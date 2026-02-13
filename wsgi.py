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
_ok_body = json.dumps({'status': 'ok'}).encode('utf-8')

def _load_flask_app():
    global _flask_app
    try:
        from app import app
        _flask_app = app
        _flask_ready.set()
        print("[wsgi] Flask app loaded successfully", flush=True)
    except Exception as e:
        print(f"[wsgi] Error loading Flask app: {e}", flush=True)
        import traceback
        traceback.print_exc()
        _flask_ready.set()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_PUT(self):
        self._handle()

    def do_DELETE(self):
        self._handle()

    def do_PATCH(self):
        self._handle()

    def do_OPTIONS(self):
        self._handle()

    def _handle(self):
        path = self.path.split('?')[0]

        if path == '/' or path == '/health':
            if _flask_ready.is_set() and _flask_app is not None:
                accept = self.headers.get('Accept', '')
                if path == '/' and 'text/html' in accept:
                    self._serve_index()
                    return
            self._send_ok()
            return

        if not _flask_ready.is_set():
            _flask_ready.wait(timeout=30)

        if _flask_app is not None:
            self._proxy_to_flask()
        else:
            self._send_json(503, {'error': 'app not ready'})

    def _send_ok(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(_ok_body)))
        self.end_headers()
        self.wfile.write(_ok_body)

    def _send_json(self, code, data):
        body = json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_index(self):
        try:
            with open(os.path.join(_static_dir, 'index.html'), 'rb') as f:
                html = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html)))
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(html)
        except Exception:
            self._send_ok()

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
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"[wsgi] Health check server ready on port {port}", flush=True)

    threading.Thread(target=_load_flask_app, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == '__main__':
    main()
