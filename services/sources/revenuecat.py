"""RevenueCat metrics source for /api/admin/metrics.

iOS subscription state derived from the User table (current state)
and processed_events (RC webhook event counts in time windows).
processed_events is a 3-column dedupe ledger — id, event_type,
processed_at — the full webhook payload is discarded by the handler.
That means we cannot break down by product_id or per-event price.

Cached for 5 minutes (matches Stripe).

DIVERGENCE FROM STRIPE: this MRR is heuristic, not source-of-truth.
Stripe's services.sources.stripe_metrics iterates live Stripe API
subscriptions and computes MRR from real subscription objects with
real per-sub prices. Here we count User rows where
pro_source='revenuecat' AND is_premium=True, then multiply by
hardcoded prices keyed off User.subscription_plan ('annual' or
'monthly'). See docs/command-center-audit.md (Path A).
"""
import logging
from datetime import datetime, timedelta

from models import db, User, ProcessedEvent
from services.metrics_cache import get_or_fetch

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60  # iOS billing should feel near-real-time once IOS_PROD_LIVE is set

# Per Phase 2 spec: $19.99 monthly -> 1999 cents/mo, $149 yearly -> 1241 cents/mo
PRO_MONTHLY_CENTS = 1999
PRO_YEARLY_MONTHLY_CENTS = 1241


def _plan_key(value):
    """Normalize User.subscription_plan to 'monthly' / 'annual' / 'other'."""
    v = (value or '').lower()
    if 'month' in v:
        return 'monthly'
    if 'year' in v or 'annual' in v:
        return 'annual'
    return 'other'


def _fetch_raw():
    import os
    now = datetime.utcnow()
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    # iOS production gate. Until App Store approval lands and
    # IOS_PROD_LIVE is set in Railway, all RC numbers are forced to 0.
    # ProcessedEvent is a 3-column dedupe ledger that doesn't
    # differentiate sandbox/TestFlight from production webhooks, so
    # any TestFlight purchase fires INITIAL_PURCHASE events that look
    # identical to real ones at this layer. Without the gate, App
    # Review prep noise inflates new_subs / canceled / billing_issues
    # in the dashboard.
    ios_prod_live = (os.environ.get('IOS_PROD_LIVE') or '').strip().lower() in ('1', 'true', 'yes', 'on')

    if not ios_prod_live:
        return {
            'active_ios_subs': 0,
            'monthly_subs': 0,
            'annual_subs': 0,
            'unknown_plan_subs': 0,
            'mrr_cents': 0,
            'new_subs_7d': 0,
            'new_subs_30d': 0,
            'canceled_30d': 0,
            'billing_issues_30d': 0,
            'currency': 'usd',
            'ios_prod_live': False,
            'note': (
                'iOS not yet live in production (IOS_PROD_LIVE env var not set). '
                'All values forced to 0 — TestFlight / sandbox webhook events '
                'in ProcessedEvent are not differentiable from real ones, so they '
                'would inflate metrics during App Review prep. Set IOS_PROD_LIVE=1 '
                'in Railway after App Store approval to start counting real RC data.'
            ),
        }

    rc_users = User.query.filter(
        User.pro_source == 'revenuecat',
        User.is_premium == True,  # noqa: E712 (SQLAlchemy)
        # Trials carry is_premium=True for access but no money has moved
        # yet, so they must not contribute to MRR. Matches Stripe's rule
        # in stripe_metrics that only counts status='active' subs.
        User.subscription_status != 'trial',
        User.is_internal == False,  # noqa: E712 — exclude employees
        User.comped == False,       # noqa: E712 — exclude gifted accounts
        User.deleted_at.is_(None),  # exclude soft-deleted spam/test
        # Apple App Reviewers use ar_user<digits>@icloud.com accounts and
        # show up as PAID via IAP sandbox. Strip them out of paid metrics.
        ~User.email.op('~')(r'^ar_user[0-9]+@icloud\.com$'),
    ).all()

    monthly_count = 0
    annual_count = 0
    other_count = 0
    for u in rc_users:
        bucket = _plan_key(u.subscription_plan)
        if bucket == 'monthly':
            monthly_count += 1
        elif bucket == 'annual':
            annual_count += 1
        else:
            other_count += 1

    mrr_cents = monthly_count * PRO_MONTHLY_CENTS + annual_count * PRO_YEARLY_MONTHLY_CENTS

    # Daily MRR series, last 90 days (oldest -> newest). Each entry sums
    # monthly-equivalent cents of RC subs that were paying on that day.
    # The User row only carries the current period end, not the original
    # sub-start timestamp, so we derive sub-start as current_period_end
    # minus the plan duration. For first periods this is exact; after a
    # renewal it gives the start of the current period, which still
    # captures all paying days within a 90-day window. Unknown-plan subs
    # are excluded to match the static mrr_cents calculation.
    DAYS = 90
    today_utc_date = now.date()
    window_start_date = today_utc_date - timedelta(days=DAYS - 1)
    mrr_daily_cents = [0] * DAYS

    for u in rc_users:
        bucket = _plan_key(u.subscription_plan)
        if bucket == 'monthly':
            user_monthly_cents = PRO_MONTHLY_CENTS
            if u.current_period_end:
                sub_start_date = (u.current_period_end - timedelta(days=30)).date()
            elif u.created_at:
                sub_start_date = u.created_at.date()
            else:
                continue
        elif bucket == 'annual':
            user_monthly_cents = PRO_YEARLY_MONTHLY_CENTS
            if u.current_period_end:
                sub_start_date = (u.current_period_end - timedelta(days=365)).date()
            elif u.created_at:
                sub_start_date = u.created_at.date()
            else:
                continue
        else:
            continue

        range_start = max(sub_start_date, window_start_date)
        range_end = today_utc_date
        if range_start <= range_end:
            start_idx = (range_start - window_start_date).days
            end_idx = (range_end - window_start_date).days
            for i in range(max(0, start_idx), min(DAYS - 1, end_idx) + 1):
                mrr_daily_cents[i] += user_monthly_cents

    mrr_daily_90d = [
        {
            'date': (window_start_date + timedelta(days=i)).isoformat(),
            'mrr_cents': mrr_daily_cents[i],
        }
        for i in range(DAYS)
    ]

    def _event_count(event_type, since):
        return ProcessedEvent.query.filter(
            ProcessedEvent.event_type == event_type,
            ProcessedEvent.processed_at >= since,
        ).count()

    new_subs_7d = _event_count('rc_INITIAL_PURCHASE', cutoff_7d)
    new_subs_30d = _event_count('rc_INITIAL_PURCHASE', cutoff_30d)
    canceled_30d = _event_count('rc_CANCELLATION', cutoff_30d)
    billing_issues_30d = _event_count('rc_BILLING_ISSUE', cutoff_30d)

    return {
        'active_ios_subs': monthly_count + annual_count + other_count,
        'monthly_subs': monthly_count,
        'annual_subs': annual_count,
        'unknown_plan_subs': other_count,
        'mrr_cents': mrr_cents,
        'mrr_daily_90d': mrr_daily_90d,
        'new_subs_7d': new_subs_7d,
        'new_subs_30d': new_subs_30d,
        'canceled_30d': canceled_30d,
        'billing_issues_30d': billing_issues_30d,
        'currency': 'usd',
        'ios_prod_live': True,
        'note': (
            'iOS state derived from User.pro_source=revenuecat (excluding '
            'is_internal, comped, and soft-deleted). MRR is heuristic '
            '($19.99/mo or $149/yr keyed by User.subscription_plan); '
            'unknown_plan_subs contribute 0. Stripe MRR is source-of-truth.'
        ),
    }


def fetch() -> dict:
    """Returns the cache envelope: {payload, fetched_at, stale, last_error}."""
    return get_or_fetch(
        cache_key='revenuecat:summary',
        ttl_seconds=CACHE_TTL_SECONDS,
        source='revenuecat',
        fetch_fn=_fetch_raw,
    )
