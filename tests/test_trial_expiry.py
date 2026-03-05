"""
Tests for trial expiry → downgrade flow.
"""
import os
import pytest
from unittest.mock import patch


def test_expire_trials_downgrades_expired_users(client, db, trial_user, active_trial_user):
    """Expired trial users get downgraded; active trial users stay premium."""
    from app import expire_trials

    assert trial_user.subscription_status == 'trial'
    assert trial_user.is_premium is True

    with patch('email_service.send_trial_expired_email', lambda *a, **k: None):
        expire_trials()

    # Refresh from DB
    db.session.refresh(trial_user)
    db.session.refresh(active_trial_user)

    assert trial_user.subscription_status == 'expired'
    assert trial_user.is_premium is False

    assert active_trial_user.subscription_status == 'trial'
    assert active_trial_user.is_premium is True


def test_cron_expire_trials_endpoint(client, db, trial_user):
    """Cron endpoint calls expire_trials and downgrades users."""
    import app as app_module
    with patch.object(app_module, 'CRON_SECRET', 'test-cron-secret'):
        with patch('email_service.send_trial_expired_email', lambda *a, **k: None):
            resp = client.post(
                '/api/cron/expire-trials',
                headers={'X-Cron-Secret': 'test-cron-secret'},
            )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('status') in ('done', 'skipped')

    db.session.refresh(trial_user)
    assert trial_user.subscription_status == 'expired'
    assert trial_user.is_premium is False
