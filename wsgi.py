import json

_real_app = None

def _get_app():
    global _real_app
    if _real_app is None:
        from app import app
        _real_app = app
    return _real_app

def application(environ, start_response):
    path = environ.get('PATH_INFO', '/')
    user_agent = ''
    for key, value in environ.items():
        if key == 'HTTP_USER_AGENT':
            user_agent = value
            break

    if path == '/health' or (path == '/' and ('GoogleHC' in user_agent or 'kube-probe' in user_agent)):
        status = '200 OK'
        body = json.dumps({'status': 'ok'}).encode('utf-8')
        headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body))),
        ]
        start_response(status, headers)
        return [body]

    app = _get_app()
    return app(environ, start_response)
