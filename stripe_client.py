import os
import stripe

def get_stripe_client():
    """Get configured Stripe client using environment secrets"""
    secret_key = os.environ.get('STRIPE_LIVE_SECRET_KEY')
    if not secret_key:
        raise Exception('STRIPE_LIVE_SECRET_KEY not found in environment')
    stripe.api_key = secret_key
    return stripe

def get_publishable_key():
    """Get publishable key for frontend"""
    pub_key = os.environ.get('STRIPE_LIVE_PUBLISHABLE_KEY')
    if not pub_key:
        raise Exception('STRIPE_LIVE_PUBLISHABLE_KEY not found in environment')
    return pub_key
