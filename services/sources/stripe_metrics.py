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

CACHE_TTL_SECONDS = 60  # Billing should feel near-real-time on the dashboard
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

    # Build the exclusion set: stripe_customer_ids of users we don't
    # count toward paid revenue metrics (employees, comped friends/family,
    # soft-deleted spam). Without this filter, Evan's own real Stripe
    # sub inflated MRR + active_subs and the four comped accounts
    # showed up as paying customers.
    excluded_customer_ids = set()
    excluded_count_internal = 0
    excluded_count_comped = 0
    try:
        from models import User
        users_with_stripe = User.query.filter(
            User.stripe_customer_id.isnot(None),
        ).with_entities(
            User.stripe_customer_id, User.is_internal, User.comped, User.deleted_at,
        ).all()
        for cust_id, is_internal, comped, deleted_at in users_with_stripe:
            if is_internal or comped or deleted_at is not None:
                excluded_customer_ids.add(cust_id)
                if is_internal:
                    excluded_count_internal += 1
                if comped:
                    excluded_count_comped += 1
    except Exception as e:
        logger.warning('stripe_metrics: exclusion-set build failed (counts will include internal/comped): %s', e)

    # mrr_cents: ACTUAL paying MRR — sum of monthly-equivalent cents
    # across status='active' subscriptions only. Trialing subs have a
    # card on file but no money has changed hands; counting them as MRR
    # is double-booking the same dollar between this month (as MRR) and
    # next month (when the trial converts).
    mrr_cents = 0
    # expected_mrr_cents: MRR + the amount we WOULD bill if every
    # in-flight trial converted. Useful as a forward indicator but not
    # the headline number.
    expected_mrr_cents = 0
    trials = 0
    new_subs_24h = 0
    new_subs_7d = 0
    new_subs_30d = 0
    # Split by current sub status. Most newly-created Stripe subs are in
    # 'trialing' (we route web checkouts through a trial); a non-trial
    # sub means the customer paid a real invoice immediately.
    new_trial_subs_24h = 0
    new_paid_subs_24h = 0
    new_trial_subs_7d = 0
    new_paid_subs_7d = 0
    canceled_30d = 0
    # Cancel-state breakdowns (Phase 3 audit fix).
    trials_with_cancel_scheduled = 0
    paid_with_cancel_scheduled = 0
    trials_likely_to_convert = 0
    # Trial conversion tracking (uses User.trial_converted_at; computed
    # below from the DB after the Stripe pass).
    paying_customer_ids = set()  # status=active only -> 'active_subs'
    trial_customer_ids = set()   # status=trialing only -> 'trials' (distinct)
    currency = 'usd'

    # Daily MRR series, last 90 days (oldest -> newest). Each entry is
    # the sum of monthly-equivalent cents from subs that were actively
    # paying (past trial_end, before canceled_at) on that day. Trialing
    # days don't contribute — money hasn't moved yet.
    DAYS = 90
    today_utc_date = now.date()
    window_start_date = today_utc_date - timedelta(days=DAYS - 1)
    mrr_daily_cents = [0] * DAYS  # [0] = oldest, [DAYS-1] = today

    def _ts_to_date(ts):
        if not ts:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc).date()

    sub_iter = stripe.Subscription.list(status='all', limit=100).auto_paging_iter()
    for n, sub in enumerate(sub_iter, start=1):
        if n > SUB_PAGE_CAP:
            logger.warning('stripe_metrics: hit SUB_PAGE_CAP=%d, results truncated', SUB_PAGE_CAP)
            break
        status = _get(sub, 'status')
        created = _get(sub, 'created', 0) or 0
        canceled_at = _get(sub, 'canceled_at', 0) or 0
        trial_end = _get(sub, 'trial_end', 0) or 0
        cancel_at_period_end = bool(_get(sub, 'cancel_at_period_end'))
        cust = _get(sub, 'customer')
        cust_id = cust if isinstance(cust, str) else (_get(cust, 'id') if cust else None)

        # Skip subs belonging to internal/comped/deleted users entirely.
        # They don't add to MRR, active sub counts, trial pipeline, or
        # any of the new/cancel windows. This is the fix that stops
        # Evan's real Stripe sub from inflating the totals.
        if cust_id and cust_id in excluded_customer_ids:
            continue

        # Compute monthly cents for this sub (used both for current
        # MRR and the daily series).
        items_container = _get(sub, 'items') or {}
        items_data = _get(items_container, 'data') or []
        sub_monthly_cents = 0
        for item in items_data:
            sub_monthly_cents += _price_to_monthly_cents(item)
            price = _get(item, 'price') or {}
            cur = _get(price, 'currency')
            if cur:
                currency = cur

        # ── Contribute to the daily MRR series ──
        # A sub's "actively paying" window is from max(created, trial_end)
        # to (canceled_at or today). Currently-active subs without a trial
        # contribute every day from created -> today. Currently-trialing
        # subs that haven't converted have trial_end in the future, so
        # max(created, trial_end) is also in the future and they
        # contribute zero days to the past 90 (correct — they haven't
        # paid yet).
        if sub_monthly_cents > 0:
            paying_start_ts = max(created, trial_end)
            paying_start_date = _ts_to_date(paying_start_ts) or window_start_date
            paying_end_date = _ts_to_date(canceled_at) if canceled_at else today_utc_date
            range_start = max(paying_start_date, window_start_date)
            range_end = min(paying_end_date, today_utc_date)
            if range_start <= range_end:
                start_idx = (range_start - window_start_date).days
                end_idx = (range_end - window_start_date).days
                for i in range(max(0, start_idx), min(DAYS - 1, end_idx) + 1):
                    mrr_daily_cents[i] += sub_monthly_cents

        if status in ('active', 'trialing'):
            if status == 'active':
                # ACTUAL paying MRR.
                mrr_cents += sub_monthly_cents
                expected_mrr_cents += sub_monthly_cents
                if cust_id:
                    paying_customer_ids.add(cust_id)
                if cancel_at_period_end:
                    paid_with_cancel_scheduled += 1
            else:  # trialing
                # Card on file, no payment yet. Counts toward expected
                # MRR ONLY if a cancel isn't already scheduled — a trial
                # with cancel_at_period_end=true will not bill, so
                # adding it to "expected" overstates the upside.
                if not cancel_at_period_end:
                    expected_mrr_cents += sub_monthly_cents
                if cust_id:
                    trial_customer_ids.add(cust_id)
                trials += 1
                if cancel_at_period_end:
                    trials_with_cancel_scheduled += 1
                else:
                    trials_likely_to_convert += 1

        if created >= window_24h_ts:
            new_subs_24h += 1
            if status == 'trialing':
                new_trial_subs_24h += 1
            elif status == 'active':
                new_paid_subs_24h += 1
        if created >= window_7d_ts:
            new_subs_7d += 1
            if status == 'trialing':
                new_trial_subs_7d += 1
            elif status == 'active':
                new_paid_subs_7d += 1
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
        # Same exclusion as the subscription loop — failed retries from
        # internal/comped customers shouldn't show up as churn risk.
        if cust_id in excluded_customer_ids:
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

    # Comped pro-account count from DB. These users have full pro
    # access but are not paying, so they're broken out separately
    # (not included in active_subs above).
    comped_count = 0
    try:
        from models import User, db as _db
        from sqlalchemy import func as _func
        comped_count = _db.session.query(_func.count(User.id)).filter(
            User.comped == True,  # noqa: E712
            User.deleted_at.is_(None),
        ).scalar() or 0
    except Exception as e:
        logger.warning('stripe_metrics: comped count failed: %s', e)

    # Orphaned-paying-customer adjustment. Users whose Stripe subscription
    # was deleted by the /api/account/delete ordering bug (fixed in
    # commit ad1480d7) are still paying customers — they paid through a
    # future period_end — but invisible to Stripe.Subscription.list, so
    # the loop above missed them. Cooper Reynolds and Spiffy are the
    # known cases as of 2026-05-18; any future divergence between local
    # is_premium and Stripe sub status surfaces here too.
    #
    # We add their monthly-equivalent contribution to mrr_cents +
    # expected_mrr_cents, and expose `mrr_orphan_cents` + a count so the
    # discrepancy is visible in the dashboard rather than hidden.
    orphan_mrr_cents = 0
    orphan_count = 0
    orphan_emails: list[str] = []
    try:
        from models import User, db as _db
        now_dt = datetime.utcnow()
        orphan_candidates = User.query.filter(
            User.is_premium == True,  # noqa: E712
            User.subscription_status.in_(('active', 'cancelling', 'trial')),
            User.current_period_end.isnot(None),
            User.current_period_end > now_dt,
            User.is_internal == False,  # noqa: E712
            User.comped == False,  # noqa: E712
            User.deleted_at.is_(None),
        ).all()
        for u in orphan_candidates:
            cust_id = u.stripe_customer_id
            if cust_id and (cust_id in paying_customer_ids or cust_id in trial_customer_ids):
                continue
            plan = (u.subscription_plan or '').lower()
            if u.founding_member:
                contrib = round(9900 / 12)
            elif 'annual' in plan:
                contrib = round(14999 / 12)
            elif 'month' in plan:
                contrib = 1999
            else:
                contrib = 0
            if contrib <= 0:
                continue
            orphan_mrr_cents += contrib
            orphan_count += 1
            if u.email:
                orphan_emails.append(u.email)
    except Exception as e:
        logger.warning('stripe_metrics: orphan MRR augmentation failed: %s', e)

    if orphan_mrr_cents > 0:
        mrr_cents += orphan_mrr_cents
        expected_mrr_cents += orphan_mrr_cents

    # Render the 90-day MRR series with date strings so the frontend
    # can use them as chart labels directly.
    mrr_daily_90d = [
        {
            'date': (window_start_date + timedelta(days=i)).isoformat(),
            'mrr_cents': mrr_daily_cents[i],
        }
        for i in range(DAYS)
    ]

    return {
        'mrr_cents': mrr_cents,                       # status='active' only — real recurring revenue
        'expected_mrr_cents': expected_mrr_cents,     # active + trialing — what MRR becomes if all trials convert
        'mrr_daily_90d': mrr_daily_90d,               # 90-day daily MRR series for the Revenue chart
        'active_subs': len(paying_customer_ids),      # distinct PAYING customers (status=active only)
        'trial_subs':  len(trial_customer_ids),       # distinct trialing customers (no money in yet)
        'comped_pro_users': comped_count,             # complimentary pro access, not in MRR
        'excluded_internal_subs': excluded_count_internal,
        'excluded_comped_subs': excluded_count_comped,
        'orphan_mrr_cents': orphan_mrr_cents,         # paying users invisible to Stripe (delete-bug victims, etc.)
        'orphan_paying_subs': orphan_count,
        'orphan_emails': orphan_emails,
        'trials': trials,
        'new_subs_24h': new_subs_24h,
        'new_subs_7d': new_subs_7d,
        'new_subs_30d': new_subs_30d,
        'new_trial_subs_24h': new_trial_subs_24h,
        'new_paid_subs_24h': new_paid_subs_24h,
        'new_trial_subs_7d': new_trial_subs_7d,
        'new_paid_subs_7d': new_paid_subs_7d,
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
