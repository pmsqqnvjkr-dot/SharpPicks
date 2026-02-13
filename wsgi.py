import json
import os

_real_app = None
_index_html = None

def _read_index_html():
    global _index_html
    if _index_html is None:
        index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist', 'index.html')
        try:
            with open(index_path, 'rb') as f:
                _index_html = f.read()
        except Exception:
            _index_html = b''
    return _index_html

def _get_app():
    global _real_app
    if _real_app is None:
        from app import app
        _real_app = app
    return _real_app

def application(environ, start_response):
    path = environ.get('PATH_INFO', '/')

    if path == '/health':
        body = json.dumps({'status': 'ok'}).encode('utf-8')
        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body))),
        ])
        return [body]

    if path == '/':
        accept = environ.get('HTTP_ACCEPT', '')
        if 'text/html' in accept:
            html = _read_index_html()
            if html:
                start_response('200 OK', [
                    ('Content-Type', 'text/html; charset=utf-8'),
                    ('Content-Length', str(len(html))),
                    ('Cache-Control', 'no-cache'),
                ])
                return [html]
        else:
            body = json.dumps({'status': 'ok'}).encode('utf-8')
            start_response('200 OK', [
                ('Content-Type', 'application/json'),
                ('Content-Length', str(len(body))),
            ])
            return [body]

    app = _get_app()
    return app(environ, start_response)
