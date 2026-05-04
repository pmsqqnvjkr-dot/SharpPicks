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
    window_24h_ts = int((now - timedelta(hours=24)).timestamp())
    window_7d_ts = int((now - timedelta(days=7)).timestamp())
    window_30d_ts = int((now - timedelta(days=30)).timestamp())

    mrr_cents = 0
    trials = 0
    new_subs_7d = 0
    new_subs_30d = 0
    canceled_30d = 0
    # Cancel-state breakdowns (Phase 3 audit fix).
    trials_with_cancel_scheduled = 0
    paid_with_cancel_scheduled = 0
    trials_likely_to_convert = 0
    # Trial conversion tracking (uses User.trial_converted_at; computed
    # below from the DB after the Stripe pass).
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
        cancel_at_period_end = bool(_get(sub, 'cancel_at_period_end'))

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
                if cancel_at_period_end:
                    trials_with_cancel_scheduled += 1
                else:
                    trials_likely_to_convert += 1
            elif status == 'active' and cancel_at_period_end:
                paid_with_cancel_scheduled += 1

        if created >= window_7d_ts:
            new_subs_7d += 1
        if created >= window_30d_ts:
            new_subs_30d += 1
        if canceled_at and canceled_at >= window_30d_ts:
            canceled_30d += 1

    # Failed payments — segmented by user, not raw charge count.
    # If one customer has 14 failed retries, that's "1 user with 14
    # attempts" not "14 failed payments". Both surface in the response.
    failed_per_customer_30d = {}
    failed_per_customer_7d = {}
    failed_per_customer_24h = {}
    charge_iter = stripe.Charge.list(
        created={'gte': window_30d_ts},
        limit=100,
    ).auto_paging_iter()
    for n, charge in enumerate(charge_iter, start=1):
        if n > CHARGE_PAGE_CAP:
            logger.warning('stripe_metrics: hit CHARGE_PAGE_CAP=%d, results truncated', CHARGE_PAGE_CAP)
            break
        if _get(charge, 'status') != 'failed':
            continue
        cust = _get(charge, 'customer')
        cust_id = cust if isinstance(cust, str) else (_get(cust, 'id') if cust else None)
        if not cust_id:
            continue
        c_created = _get(charge, 'created', 0) or 0
        failed_per_customer_30d[cust_id] = failed_per_customer_30d.get(cust_id, 0) + 1
        if c_created >= window_7d_ts:
            failed_per_customer_7d[cust_id] = failed_per_customer_7d.get(cust_id, 0) + 1
        if c_created >= window_24h_ts:
            failed_per_customer_24h[cust_id] = failed_per_customer_24h.get(cust_id, 0) + 1

    # Resolve customer_id -> email for the per-user breakdown so the
    # admin UI can show "user X has 14 failed payments" by name. Cap at
    # the top 10 offenders to avoid an unbounded payload.
    top_offenders = sorted(failed_per_customer_30d.items(), key=lambda kv: -kv[1])[:10]
    failing_users = []
    if top_offenders:
        try:
            from models import User
            cust_ids = [c for c, _ in top_offenders]
            users_by_cust = {
                u.stripe_customer_id: u for u in
                User.query.filter(User.stripe_customer_id.in_(cust_ids)).all()
            }
            for cust_id, attempts in top_offenders:
                u = users_by_cust.get(cust_id)
                failing_users.append({
                    'customer_id': cust_id,
                    'email': u.email if u else None,
                    'first_name': (u.first_name if u else None),
                    'attempts_30d': attempts,
                    'attempts_7d': failed_per_customer_7d.get(cust_id, 0),
                    'attempts_24h': failed_per_customer_24h.get(cust_id, 0),
                })
        except Exception as e:
            logger.warning('stripe_metrics: user resolution for failed payments failed: %s', e)

    # Trial conversion counts come from our DB (User.trial_converted_at)
    # since Stripe doesn't have a single "converted" event we can count.
    # Wrapped in try/except so a DB error here doesn't poison the
    # whole Stripe envelope.
    trial_conversions_24h = 0
    trial_conversions_7d = 0
    trial_conversions_30d = 0
    try:
        from models import db, User
        from sqlalchemy import func
        cutoff_24h = datetime.utcnow() - timedelta(hours=24)
        cutoff_7d  = datetime.utcnow() - timedelta(days=7)
        cutoff_30d = datetime.utcnow() - timedelta(days=30)
        trial_conversions_24h = db.session.query(func.count(User.id)).filter(
            User.trial_converted_at.isnot(None),
            User.trial_converted_at >= cutoff_24h,
            User.is_internal == False,  # noqa: E712
            User.deleted_at.is_(None),
        ).scalar() or 0
        trial_conversions_7d = db.session.query(func.count(User.id)).filter(
            User.trial_converted_at.isnot(None),
            User.trial_converted_at >= cutoff_7d,
            User.is_internal == False,  # noqa: E712
            User.deleted_at.is_(None),
        ).scalar() or 0
        trial_conversions_30d = db.session.query(func.count(User.id)).filter(
            User.trial_converted_at.isnot(None),
            User.trial_converted_at >= cutoff_30d,
            User.is_internal == False,  # noqa: E712
            User.deleted_at.is_(None),
        ).scalar() or 0
    except Exception as e:
        logger.warning('stripe_metrics: trial conversion count failed: %s', e)

    return {
        'mrr_cents': mrr_cents,
        'active_subs': len(customer_ids),  # distinct customers in active+trialing
        'trials': trials,
        'new_subs_7d': new_subs_7d,
        'new_subs_30d': new_subs_30d,
        'canceled_30d': canceled_30d,
        # Cancel-state breakdowns
        'trials_with_cancel_scheduled': trials_with_cancel_scheduled,
        'paid_with_cancel_scheduled': paid_with_cancel_scheduled,
        'trials_likely_to_convert': trials_likely_to_convert,
        # Trial conversion timestamps (from User.trial_converted_at)
        'trial_conversions_24h': trial_conversions_24h,
        'trial_conversions_7d': trial_conversions_7d,
        'trial_conversions_30d': trial_conversions_30d,
        # Failed payments — segmented by user. The 30d/7d/24h totals
        # double-count the same customer's retries; the per-user
        # breakdown below is the honest signal.
        'failed_payment_attempts_30d': sum(failed_per_customer_30d.values()),
        'failed_payment_attempts_7d':  sum(failed_per_customer_7d.values()),
        'failed_payment_attempts_24h': sum(failed_per_customer_24h.values()),
        'failed_payment_users_30d': len(failed_per_customer_30d),
        'failed_payment_users_7d':  len(failed_per_customer_7d),
        'failed_payment_users_24h': len(failed_per_customer_24h),
        'failing_users': failing_users,
        # Legacy field kept so older clients (the Phase 2 dashboard)
        # don't break; identical to failed_payment_attempts_30d.
        'failed_payments_30d': sum(failed_per_customer_30d.values()),
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
