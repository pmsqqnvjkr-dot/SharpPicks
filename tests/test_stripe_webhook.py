"""
Tests for Stripe webhook subscription status sync.
"""
import pytest
from unittest.mock import patch


def _webhook_payload(event_type, data_obj):
    """Build webhook payload (no sig in test mode)."""
    import json
    return json.dumps({
        'id': f'evt_test_{event_type.replace(".", "_")}',
        'type': event_type,
        'data': {'object': data_obj},
    })


def test_subscription_updated_canceled_downgrades(client, db, test_user):
    """subscription.updated with status=canceled downgrades user."""
    from models import User

    test_user.stripe_customer_id = 'cus_test123'
    test_user.subscription_status = 'trial'
    test_user.is_premium = True
    db.session.commit()

    payload = _webhook_payload('customer.subscription.updated', {
        'customer': 'cus_test123',
        'status': 'canceled',
        'current_period_end': 1234567890,
    })
    resp = client.post(
        '/api/stripe/webhook',
        data=payload,
        content_type='application/json',
    )
    assert resp.status_code == 200

    db.session.refresh(test_user)
    assert test_user.subscription_status == 'cancelled'
    assert test_user.is_premium is False


def test_subscription_updated_unpaid_downgrades(client, db, test_user):
    """subscription.updated with status=unpaid (trial ended without payment) downgrades."""
    from models import User

    test_user.stripe_customer_id = 'cus_unpaid'
    test_user.subscription_status = 'trial'
    test_user.is_premium = True
    db.session.commit()

    payload = _webhook_payload('customer.subscription.updated', {
        'customer': 'cus_unpaid',
        'status': 'unpaid',
        'current_period_end': 1234567890,
    })
    resp = client.post(
        '/api/stripe/webhook',
        data=payload,
        content_type='application/json',
    )
    assert resp.status_code == 200

    db.session.refresh(test_user)
    assert test_user.subscription_status == 'expired'
    assert test_user.is_premium is False


def test_subscription_updated_incomplete_expired_downgrades(client, db, test_user):
    """subscription.updated with status=incomplete_expired downgrades."""
    from models import User

    test_user.stripe_customer_id = 'cus_inc'
    test_user.subscription_status = 'trial'
    test_user.is_premium = True
    db.session.commit()

    payload = _webhook_payload('customer.subscription.updated', {
        'customer': 'cus_inc',
        'status': 'incomplete_expired',
        'current_period_end': 1234567890,
    })
    resp = client.post(
        '/api/stripe/webhook',
        data=payload,
        content_type='application/json',
    )
    assert resp.status_code == 200

    db.session.refresh(test_user)
    assert test_user.subscription_status == 'expired'
    assert test_user.is_premium is False


def test_subscription_deleted_downgrades(client, db, test_user):
    """subscription.deleted downgrades user."""
    from models import User

    test_user.stripe_customer_id = 'cus_del'
    test_user.subscription_status = 'active'
    test_user.is_premium = True
    db.session.commit()

    with patch('email_service.send_cancellation_email', lambda *a, **k: None):
        payload = _webhook_payload('customer.subscription.deleted', {
            'customer': 'cus_del',
        })
        resp = client.post(
            '/api/stripe/webhook',
            data=payload,
            content_type='application/json',
        )
    assert resp.status_code == 200

    db.session.refresh(test_user)
    assert test_user.subscription_status == 'cancelled'
    assert test_user.is_premium is False
