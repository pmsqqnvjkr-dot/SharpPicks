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
    over good wins over quiet."""
    stripe = _payload(metrics, 'stripe')
    rc     = _payload(metrics, 'revenuecat')
    events = _payload(metrics, 'events')
    ga4    = _payload(metrics, 'ga4')

    mrr_cents      = (stripe.get('mrr_cents') or 0) + (rc.get('mrr_cents') or 0)
    new_subs_7d    = (stripe.get('new_subs_7d') or 0) + (rc.get('new_subs_7d') or 0)
    canceled_30d   = (stripe.get('canceled_30d') or 0) + (rc.get('canceled_30d') or 0)
    failed_payments_30d = stripe.get('failed_payments_30d') or 0
    signals_today  = sum((events.get('signals_issued') or {}).values())

    # bad_day: revenue health is actively concerning
    if failed_payments_30d > 0 and canceled_30d > 0:
        return {
            'template': 'bad_day',
            'sentence': (
                f'{failed_payments_30d} failed payment'
                + ('s' if failed_payments_30d != 1 else '')
                + f' and {canceled_30d} cancellation'
                + ('s' if canceled_30d != 1 else '')
                + ' in the last 30 days. Check the at-risk users on the Users tab.'
            ),
            'color': 'red',
        }

    # good_day: revenue moving up, no churn
    if new_subs_7d > 0 and canceled_30d == 0 and mrr_cents > 0:
        return {
            'template': 'good_day',
            'sentence': (
                f'MRR holding at {_money(mrr_cents)}. {new_subs_7d} new subscriber'
                + ('s' if new_subs_7d != 1 else '')
                + ' this week, no churn.'
            ),
            'color': 'green',
        }

    # mixed_day: subs growing but with some churn or payment friction
    if new_subs_7d > 0 and (canceled_30d > 0 or failed_payments_30d > 0):
        return {
            'template': 'mixed_day',
            'sentence': (
                f'{new_subs_7d} new subscriber'
                + ('s' if new_subs_7d != 1 else '')
                + f' this week, but {canceled_30d} cancellation'
                + ('s' if canceled_30d != 1 else '')
                + ' in the last 30 days. Net positive.'
            ),
            'color': 'amber',
        }

    # anomaly_day: signal volume notably high or notably low
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

    # warn: trial-no-card not currently exposed by Phase 2 sources; skip
    # warn: failed payments in flight
    failed = stripe.get('failed_payments_30d') or 0
    if failed > 0:
        items.append({
            'type': 'failed_payments',
            'priority': 'warn',
            'message': (
                f'{failed} failed payment'
                + ('s' if failed != 1 else '')
                + ' in the last 30 days. Review on the Users tab to identify churned customers.'
            ),
        })

    # warn: canceled subs in 30d window
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

    # good: clean revenue health
    new_subs = (stripe.get('new_subs_7d') or 0) + (rc.get('new_subs_7d') or 0)
    if failed == 0 and canceled == 0 and new_subs > 0:
        items.append({
            'type': 'clean_revenue',
            'priority': 'good',
            'message': (
                f'No failed payments, no cancellations, {new_subs} new subscriber'
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
