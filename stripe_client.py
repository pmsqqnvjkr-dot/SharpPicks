import os
import stripe
import requests

_credentials = None

def get_credentials():
    """Fetch Stripe credentials from Replit connection API"""
    global _credentials
    
    if _credentials:
        return _credentials
    
    hostname = os.environ.get('REPLIT_CONNECTORS_HOSTNAME')
    repl_identity = os.environ.get('REPL_IDENTITY')
    web_repl_renewal = os.environ.get('WEB_REPL_RENEWAL')
    
    if repl_identity:
        x_replit_token = f'repl {repl_identity}'
    elif web_repl_renewal:
        x_replit_token = f'depl {web_repl_renewal}'
    else:
        raise Exception('X_REPLIT_TOKEN not found for repl/depl')
    
    is_production = os.environ.get('REPLIT_DEPLOYMENT') == '1'
    target_environment = 'production' if is_production else 'development'
    
    url = f'https://{hostname}/api/v2/connection'
    params = {
        'include_secrets': 'true',
        'connector_names': 'stripe',
        'environment': target_environment
    }
    
    response = requests.get(url, params=params, headers={
        'Accept': 'application/json',
        'X_REPLIT_TOKEN': x_replit_token
    })
    
    data = response.json()
    connection = data.get('items', [{}])[0]
    settings = connection.get('settings', {})
    
    if not settings.get('publishable') or not settings.get('secret'):
        raise Exception(f'Stripe {target_environment} connection not found')
    
    _credentials = {
        'publishable_key': settings['publishable'],
        'secret_key': settings['secret']
    }
    
    return _credentials

def get_stripe_client():
    """Get configured Stripe client"""
    creds = get_credentials()
    stripe.api_key = creds['secret_key']
    return stripe

def get_publishable_key():
    """Get publishable key for frontend"""
    creds = get_credentials()
    return creds['publishable_key']
