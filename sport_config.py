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

        'sigma': 11.7,
        'model_weight': 0.45,
        'edge_threshold_pct': 3.5,
        'max_edge_pct': 15.0,
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
        'live': False,
        'model_phase': 'calibration',

        'sigma': 10.5,
        'model_weight': 0.45,
        'edge_threshold_pct': 3.5,
        'max_edge_pct': 15.0,
        'margin_std_floor': 7.0,
        'margin_std_ceiling': 13.0,
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

        # Walk-forward raw sigma: 4.4 runs. Previous ceiling of 2.5 inflated
        # z-scores by 1.76x, causing overconfidence in 55-65% buckets.
        'sigma': 4.0,
        'model_weight': 0.45,
        'edge_threshold_pct': 4.5,
        'max_edge_pct': 15.0,
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
