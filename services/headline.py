"""Rule-based headline + actions for the Command Center dashboard.

Reads the unified /api/admin/metrics envelope and emits two fields the
admin UI consumes directly:

  headline = {template, sentence, color}
    template: 'good_day' | 'quiet_day' | 'mixed_day' | 'bad_day' | 'anomaly_day'
    sentence: a single English sentence summarizing the state of the business
    color:    'green' | 'blue' | 'amber' | 'red'  (drives the headline tint)

  actions = [{type, message, priority}]
    Up to 3 items, sorted by priority. priority is 'warn' | 'info' | 'good'.

Rules are intentionally small and rule-based, not LLM-based. Each rule
is a pure function of the metrics dict — easy to test, easy to reason
about, easy to tweak. If a source is stale (last_error != null) its
fields are treated as missing rather than errored, so a single broken
source doesn't break the headline.

See docs/phase-3/PHASE_3_BUILD_SPEC.md step 3.3 for the spec.
"""
from typing import Optional


def _money(cents: Optional[int]) -> str:
    if cents is None:
        return '$—'
    dollars = cents / 100
    if abs(dollars) >= 1000:
        return f'${dollars:,.0f}'
    return f'${dollars:,.2f}'


def _payload(metrics: dict, source: str) -> dict:
    """Return a source's payload dict if the source is healthy, else {}."""
    env = metrics.get(source) or {}
    if env.get('last_error') is not None:
        return {}
    return env.get('payload') or {}


def compute_headline(metrics: dict) -> dict:
    """Pick exactly one of the five headline templates based on revenue
    and activity signals. Order matters: bad_day wins over mixed wins
    over good wins over quiet.

    Failed-payment signals use the *distinct user* count, not the raw
    attempt count — one customer with 14 retries shouldn't read the
    same as 14 different customers in trouble. Cancellations include
    BOTH already-executed cancellations (canceled_30d) and scheduled-
    but-not-yet-executed ones (paid_with_cancel_scheduled +
    trials_with_cancel_scheduled), so the headline doesn't read 'no
    churn' when 5 cancellations are queued for next week.
    """
    stripe = _payload(metrics, 'stripe')
    rc     = _payload(metrics, 'revenuecat')
    events = _payload(metrics, 'events')

    # mrr_cents is the ACTUAL paying revenue (status='active' only).
    # Trial subs are counted separately in stripe.trial_subs and
    # contribute to expected_mrr_cents but NOT mrr_cents.
    mrr_cents      = (stripe.get('mrr_cents') or 0) + (rc.get('mrr_cents') or 0)
    new_subs_7d    = (stripe.get('new_subs_7d') or 0) + (rc.get('new_subs_7d') or 0)
    canceled_30d   = (stripe.get('canceled_30d') or 0) + (rc.get('canceled_30d') or 0)
    cancels_scheduled = (stripe.get('paid_with_cancel_scheduled') or 0) + (stripe.get('trials_with_cancel_scheduled') or 0)
    # Use distinct user count, not raw attempt count.
    failed_users = stripe.get('failed_payment_users_30d')
    if failed_users is None:
        failed_users = stripe.get('failed_payments_30d') or 0  # legacy fallback
    signals_today  = sum((events.get('signals_issued') or {}).values())

    # bad_day: real revenue trouble — multiple users in payment failure
    # AND actual cancellations executed
    if failed_users > 0 and canceled_30d > 0:
        return {
            'template': 'bad_day',
            'sentence': (
                f'{failed_users} customer'
                + ('s' if failed_users != 1 else '')
                + f' in payment failure and {canceled_30d} cancellation'
                + ('s' if canceled_30d != 1 else '')
                + ' in the last 30 days. Check the failed-payments list and at-risk users.'
            ),
            'color': 'red',
        }

    # good_day: revenue moving up, no actual churn AND nothing queued
    if new_subs_7d > 0 and canceled_30d == 0 and cancels_scheduled == 0 and mrr_cents > 0:
        return {
            'template': 'good_day',
            'sentence': (
                f'MRR holding at {_money(mrr_cents)}. {new_subs_7d} new subscriber'
                + ('s' if new_subs_7d != 1 else '')
                + ' this week, no churn, no cancellations queued.'
            ),
            'color': 'green',
        }

    # mixed_day: any combination of growth + friction (executed churn,
    # scheduled cancellation, or distinct payment failures)
    if new_subs_7d > 0 and (canceled_30d > 0 or cancels_scheduled > 0 or failed_users > 0):
        friction_bits = []
        if cancels_scheduled > 0:
            friction_bits.append(
                f'{cancels_scheduled} cancellation'
                + ('s' if cancels_scheduled != 1 else '')
                + ' scheduled'
            )
        if canceled_30d > 0:
            friction_bits.append(
                f'{canceled_30d} cancelled in 30d'
            )
        if failed_users > 0:
            friction_bits.append(
                f'{failed_users} customer'
                + ('s' if failed_users != 1 else '')
                + ' in payment failure'
            )
        friction = ', '.join(friction_bits)
        return {
            'template': 'mixed_day',
            'sentence': (
                f'{new_subs_7d} new subscriber'
                + ('s' if new_subs_7d != 1 else '')
                + f' this week. {friction}. Net positive.'
            ),
            'color': 'amber',
        }

    # anomaly_day: signal volume notably high
    if signals_today >= 5:
        return {
            'template': 'anomaly_day',
            'sentence': (
                f'{signals_today} signals issued this week. Above normal volume — review the Signals section.'
            ),
            'color': 'blue',
        }

    # quiet_day: default — nothing eventful, no movement
    return {
        'template': 'quiet_day',
        'sentence': (
            f'MRR steady at {_money(mrr_cents)}. No new subscribers, no churn this week. '
            f'{signals_today} signal' + ('s' if signals_today != 1 else '') + ' issued.'
        ),
        'color': 'blue',
    }


def compute_actions(metrics: dict) -> list:
    """Surface up to 3 prioritized "what to do today" lines. Order:
    warn (action needed) > info (worth a look) > good (validation)."""
    stripe = _payload(metrics, 'stripe')
    rc     = _payload(metrics, 'revenuecat')
    events = _payload(metrics, 'events')
    gsc    = _payload(metrics, 'gsc')

    items = []

    # warn: failed payments — distinct USERS, with attempt context if
    # the same customer is retrying. One person on a dead card vs. ten
    # people in dunning are very different problems.
    failed_users = stripe.get('failed_payment_users_30d')
    failed_attempts = stripe.get('failed_payment_attempts_30d')
    failing_users_list = stripe.get('failing_users') or []
    if failed_users is None:
        # Legacy fallback — old payload only had raw count
        failed_users = stripe.get('failed_payments_30d') or 0
        failed_attempts = failed_users
    if failed_users > 0:
        # If the worst offender accounts for most attempts, name them.
        worst = failing_users_list[0] if failing_users_list else None
        if worst and worst.get('attempts_30d', 0) >= max(3, failed_attempts * 0.5):
            who = worst.get('email') or worst.get('customer_id', 'one customer')
            msg = (
                f'{worst["attempts_30d"]} of {failed_attempts} failed payment'
                + ('s' if failed_attempts != 1 else '')
                + f' in 30 days are from {who}. Likely a single dead card; reach out before churning them.'
            )
        else:
            msg = (
                f'{failed_users} customer'
                + ('s' if failed_users != 1 else '')
                + f' with failed payments in 30 days ({failed_attempts} attempts total). Review the failed-payments list.'
            )
        items.append({
            'type': 'failed_payments',
            'priority': 'warn',
            'message': msg,
        })

    # warn: cancellations scheduled but not yet executed
    cancels_scheduled = (stripe.get('paid_with_cancel_scheduled') or 0) + (stripe.get('trials_with_cancel_scheduled') or 0)
    if cancels_scheduled > 0:
        items.append({
            'type': 'cancel_scheduled',
            'priority': 'warn',
            'message': (
                f'{cancels_scheduled} cancellation'
                + ('s' if cancels_scheduled != 1 else '')
                + ' scheduled but not yet effective. Save attempts have a window.'
            ),
        })

    # warn: canceled subs in 30d window (already executed)
    canceled = (stripe.get('canceled_30d') or 0) + (rc.get('canceled_30d') or 0)
    if canceled >= 3:
        items.append({
            'type': 'churn_burst',
            'priority': 'warn',
            'message': (
                f'{canceled} cancellations in the last 30 days. Worth a churn-survey pass.'
            ),
        })

    # info: GSC clicks growth signal
    gsc_clicks = gsc.get('clicks')
    if gsc_clicks and gsc_clicks > 50:
        items.append({
            'type': 'gsc_traffic',
            'priority': 'info',
            'message': (
                f'GSC: {gsc_clicks:,} clicks last 7 days. Review top queries for content opportunities.'
            ),
        })

    # info: signal volume context
    signals_total = sum((events.get('signals_issued') or {}).values())
    if signals_total > 0:
        sport_breakdown = ', '.join(
            f'{sport.upper()}: {n}' for sport, n in (events.get('signals_issued') or {}).items() if n
        )
        items.append({
            'type': 'signal_volume',
            'priority': 'info',
            'message': f'{signals_total} signals issued this week ({sport_breakdown}).',
        })

    # good: clean revenue health (no payment failures, no churn, no
    # cancellations queued)
    new_subs = (stripe.get('new_subs_7d') or 0) + (rc.get('new_subs_7d') or 0)
    if failed_users == 0 and canceled == 0 and cancels_scheduled == 0 and new_subs > 0:
        items.append({
            'type': 'clean_revenue',
            'priority': 'good',
            'message': (
                f'No failed payments, no cancellations executed or scheduled, '
                f'{new_subs} new subscriber'
                + ('s' if new_subs != 1 else '')
                + ' this week. Revenue health is clean.'
            ),
        })

    # Sort by priority and cap at 3
    PRIORITY_ORDER = {'warn': 0, 'info': 1, 'good': 2}
    items.sort(key=lambda a: PRIORITY_ORDER.get(a['priority'], 9))
    return items[:3]


def compute(metrics: dict) -> dict:
    """Public entry point. Returns {'headline': {...}, 'actions': [...]}.
    Wired into /api/admin/metrics in admin_api.py."""
    return {
        'headline': compute_headline(metrics),
        'actions':  compute_actions(metrics),
    }
