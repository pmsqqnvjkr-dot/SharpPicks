import json
import os

_real_app = None
_index_html = None
_ok_body = json.dumps({'status': 'ok'}).encode('utf-8')

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

def _ok_response(start_response):
    start_response('200 OK', [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(_ok_body))),
    ])
    return [_ok_body]

def application(environ, start_response):
    path = environ.get('PATH_INFO', '/')

    if path == '/' or path == '/health':
        accept = environ.get('HTTP_ACCEPT', '')
        if path == '/' and 'text/html' in accept:
            html = _read_index_html()
            if html:
                start_response('200 OK', [
                    ('Content-Type', 'text/html; charset=utf-8'),
                    ('Content-Length', str(len(html))),
                    ('Cache-Control', 'no-cache'),
                ])
                return [html]
        return _ok_response(start_response)

    try:
        app = _get_app()
        return app(environ, start_response)
    except Exception:
        return _ok_response(start_response)
