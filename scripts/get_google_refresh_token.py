#!/usr/bin/env python3
"""One-time CLI to capture a Google OAuth refresh token for GA4 + GSC.

Run locally exactly once. Reads the OAuth client JSON from
secrets/google_oauth_client.json (gitignored), opens a browser for
consent, prints the refresh token to stdout. Copy the three values
the script prints into Railway env vars.

When the browser opens, sign in as evan@sharppicks.ai (the admin
identity on the GA4 property and Search Console site). Do NOT sign
in as dev@.

Usage:
    python3 scripts/get_google_refresh_token.py
"""
import json
import os
import sys

CLIENT_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'secrets', 'google_oauth_client.json',
)

SCOPES = [
    'https://www.googleapis.com/auth/analytics.readonly',
    'https://www.googleapis.com/auth/webmasters.readonly',
]


def main():
    if not os.path.exists(CLIENT_JSON_PATH):
        print(f'ERROR: OAuth client JSON not found at {CLIENT_JSON_PATH}', file=sys.stderr)
        print('Download from GCP Console -> APIs & Services -> Credentials,', file=sys.stderr)
        print('then place at secrets/google_oauth_client.json (gitignored).', file=sys.stderr)
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print('ERROR: google-auth-oauthlib not installed.', file=sys.stderr)
        print('Run: uv sync (or pip install google-auth-oauthlib)', file=sys.stderr)
        sys.exit(1)

    print('Opening browser for OAuth consent...')
    print('Sign in as evan@sharppicks.ai (NOT dev@) when prompted.')
    print()

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_JSON_PATH, SCOPES)
    # 'select_account consent' forces both the account picker AND
    # re-consent, so a stale Chrome login doesn't silently pick the
    # wrong identity.
    creds = flow.run_local_server(
        port=8765,
        prompt='select_account consent',
        access_type='offline',
    )

    if not creds.refresh_token:
        print('ERROR: no refresh_token returned by Google.', file=sys.stderr)
        print('This usually means a stale grant — revoke the app at', file=sys.stderr)
        print('https://myaccount.google.com/permissions and try again.', file=sys.stderr)
        sys.exit(1)

    with open(CLIENT_JSON_PATH) as f:
        client_data = json.load(f)
    inner = client_data.get('installed') or client_data.get('web') or {}
    client_id = inner.get('client_id', '')
    client_secret = inner.get('client_secret', '')

    print()
    print('=' * 70)
    print('SUCCESS. Copy these three values into Railway env vars:')
    print('=' * 70)
    print()
    print(f'GOOGLE_OAUTH_CLIENT_ID={client_id}')
    print(f'GOOGLE_OAUTH_CLIENT_SECRET={client_secret}')
    print(f'GOOGLE_OAUTH_REFRESH_TOKEN={creds.refresh_token}')
    print()
    print('Also paste the same values into your local .env so smoke tests work.')
    print('=' * 70)


if __name__ == '__main__':
    main()
