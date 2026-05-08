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
    """Growth-led headline. Lead with MRR + new signups + trial pipeline,
    not payment failures. Order: bad_day (only if material) > good_day
    (revenue + signups) > trial_day (pipeline loaded, no new bookings yet)
    > mixed_day (growth with friction) > quiet_day (default).

    'bad_day' now requires both >=2 distinct customers in payment failure
    AND material churn (>=1 cancellation in 30d). Single dunning loops
    or zero-failure signals don't count as "today's headline".

    Failed-payment signals use the *distinct user* count, not the raw
    attempt count — one customer with 14 retries shouldn't read the
    same as 14 different customers in trouble.
    """
    stripe = _payload(metrics, 'stripe')
    rc     = _payload(metrics, 'revenuecat')
    gp     = _payload(metrics, 'google_play')

    # mrr_cents is the ACTUAL paying revenue (status='active' only).
    # Trial subs are counted separately in stripe.trial_subs and
    # contribute to expected_mrr_cents but NOT mrr_cents.
    mrr_cents      = (stripe.get('mrr_cents') or 0) + (rc.get('mrr_cents') or 0)
    new_subs_7d    = (stripe.get('new_subs_7d') or 0) + (rc.get('new_subs_7d') or 0)
    trials         = stripe.get('trials') or 0
    trials_likely  = stripe.get('trials_likely_to_convert') or 0
    trial_conv_7d  = stripe.get('trial_conversions_7d') or 0
    canceled_30d   = (stripe.get('canceled_30d') or 0) + (rc.get('canceled_30d') or 0)
    cancels_scheduled = (stripe.get('paid_with_cancel_scheduled') or 0) + (stripe.get('trials_with_cancel_scheduled') or 0)
    failed_users = stripe.get('failed_payment_users_30d')
    if failed_users is None:
        failed_users = stripe.get('failed_payments_30d') or 0  # legacy fallback
    installs_28d   = gp.get('user_installs_28d') or 0
    dau_avg        = gp.get('dau_avg_28d') or 0

    # bad_day: only when payment trouble is material, churn is real,
    # AND there's no growth offsetting it. New subs + trial conversions
    # this week qualify as growth — even one positive signal is enough
    # to drop into mixed_day instead. The payment-failures action item
    # still surfaces below the headline when material.
    has_growth = (new_subs_7d > 0) or (trial_conv_7d > 0)
    if failed_users >= 2 and canceled_30d >= 1 and not has_growth:
        return {
            'template': 'bad_day',
            'sentence': (
                f'{failed_users} customers in payment failure and {canceled_30d} cancellation'
                + ('s' if canceled_30d != 1 else '')
                + ' in 30d, no offsetting growth. Top of the action queue today.'
            ),
            'color': 'red',
        }

    # good_day: actual paying customers + new signups this week. Adds
    # acquisition context (installs, DAU) when present so the headline
    # carries the full top-of-funnel signal, not just billings.
    if new_subs_7d > 0 and mrr_cents > 0:
        bits = [
            f'MRR {_money(mrr_cents)}',
            f'{new_subs_7d} new subscriber' + ('s' if new_subs_7d != 1 else '') + ' this week',
        ]
        if trials > 0:
            bits.append(f'{trials} trial' + ('s' if trials != 1 else '') + ' in flight')
        if installs_28d > 0:
            bits.append(f'{installs_28d} install' + ('s' if installs_28d != 1 else '') + ' (28d)')
        return {
            'template': 'good_day',
            'sentence': '. '.join(bits) + '.',
            'color': 'green',
        }

    # trial_day: pipeline filling even if no new paying conversions
    # this week. Distinct from quiet_day so the headline acknowledges
    # demand exists; the conversion is just downstream.
    if trials > 0 or trial_conv_7d > 0:
        head = f'MRR {_money(mrr_cents)}.' if mrr_cents > 0 else 'No paying customers yet.'
        bits = [head]
        if trials > 0:
            bits.append(
                f'{trials} trial' + ('s' if trials != 1 else '') + ' in flight'
                + (f' ({trials_likely} likely to convert)' if trials_likely else '')
            )
        if trial_conv_7d > 0:
            bits.append(f'{trial_conv_7d} trial' + ('s' if trial_conv_7d != 1 else '') + ' converted this week')
        if installs_28d > 0:
            bits.append(f'{installs_28d} install' + ('s' if installs_28d != 1 else '') + ' driving the funnel (28d)')
        return {
            'template': 'trial_day',
            'sentence': ' '.join(bits) + '.',
            'color': 'blue',
        }

    # mixed_day: growth and friction together. Friction is real but
    # subordinated — the headline still leads with the win.
    if new_subs_7d > 0 and (canceled_30d > 0 or cancels_scheduled > 0 or failed_users > 0):
        friction_bits = []
        if cancels_scheduled > 0:
            friction_bits.append(
                f'{cancels_scheduled} cancellation'
                + ('s' if cancels_scheduled != 1 else '')
                + ' scheduled'
            )
        if canceled_30d > 0:
            friction_bits.append(f'{canceled_30d} cancelled in 30d')
        if failed_users > 0:
            friction_bits.append(
                f'{failed_users} customer'
                + ('s' if failed_users != 1 else '')
                + ' in payment failure'
            )
        return {
            'template': 'mixed_day',
            'sentence': (
                f'{new_subs_7d} new subscriber'
                + ('s' if new_subs_7d != 1 else '')
                + f' this week. {", ".join(friction_bits)}. Net positive.'
            ),
            'color': 'amber',
        }

    # quiet_day: default — nothing happening on the revenue or pipeline
    # surfaces. Acknowledge install funnel if any.
    parts = [f'MRR steady at {_money(mrr_cents)}.']
    if installs_28d > 0:
        parts.append(f'{installs_28d} app install' + ('s' if installs_28d != 1 else '') + ' (28d), no new bookings this week.')
    elif dau_avg > 0:
        parts.append(f'{dau_avg:.1f} DAU avg, no new bookings this week.')
    else:
        parts.append('No new subscribers, no trials in flight, no churn.')
    return {
        'template': 'quiet_day',
        'sentence': ' '.join(parts),
        'color': 'blue',
    }


def compute_actions(metrics: dict) -> list:
    """Growth-led action surface for Today's Read. Items render in this
    fixed order regardless of how many fire:

      1. growth          — new signups + trial conversions (good)
      2. acquisition     — GSC clicks, GA4 sessions, Play Store installs (info)
      3. model_perf      — last-30d win/loss + ROI per sport (info)
      4. signal_volume   — signals issued this week (info, lower)
      5. cancel_scheduled— cancellations queued, save window open (warn)
      6. failed_payments — distinct customers in payment failure (warn,
                           only if material — >=2 distinct users)

    Cap at 4 items. Payment-failure copy now requires >=2 distinct
    customers; a single retry loop dunning case doesn't qualify as a
    Today's Read item — it lives on the Failing Customers section.
    """
    stripe = _payload(metrics, 'stripe')
    rc     = _payload(metrics, 'revenuecat')
    events = _payload(metrics, 'events')
    gsc    = _payload(metrics, 'gsc')
    ga4    = _payload(metrics, 'ga4')
    gp     = _payload(metrics, 'google_play')
    model  = _payload(metrics, 'model_perf')

    items = []

    # 1. growth — new signups + trial conversions
    new_subs = (stripe.get('new_subs_7d') or 0) + (rc.get('new_subs_7d') or 0)
    trial_conv_7d = stripe.get('trial_conversions_7d') or 0
    trials = stripe.get('trials') or 0
    trials_likely = stripe.get('trials_likely_to_convert') or 0
    if new_subs > 0 or trial_conv_7d > 0 or trials > 0:
        bits = []
        if new_subs > 0:
            bits.append(f'{new_subs} new subscriber' + ('s' if new_subs != 1 else ''))
        if trial_conv_7d > 0:
            bits.append(f'{trial_conv_7d} trial conversion' + ('s' if trial_conv_7d != 1 else ''))
        if trials > 0:
            tail = f' ({trials_likely} likely to convert)' if trials_likely else ''
            bits.append(f'{trials} trial' + ('s' if trials != 1 else '') + ' in flight' + tail)
        items.append({
            'type': 'growth',
            'priority': 'good',
            'message': ', '.join(bits) + '.',
        })

    # 2. acquisition — GSC + GA4 + Play Store
    gsc_clicks   = gsc.get('clicks') or 0
    ga4_sessions = ga4.get('sessions') or ga4.get('sessions_30d') or 0
    installs_28d = gp.get('user_installs_28d') or 0
    dau_avg      = gp.get('dau_avg_28d') or 0
    if gsc_clicks or ga4_sessions or installs_28d:
        bits = []
        if ga4_sessions:
            bits.append(f'{int(ga4_sessions):,} web session' + ('s' if int(ga4_sessions) != 1 else ''))
        if gsc_clicks:
            bits.append(f'{int(gsc_clicks):,} GSC click' + ('s' if int(gsc_clicks) != 1 else ''))
        if installs_28d:
            bits.append(f'{installs_28d} install' + ('s' if installs_28d != 1 else ''))
        if dau_avg:
            bits.append(f'{dau_avg:.1f} DAU avg')
        items.append({
            'type': 'acquisition',
            'priority': 'info',
            'message': 'Acquisition (28d): ' + ', '.join(bits) + '.',
        })

    # 3. model_perf — last-30d win/loss + unit ROI per sport. Threshold
    # of 3 graded picks per sport so a single revoked-but-graded outlier
    # doesn't get headlined as the model's read.
    by_sport = (model.get('by_sport') or {}) if isinstance(model, dict) else {}
    sport_summaries = []
    sport_order = ['nba', 'mlb', 'wnba']
    for sport in sport_order + [s for s in by_sport.keys() if s not in sport_order]:
        agg = by_sport.get(sport)
        if not agg or agg.get('graded', 0) < 3:
            continue
        wins, losses = agg['wins'], agg['losses']
        wr = agg.get('win_rate')
        roi = agg.get('profit_units') or 0
        seg = f"{sport.upper()} {wins}-{losses}"
        if wr is not None:
            seg += f" ({wr}%)"
        if roi:
            seg += f" {roi:+.1f}u"
        sport_summaries.append(seg)
    if sport_summaries:
        items.append({
            'type': 'model_performance',
            'priority': 'info',
            'message': 'Model 30d: ' + '; '.join(sport_summaries) + '.',
        })

    # 4. signal volume — informational, lower priority than acquisition.
    signals_total = sum((events.get('signals_issued') or {}).values())
    if signals_total > 0:
        breakdown = ', '.join(
            f'{sport.upper()} {n}' for sport, n in sorted((events.get('signals_issued') or {}).items()) if n
        )
        items.append({
            'type': 'signal_volume',
            'priority': 'info',
            'message': f'{signals_total} signal' + ('s' if signals_total != 1 else '') + f' issued this week ({breakdown}).',
        })

    # 5. warn — cancellations scheduled (save window)
    cancels_scheduled = (stripe.get('paid_with_cancel_scheduled') or 0) + (stripe.get('trials_with_cancel_scheduled') or 0)
    if cancels_scheduled > 0:
        items.append({
            'type': 'cancel_scheduled',
            'priority': 'warn',
            'message': (
                f'{cancels_scheduled} cancellation'
                + ('s' if cancels_scheduled != 1 else '')
                + ' scheduled. Save window open.'
            ),
        })

    # 6. warn — payment failures (only if material: >=2 distinct customers)
    failed_users = stripe.get('failed_payment_users_30d')
    failed_attempts = stripe.get('failed_payment_attempts_30d')
    if failed_users is None:
        failed_users = stripe.get('failed_payments_30d') or 0  # legacy
        failed_attempts = failed_users
    if failed_users >= 2:
        items.append({
            'type': 'failed_payments',
            'priority': 'warn',
            'message': (
                f'{failed_users} customers with failed payments in 30d '
                f'({failed_attempts} attempts total). Review the failed-payments list.'
            ),
        })

    # Cap at 4. Items are already in the desired display order so no
    # priority sort here — that would put warns at the bottom and undo
    # the operator's "growth-led" ordering.
    return items[:4]


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
    # The summary leads with the actual paying MRR. For trial upside,
    # we surface BOTH the MRR equivalent (e.g. $115.50/mo) AND the
    # upfront annual billings the trials would generate at conversion
    # (e.g. $1,386 cash). The cash framing matters for an annual-plan-
    # heavy business; pure MRR understates the immediate impact.
    mrr_now = (stripe.get('mrr_cents') or 0) + (rc.get('mrr_cents') or 0)
    expected_now = (stripe.get('expected_mrr_cents') or stripe.get('mrr_cents') or 0) + (rc.get('mrr_cents') or 0)
    daily = stripe.get('mrr_daily_90d') or []
    mrr_90d_ago = (daily[0].get('mrr_cents') if daily else 0) or 0
    delta_str = _delta(stripe.get('mrr_cents') or 0, mrr_90d_ago)
    upside = expected_now - mrr_now
    # Upfront annual billings = MRR upside × 12. For an annual sub
    # billed at $99/year, the customer pays $99 upfront on conversion;
    # MRR = $99/12 = $8.25 but the cash hits in one chunk.
    upside_annual_cash = upside * 12
    parts = [f'MRR is {_money(mrr_now)} from active paying customers']
    if upside > 0:
        parts.append(
            f'{_money(upside)}/mo more (~{_money(upside_annual_cash)} in upfront billings) '
            f'if all in-flight trials convert at the founding rate'
        )
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
