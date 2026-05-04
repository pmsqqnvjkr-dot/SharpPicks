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


def _pluralize(n: int, word: str, plural: str = None) -> str:
    """'1 trial' / '2 trials' helper."""
    if n == 1:
        return f'{n} {word}'
    return f'{n} {plural or (word + "s")}'


def _delta(current: int, baseline: int) -> str:
    """Return a +/- delta string in money format. baseline=0 means no
    prior data."""
    if baseline is None or baseline == 0:
        return ''
    diff = current - baseline
    if diff == 0:
        return 'flat vs 90d ago'
    sign = '+' if diff > 0 else '−'
    return f'{sign}{_money(abs(diff))} vs 90d ago'


def compute_summaries(metrics: dict) -> dict:
    """Per-section summary sentences for the Command tab. Each value
    is one short sentence (or two) computed from real metrics — no
    invented trends, no exclamation marks. Sections without enough
    data fall back to a neutral 'no activity yet' note instead of
    making something up."""
    stripe = _payload(metrics, 'stripe')
    rc     = _payload(metrics, 'revenuecat')
    events = _payload(metrics, 'events')
    ga4    = _payload(metrics, 'ga4')
    gsc    = _payload(metrics, 'gsc')

    summaries = {}

    # ── revenue · 90d ──
    mrr_now = (stripe.get('mrr_cents') or 0) + (rc.get('mrr_cents') or 0)
    expected_now = (stripe.get('expected_mrr_cents') or stripe.get('mrr_cents') or 0) + (rc.get('mrr_cents') or 0)
    daily = stripe.get('mrr_daily_90d') or []
    mrr_90d_ago = (daily[0].get('mrr_cents') if daily else 0) or 0
    delta_str = _delta(stripe.get('mrr_cents') or 0, mrr_90d_ago)
    upside = expected_now - mrr_now
    parts = [f'MRR is {_money(mrr_now)} from active paying customers']
    if upside > 0:
        parts.append(f'{_money(upside)} more would convert if all in-flight trials bill')
    if delta_str:
        parts.append(delta_str)
    summaries['section-revenue'] = '. '.join(parts) + '.'

    # ── trial pipeline ──
    trials = stripe.get('trials') or 0
    trials_likely = stripe.get('trials_likely_to_convert') or 0
    trials_cancel = stripe.get('trials_with_cancel_scheduled') or 0
    paid_cancel = stripe.get('paid_with_cancel_scheduled') or 0
    conv_7d = stripe.get('trial_conversions_7d') or 0
    if trials == 0 and conv_7d == 0 and paid_cancel == 0:
        summaries['section-trial-pipeline'] = (
            'No trials in flight and no cancellations queued. The card-on-file pipeline is empty.'
        )
    else:
        bits = []
        if trials > 0:
            bits.append(f'{_pluralize(trials, "trial")} in flight ({trials_likely} likely to bill, {trials_cancel} with cancel scheduled)')
        if paid_cancel > 0:
            bits.append(f'{_pluralize(paid_cancel, "paid sub")} with cancel scheduled')
        if conv_7d > 0:
            bits.append(f'{_pluralize(conv_7d, "trial converted", "trials converted")} in the last 7 days')
        summaries['section-trial-pipeline'] = '. '.join(bits) + '.'

    # ── failed payments · top offenders ──
    failed_users_30d = stripe.get('failed_payment_users_30d') or 0
    failed_attempts_30d = stripe.get('failed_payment_attempts_30d') or 0
    failing = stripe.get('failing_users') or []
    if failed_users_30d == 0:
        summaries['section-failing-customers'] = (
            'No failed payments in the last 30 days. Revenue collection is clean.'
        )
    else:
        worst = failing[0] if failing else None
        worst_share = (worst.get('attempts_30d', 0) / failed_attempts_30d * 100) if (worst and failed_attempts_30d) else 0
        if worst and worst_share >= 50:
            who = worst.get('email') or worst.get('customer_id', 'one customer')
            summaries['section-failing-customers'] = (
                f'{_pluralize(failed_users_30d, "customer")} with failed payments in 30d, '
                f'{worst.get("attempts_30d", 0)} of {failed_attempts_30d} attempts from {who}. '
                f'Likely a single dead card — reach out before churning them.'
            )
        else:
            summaries['section-failing-customers'] = (
                f'{_pluralize(failed_users_30d, "customer")} with failed payments in 30d, '
                f'{failed_attempts_30d} attempts total. Per-user breakdown below.'
            )

    # ── user activity · 30d ──
    funnel = events.get('funnel') or []
    signal_views = next((s.get('users') for s in funnel if s.get('step') == 'signal_view'), 0) or 0
    if signal_views == 0:
        summaries['section-user-activity'] = (
            'No tracked user activity in the last 7 days. Login + event tracking populates from this point forward.'
        )
    else:
        summaries['section-user-activity'] = (
            f'{_pluralize(signal_views, "user")} viewed a signal in the last 7 days. '
            f'Bet-tap conversion follows in the funnel section below.'
        )

    # ── signals · 7d ──
    signals_by_sport = events.get('signals_issued') or {}
    total_signals = sum(signals_by_sport.values())
    if total_signals == 0:
        summaries['section-signals'] = (
            'No signals issued in the last 7 days. Pass days are a feature, not a failure.'
        )
    else:
        breakdown = ', '.join(f'{n} {sport.upper()}' for sport, n in sorted(signals_by_sport.items()) if n)
        summaries['section-signals'] = (
            f'{_pluralize(total_signals, "signal")} issued in the last 7 days ({breakdown}).'
        )

    # ── funnel ──
    if funnel:
        steps = {s.get('step'): s for s in funnel if s.get('step')}
        view_users = (steps.get('signal_view') or {}).get('users', 0)
        bet_card = (steps.get('bet_tap_signal_card') or {}).get('users', 0)
        bet_place = (steps.get('bet_tap_place_bet') or {}).get('users', 0)
        if view_users == 0:
            summaries['section-funnel'] = (
                'No signal views recorded yet. The funnel populates as authenticated users tap signals.'
            )
        else:
            conv1 = round(100.0 * bet_card / view_users, 1) if view_users else 0
            conv2 = round(100.0 * bet_place / view_users, 1) if view_users else 0
            summaries['section-funnel'] = (
                f'{_pluralize(view_users, "user")} viewed signals, '
                f'{bet_card} tapped a bet card ({conv1}%), '
                f'{bet_place} reached the place-bet surface ({conv2}%).'
            )

    # ── traffic ──
    sessions = ga4.get('sessions') or ga4.get('sessions_30d') or 0
    if sessions == 0:
        summaries['section-traffic'] = (
            'GA4 reports 0 sessions in the window. Confirm tracking is firing on the marketing site.'
        )
    else:
        gsc_clicks = gsc.get('clicks') or 0
        if gsc_clicks > 0:
            summaries['section-traffic'] = (
                f'{int(sessions):,} sessions in the window. {int(gsc_clicks):,} GSC clicks last 7 days — search is contributing real top-of-funnel.'
            )
        else:
            summaries['section-traffic'] = (
                f'{int(sessions):,} sessions in the window. GSC reporting is empty — likely propagation delay or the verified property is wrong.'
            )

    # ── bet taps ──
    bet_taps_by_surface = events.get('bet_taps') or {}
    total_taps = sum(bet_taps_by_surface.values())
    if total_taps == 0:
        summaries['section-bet-taps'] = (
            'No bet taps from real users in the last 7 days. Distribution is the bottleneck — instrumentation is fine.'
        )
    else:
        surfaces = ', '.join(f'{n} from {surface}' for surface, n in sorted(bet_taps_by_surface.items()) if n)
        summaries['section-bet-taps'] = (
            f'{_pluralize(total_taps, "bet tap")} in the last 7 days ({surfaces}).'
        )

    return summaries


def compute(metrics: dict) -> dict:
    """Public entry point. Returns {'headline': {...}, 'actions': [...],
    'summaries': {...}}. Wired into /api/admin/metrics in admin_api.py."""
    return {
        'headline':  compute_headline(metrics),
        'actions':   compute_actions(metrics),
        'summaries': compute_summaries(metrics),
    }
