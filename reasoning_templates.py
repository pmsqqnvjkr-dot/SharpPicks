"""
Signal Reasoning Engine - Template Library (v2)

Maps engineered feature names to human-readable analyst-style bullets.

v2 schema (changed from v1):
  TEMPLATES[feature_name] = {
      'category': <dedupe key>,
      'tiers': [
          {'when': lambda v, ctx -> bool,        # first matching tier wins
           'fields': lambda v, ctx -> dict|None,  # derived placeholders, None = skip
           'variants': [str, ...]},               # phrasing pool, .format(**fields)
          ...
      ],
  }

Selection (generate_reasoning_bullets):
  - Walk top-8 features by importance.
  - First matching tier per feature renders a bullet.
  - One bullet per category. Stop at 2 primary bullets.
  - Append one contrarian market bullet (separate generator) as bullet 3 if
    any contrarian bucket clears; otherwise return 2. No filler.

Variant selection is seeded on pick_id so a given pick always renders the same
phrasing, but adjacent picks vary. Variants whose placeholders are missing or
None are skipped in favor of the next variant in the pool.

Voice guardrails: cite the input value and what it implies. No "detected,"
"model identifies," "model finds value," "professional money," or any phrasing
that frames the model as special rather than reading a specific signal.
"""
import re
import hashlib

# Categories (dedupe keys): schedule, form, efficiency, splits, market,
# injuries, pitching, bullpen, park_context, officiating.

_FIELD_RE = re.compile(r'\{(\w+)')


# ─── ACCESSORS ────────────────────────────────────────────────────────────────

def _pick_val(diff_val, ctx):
    """Home-minus-away (or away-minus-home for 2026-05 features) diff from the
    pick side's perspective. Positive = favors the pick."""
    return diff_val if ctx.get('is_pick_home') else -diff_val


def _pick_rest(ctx):
    return ctx.get('home_rest') if ctx.get('is_pick_home') else ctx.get('away_rest')


def _opp_rest(ctx):
    return ctx.get('away_rest') if ctx.get('is_pick_home') else ctx.get('home_rest')


def _num(x):
    """Coerce to float, or None if not a finite number."""
    if x is None:
        return None
    try:
        f = float(x)
    except (ValueError, TypeError):
        return None
    if f != f or f in (float('inf'), float('-inf')):
        return None
    return f


def _pct(ctx, side, key):
    """Win-rate / pct from ctx extras as an integer 0-100, or None if absent."""
    if side == 'pick':
        full = f"{'home' if ctx.get('is_pick_home') else 'away'}_{key}"
    elif side == 'opp':
        full = f"{'away' if ctx.get('is_pick_home') else 'home'}_{key}"
    else:
        full = f"{side}_{key}"
    raw = _num(ctx.get(full))
    if raw is None:
        return None
    return round(raw * 100)


# ─── ENGINE ───────────────────────────────────────────────────────────────────

def _stable_hash(seed):
    """Deterministic across processes (unlike builtin hash, which is salted)."""
    return int(hashlib.md5(str(seed).encode('utf-8')).hexdigest(), 16)


def _render_variant(variant, fields):
    """Format one variant, or None if any referenced placeholder is missing/None."""
    for k in _FIELD_RE.findall(variant):
        if k not in fields or fields[k] is None:
            return None
    try:
        return variant.format(**fields)
    except (KeyError, IndexError, ValueError):
        return None


def _select_variant(variants, fields, seed):
    """Pick a seed-stable variant, falling back through the pool if the chosen
    one has missing placeholders."""
    n = len(variants)
    if n == 0:
        return None
    start = _stable_hash(seed) % n if seed else 0
    for i in range(n):
        rendered = _render_variant(variants[(start + i) % n], fields)
        if rendered:
            return rendered
    return None


def render_template(feature_name, value, ctx):
    """Resolve a feature to a bullet string, or None. Walks the template's tiers
    in order; the first whose `when` passes and whose fields resolve wins."""
    entry = TEMPLATES.get(feature_name)
    if not entry:
        return None
    seed = f"{ctx.get('pick_id', '')}:{feature_name}"
    for tier in entry.get('tiers', []):
        try:
            if not tier['when'](value, ctx):
                continue
        except Exception:
            continue
        fields = dict(ctx)
        builder = tier.get('fields')
        if builder is not None:
            try:
                extra = builder(value, ctx)
            except Exception:
                extra = None
            if extra is None:
                continue
            fields.update(extra)
        rendered = _select_variant(tier['variants'], fields, seed)
        if rendered:
            return rendered
    return None


# ─── TEMPLATE REGISTRY ────────────────────────────────────────────────────────

TEMPLATES = {

    # ═══ SCHEDULE / REST ═══

    'rest_advantage': {
        'category': 'schedule',
        'tiers': [
            {  # Tier A: decisive, favors pick, |diff| >= 2
                'when': lambda v, ctx: (_pick_val(v, ctx) > 0
                                        and _num(_pick_rest(ctx)) is not None
                                        and _num(_opp_rest(ctx)) is not None
                                        and abs(_num(_pick_rest(ctx)) - _num(_opp_rest(ctx))) >= 2),
                'fields': lambda v, ctx: {
                    'pick_rest': _num(_pick_rest(ctx)),
                    'opp_rest': _num(_opp_rest(ctx)),
                    'advantage_days': abs(round(_num(_pick_rest(ctx)) - _num(_opp_rest(ctx)))),
                },
                'variants': [
                    "Rest advantage: {pick_team} on {pick_rest:.0f}d rest vs {opp_team} on {opp_rest:.0f}d. Schedule is the dominant input on this read.",
                    "Schedule edge: {pick_team} enters on {pick_rest:.0f}d rest, {opp_team} on {opp_rest:.0f}d. {advantage_days}-day differential is the top model contributor.",
                    "{pick_team} on {pick_rest:.0f}d vs {opp_team} on {opp_rest:.0f}d, rest gap of {advantage_days} days drives the projection.",
                ],
            },
            {  # Tier B: modest, favors pick, |diff| == 1
                'when': lambda v, ctx: (_pick_val(v, ctx) > 0
                                        and _num(_pick_rest(ctx)) is not None
                                        and _num(_opp_rest(ctx)) is not None
                                        and abs(_num(_pick_rest(ctx)) - _num(_opp_rest(ctx))) == 1),
                'fields': lambda v, ctx: {
                    'pick_rest': _num(_pick_rest(ctx)),
                    'opp_rest': _num(_opp_rest(ctx)),
                },
                'variants': [
                    "Marginal rest edge to {pick_team} ({pick_rest:.0f}d vs {opp_rest:.0f}d). One-day differential, but in the model's favor.",
                    "{pick_team} on {pick_rest:.0f}d rest, {opp_team} on {opp_rest:.0f}d. Small but directionally aligned with the read.",
                ],
            },
            {  # Tier C: against pick, edge persists
                'when': lambda v, ctx: (_pick_val(v, ctx) < 0
                                        and _num(_pick_rest(ctx)) is not None
                                        and _num(_opp_rest(ctx)) is not None
                                        and abs(_num(_pick_rest(ctx)) - _num(_opp_rest(ctx))) >= 1),
                'fields': lambda v, ctx: {
                    'pick_rest': _num(_pick_rest(ctx)),
                    'opp_rest': _num(_opp_rest(ctx)),
                },
                'variants': [
                    "Rest disadvantage: {pick_team} on shorter rest ({pick_rest:.0f}d vs {opp_rest:.0f}d). Edge persists net of the schedule spot.",
                    "Schedule headwind: {pick_team} the more-fatigued side. Read holds with the rest deficit priced in.",
                ],
            },
        ],
    },

    'home_rest': {
        'category': 'schedule',
        'tiers': [
            {  # well-rested
                'when': lambda v, ctx: _num(v) is not None and _num(v) >= 3,
                'fields': lambda v, ctx: {'team': ctx.get('home_team'), 'n': _num(v)},
                'variants': [
                    "{team} on {n:.0f} days rest, fully recovered, no schedule friction.",
                    "{team} arriving on {n:.0f}d rest. Clean prep window.",
                    "Rested side: {team} on {n:.0f} days off.",
                ],
            },
            {  # back-to-back
                'when': lambda v, ctx: _num(v) is not None and _num(v) == 0,
                'fields': lambda v, ctx: {'team': ctx.get('home_team')},
                'variants': [
                    "{team} on a back-to-back. Second-leg net rating historically degrades 2-3%.",
                    "{team} playing a B2B. Watch fourth-quarter legs.",
                    "Back-to-back spot for {team}. Schedule fatigue is in the projection.",
                ],
            },
        ],
    },

    'away_rest': {
        'category': 'schedule',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) >= 3,
                'fields': lambda v, ctx: {'team': ctx.get('away_team'), 'n': _num(v)},
                'variants': [
                    "{team} on {n:.0f} days rest, fully recovered, no schedule friction.",
                    "{team} arriving on {n:.0f}d rest. Clean prep window.",
                    "Rested side: {team} on {n:.0f} days off.",
                ],
            },
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) == 0,
                'fields': lambda v, ctx: {'team': ctx.get('away_team')},
                'variants': [
                    "{team} on a back-to-back. Second-leg net rating historically degrades 2-3%.",
                    "{team} playing a B2B. Watch fourth-quarter legs.",
                    "Back-to-back spot for {team}. Schedule fatigue is in the projection.",
                ],
            },
        ],
    },

    'away_travel_miles': {
        'category': 'schedule',
        'tiers': [
            {  # Tier A: cross-country
                'when': lambda v, ctx: _num(v) is not None and _num(v) > 2000,
                'fields': lambda v, ctx: {'away_team': ctx.get('away_team'), 'miles': _num(v)},
                'variants': [
                    "Travel: {away_team} traveled {miles:.0f} miles for this game. Cross-country trips degrade road performance materially.",
                    "Coast-to-coast trip: {away_team} on {miles:.0f} miles of travel. Documented fatigue factor.",
                ],
            },
            {  # Tier B: long
                'when': lambda v, ctx: _num(v) is not None and 1500 <= _num(v) <= 2000,
                'fields': lambda v, ctx: {'away_team': ctx.get('away_team'), 'miles': _num(v)},
                'variants': [
                    "Travel factor: {away_team} on {miles:.0f} miles into this spot. Notable but not extreme.",
                    "{away_team} traveled {miles:.0f} miles. Moderate travel headwind priced in.",
                ],
            },
        ],
    },

    'away_tz_change': {
        'category': 'schedule',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and abs(_num(v)) >= 2,
                'fields': lambda v, ctx: {'away_team': ctx.get('away_team'), 'n': abs(round(_num(v)))},
                'variants': [
                    "Timezone shift: {away_team} crossing {n} time zones. Body-clock effect typically worth ~1pt of net rating.",
                    "{away_team} on a {n}-TZ shift. Circadian disadvantage in the projection.",
                    "{n} time zone change for {away_team}. Read accounts for the body-clock spot.",
                ],
            },
        ],
    },

    'home_games_last_7d': {
        'category': 'schedule',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) >= 4,
                'fields': lambda v, ctx: {'team': ctx.get('home_team'), 'n': round(_num(v))},
                'variants': [
                    "Schedule density: {team} has played {n} games in the last 7 days. Heavy workload spot.",
                    "Compressed schedule for {team}: {n} games in a week. Fatigue priced into the read.",
                    "{team} on {n}-in-7. Workload at the high end of league distribution.",
                ],
            },
        ],
    },

    'away_games_last_7d': {
        'category': 'schedule',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) >= 4,
                'fields': lambda v, ctx: {'team': ctx.get('away_team'), 'n': round(_num(v))},
                'variants': [
                    "Schedule density: {team} has played {n} games in the last 7 days. Heavy workload spot.",
                    "Compressed schedule for {team}: {n} games in a week. Fatigue priced into the read.",
                    "{team} on {n}-in-7. Workload at the high end of league distribution.",
                ],
            },
        ],
    },

    # ═══ RECENT FORM ═══

    'form_diff': {
        'category': 'form',
        'tiers': [
            {  # Tier A: lopsided
                'when': lambda v, ctx: abs(_pick_val(v, ctx)) > 0.30
                                       and _pct(ctx, 'pick', 'form') is not None
                                       and _pct(ctx, 'opp', 'form') is not None,
                'fields': lambda v, ctx: {'pick_l5_pct': _pct(ctx, 'pick', 'form'),
                                          'opp_l5_pct': _pct(ctx, 'opp', 'form')},
                'variants': [
                    "Form gap: {pick_team} on {pick_l5_pct}% wins L5 vs {opp_team} at {opp_l5_pct}%. Wide divergence in recent results.",
                    "{pick_team} {pick_l5_pct}% L5, {opp_team} {opp_l5_pct}% L5. Form delta is one of the top model inputs here.",
                ],
            },
            {  # Tier B: notable, favors pick
                'when': lambda v, ctx: 0.15 < _pick_val(v, ctx) <= 0.30
                                       and _pct(ctx, 'pick', 'form') is not None
                                       and _pct(ctx, 'opp', 'form') is not None,
                'fields': lambda v, ctx: {'pick_l5_pct': _pct(ctx, 'pick', 'form'),
                                          'opp_l5_pct': _pct(ctx, 'opp', 'form')},
                'variants': [
                    "Form edge: {pick_team} trending at {pick_l5_pct}% L5 vs {opp_team} at {opp_l5_pct}%.",
                    "Recent results favor {pick_team} ({pick_l5_pct}% vs {opp_l5_pct}% L5).",
                ],
            },
            {  # Tier C: against, edge persists
                'when': lambda v, ctx: _pick_val(v, ctx) < -0.20
                                       and _pct(ctx, 'pick', 'form') is not None,
                'fields': lambda v, ctx: {'pick_l5_pct': _pct(ctx, 'pick', 'form')},
                'variants': [
                    "Form disadvantage: {pick_team} cold at {pick_l5_pct}% L5. Read survives the slump.",
                    "{pick_team} on a rough L5 ({pick_l5_pct}%), but the model's edge is net of recent form.",
                ],
            },
        ],
    },

    'win_pct_diff': {
        'category': 'form',
        'tiers': [
            {  # Tier A
                'when': lambda v, ctx: abs(_num(v) or 0) > 0.15
                                       and _pct(ctx, 'pick', 'win_pct') is not None
                                       and _pct(ctx, 'opp', 'win_pct') is not None,
                'fields': lambda v, ctx: {'pick_pct': _pct(ctx, 'pick', 'win_pct'),
                                          'opp_pct': _pct(ctx, 'opp', 'win_pct')},
                'variants': [
                    "Record gap: {pick_team} at {pick_pct}% on the season, {opp_team} at {opp_pct}%. Substantial separation.",
                    "Season-long quality gap: {pick_team} {pick_pct}%, {opp_team} {opp_pct}%.",
                ],
            },
            {  # Tier B
                'when': lambda v, ctx: 0.08 < abs(_num(v) or 0) <= 0.15
                                       and _pct(ctx, 'pick', 'win_pct') is not None
                                       and _pct(ctx, 'opp', 'win_pct') is not None,
                'fields': lambda v, ctx: {'pick_pct': _pct(ctx, 'pick', 'win_pct'),
                                          'opp_pct': _pct(ctx, 'opp', 'win_pct')},
                'variants': [
                    "Season record: {pick_team} {pick_pct}% vs {opp_team} {opp_pct}%.",
                    "{pick_team} ({pick_pct}%) sits ahead of {opp_team} ({opp_pct}%) on the season.",
                ],
            },
        ],
    },

    'bdl_win_pct_diff': {
        'category': 'form',
        'tiers': [
            {  # only fires if BDL pct present and differs from primary
                'when': lambda v, ctx: abs(_num(v) or 0) > 0.10
                                       and _pct(ctx, 'pick', 'bdl_win_pct') is not None
                                       and _pct(ctx, 'opp', 'bdl_win_pct') is not None
                                       and _pct(ctx, 'pick', 'bdl_win_pct') != _pct(ctx, 'opp', 'bdl_win_pct'),
                'fields': lambda v, ctx: {'pick_pct': _pct(ctx, 'pick', 'bdl_win_pct'),
                                          'opp_pct': _pct(ctx, 'opp', 'bdl_win_pct')},
                'variants': [
                    "Cross-source check: BDL data has {pick_team} at {pick_pct}% vs {opp_team} at {opp_pct}%. Confirms the read across feeds.",
                    "Independent feed confirms: {pick_team} {pick_pct}% / {opp_team} {opp_pct}% via BDL.",
                ],
            },
        ],
    },

    'cold_streak_diff': {
        'category': 'form',
        'tiers': [
            {  # Tier A: opponent on cold stretch
                'when': lambda v, ctx: _pick_val(v, ctx) >= 2,
                'fields': lambda v, ctx: {'n': max(3, round(abs(_pick_val(v, ctx)) + 2)), 'window': 5},
                'variants': [
                    "Opponent cold stretch: {opp_team} dropped {n} of the last {window}. Bounce-back risk priced low.",
                    "{opp_team} into the game on a {n}-game skid. Read aligns with the cold side staying cold short-term.",
                ],
            },
            {  # Tier B: opponent cold, marginal
                'when': lambda v, ctx: _pick_val(v, ctx) == 1,
                'fields': lambda v, ctx: {},
                'variants': [
                    "{opp_team} coming off a rough stretch. Marginal but consistent with the read.",
                ],
            },
            {  # Tier C: pick is the cold side
                'when': lambda v, ctx: _pick_val(v, ctx) <= -1,
                'fields': lambda v, ctx: {},
                'variants': [
                    "Cold note: {pick_team} on a rough stretch. Edge persists despite recent form.",
                    "{pick_team} fading recently, but the model isolates a structural edge unrelated to short-run results.",
                ],
            },
        ],
    },

    # ═══ TEAM RATINGS / EFFICIENCY ═══

    'net_rtg_diff': {
        'category': 'efficiency',
        'tiers': [
            {  # Tier A
                'when': lambda v, ctx: abs(_pick_val(v, ctx)) > 5,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)), 1)},
                'variants': [
                    "Net rating: {pick_team} holds a +{n} advantage per 100 possessions. Substantial efficiency gap.",
                    "{pick_team} outrates {opp_team} by {n} points per 100. Dominant separator.",
                ],
            },
            {  # Tier B: favors pick
                'when': lambda v, ctx: 2 < _pick_val(v, ctx) <= 5,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)), 1)},
                'variants': [
                    "Net rating edge: {pick_team} ahead by {n} per 100 possessions.",
                    "Efficiency: {pick_team} +{n} net rtg over {opp_team}.",
                ],
            },
            {  # Tier C: against, edge persists
                'when': lambda v, ctx: _pick_val(v, ctx) < -3,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)), 1)},
                'variants': [
                    "Net rating: {opp_team} rates higher, but the spread overcompensates by {n} points.",
                    "{opp_team} the better efficiency team on paper; market price gives that back and more.",
                ],
            },
        ],
    },

    'home_off_rtg': {
        'category': 'efficiency',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) > 118,
                'fields': lambda v, ctx: {'team': ctx.get('home_team'), 'n': round(_num(v), 1)},
                'variants': [
                    "{team} offensive rating: {n}, top-tier league-wide.",
                    "Elite offense: {team} at {n} ortg, drives the projection.",
                ],
            },
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) < 106,
                'fields': lambda v, ctx: {'team': ctx.get('home_team'), 'n': round(_num(v), 1)},
                'variants': [
                    "Offensive concern: {team} at {n} ortg. Bottom of the league.",
                ],
            },
        ],
    },

    'away_off_rtg': {
        'category': 'efficiency',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) > 118,
                'fields': lambda v, ctx: {'team': ctx.get('away_team'), 'n': round(_num(v), 1)},
                'variants': [
                    "{team} offensive rating: {n}, top-tier league-wide.",
                    "Elite offense: {team} at {n} ortg, drives the projection.",
                ],
            },
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) < 106,
                'fields': lambda v, ctx: {'team': ctx.get('away_team'), 'n': round(_num(v), 1)},
                'variants': [
                    "Offensive concern: {team} at {n} ortg. Bottom of the league.",
                ],
            },
        ],
    },

    'home_def_rtg': {
        'category': 'efficiency',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) < 108,
                'fields': lambda v, ctx: {'team': ctx.get('home_team'), 'n': round(_num(v), 1)},
                'variants': [
                    "Defense: {team} at {n} drtg, elite tier.",
                    "{team} defense holding opponents to {n} per 100. Top-tier unit.",
                ],
            },
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) > 118,
                'fields': lambda v, ctx: {'team': ctx.get('home_team'), 'n': round(_num(v), 1)},
                'variants': [
                    "Defensive vulnerability: {team} allowing {n} per 100. Bottom-tier.",
                    "{team} bleeding {n} drtg. Defensive weakness in the matchup.",
                ],
            },
        ],
    },

    'away_def_rtg': {
        'category': 'efficiency',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) < 108,
                'fields': lambda v, ctx: {'team': ctx.get('away_team'), 'n': round(_num(v), 1)},
                'variants': [
                    "Defense: {team} at {n} drtg, elite tier.",
                    "{team} defense holding opponents to {n} per 100. Top-tier unit.",
                ],
            },
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) > 118,
                'fields': lambda v, ctx: {'team': ctx.get('away_team'), 'n': round(_num(v), 1)},
                'variants': [
                    "Defensive vulnerability: {team} allowing {n} per 100. Bottom-tier.",
                    "{team} bleeding {n} drtg. Defensive weakness in the matchup.",
                ],
            },
        ],
    },

    'off_matchup': {
        'category': 'efficiency',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and abs(_num(v)) > 5,
                'fields': lambda v, ctx: {'n': round(abs(_num(v)), 1)},
                'variants': [
                    "Matchup: {pick_team} attacks {opp_team}'s weaker side, +{n} ortg/drtg differential.",
                    "{pick_team} offense vs {opp_team} defense opens a {n}pt efficiency gap.",
                ],
            },
        ],
    },

    'def_matchup': {
        'category': 'efficiency',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and abs(_num(v)) > 5,
                'fields': lambda v, ctx: {'n': round(abs(_num(v)), 1)},
                'variants': [
                    "Defensive matchup: {pick_team}'s D vs {opp_team}'s O, {n}pt suppression edge.",
                ],
            },
        ],
    },

    'pace_diff': {
        'category': 'efficiency',
        'tiers': [
            {  # Tier A
                'when': lambda v, ctx: _num(v) is not None and abs(_num(v)) > (2 if ctx.get('sport') == 'wnba' else 4)
                                       and _num(ctx.get('home_pace')) is not None
                                       and _num(ctx.get('away_pace')) is not None,
                'fields': lambda v, ctx: {'pick_pace': round(_num(ctx.get('home_pace')) if ctx.get('is_pick_home') else _num(ctx.get('away_pace')), 1),
                                          'opp_pace': round(_num(ctx.get('away_pace')) if ctx.get('is_pick_home') else _num(ctx.get('home_pace')), 1)},
                'variants': [
                    "Pace mismatch: {pick_team} {pick_pace} poss vs {opp_team} {opp_pace}. Tempo difference creates exploitable spots.",
                    "Tempo gap: {pick_pace} vs {opp_pace}. Faster side dictates style ~60% of games.",
                ],
            },
            {  # Tier B
                'when': lambda v, ctx: _num(v) is not None
                                       and (1 if ctx.get('sport') == 'wnba' else 2) < abs(_num(v)) <= (2 if ctx.get('sport') == 'wnba' else 4)
                                       and _num(ctx.get('home_pace')) is not None
                                       and _num(ctx.get('away_pace')) is not None,
                'fields': lambda v, ctx: {'pick_pace': round(_num(ctx.get('home_pace')) if ctx.get('is_pick_home') else _num(ctx.get('away_pace')), 1),
                                          'opp_pace': round(_num(ctx.get('away_pace')) if ctx.get('is_pick_home') else _num(ctx.get('home_pace')), 1)},
                'variants': [
                    "Pace: {pick_team} ({pick_pace}) vs {opp_team} ({opp_pace}). Modest tempo edge.",
                ],
            },
        ],
    },

    # ═══ HOME / AWAY SPLITS ═══

    'split_advantage': {
        'category': 'splits',
        'tiers': [
            {  # Tier A: lopsided
                'when': lambda v, ctx: _num(v) is not None and _num(v) > 0.20
                                       and _pct(ctx, 'pick', ('home_pct' if ctx.get('is_pick_home') else 'away_pct')) is not None
                                       and _pct(ctx, 'opp', ('away_pct' if ctx.get('is_pick_home') else 'home_pct')) is not None,
                'fields': lambda v, ctx: {
                    'pct': _pct(ctx, 'pick', ('home_pct' if ctx.get('is_pick_home') else 'away_pct')),
                    'opp_pct': _pct(ctx, 'opp', ('away_pct' if ctx.get('is_pick_home') else 'home_pct')),
                    'home_or_away': 'home' if ctx.get('is_pick_home') else 'on the road',
                    'opp_home_or_away': 'on the road' if ctx.get('is_pick_home') else 'at home',
                },
                'variants': [
                    "Split: {pick_team} {pct}% {home_or_away}, {opp_team} {opp_pct}% {opp_home_or_away}. Wide venue gap.",
                    "Venue effect: {pick_team} dominates {home_or_away} ({pct}%) while {opp_team} struggles {opp_home_or_away} ({opp_pct}%).",
                ],
            },
            {  # Tier B: notable
                'when': lambda v, ctx: _num(v) is not None and 0.10 < _num(v) <= 0.20
                                       and _pct(ctx, 'pick', ('home_pct' if ctx.get('is_pick_home') else 'away_pct')) is not None
                                       and _pct(ctx, 'opp', ('away_pct' if ctx.get('is_pick_home') else 'home_pct')) is not None,
                'fields': lambda v, ctx: {
                    'pct': _pct(ctx, 'pick', ('home_pct' if ctx.get('is_pick_home') else 'away_pct')),
                    'opp_pct': _pct(ctx, 'opp', ('away_pct' if ctx.get('is_pick_home') else 'home_pct')),
                    'home_or_away': 'home' if ctx.get('is_pick_home') else 'road',
                    'opp_home_or_away': 'on the road' if ctx.get('is_pick_home') else 'at home',
                },
                'variants': [
                    "Home/away split favors {pick_team}: {pct}% vs {opp_pct}%.",
                    "Venue: {pick_team} {pct}% {home_or_away}, {opp_team} {opp_pct}% {opp_home_or_away}.",
                ],
            },
            {  # Tier C: against, edge persists
                'when': lambda v, ctx: _num(v) is not None and _num(v) < -0.10,
                'fields': lambda v, ctx: {},
                'variants': [
                    "Split disadvantage for {pick_team}, but the model isolates an unrelated edge.",
                    "Venue factor cuts against {pick_team}; the read survives net of it.",
                ],
            },
        ],
    },

    # ═══ MARKET / LINE ═══

    'line_movement': {
        'category': 'market',
        'tiers': [
            {  # Tier A: steam toward pick
                'when': lambda v, ctx: _line_toward(v, ctx) and abs(_num(v) or 0) >= 1.5,
                'fields': lambda v, ctx: {'n': round(abs(_num(v)), 1)},
                'variants': [
                    "Steam in the model's direction: {n}pts of movement since open. Sharp side agrees.",
                    "Significant line move toward the pick ({n}pts). Buying alongside informed flow.",
                ],
            },
            {  # Tier B: drift toward pick
                'when': lambda v, ctx: _line_toward(v, ctx) and 0.5 <= abs(_num(v) or 0) < 1.5,
                'fields': lambda v, ctx: {'n': round(abs(_num(v)), 1)},
                'variants': [
                    "Line drift: {n}pts in the model's favor since open. Modest but aligned.",
                    "{n}pts of movement toward the pick since open.",
                ],
            },
            {  # Tier C: against, edge persists
                'when': lambda v, ctx: (not _line_toward(v, ctx)) and abs(_num(v) or 0) >= 1.0,
                'fields': lambda v, ctx: {'n': round(abs(_num(v)), 1)},
                'variants': [
                    "Line moved {n}pts against the model's position since open. Edge persists at the worse number.",
                    "Number got worse by {n}pts post-open. Read holds at current price.",
                ],
            },
        ],
    },

    'spread_vs_consensus': {
        'category': 'market',
        'tiers': [
            {  # Tier A
                'when': lambda v, ctx: _num(v) is not None and abs(_num(v)) >= 2.0,
                'fields': lambda v, ctx: {'n': round(abs(_num(v)), 1)},
                'variants': [
                    "Outlier price: current spread is {n}pts off book consensus. Material disagreement to exploit.",
                    "Spread sits {n}pts off consensus. One book mispricing relative to the field.",
                ],
            },
            {  # Tier B
                'when': lambda v, ctx: _num(v) is not None and 1.0 <= abs(_num(v)) < 2.0,
                'fields': lambda v, ctx: {'n': round(abs(_num(v)), 1)},
                'variants': [
                    "Spread differs from consensus by {n}pts. Modest book-level disagreement.",
                    "Current number is {n}pts off the cross-book consensus.",
                ],
            },
        ],
    },

    'rundown_spread_std': {
        'category': 'market',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) >= 0.5,
                'fields': lambda v, ctx: {'n': round(_num(v), 1)},
                'variants': [
                    "Books disagree: spread std of {n} across the field. Market uncertainty.",
                    "Cross-book dispersion: {n} std on the spread. No consensus.",
                    "Sportsbooks don't agree, {n} std on this number.",
                ],
            },
        ],
    },

    'line_velocity': {
        'category': 'market',
        'tiers': [
            {  # Tier A
                'when': lambda v, ctx: _num(v) is not None and abs(_num(v)) > 0.6,
                'fields': lambda v, ctx: {'v': round(abs(_num(v)), 2)},
                'variants': [
                    "Line velocity at {v}, pricing moving substantially faster than book-average drift. Consistent with informed flow.",
                    "High velocity ({v}) on this number. Above-average rate of pricing pressure.",
                ],
            },
            {  # Tier B
                'when': lambda v, ctx: _num(v) is not None and 0.3 < abs(_num(v)) <= 0.6,
                'fields': lambda v, ctx: {'v': round(abs(_num(v)), 2)},
                'variants': [
                    "Line velocity {v}, above the league baseline. Some informed pressure on the price.",
                ],
            },
        ],
    },

    'ml_rl_implied_gap_home': {
        'category': 'market',
        'tiers': [
            {  # Tier A: close-game pricing
                'when': lambda v, ctx: ctx.get('is_pick_home') and _num(v) is not None and _num(v) >= 0.18,
                'fields': lambda v, ctx: {'pp': round(abs(_num(v)) * 100)},
                'variants': [
                    "Market shape: book pricing implies a tight game for {pick_team} ({pp}pp gap between win and cover prob). Run-line value if model agrees.",
                    "Close-game pricing: {pp}pp gap between ML and RL implied probs for {pick_team}.",
                ],
            },
            {  # Tier B: modest close-game
                'when': lambda v, ctx: ctx.get('is_pick_home') and _num(v) is not None and 0.12 <= _num(v) < 0.18,
                'fields': lambda v, ctx: {'pp': round(abs(_num(v)) * 100)},
                'variants': [
                    "Market reads this as competitive: {pp}pp ML-vs-RL gap for {pick_team}.",
                ],
            },
            {  # Tier C: blowout pricing
                'when': lambda v, ctx: ctx.get('is_pick_home') and _num(v) is not None and 0 <= _num(v) <= 0.04,
                'fields': lambda v, ctx: {'pp': round(abs(_num(v)) * 100)},
                'variants': [
                    "Blowout pricing: narrow ML-RL gap for {pick_team} ({pp}pp). Market expects a wide final.",
                    "Book pricing implies a dominant outcome for {pick_team}, only {pp}pp between win prob and cover prob.",
                ],
            },
        ],
    },

    'ml_rl_implied_gap_away': {
        'category': 'market',
        'tiers': [
            {
                'when': lambda v, ctx: (not ctx.get('is_pick_home')) and _num(v) is not None and _num(v) >= 0.18,
                'fields': lambda v, ctx: {'pp': round(abs(_num(v)) * 100)},
                'variants': [
                    "Market shape: book pricing implies a tight game for {pick_team} ({pp}pp gap between win and cover prob). Run-line value if model agrees.",
                    "Close-game pricing: {pp}pp gap between ML and RL implied probs for {pick_team}.",
                ],
            },
            {
                'when': lambda v, ctx: (not ctx.get('is_pick_home')) and _num(v) is not None and 0.12 <= _num(v) < 0.18,
                'fields': lambda v, ctx: {'pp': round(abs(_num(v)) * 100)},
                'variants': [
                    "Market reads this as competitive: {pp}pp ML-vs-RL gap for {pick_team}.",
                ],
            },
            {
                'when': lambda v, ctx: (not ctx.get('is_pick_home')) and _num(v) is not None and 0 <= _num(v) <= 0.04,
                'fields': lambda v, ctx: {'pp': round(abs(_num(v)) * 100)},
                'variants': [
                    "Blowout pricing: narrow ML-RL gap for {pick_team} ({pp}pp). Market expects a wide final.",
                    "Book pricing implies a dominant outcome for {pick_team}, only {pp}pp between win prob and cover prob.",
                ],
            },
        ],
    },

    'rl_ml_agree': {
        'category': 'market',
        'tiers': [
            {  # run line tighter than moneyline implies
                'when': lambda v, ctx: _num(v) is not None and _num(v) < 0,
                'fields': lambda v, ctx: {},
                'variants': [
                    "RL and ML disagree directionally: run line pricing tighter than the ML implies. Market split on margin.",
                    "Cross-market disagreement: run line treats this as closer than the moneyline does.",
                ],
            },
            {  # moneyline tighter than run line implies
                'when': lambda v, ctx: _num(v) is not None and _num(v) > 0,
                'fields': lambda v, ctx: {},
                'variants': [
                    "RL and ML disagree: ML pricing tighter than the run line implies. Market split on win prob vs margin.",
                    "Cross-market split: moneyline closer than the RL would suggest.",
                ],
            },
        ],
    },

    'chalk_level': {
        'category': 'market',
        'tiers': [
            {  # Tier A: heavy favorite
                'when': lambda v, ctx: _num(v) is not None and _num(v) > 200,
                'fields': lambda v, ctx: {'v': round(abs(_num(v)))},
                'variants': [
                    "Heavy chalk: favorite priced at -{v}. The model's implied edge holds at the current number.",
                    "Favorite at -{v}; the model's projection still clears the price despite the juice.",
                ],
            },
            {  # Tier B: heavy dog the model likes
                'when': lambda v, ctx: _num(v) is not None and _num(v) <= -180 and not ctx.get('is_pick_favorite', False),
                'fields': lambda v, ctx: {'v': round(abs(_num(v)))},
                'variants': [
                    "Heavy dog spot: pick priced at +{v}. The model's implied probability exceeds the market by a wide margin.",
                    "Plus-{v} on the dog with a model edge, high variance but a priced inefficiency.",
                ],
            },
        ],
    },

    # ═══ INJURIES ═══

    'injury_ppg_diff': {
        'category': 'injuries',
        'tiers': [
            {  # Tier A
                'when': lambda v, ctx: abs(_pick_val(v, ctx)) > 10,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)), 1)},
                'variants': [
                    "Injury asymmetry: {opp_team} missing {n} more PPG of production than {pick_team}. Lineup materially weakened.",
                    "{opp_team} down {n} PPG vs {pick_team}'s absences. Structural lineup gap.",
                ],
            },
            {  # Tier B: favors pick
                'when': lambda v, ctx: 5 < _pick_val(v, ctx) <= 10,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)), 1)},
                'variants': [
                    "Injury edge: {opp_team} missing {n} more PPG of production. Notable lineup gap.",
                ],
            },
            {  # Tier C: against, edge persists
                'when': lambda v, ctx: _pick_val(v, ctx) < -5,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)), 1)},
                'variants': [
                    "Injury headwind: {pick_team} missing {n} more PPG of production. Edge is net of the absences.",
                ],
            },
        ],
    },

    'home_ppg_at_risk': {
        'category': 'injuries',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) > 10,
                'fields': lambda v, ctx: {'team': ctx.get('home_team'), 'n': round(_num(v), 1)},
                'variants': [
                    "{team} carrying {n} PPG at risk from injuries. Watch late scratches.",
                    "Injury watch: {team} has {n} PPG of production in question.",
                ],
            },
        ],
    },

    'away_ppg_at_risk': {
        'category': 'injuries',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) > 10,
                'fields': lambda v, ctx: {'team': ctx.get('away_team'), 'n': round(_num(v), 1)},
                'variants': [
                    "{team} carrying {n} PPG at risk from injuries. Watch late scratches.",
                    "Injury watch: {team} has {n} PPG of production in question.",
                ],
            },
        ],
    },

    'home_star_out': {
        'category': 'injuries',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) >= 1,
                'fields': lambda v, ctx: {'team': ctx.get('home_team')},
                'variants': [
                    "{team} missing a key rotation player. Significant absence.",
                    "Star absence for {team}. Lineup is below normal.",
                    "{team} short a primary contributor.",
                ],
            },
        ],
    },

    'away_star_out': {
        'category': 'injuries',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and _num(v) >= 1,
                'fields': lambda v, ctx: {'team': ctx.get('away_team')},
                'variants': [
                    "{team} missing a key rotation player. Significant absence.",
                    "Star absence for {team}. Lineup is below normal.",
                    "{team} short a primary contributor.",
                ],
            },
        ],
    },

    'injury_diff': {  # MLB
        'category': 'injuries',
        'tiers': [
            {  # Tier A
                'when': lambda v, ctx: abs(_pick_val(v, ctx)) > 8,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)))},
                'variants': [
                    "Injury asymmetry: {opp_team} significantly more banged up, {n}-point impact differential.",
                ],
            },
            {  # Tier B
                'when': lambda v, ctx: 4 < _pick_val(v, ctx) <= 8,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)))},
                'variants': [
                    "Injury edge: {opp_team} carrying a heavier injury burden ({n}-pt impact gap).",
                ],
            },
            {  # Tier C
                'when': lambda v, ctx: _pick_val(v, ctx) < -4,
                'fields': lambda v, ctx: {},
                'variants': [
                    "Injury headwind: {pick_team} the more-banged-up side. Read holds net of absences.",
                ],
            },
        ],
    },

    # ═══ MLB PITCHING ═══

    'era_diff': {
        'category': 'pitching',
        'tiers': [
            {  # Tier A
                'when': lambda v, ctx: abs(_pick_val(v, ctx)) > 1.5,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)), 2),
                                          'pick_sp': ctx.get('pick_sp'), 'opp_sp': ctx.get('opp_sp')},
                'variants': [
                    "Pitching edge: starter ERA gap of {n} runs favors {pick_team}. Top-of-rotation mismatch.",
                    "{pick_sp} vs {opp_sp}: {n} ERA differential, decisive on paper.",
                    "Pitching edge: {n} ERA gap in {pick_team}'s favor.",
                ],
            },
            {  # Tier B: favors pick
                'when': lambda v, ctx: 0.8 < _pick_val(v, ctx) <= 1.5,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)), 2),
                                          'pick_sp': ctx.get('pick_sp')},
                'variants': [
                    "Starter ERA: {n}-run advantage to {pick_team}'s {pick_sp}.",
                    "Pitching edge: {n} ERA gap in {pick_team}'s favor.",
                ],
            },
            {  # Tier C: against, edge persists
                'when': lambda v, ctx: _pick_val(v, ctx) < -0.8,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)), 2)},
                'variants': [
                    "Pitching disadvantage: opposing starter ERA is {n} runs lower. Edge sits in the lineup matchup.",
                ],
            },
        ],
    },

    'whip_diff': {
        'category': 'pitching',
        'tiers': [
            {
                'when': lambda v, ctx: _pick_val(v, ctx) > 0.15,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)), 2),
                                          'pick_sp': ctx.get('pick_sp')},
                'variants': [
                    "WHIP edge: {pick_sp} allowing fewer baserunners ({n} WHIP gap).",
                    "Traffic management: {pick_team}'s starter at a {n} WHIP advantage.",
                ],
            },
        ],
    },

    'pitcher_win_pct_diff': {
        'category': 'pitching',
        'tiers': [
            {
                'when': lambda v, ctx: abs(_pick_val(v, ctx)) > 0.15,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)) * 100),
                                          'pick_sp': ctx.get('pick_sp'), 'opp_sp': ctx.get('opp_sp')},
                'variants': [
                    "Starter win rate: {pick_sp} carrying a {n}pp higher win % this season.",
                    "{pick_sp} ({pick_team}) wins at a materially higher rate than {opp_sp}.",
                ],
            },
        ],
    },

    'bullpen_fatigue_diff': {
        'category': 'pitching',
        'tiers': [
            {  # Tier A
                'when': lambda v, ctx: _pick_val(v, ctx) > 3,
                'fields': lambda v, ctx: {},
                'variants': [
                    "Bullpen edge: {opp_team}'s pen significantly more fatigued. Late-inning leverage skews hard.",
                    "Pen fatigue gap: {opp_team} much heavier workload than {pick_team}. Late-game edge.",
                ],
            },
            {  # Tier B
                'when': lambda v, ctx: 1.5 < _pick_val(v, ctx) <= 3,
                'fields': lambda v, ctx: {},
                'variants': [
                    "Bullpen edge: {opp_team}'s pen running heavier than {pick_team}'s.",
                ],
            },
            {  # Tier C
                'when': lambda v, ctx: _pick_val(v, ctx) < -1.5,
                'fields': lambda v, ctx: {},
                'variants': [
                    "Bullpen concern: {pick_team}'s pen carrying a workload gap. Factored in.",
                ],
            },
        ],
    },

    'bullpen_era_diff': {  # 14-day form
        'category': 'pitching',
        'tiers': [
            {  # Tier A
                'when': lambda v, ctx: abs(_pick_val(v, ctx)) > 1.5,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)), 2)},
                'variants': [
                    "Bullpen form: {opp_team}'s pen at a {n}-run ERA disadvantage over 14 days. Late-inning edge to {pick_team}.",
                    "14-day pen ERA: {opp_team}'s relievers {n} runs worse than {pick_team}'s. Significant.",
                ],
            },
            {  # Tier B
                'when': lambda v, ctx: 0.75 < _pick_val(v, ctx) <= 1.5,
                'fields': lambda v, ctx: {'n': round(abs(_pick_val(v, ctx)), 2)},
                'variants': [
                    "Pen form: {n}-run ERA gap over 14 days favors {pick_team}.",
                ],
            },
            {  # Tier C
                'when': lambda v, ctx: _pick_val(v, ctx) < -0.75,
                'fields': lambda v, ctx: {},
                'variants': [
                    "Pen form note: {pick_team}'s pen running worse over 14 days. Edge sustains despite it.",
                ],
            },
        ],
    },

    'ump_deviation': {
        'category': 'pitching',
        'tiers': [
            {  # Tier A high-scoring
                'when': lambda v, ctx: _num(v) is not None and _num(v) > 0.5,
                'fields': lambda v, ctx: {'n': round(abs(_num(v)), 1)},
                'variants': [
                    "Plate umpire trends high-scoring (+{n} runs/game vs league avg). Wider margins favor the projected cover side.",
                    "Umpire factor: +{n} runs/game tendency. Pushes toward wider finals.",
                ],
            },
            {  # Tier A low-scoring
                'when': lambda v, ctx: _num(v) is not None and _num(v) < -0.5,
                'fields': lambda v, ctx: {'n': round(abs(_num(v)), 1)},
                'variants': [
                    "Plate umpire trends low-scoring ({n} runs/game vs league avg). Tighter finals make run-line covers harder.",
                ],
            },
            {  # Tier B mild
                'when': lambda v, ctx: _num(v) is not None and 0.3 < abs(_num(v)) <= 0.5,
                'fields': lambda v, ctx: {'sign': '+' if _num(v) > 0 else '-', 'n': round(abs(_num(v)), 1)},
                'variants': [
                    "Umpire mild tilt: {sign}{n} runs/game vs league. Marginal factor.",
                ],
            },
        ],
    },

    # ═══ MLB BULLPEN AVAILABILITY ═══

    'closer_used_diff': {
        'category': 'bullpen',
        'tiers': [
            # Tier A (closer + setup arms unavailable) added with leverage-arm
            # feature in Phase 2; Tier B/C available now from the closer heuristic.
            {  # Tier B: opposing closer unavailable
                'when': lambda v, ctx: _pick_val(v, ctx) == 2,
                'fields': lambda v, ctx: {},
                'variants': [
                    "Closer availability: {opp_team}'s closer used in 2+ of last 3. Late-inning leverage favors {pick_team}.",
                    "{opp_team}'s closer likely unavailable. Edge in the 9th.",
                ],
            },
            {  # Tier C: pick's closer worked recently
                'when': lambda v, ctx: _pick_val(v, ctx) <= -2,
                'fields': lambda v, ctx: {},
                'variants': [
                    "Closer note: {pick_team}'s closer worked recently. Workload factored in.",
                ],
            },
        ],
    },

    # ═══ MLB PARK / SERIES ═══

    'park_factor': {
        'category': 'park_context',
        'tiers': [
            {  # Tier A hitter
                'when': lambda v, ctx: _num(v) is not None and _num(v) > 1.10,
                'fields': lambda v, ctx: {'venue': ctx.get('venue'), 'n': round(_num(v), 2)},
                'variants': [
                    "Park: {venue} plays extremely hitter-friendly (PF: {n}). Run environment elevated, run-line probabilities shift.",
                    "Hitter's park: {venue} ({n} factor). Material impact on run expectation.",
                ],
            },
            {  # Tier A pitcher
                'when': lambda v, ctx: _num(v) is not None and _num(v) < 0.90,
                'fields': lambda v, ctx: {'venue': ctx.get('venue'), 'n': round(_num(v), 2)},
                'variants': [
                    "Pitcher's park: {venue} suppresses scoring ({n} PF). Tighter finals.",
                ],
            },
            {  # Tier B lean
                'when': lambda v, ctx: _num(v) is not None and (1.06 < _num(v) <= 1.10 or 0.90 <= _num(v) < 0.94),
                'fields': lambda v, ctx: {'venue': ctx.get('venue'), 'n': round(_num(v), 2),
                                          'lean': 'hitter' if _num(v) > 1.0 else 'pitcher'},
                'variants': [
                    "Park lean: {venue} mildly {lean}-friendly ({n} PF). Modest run-environment shift.",
                ],
            },
        ],
    },

    'series_game_num': {
        'category': 'park_context',
        'tiers': [
            {
                'when': lambda v, ctx: _num(v) is not None and int(_num(v)) >= 2,
                'fields': lambda v, ctx: {'n': int(_num(v))},
                'variants': [
                    "Series context: game {n} of the set. Bullpen carryover and lineup state from prior games factored in.",
                    "G{n} of the series, the model accounts for pen usage and lineup rotation from earlier games.",
                    "In-series game ({n} of set). Carryover effects priced in.",
                ],
            },
        ],
    },
}


# ─── LINE-MOVEMENT DIRECTION ──────────────────────────────────────────────────

def _line_toward(movement, ctx):
    """True when line_movement favors the pick. Positive movement = spread_home
    rose (home getting more points = home less favored). So home pick is favored
    by negative movement, away pick by positive."""
    m = _num(movement)
    if m is None:
        return False
    return (m < 0) if ctx.get('is_pick_home') else (m > 0)


# ─── CONTRARIAN ───────────────────────────────────────────────────────────────

# Three buckets, each tiered, picked in priority order. Returns None when no
# bucket clears (no filler third bullet).

_CONTRARIAN_VARIANTS = {
    'move_toward_A': [
        "Line moved {n}pts toward the model since open. Market converging on the same read.",
        "Sharp steam in the model's direction ({n}pts since open). Aligned with informed flow.",
    ],
    'move_toward_B': [
        "Line moved {n}pts toward the pick. Modest agreement from the market.",
        "Number drifted {n}pts in the model's favor since open.",
    ],
    'move_against': [
        "Line moved {n}pts against the model since open. Edge persists at the current number.",
        "Number got worse by {n}pts post-open; the model still clears the price.",
    ],
    'books_A': [
        "Books disagree sharply: {n}pt range across the field. Material market uncertainty.",
        "Cross-book dispersion: {std} std on the spread. No consensus, value at the outlier.",
    ],
    'books_B': [
        "Books mildly split: {n}pt range on the spread.",
        "Modest cross-book disagreement ({std} std). Some pricing inefficiency.",
    ],
    'consensus': [
        "Current spread sits {n}pts off cross-book consensus. Mispriced relative to the field.",
        "Pricing gap: this number is {n}pts away from book consensus.",
    ],
}


def generate_contrarian(market_data, ctx):
    """One contrarian market bullet, or None. Priority: directional line
    movement, then book-level disagreement, then consensus gap."""
    seed = f"{ctx.get('pick_id', '')}:contrarian"
    movement = _num(market_data.get('line_movement')) or 0
    spread_std = _num(market_data.get('rundown_spread_std')) or 0
    spread_range = _num(market_data.get('rundown_spread_range')) or 0
    consensus_diff = _num(market_data.get('spread_vs_consensus')) or 0

    toward = _line_toward(movement, ctx)

    # Bucket 1: directional line movement
    if toward and abs(movement) >= 1.5:
        out = _select_variant(_CONTRARIAN_VARIANTS['move_toward_A'], {'n': round(abs(movement), 1)}, seed)
        if out:
            return out
    if toward and 0.5 <= abs(movement) < 1.5:
        out = _select_variant(_CONTRARIAN_VARIANTS['move_toward_B'], {'n': round(abs(movement), 1)}, seed)
        if out:
            return out
    if (not toward) and abs(movement) >= 1.0:
        out = _select_variant(_CONTRARIAN_VARIANTS['move_against'], {'n': round(abs(movement), 1)}, seed)
        if out:
            return out

    # Bucket 2: book-level disagreement
    if spread_range >= 2.0 or spread_std >= 0.7:
        out = _select_variant(_CONTRARIAN_VARIANTS['books_A'],
                              {'n': round(spread_range, 1), 'std': round(spread_std, 1)}, seed)
        if out:
            return out
    if spread_range >= 1.0 or spread_std >= 0.5:
        out = _select_variant(_CONTRARIAN_VARIANTS['books_B'],
                              {'n': round(spread_range, 1), 'std': round(spread_std, 1)}, seed)
        if out:
            return out

    # Bucket 3: consensus gap
    if abs(consensus_diff) >= 0.5:
        out = _select_variant(_CONTRARIAN_VARIANTS['consensus'], {'n': round(abs(consensus_diff), 1)}, seed)
        if out:
            return out

    # Bucket 4: explicit empty. No filler.
    return None


# ─── SELECTION ────────────────────────────────────────────────────────────────

def generate_reasoning_bullets(top_features, game_context, market_data):
    """Build the reasoning bullets for a signal card.

    Walks top-8 features by importance, renders the first matching tier per
    feature, dedupes by category, stops at 2 primary bullets. Appends one
    contrarian market bullet if any bucket clears. Returns a list of 2-3
    strings (or fewer in degenerate cases); no filler.

    Args:
        top_features: list of (feature_name, importance, value)
        game_context: dict with pick_team, opp_team, home/away_team,
                      is_pick_home, spread, edge, pick_id, sport, plus raw
                      feature values used by template fields.
        market_data: dict with line_movement, spread_home_open, spread_home,
                     rundown_spread_std, rundown_spread_range, spread_vs_consensus.
    """
    model_bullets = []
    used_categories = set()

    for feature_name, importance, value in top_features:
        if len(model_bullets) >= 2:
            break
        entry = TEMPLATES.get(feature_name)
        if not entry:
            continue
        category = entry.get('category', 'other')
        if category in used_categories:
            continue
        bullet = render_template(feature_name, value, game_context)
        if bullet:
            model_bullets.append(bullet)
            used_categories.add(category)

    bullets = model_bullets[:2]

    contrarian = generate_contrarian(market_data, game_context)
    if contrarian:
        bullets.append(contrarian)

    # Degenerate safety: if nothing rendered, cite the edge magnitude once.
    # Falsifiable and guardrail-compliant; not market filler.
    if not bullets:
        edge = _num(game_context.get('edge'))
        if edge is not None:
            bullets.append(f"Adjusted edge {edge:+.1f}% clears the qualification threshold.")

    return bullets
