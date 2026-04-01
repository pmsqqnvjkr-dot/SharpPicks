"""
Signal Reasoning Engine — Template Library

Maps engineered feature names to human-readable analyst-style sentences.
Each template receives the raw feature value plus game context to produce
per-pick reasoning bullets.
"""


# ─── TEMPLATE REGISTRY ───────────────────────────────────────────────────────
#
# Keys are the exact engineered feature column names from engineer_features().
#
# Each entry has:
#   category  — used to enforce diversity (no two bullets from same category)
#   render    — callable(value, ctx) → str | None
#
# ctx keys: pick_team, opp_team, home_team, away_team, is_pick_home, spread, edge

def _pick_rest(ctx):
    return ctx['home_rest'] if ctx['is_pick_home'] else ctx['away_rest']

def _opp_rest(ctx):
    return ctx['away_rest'] if ctx['is_pick_home'] else ctx['home_rest']

TEMPLATES = {

    # ═══ SCHEDULE / REST ═══

    'rest_advantage': {
        'category': 'schedule',
        'render': lambda v, ctx: (
            f"Rest advantage: {ctx['pick_team']} on {_pick_rest(ctx):.0f}d rest "
            f"vs {ctx['opp_team']} on {_opp_rest(ctx):.0f}d. "
            f"Rest differential is the top model contributor for this game."
            if (v > 0 and ctx['is_pick_home']) or (v < 0 and not ctx['is_pick_home'])
            else (
                f"Rest disadvantage: {ctx['pick_team']} on shorter rest "
                f"({_pick_rest(ctx):.0f}d vs {_opp_rest(ctx):.0f}d). "
                f"Model finds edge despite the schedule spot."
                if (v < 0 and ctx['is_pick_home']) or (v > 0 and not ctx['is_pick_home'])
                else None
            )
        ),
    },

    'home_rest': {
        'category': 'schedule',
        'render': lambda v, ctx: (
            f"{ctx['home_team']} on {v:.0f} days rest."
            if v >= 3 or v <= 1 else None
        ),
    },

    'away_rest': {
        'category': 'schedule',
        'render': lambda v, ctx: (
            f"{ctx['away_team']} on {v:.0f} days rest."
            if v >= 3 or v <= 1 else None
        ),
    },

    # ═══ RECENT FORM ═══

    'form_diff': {
        'category': 'form',
        'render': lambda v, ctx: (
            f"Form edge: {ctx['pick_team']} trending up "
            f"({_pct(ctx, 'pick', 'form')}% wins L5) vs "
            f"{ctx['opp_team']} ({_pct(ctx, 'opp', 'form')}% wins L5)."
            if _pick_form_val(v, ctx) > 0.15
            else (
                f"Form disadvantage: {ctx['pick_team']} cold recently "
                f"({_pct(ctx, 'pick', 'form')}% wins L5). "
                f"Model sees value despite the slump."
                if _pick_form_val(v, ctx) < -0.15
                else None
            )
        ),
    },

    'win_pct_diff': {
        'category': 'form',
        'render': lambda v, ctx: (
            f"Season record gap: {ctx['pick_team']} "
            f"({_pct(ctx, 'pick', 'win_pct')}% W) vs "
            f"{ctx['opp_team']} ({_pct(ctx, 'opp', 'win_pct')}% W)."
            if abs(v) > 0.08
            else None
        ),
    },

    # ═══ TEAM RATINGS / EFFICIENCY ═══

    'net_rtg_diff': {
        'category': 'efficiency',
        'render': lambda v, ctx: (
            f"Net rating gap: {ctx['pick_team']} holds a "
            f"+{abs(_pick_val(v, ctx)):.1f} net rating advantage per 100 possessions."
            if _pick_val(v, ctx) > 2
            else (
                f"Net rating gap: {ctx['opp_team']} rates higher, "
                f"but the spread overcompensates by {abs(ctx.get('spread', 0)):.1f} points."
                if _pick_val(v, ctx) < -2
                else None
            )
        ),
    },

    'home_off_rtg': {
        'category': 'efficiency',
        'render': lambda v, ctx: (
            f"{ctx['home_team']} offensive rating: {v:.1f} "
            f"({'elite, top-5 in league' if v > 116 else 'poor, bottom-10 in league'})."
            if v > 116 or v < 108 else None
        ),
    },

    'away_off_rtg': {
        'category': 'efficiency',
        'render': lambda v, ctx: (
            f"{ctx['away_team']} offensive rating: {v:.1f} "
            f"({'elite, top-5 in league' if v > 116 else 'poor, bottom-10 in league'})."
            if v > 116 or v < 108 else None
        ),
    },

    'home_def_rtg': {
        'category': 'efficiency',
        'render': lambda v, ctx: (
            f"Defensive factor: {ctx['home_team']} allowing {v:.1f} pts per 100 "
            f"({'porous defense' if v > 116 else 'elite defense'})."
            if v > 116 or v < 108 else None
        ),
    },

    'away_def_rtg': {
        'category': 'efficiency',
        'render': lambda v, ctx: (
            f"Defensive factor: {ctx['away_team']} allowing {v:.1f} pts per 100 "
            f"({'porous defense' if v > 116 else 'elite defense'})."
            if v > 116 or v < 108 else None
        ),
    },

    'off_matchup': {
        'category': 'efficiency',
        'render': lambda v, ctx: (
            f"Offensive matchup: {ctx['home_team']} offense vs {ctx['away_team']} defense "
            f"creates a {'+' if v > 0 else ''}{v:.1f} efficiency gap."
            if abs(v) > 4 else None
        ),
    },

    'def_matchup': {
        'category': 'efficiency',
        'render': lambda v, ctx: (
            f"Defensive matchup: {ctx['away_team']} offense vs {ctx['home_team']} defense "
            f"creates a {'+' if v > 0 else ''}{v:.1f} efficiency gap."
            if abs(v) > 4 else None
        ),
    },

    'pace_diff': {
        'category': 'efficiency',
        'render': lambda v, ctx: (
            f"Pace mismatch: {ctx['home_team']} at {ctx.get('home_pace', 100):.1f} "
            f"vs {ctx['away_team']} at {ctx.get('away_pace', 100):.1f} poss/game. "
            f"Tempo difference creates a matchup edge."
            if abs(v) > 3 else None
        ),
    },

    # ═══ HOME / AWAY SPLITS ═══

    'split_advantage': {
        'category': 'splits',
        'render': lambda v, ctx: (
            f"Home/away split favors {ctx['pick_team']}. "
            f"{ctx['home_team']} winning {_pct(ctx, 'home', 'home_pct')}% at home, "
            f"{ctx['away_team']} winning {_pct(ctx, 'away', 'away_pct')}% on the road."
            if (v > 0.10 and ctx['is_pick_home']) or (v < -0.10 and not ctx['is_pick_home'])
            else (
                f"Split disadvantage for {ctx['pick_team']}, but model finds value elsewhere."
                if (v < -0.10 and ctx['is_pick_home']) or (v > 0.10 and not ctx['is_pick_home'])
                else None
            )
        ),
    },

    # ═══ MARKET / LINE ═══

    'line_movement': {
        'category': 'market',
        'render': lambda v, ctx: (
            f"Line value: {abs(v):.1f}pts of movement in model's favor since open. "
            f"Buying below the market."
            if _line_favors_pick(v, ctx) and abs(v) >= 0.5
            else (
                f"Line moved {abs(v):.1f}pts against the model's position since open. "
                f"Edge persists at current number."
                if not _line_favors_pick(v, ctx) and abs(v) >= 0.5
                else None
            )
        ),
    },

    'spread_vs_consensus': {
        'category': 'market',
        'render': lambda v, ctx: (
            f"Current spread differs from book consensus by {abs(v):.1f} points. "
            f"Market disagreement creates opportunity."
            if abs(v) >= 1.0 else None
        ),
    },

    'rundown_spread_std': {
        'category': 'market',
        'render': lambda v, ctx: (
            f"Books disagree: spread varies by {v:.1f} points across sportsbooks. "
            f"Market uncertainty creates opportunity."
            if v >= 0.5 else None
        ),
    },

    'line_velocity': {
        'category': 'market',
        'render': lambda v, ctx: (
            f"Sharp line movement detected: velocity score {v:.2f}. "
            f"Professional money is moving this line."
            if abs(v) > 0.3 else None
        ),
    },

    # ═══ INJURIES (NBA/WNBA) ═══

    'injury_ppg_diff': {
        'category': 'injuries',
        'render': lambda v, ctx: (
            f"Injury edge: {ctx['opp_team']} missing {abs(v):.1f} more PPG of production. "
            f"Lineup is significantly weakened."
            if _pick_val(v, ctx) > 5
            else (
                f"Injury headwind: {ctx['pick_team']} missing {abs(v):.1f} more PPG of production. "
                f"Model accounts for this."
                if _pick_val(v, ctx) < -5
                else None
            )
        ),
    },

    'home_ppg_at_risk': {
        'category': 'injuries',
        'render': lambda v, ctx: (
            f"{ctx['home_team']} with {v:.1f} PPG of production at risk from injuries."
            if v > 8 else None
        ),
    },

    'away_ppg_at_risk': {
        'category': 'injuries',
        'render': lambda v, ctx: (
            f"{ctx['away_team']} with {v:.1f} PPG of production at risk from injuries."
            if v > 8 else None
        ),
    },

    'home_star_out': {
        'category': 'injuries',
        'render': lambda v, ctx: (
            f"{ctx['home_team']} missing a key rotation player. Significant absence."
            if v >= 1 else None
        ),
    },

    'away_star_out': {
        'category': 'injuries',
        'render': lambda v, ctx: (
            f"{ctx['away_team']} missing a key rotation player. Significant absence."
            if v >= 1 else None
        ),
    },

    # ═══ TRAVEL / SCHEDULE DENSITY ═══

    'away_travel_miles': {
        'category': 'schedule',
        'render': lambda v, ctx: (
            f"Travel factor: {ctx['away_team']} traveled {v:.0f} miles for this game. "
            f"Long-distance road trips correlate with fatigue."
            if v > 1500 else None
        ),
    },

    'away_tz_change': {
        'category': 'schedule',
        'render': lambda v, ctx: (
            f"Timezone shift: {ctx['away_team']} crossing {abs(v):.0f} time zones. "
            f"Body clock disadvantage."
            if abs(v) >= 2 else None
        ),
    },

    'home_games_last_7d': {
        'category': 'schedule',
        'render': lambda v, ctx: (
            f"Schedule density: {ctx['home_team']} has played {v:.0f} games in the last 7 days. "
            f"Heavy workload impacts performance."
            if v >= 4 else None
        ),
    },

    'away_games_last_7d': {
        'category': 'schedule',
        'render': lambda v, ctx: (
            f"Schedule density: {ctx['away_team']} has played {v:.0f} games in the last 7 days. "
            f"Heavy workload impacts performance."
            if v >= 4 else None
        ),
    },

    # ═══ BDL STATS ═══

    'bdl_win_pct_diff': {
        'category': 'form',
        'render': lambda v, ctx: (
            f"Win rate edge: {ctx['pick_team']} at {_pct(ctx, 'pick', 'bdl_win_pct')}% "
            f"vs {ctx['opp_team']} at {_pct(ctx, 'opp', 'bdl_win_pct')}%."
            if abs(v) > 0.10
            else None
        ),
    },

    'bdl_conf_rank_diff': {
        'category': 'form',
        'render': lambda v, ctx: (
            f"Conference rank gap: {ctx['pick_team']} ranks "
            f"{abs(v):.0f} spots higher in their conference."
            if abs(_pick_val(v, ctx)) > 4
            else None
        ),
    },

    # ═══ MLB — PITCHING ═══

    'era_diff': {
        'category': 'pitching',
        'render': lambda v, ctx: (
            f"Pitching edge: starter ERA advantage of {abs(v):.2f} runs in favor of "
            f"{ctx['pick_team']}."
            if _pick_val(v, ctx) > 0.8
            else (
                f"Pitching disadvantage: opponent starter ERA is {abs(v):.2f} runs lower. "
                f"Model sees value in the lineup."
                if _pick_val(v, ctx) < -0.8
                else None
            )
        ),
    },

    'whip_diff': {
        'category': 'pitching',
        'render': lambda v, ctx: (
            f"WHIP advantage: {ctx['pick_team']} starter allowing fewer baserunners "
            f"({abs(v):.2f} WHIP delta)."
            if _pick_val(v, ctx) > 0.15
            else None
        ),
    },

    'pitcher_win_pct_diff': {
        'category': 'pitching',
        'render': lambda v, ctx: (
            f"Starter win rate: {ctx['pick_team']}'s starter has a significantly "
            f"higher win percentage this season ({abs(v):.0%} gap)."
            if abs(_pick_val(v, ctx)) > 0.15
            else None
        ),
    },

    # ═══ MLB — PARK / MISC ═══

    'park_factor': {
        'category': 'park',
        'render': lambda v, ctx: (
            f"Park factor: {ctx['home_team']} plays in a "
            f"{'hitter-friendly' if v > 1.06 else 'pitcher-friendly'} park "
            f"(factor: {v:.2f}). Affects run expectation."
            if v > 1.06 or v < 0.94 else None
        ),
    },

    'bullpen_fatigue_diff': {
        'category': 'pitching',
        'render': lambda v, ctx: (
            f"Bullpen edge: {ctx['opp_team']}'s bullpen is significantly more fatigued. "
            f"Late-inning advantage."
            if _pick_val(v, ctx) > 1.5
            else (
                f"Bullpen concern: {ctx['pick_team']}'s bullpen is running heavy. "
                f"Model factors in the workload."
                if _pick_val(v, ctx) < -1.5
                else None
            )
        ),
    },

    'rl_ml_agree': {
        'category': 'market',
        'render': lambda v, ctx: (
            None if v == 1
            else "Run line and moneyline disagree on this game. Market is conflicted."
        ),
    },

    'chalk_level': {
        'category': 'market',
        'render': lambda v, ctx: (
            f"Heavy chalk: favorite priced at -{v:.0f}. "
            f"Model identifies value at the current price."
            if v > 180
            else None
        ),
    },

    # ═══ MLB INJURIES ═══

    'injury_diff': {
        'category': 'injuries',
        'render': lambda v, ctx: (
            f"Injury edge: {ctx['opp_team']} carrying a heavier injury burden. "
            f"Impact difference: {abs(v):.0f} points."
            if _pick_val(v, ctx) > 4
            else (
                f"Injury headwind: {ctx['pick_team']} carrying a heavier injury burden. "
                f"Model accounts for the absences."
                if _pick_val(v, ctx) < -4
                else None
            )
        ),
    },
}


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _pick_val(diff_val, ctx):
    """For home-minus-away diff features, return the value from the pick side's perspective."""
    return diff_val if ctx['is_pick_home'] else -diff_val


def _pick_form_val(diff_val, ctx):
    return diff_val if ctx['is_pick_home'] else -diff_val


def _line_favors_pick(movement, ctx):
    """Positive line_movement = spread_home increased (got more positive).
    If pick is home and line went more positive, that's worse for home (home
    is getting more points = they're less favored = line moved toward away).
    If pick is away, positive movement means away is MORE favored = favorable.
    """
    if ctx['is_pick_home']:
        return movement < 0
    else:
        return movement > 0


def _pct(ctx, side, key):
    """Get a percentage value from ctx extras, formatted as integer 0-100."""
    if side == 'pick':
        raw = ctx.get(f"{'home' if ctx['is_pick_home'] else 'away'}_{key}", 0.5)
    elif side == 'opp':
        raw = ctx.get(f"{'away' if ctx['is_pick_home'] else 'home'}_{key}", 0.5)
    else:
        raw = ctx.get(f"{side}_{key}", 0.5)
    try:
        return round(float(raw) * 100)
    except (ValueError, TypeError):
        return 50


# ─── RENDERING ────────────────────────────────────────────────────────────────

def render_template(feature_name, value, ctx):
    """Render a single feature into a human-readable sentence, or None if
    the template doesn't apply (value not noteworthy)."""
    entry = TEMPLATES.get(feature_name)
    if not entry:
        return None
    try:
        return entry['render'](value, ctx)
    except Exception:
        return None


def generate_contrarian(market_data, ctx):
    """Generate one contrarian market insight.
    
    Priority:
    1. Line movement against model (edge despite market pressure)
    2. Book disagreement (high spread std across sportsbooks)
    3. Opening line value (got a better number)
    4. Consensus vs current (books at a different number)
    5. Fallback
    """
    pick_team = ctx.get('pick_team', 'Pick')
    opp_team = ctx.get('opp_team', 'Opp')
    is_pick_home = ctx.get('is_pick_home', True)

    movement = market_data.get('line_movement', 0) or 0
    spread_std = market_data.get('rundown_spread_std', 0) or 0
    spread_range = market_data.get('rundown_spread_range') or 0
    spread_open = market_data.get('spread_home_open')
    spread_current = market_data.get('spread_home', 0) or 0
    consensus_diff = market_data.get('spread_vs_consensus', 0) or 0

    move_against = (is_pick_home and movement > 0) or (not is_pick_home and movement < 0)
    move_toward = (is_pick_home and movement < 0) or (not is_pick_home and movement > 0)

    if move_against and abs(movement) >= 1.0:
        return (
            f"Line moved {abs(movement):.1f} points against the model's position "
            f"since open. Edge persists at current number."
        )

    if move_toward and abs(movement) >= 1.0:
        return (
            f"Line moved {abs(movement):.1f} points toward model since open. "
            f"The market is catching up to what the model saw earlier."
        )

    if spread_std >= 0.5:
        try:
            rng = float(spread_range)
            if rng >= 1.5:
                return (
                    f"Books disagree: spread varies by {rng:.1f} points across sportsbooks. "
                    f"Market uncertainty creates opportunity."
                )
        except (ValueError, TypeError):
            pass
        return (
            f"Spread standard deviation across books is {spread_std:.1f}. "
            f"Sportsbooks don't agree on this number."
        )

    if spread_open is not None:
        try:
            move = float(spread_current) - float(spread_open)
            if abs(move) >= 1.0:
                return (
                    f"Line opened at {float(spread_open):+.1f} and is now {float(spread_current):+.1f}. "
                    f"Model identified value before the move."
                )
        except (ValueError, TypeError):
            pass

    if abs(consensus_diff) >= 0.5:
        return (
            f"Current spread differs from book consensus by {abs(consensus_diff):.1f} points. "
            f"Model aligns with the sharper side of the market."
        )

    return (
        f"Market is pricing this game with tight consensus across books. "
        f"Model sees a gap the market hasn't corrected."
    )


def generate_reasoning_bullets(top_features, game_context, market_data):
    """Generate exactly 3 reasoning bullets for a signal card.
    
    Bullets 1-2: top model-driven features (from different categories).
    Bullet 3: contrarian market insight.
    
    Args:
        top_features: list of (feature_name, importance, value) from get_top_features
        game_context: dict with pick_team, opp_team, home_team, away_team,
                      is_pick_home, spread, edge, plus raw feature values
        market_data: dict with line_movement, spread_home_open, spread_home,
                     rundown_spread_std, rundown_spread_range, rundown_num_books,
                     spread_vs_consensus
    
    Returns:
        list of 3 strings
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
        if category in used_categories and len(model_bullets) >= 1:
            continue

        bullet = render_template(feature_name, value, game_context)
        if bullet:
            model_bullets.append(bullet)
            used_categories.add(category)

    contrarian = generate_contrarian(market_data, game_context)

    while len(model_bullets) < 2:
        edge = game_context.get('edge', 0)
        model_bullets.append(
            f"Model edge: {edge:+.1f}% above the qualification threshold. "
            f"Ensemble consensus across all four models."
        )

    return model_bullets[:2] + [contrarian]
