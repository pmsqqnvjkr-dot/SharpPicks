import os
import stripe
import requests as http_requests
import logging

_cached_credentials = {}

def _fetch_connector_credentials():
    """Fetch Stripe credentials from Replit connector API"""
    global _cached_credentials
    if _cached_credentials:
        return _cached_credentials

    hostname = os.environ.get('REPLIT_CONNECTORS_HOSTNAME')
    token = os.environ.get('REPL_IDENTITY')
    if token:
        auth = 'repl ' + token
    else:
        token = os.environ.get('WEB_REPL_RENEWAL')
        auth = 'depl ' + token if token else None

    if not hostname or not auth:
        return None

    is_production = os.environ.get('REPLIT_DEPLOYMENT') == '1'
    env = 'production' if is_production else 'development'

    try:
        url = f'https://{hostname}/api/v2/connection?include_secrets=true&connector_names=stripe&environment={env}'
        resp = http_requests.get(url, headers={'Accept': 'application/json', 'X_REPLIT_TOKEN': auth}, timeout=5)
        data = resp.json()
        items = data.get('items', [])
        if items:
            settings = items[0].get('settings', {})
            publishable = settings.get('publishable')
            secret = settings.get('secret')
            if publishable and secret:
                _cached_credentials = {'publishable': publishable, 'secret': secret}
                return _cached_credentials
    except Exception as e:
        logging.warning(f"Failed to fetch Stripe connector credentials: {e}")

    return None


def get_stripe_client():
    """Get configured Stripe client, trying Replit connector first, then env vars"""
    creds = _fetch_connector_credentials()
    if creds:
        stripe.api_key = creds['secret']
        return stripe

    secret_key = os.environ.get('STRIPE_LIVE_SECRET_KEY')
    if not secret_key:
        raise Exception('Stripe not configured: no connector or STRIPE_LIVE_SECRET_KEY found')
    stripe.api_key = secret_key
    return stripe


def get_publishable_key():
    """Get publishable key for frontend"""
    creds = _fetch_connector_credentials()
    if creds:
        return creds['publishable']

    pub_key = os.environ.get('STRIPE_LIVE_PUBLISHABLE_KEY')
    if not pub_key:
        raise Exception('Stripe not configured: no connector or STRIPE_LIVE_PUBLISHABLE_KEY found')
    return pub_key
