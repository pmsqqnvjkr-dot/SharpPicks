PHASE_LABELS = {
    'calibration': 'Beta',
    'validation': 'Validation',
    'deployment': None,
}


def get_phase_label(phase):
    return PHASE_LABELS.get(phase)


SPORT_CONFIG = {
    'nba': {
        'name': 'NBA',
        'display_name': 'NBA Basketball',
        'active': True,
        'live': True,
        'model_phase': 'deployment',
        'model_run_hour': 10,

        'sigma': 11.7,
        'model_weight': 0.30,  # Post-Feb-2026 calibration: market MAE 10.06 < model MAE 12.03, favor market
        'edge_threshold_pct': 3.5,
        'max_edge_pct': 8.0,
        'margin_std_floor': 8.0,
        'margin_std_ceiling': 15.0,
        'standard_odds': -110,

        'spread_edge_curve': [
            (0, 7, 3.5),
            (7, 11, 5.0),
            (11, float('inf'), 8.0),
        ],

        # Max signals published per day. 1 = "selective by design" brand identity.
        # Increase only if CLV data shows consistent alpha on 2nd/3rd best edges.
        'max_daily_picks': 1,

        'odds_api_sport_key': 'basketball_nba',
        'espn_slug': 'basketball/nba',
        'espn_scoreboard': 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard',
        'espn_injuries': 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries',
        'espn_teams': 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams',

        'season_months': list(range(1, 13)),
        'games_per_season': 82,
    },

    'wnba': {
        'name': 'WNBA',
        'display_name': 'WNBA Basketball',
        'active': True,
        'live': True,
        'model_phase': 'calibration',
        # WNBA piggybacks on the 10 AM ET NBA run via /api/cron/run-model
        # rather than its own dedicated cron, so the UI countdown should
        # match. Previously 9 here, which made the home countdown card
        # render 'MODEL RUNS AT 9:00 AM ET' on WNBA tab even though the
        # cron actually fires at 10. Confirmed with Evan 2026-05-08.
        'model_run_hour': 10,
        'season_start_date': '2026-05-08',

        # Initial 2022-2024 train: cv_std_raw 11.3, MAE 13.3 (calib_ratio 0.85,
        # overconfident). Floor 16.0 inflates published sigma to ~1.21 ratio.
        # Beta calibration; revisit with 2026 data when corpus refreshes.
        'sigma': 16.0,
        'model_weight': 0.35,
        'edge_threshold_pct': 3.5,
        'max_edge_pct': 8.0,
        'margin_std_floor': 16.0,
        'margin_std_ceiling': 18.0,
        'standard_odds': -110,

        'spread_edge_curve': [
            (0, 7, 3.5),
            (7, 11, 5.0),
            (11, float('inf'), 8.0),
        ],

        'max_daily_picks': 1,

        'odds_api_sport_key': 'basketball_wnba',
        'espn_slug': 'basketball/wnba',
        'espn_scoreboard': 'https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard',
        'espn_injuries': 'https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/injuries',
        'espn_teams': 'https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams',

        'season_months': [5, 6, 7, 8, 9],
        'games_per_season': 40,
    },

    'mlb': {
        'name': 'MLB',
        'display_name': 'MLB Baseball',
        'active': True,
        'live': True,
        'model_phase': 'calibration',
        # MLB run shifted from 11 AM ET to 1 PM ET on 2026-05-12. The
        # 11 AM run fired before most starting pitchers were confirmed
        # and weather/lineup data was settled, which drove a 45%
        # revocation rate as the market repriced 3+ points between
        # publish and tip. 1 PM gives the model the confirmed pitcher
        # matchups + lineup cards + first-pitch weather, so pre-tip
        # validation rarely needs to flip the line.
        'model_run_hour': 13,

        # Walk-forward raw sigma: 4.4 runs. Previous ceiling of 2.5 inflated
        # z-scores by 1.76x, causing overconfidence in 55-65% buckets.
        'sigma': 4.0,
        'model_weight': 0.30,
        'edge_threshold_pct': 4.5,
        # max_edge_pct caps adjusted_edge so absurd outliers (e.g. 30%+ from
        # a divergent prior) can't ship. Was 6.0, which left only 1.5pt of
        # headroom above the 4.5% threshold and silently collapsed every
        # MLB pick to a uniform edge_pct=6.0 in storage. Bumped to 12.0
        # to give a real distribution; cover_prob already ranges 0.55-0.71
        # so true edges run roughly -1.5 to +14.5 around -130 implied prob.
        # NBA and WNBA both run 8.0 against a 3.5% threshold (4.5pt of
        # headroom). MLB threshold is 4.5%, so 12.0 gives 7.5pt of headroom,
        # comfortably wider than the basketball sports because run-line
        # outcomes have higher per-game variance.
        'max_edge_pct': 12.0,
        'margin_std_floor': 3.5,
        'margin_std_ceiling': 5.5,
        'standard_odds': -130,

        'spread_edge_curve': [
            (0, 1.5, 4.5),
            (1.5, 2.5, 5.5),
            (2.5, float('inf'), 7.0),
        ],

        'max_daily_picks': 1,

        'odds_api_sport_key': 'baseball_mlb',
        'espn_slug': 'baseball/mlb',
        'espn_scoreboard': 'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard',
        'espn_injuries': 'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/injuries',
        'espn_teams': 'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams',

        'season_months': [3, 4, 5, 6, 7, 8, 9, 10],
        'games_per_season': 162,
        'is_baseball': True,
        'primary_market': 'moneyline',
    },
}


def get_sport_config(sport='nba'):
    return SPORT_CONFIG.get(sport, SPORT_CONFIG['nba'])


def get_active_sports():
    return [k for k, v in SPORT_CONFIG.items() if v.get('active')]


def get_live_sports():
    return [k for k, v in SPORT_CONFIG.items() if v.get('live')]


def get_odds_api_url(sport='nba'):
    cfg = get_sport_config(sport)
    return f"https://api.the-odds-api.com/v4/sports/{cfg['odds_api_sport_key']}/odds/"


def get_espn_scoreboard_url(sport='nba', date_str=None):
    cfg = get_sport_config(sport)
    url = cfg['espn_scoreboard']
    if date_str:
        url += f"?dates={date_str.replace('-', '')}"
    return url


def get_edge_threshold_for_spread(spread_abs, sport='nba'):
    cfg = get_sport_config(sport)
    for low, high, threshold in cfg['spread_edge_curve']:
        if low <= spread_abs < high:
            return threshold
    return 8.0
