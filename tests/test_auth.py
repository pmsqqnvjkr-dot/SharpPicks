"""
Tests for auth: sign in, sign out, invalid login, session.
"""
import pytest


def test_login_success(client, db, test_user):
    """Valid login returns user and token."""
    resp = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123',
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    assert 'user' in data
    assert data['user']['email'] == 'test@example.com'
    assert 'token' in data


def test_login_invalid_password(client, db, test_user):
    """Invalid password returns 401."""
    resp = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'wrongpassword',
    })
    assert resp.status_code == 401
    data = resp.get_json()
    assert 'error' in data


def test_login_nonexistent_user(client, db):
    """Login with non-existent email returns 401."""
    resp = client.post('/api/auth/login', json={
        'email': 'nobody@example.com',
        'password': 'anything',
    })
    assert resp.status_code == 401


def test_login_missing_credentials(client):
    """Login without email/password returns 400."""
    resp = client.post('/api/auth/login', json={})
    assert resp.status_code == 400


def test_logout(client, db, test_user):
    """Logout succeeds."""
    # Login first
    client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123',
    })
    resp = client.post('/api/auth/logout')
    assert resp.status_code == 200
    assert resp.get_json().get('success') is True


def test_auth_user_unauthenticated(client):
    """Auth user endpoint returns authenticated: false when not logged in."""
    resp = client.get('/api/auth/user')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('authenticated') is False
    assert data.get('user') is None


def test_health_endpoint(client):
    """Health check works without auth."""
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.get_json().get('status') == 'ok'
