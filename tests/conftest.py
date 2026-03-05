"""
Pytest fixtures for SharpPicks. Sets test env before any app imports.
"""
import os
import sys

# Force test configuration before any app imports
os.environ.setdefault('TESTING', '1')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:')
os.environ.setdefault('REPLIT_DEPLOYMENT', '0')
os.environ.setdefault('SESSION_SECRET', 'test-secret-change-me')
os.environ['CRON_SECRET'] = 'test-cron-secret'
# Allow raw JSON webhook payloads (no Stripe sig verification in tests)
os.environ.setdefault('STRIPE_WEBHOOK_SECRET', '')
# Stripe client needs a key for webhook handler (use test key for tests)
os.environ.setdefault('STRIPE_LIVE_SECRET_KEY', 'sk_test_fake_key_for_tests')

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta


@pytest.fixture
def app():
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    from app import db
    with app.app_context():
        db.create_all()
        yield db
        db.drop_all()


def _hash_password(password, method='pbkdf2:sha256'):
    """Hash password with method compatible across Python/OpenSSL versions."""
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password, method=method)


@pytest.fixture
def test_user(db):
    """Create a standard test user (free tier)."""
    from models import User
    user = User(
        email='test@example.com',
        email_normalized='test@example.com',
        email_verified=True,
        first_name='Test',
        subscription_status='free',
        is_premium=False,
        password_hash=_hash_password('password123'),
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def trial_user(db):
    """Create a trial user with trial_end_date in the past (expired)."""
    from models import User
    user = User(
        email='trial@example.com',
        email_normalized='trial@example.com',
        email_verified=True,
        first_name='Trial',
        subscription_status='trial',
        is_premium=True,
        trial_used=True,
        trial_end_date=datetime.now() - timedelta(hours=1),
        password_hash=_hash_password('password123'),
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def active_trial_user(db):
    """Create a trial user with trial_end_date in the future."""
    from models import User
    user = User(
        email='activetrial@example.com',
        email_normalized='activetrial@example.com',
        email_verified=True,
        first_name='ActiveTrial',
        subscription_status='trial',
        is_premium=True,
        trial_used=True,
        trial_end_date=datetime.now() + timedelta(days=7),
        password_hash=_hash_password('password123'),
    )
    db.session.add(user)
    db.session.commit()
    return user
