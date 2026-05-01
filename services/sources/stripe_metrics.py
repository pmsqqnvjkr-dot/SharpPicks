"""Stripe metrics source for the unified /api/admin/metrics endpoint.

Iterates subscriptions and charges to compute MRR, active subscriber
count, trials, new/canceled subs, and failed payments. MRR normalized
to USD cents and monthly cadence. Cached for 5 minutes.

Uses the existing stripe_client.get_stripe_client() — no new SDK init
or secret loader. Caps subscription pagination at SUB_PAGE_CAP as a
sanity guard; logs a warning if hit.

This is the source of truth for MRR going forward. The legacy
admin_api.py:909-915 calc (Users.subscription_plan strings * hardcoded
$29/$99) is the bug-source surfaced in the audit. Phase 4
reconciliation will compare; Stripe wins.
"""
import logging
from datetime import datetime, timedelta, timezone

from stripe_client import get_stripe_client
from services.metrics_cache import get_or_fetch

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 5 * 60
SUB_PAGE_CAP = 1000
CHARGE_PAGE_CAP = 5000


def _get(obj, key, default=None):
    """Access a Stripe object field whether it's a dict or an attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _price_to_monthly_cents(item) -> int:
    """Normalize one SubscriptionItem to monthly cents.
    Returns 0 if any required field is missing."""
    price = _get(item, 'price')
    if not price:
        return 0
    unit_amount = _get(price, 'unit_amount')
    if unit_amount is None:
        return 0
    recurring = _get(price, 'recurring')
    if not recurring:
        return 0
    interval = _get(recurring, 'interval', '')
    interval_count = _get(recurring, 'interval_count', 1) or 1
    quantity = _get(item, 'quantity', 1) or 1
    base = unit_amount * interval_count * quantity

    if interval == 'month':
        return base
    if interval == 'year':
        return base // 12
    if interval == 'week':
        return int(base * 4.345)
    if interval == 'day':
        return base * 30

    logger.warning('stripe_metrics: unknown interval %r on price %s', interval, _get(price, 'id'))
    return 0


def _fetch_raw() -> dict:
    stripe = get_stripe_client()
    now = datetime.now(timezone.utc)
    window_7d_ts = int((now - timedelta(days=7)).timestamp())
    window_30d_ts = int((now - timedelta(days=30)).timestamp())

    mrr_cents = 0
    trials = 0
    new_subs_7d = 0
    new_subs_30d = 0
    canceled_30d = 0
    customer_ids = set()
    currency = 'usd'

    sub_iter = stripe.Subscription.list(status='all', limit=100).auto_paging_iter()
    for n, sub in enumerate(sub_iter, start=1):
        if n > SUB_PAGE_CAP:
            logger.warning('stripe_metrics: hit SUB_PAGE_CAP=%d, results truncated', SUB_PAGE_CAP)
            break
        status = _get(sub, 'status')
        created = _get(sub, 'created', 0) or 0
        canceled_at = _get(sub, 'canceled_at', 0) or 0

        if status in ('active', 'trialing'):
            cust = _get(sub, 'customer')
            if cust:
                customer_ids.add(cust if isinstance(cust, str) else _get(cust, 'id'))
            items_container = _get(sub, 'items') or {}
            items_data = _get(items_container, 'data') or []
            for item in items_data:
                mrr_cents += _price_to_monthly_cents(item)
                price = _get(item, 'price') or {}
                cur = _get(price, 'currency')
                if cur:
                    currency = cur

            if status == 'trialing':
                trials += 1

        if created >= window_7d_ts:
            new_subs_7d += 1
        if created >= window_30d_ts:
            new_subs_30d += 1
        if canceled_at and canceled_at >= window_30d_ts:
            canceled_30d += 1

    failed_payments_30d = 0
    charge_iter = stripe.Charge.list(
        created={'gte': window_30d_ts},
        limit=100,
    ).auto_paging_iter()
    for n, charge in enumerate(charge_iter, start=1):
        if n > CHARGE_PAGE_CAP:
            logger.warning('stripe_metrics: hit CHARGE_PAGE_CAP=%d, results truncated', CHARGE_PAGE_CAP)
            break
        if _get(charge, 'status') == 'failed':
            failed_payments_30d += 1

    return {
        'mrr_cents': mrr_cents,
        'active_subs': len(customer_ids),  # distinct customers in active+trialing
        'trials': trials,
        'new_subs_7d': new_subs_7d,
        'new_subs_30d': new_subs_30d,
        'canceled_30d': canceled_30d,
        'failed_payments_30d': failed_payments_30d,
        'currency': currency,
    }


def fetch() -> dict:
    """Returns the cache envelope: {payload, fetched_at, stale, last_error}."""
    return get_or_fetch(
        cache_key='stripe:summary',
        ttl_seconds=CACHE_TTL_SECONDS,
        source='stripe',
        fetch_fn=_fetch_raw,
    )
