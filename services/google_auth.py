"""Google OAuth credentials helper for GA4 + GSC sources.

Builds google.oauth2.credentials.Credentials from three env vars:
  GOOGLE_OAUTH_CLIENT_ID
  GOOGLE_OAUTH_CLIENT_SECRET
  GOOGLE_OAUTH_REFRESH_TOKEN

The Credentials object auto-refreshes the access token when expired.
Cached at module load for the process lifetime so we don't rebuild
the object on every fetch.

The refresh token is captured once via scripts/get_google_refresh_token.py
by signing in as evan@sharppicks.ai (admin on GA4 property + GSC site).
"""
import os
import threading

_credentials_lock = threading.Lock()
_credentials_cache = None


def get_credentials():
    """Return a cached Credentials object. First call builds it from env."""
    global _credentials_cache
    if _credentials_cache is not None:
        return _credentials_cache

    with _credentials_lock:
        if _credentials_cache is not None:
            return _credentials_cache

        client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
        refresh_token = os.environ.get('GOOGLE_OAUTH_REFRESH_TOKEN')
        missing = [
            name for name, val in (
                ('GOOGLE_OAUTH_CLIENT_ID', client_id),
                ('GOOGLE_OAUTH_CLIENT_SECRET', client_secret),
                ('GOOGLE_OAUTH_REFRESH_TOKEN', refresh_token),
            ) if not val
        ]
        if missing:
            raise RuntimeError(f'Google OAuth env vars not set: {", ".join(missing)}')

        from google.oauth2.credentials import Credentials
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=[
                'https://www.googleapis.com/auth/analytics.readonly',
                'https://www.googleapis.com/auth/webmasters.readonly',
            ],
        )
        _credentials_cache = creds
        return creds
