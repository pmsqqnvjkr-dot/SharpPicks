"""
SharpPicks Content Engine
Public-facing SEO pages rendered from existing model pipeline data.
"""

import json
import random
import re
import sqlite3
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, render_template, abort, request, make_response
from models import db, Pick, Pass, ModelRun, ContentPageView
from public_api import build_market_report_dict
from sport_config import get_sport_config, get_live_sports, SPORT_CONFIG
from db_path import get_sqlite_path

log = logging.getLogger(__name__)
ET = ZoneInfo('America/New_York')

content_bp = Blueprint('content', __name__)

BOT_TOKENS = ('bot', 'crawler', 'spider', 'googlebot', 'bingbot', 'slurp',
               'duckduckbot', 'facebookexternalhit', 'twitterbot', 'linkedinbot')


@content_bp.before_request
def log_content_page_view():
    try:
        import hashlib
        ua = request.headers.get('User-Agent', '')
        is_bot = any(b in ua.lower() for b in BOT_TOKENS)
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else None
        view = ContentPageView(
            path=request.path,
            ip_hash=ip_hash,
            user_agent=ua[:500],
            is_bot=is_bot
        )
        db.session.add(view)
        db.session.commit()
    except Exception:
        db.session.rollback()


VALID_SPORTS = {'nba', 'mlb', 'nfl', 'wnba'}

CANONICAL_DOMAIN = 'https://sharppicks.ai'

# ---------------------------------------------------------------------------
# Team name mapping
# ---------------------------------------------------------------------------

NBA_TEAMS = {
    'ATL': {'name': 'Atlanta Hawks', 'slug': 'hawks', 'conf': 'Eastern', 'div': 'Southeast'},
    'BOS': {'name': 'Boston Celtics', 'slug': 'celtics', 'conf': 'Eastern', 'div': 'Atlantic'},
    'BKN': {'name': 'Brooklyn Nets', 'slug': 'nets', 'conf': 'Eastern', 'div': 'Atlantic'},
    'CHA': {'name': 'Charlotte Hornets', 'slug': 'hornets', 'conf': 'Eastern', 'div': 'Southeast'},
    'CHI': {'name': 'Chicago Bulls', 'slug': 'bulls', 'conf': 'Eastern', 'div': 'Central'},
    'CLE': {'name': 'Cleveland Cavaliers', 'slug': 'cavaliers', 'conf': 'Eastern', 'div': 'Central'},
    'DAL': {'name': 'Dallas Mavericks', 'slug': 'mavericks', 'conf': 'Western', 'div': 'Southwest'},
    'DEN': {'name': 'Denver Nuggets', 'slug': 'nuggets', 'conf': 'Western', 'div': 'Northwest'},
    'DET': {'name': 'Detroit Pistons', 'slug': 'pistons', 'conf': 'Eastern', 'div': 'Central'},
    'GSW': {'name': 'Golden State Warriors', 'slug': 'warriors', 'conf': 'Western', 'div': 'Pacific'},
    'HOU': {'name': 'Houston Rockets', 'slug': 'rockets', 'conf': 'Western', 'div': 'Southwest'},
    'IND': {'name': 'Indiana Pacers', 'slug': 'pacers', 'conf': 'Eastern', 'div': 'Central'},
    'LAC': {'name': 'Los Angeles Clippers', 'slug': 'clippers', 'conf': 'Western', 'div': 'Pacific'},
    'LAL': {'name': 'Los Angeles Lakers', 'slug': 'lakers', 'conf': 'Western', 'div': 'Pacific'},
    'MEM': {'name': 'Memphis Grizzlies', 'slug': 'grizzlies', 'conf': 'Western', 'div': 'Southwest'},
    'MIA': {'name': 'Miami Heat', 'slug': 'heat', 'conf': 'Eastern', 'div': 'Southeast'},
    'MIL': {'name': 'Milwaukee Bucks', 'slug': 'bucks', 'conf': 'Eastern', 'div': 'Central'},
    'MIN': {'name': 'Minnesota Timberwolves', 'slug': 'timberwolves', 'conf': 'Western', 'div': 'Northwest'},
    'NOP': {'name': 'New Orleans Pelicans', 'slug': 'pelicans', 'conf': 'Western', 'div': 'Southwest'},
    'NYK': {'name': 'New York Knicks', 'slug': 'knicks', 'conf': 'Eastern', 'div': 'Atlantic'},
    'OKC': {'name': 'Oklahoma City Thunder', 'slug': 'thunder', 'conf': 'Western', 'div': 'Northwest'},
    'ORL': {'name': 'Orlando Magic', 'slug': 'magic', 'conf': 'Eastern', 'div': 'Southeast'},
    'PHI': {'name': 'Philadelphia 76ers', 'slug': '76ers', 'conf': 'Eastern', 'div': 'Atlantic'},
    'PHX': {'name': 'Phoenix Suns', 'slug': 'suns', 'conf': 'Western', 'div': 'Pacific'},
    'POR': {'name': 'Portland Trail Blazers', 'slug': 'trail-blazers', 'conf': 'Western', 'div': 'Northwest'},
    'SAC': {'name': 'Sacramento Kings', 'slug': 'kings', 'conf': 'Western', 'div': 'Pacific'},
    'SAS': {'name': 'San Antonio Spurs', 'slug': 'spurs', 'conf': 'Western', 'div': 'Southwest'},
    'TOR': {'name': 'Toronto Raptors', 'slug': 'raptors', 'conf': 'Eastern', 'div': 'Atlantic'},
    'UTA': {'name': 'Utah Jazz', 'slug': 'jazz', 'conf': 'Western', 'div': 'Northwest'},
    'WAS': {'name': 'Washington Wizards', 'slug': 'wizards', 'conf': 'Eastern', 'div': 'Southeast'},
}

MLB_TEAMS = {
    'ARI': {'name': 'Arizona Diamondbacks', 'slug': 'diamondbacks', 'conf': 'National', 'div': 'NL West'},
    'ATL': {'name': 'Atlanta Braves', 'slug': 'braves', 'conf': 'National', 'div': 'NL East'},
    'BAL': {'name': 'Baltimore Orioles', 'slug': 'orioles', 'conf': 'American', 'div': 'AL East'},
    'BOS': {'name': 'Boston Red Sox', 'slug': 'red-sox', 'conf': 'American', 'div': 'AL East'},
    'CHC': {'name': 'Chicago Cubs', 'slug': 'cubs', 'conf': 'National', 'div': 'NL Central'},
    'CHW': {'name': 'Chicago White Sox', 'slug': 'white-sox', 'conf': 'American', 'div': 'AL Central'},
    'CIN': {'name': 'Cincinnati Reds', 'slug': 'reds', 'conf': 'National', 'div': 'NL Central'},
    'CLE': {'name': 'Cleveland Guardians', 'slug': 'guardians', 'conf': 'American', 'div': 'AL Central'},
    'COL': {'name': 'Colorado Rockies', 'slug': 'rockies', 'conf': 'National', 'div': 'NL West'},
    'DET': {'name': 'Detroit Tigers', 'slug': 'tigers', 'conf': 'American', 'div': 'AL Central'},
    'HOU': {'name': 'Houston Astros', 'slug': 'astros', 'conf': 'American', 'div': 'AL West'},
    'KC': {'name': 'Kansas City Royals', 'slug': 'royals', 'conf': 'American', 'div': 'AL Central'},
    'LAA': {'name': 'Los Angeles Angels', 'slug': 'angels', 'conf': 'American', 'div': 'AL West'},
    'LAD': {'name': 'Los Angeles Dodgers', 'slug': 'dodgers', 'conf': 'National', 'div': 'NL West'},
    'MIA': {'name': 'Miami Marlins', 'slug': 'marlins', 'conf': 'National', 'div': 'NL East'},
    'MIL': {'name': 'Milwaukee Brewers', 'slug': 'brewers', 'conf': 'National', 'div': 'NL Central'},
    'MIN': {'name': 'Minnesota Twins', 'slug': 'twins', 'conf': 'American', 'div': 'AL Central'},
    'NYM': {'name': 'New York Mets', 'slug': 'mets', 'conf': 'National', 'div': 'NL East'},
    'NYY': {'name': 'New York Yankees', 'slug': 'yankees', 'conf': 'American', 'div': 'AL East'},
    'OAK': {'name': 'Oakland Athletics', 'slug': 'athletics', 'conf': 'American', 'div': 'AL West'},
    'PHI': {'name': 'Philadelphia Phillies', 'slug': 'phillies', 'conf': 'National', 'div': 'NL East'},
    'PIT': {'name': 'Pittsburgh Pirates', 'slug': 'pirates', 'conf': 'National', 'div': 'NL Central'},
    'SD': {'name': 'San Diego Padres', 'slug': 'padres', 'conf': 'National', 'div': 'NL West'},
    'SF': {'name': 'San Francisco Giants', 'slug': 'giants', 'conf': 'National', 'div': 'NL West'},
    'SEA': {'name': 'Seattle Mariners', 'slug': 'mariners', 'conf': 'American', 'div': 'AL West'},
    'STL': {'name': 'St. Louis Cardinals', 'slug': 'cardinals', 'conf': 'National', 'div': 'NL Central'},
    'TB': {'name': 'Tampa Bay Rays', 'slug': 'rays', 'conf': 'American', 'div': 'AL East'},
    'TEX': {'name': 'Texas Rangers', 'slug': 'rangers', 'conf': 'American', 'div': 'AL West'},
    'TOR': {'name': 'Toronto Blue Jays', 'slug': 'blue-jays', 'conf': 'American', 'div': 'AL East'},
    'WAS': {'name': 'Washington Nationals', 'slug': 'nationals', 'conf': 'National', 'div': 'NL East'},
}

SPORT_TEAM_MAP = {'nba': NBA_TEAMS, 'mlb': MLB_TEAMS}

# Reverse lookup: map full team name (lowercased) -> abbreviation for each sport
_NAME_TO_ABBR = {}
for _sport_key, _team_dict in SPORT_TEAM_MAP.items():
    for _abbr, _info in _team_dict.items():
        _NAME_TO_ABBR[(_sport_key, _info['name'].lower())] = _abbr
        # Also map the nickname alone (e.g. "lakers" -> LAL)
        _nickname = _info['name'].split()[-1].lower()
        _NAME_TO_ABBR[(_sport_key, _nickname)] = _abbr


def _resolve_team_abbr(team_ref, sport='nba'):
    """Resolve any team reference (abbr, full name, nickname) to canonical abbreviation."""
    if not team_ref:
        return team_ref
    teams = SPORT_TEAM_MAP.get(sport, NBA_TEAMS)
    if team_ref in teams:
        return team_ref
    key_lower = team_ref.strip().lower()
    found = _NAME_TO_ABBR.get((sport, key_lower))
    if found:
        return found
    # Try slugified match against team slugs
    slugified = _slugify(team_ref)
    for abbr, info in teams.items():
        if info['slug'] == slugified:
            return abbr
    return team_ref


def _team_lookup(abbr, sport='nba'):
    teams = SPORT_TEAM_MAP.get(sport, NBA_TEAMS)
    resolved = _resolve_team_abbr(abbr, sport)
    return teams.get(resolved, {'name': abbr, 'slug': _slugify(abbr), 'conf': '', 'div': ''})


def _team_full_name(abbr, sport='nba'):
    return _team_lookup(abbr, sport)['name']


def _team_slug(abbr, sport='nba'):
    return _team_lookup(abbr, sport)['slug']


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

def _slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    return text.strip('-')


def make_game_slug(away, home, date_str, sport='nba'):
    away_slug = _slugify(_team_slug(away, sport))
    home_slug = _slugify(_team_slug(home, sport))
    return f"{away_slug}-vs-{home_slug}-{date_str}"


def _format_date_display(date_str):
    """'2026-04-05' -> 'April 5, 2026'"""
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%B %-d, %Y')
    except Exception:
        return date_str


def _format_date_short(date_str):
    """'2026-04-05' -> 'Apr 5'"""
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%b %-d')
    except Exception:
        return date_str


# ---------------------------------------------------------------------------
# Public edge bands
# ---------------------------------------------------------------------------

def get_public_edge_band(edge):
    edge = abs(edge) if edge else 0
    if edge < 2.0:
        return "Below 2%"
    elif edge < 3.0:
        return "2% -- 2.9%"
    elif edge < 4.5:
        return "3% -- 4.4%"
    else:
        return "4.5%+"


# ---------------------------------------------------------------------------
# Index scoring
# ---------------------------------------------------------------------------

def get_index_score(game):
    score = 0
    if game.get('official_signal') or game.get('signal'):
        score += 5
    edge = abs(game.get('model_edge', 0) or game.get('edge', 0) or 0)
    if edge >= 5.0:
        score += 4
    elif edge >= 3.0:
        score += 2
    lm = abs(game.get('line_movement_points', 0) or 0)
    if lm >= 1.5:
        score += 3
    elif lm >= 1.0:
        score += 2
    if game.get('postgame_clv') is not None or game.get('clv_display'):
        score += 2
    if game.get('featured_team'):
        score += 1
    if game.get('has_result_story'):
        score += 2
    return score


def should_index_game_page(game):
    return get_index_score(game) >= 5


# ---------------------------------------------------------------------------
# Pass reason taxonomy
# ---------------------------------------------------------------------------

PASS_REASON_DISPLAY = {
    "spread_too_large": "Spread exceeds model comfort range",
    "mid_spread_insufficient_edge": "Edge insufficient for this spread size",
    "star_questionable": "Player availability uncertainty",
    "star_out": "Key player confirmed out, reducing projection reliability",
    "below_threshold": "Below qualification threshold",
    "confidence_split": "Model ensemble did not reach sufficient agreement",
    "margin_of_error": "Edge within the model's margin of error",
    "no_edge": "No measurable disagreement between model and market",
    "insufficient_data": "Not enough recent data to generate a reliable projection",
    "low_confidence": "Model confidence below required level",
    "volatility": "Line volatility exceeds model parameters",
    "back_to_back": "Schedule context reduced projection confidence",
    "edge_too_small": "Edge below qualification threshold",
    "validation_fail": "Did not pass secondary validation checks",
    "lineup_uncertain": "Starting lineup not confirmed, projection unreliable",
    "early_season": "Insufficient season data for stable projection",
    "high_variance": "Outcome variance too high for reliable edge estimate",
    "model_disagreement": "Individual models disagree on direction",
    "stale_line": "Line data may be stale or unavailable",
    "missing_spread": "Spread data unavailable for this game",
    "missing_prediction": "Model could not generate a prediction",
    "fallback_sigma": "Prediction uncertainty too high",
    "extreme_line_move": "Line moved significantly since model ran",
}


def format_fail_reason(raw_reason):
    """Convert an internal fail_reason token to user-facing copy."""
    if not raw_reason:
        return "Below qualification threshold"
    cleaned = raw_reason.strip()
    cleaned_lower = cleaned.lower()
    # Direct match
    if cleaned_lower in PASS_REASON_DISPLAY:
        return PASS_REASON_DISPLAY[cleaned_lower]
    # Strip parenthetical data (e.g. "spread_too_large (14.5, need 6% edge)")
    base_token = re.sub(r'\s*\(.*\)\s*$', '', cleaned_lower).strip()
    if base_token in PASS_REASON_DISPLAY:
        return PASS_REASON_DISPLAY[base_token]
    # Check for partial/prefix matches
    for key, display in PASS_REASON_DISPLAY.items():
        if key in cleaned_lower:
            return display
    # If it already looks like readable text (contains spaces, no underscores), pass through
    if ' ' in cleaned and '_' not in cleaned:
        return cleaned
    # Catch-all: convert any remaining underscore tokens to title case
    if '_' in cleaned:
        return cleaned.replace('_', ' ').capitalize()
    return "Below qualification threshold"


def format_fail_reasons(reasons_list):
    """Convert a list of internal fail_reason tokens to user-facing copy."""
    if not reasons_list:
        return []
    seen = set()
    result = []
    for r in reasons_list:
        display = format_fail_reason(r)
        if display not in seen:
            seen.add(display)
            result.append(display)
    return result


def get_pass_reason(edge):
    edge = abs(edge) if edge else 0
    if edge < 1.0:
        return "No measurable edge"
    elif edge < 2.0:
        return "Below internal threshold"
    elif edge < 3.5:
        return "Near threshold but not qualified"
    else:
        return "Filtered by confidence or validation checks"


# ---------------------------------------------------------------------------
# Rotating narrative blocks
# ---------------------------------------------------------------------------

MARKET_OVERVIEW_BLOCKS = [
    "The model reviewed {games_analyzed} {sport_upper} games on {date_formatted} and found {edges_found} spots with measurable disagreement versus the market. Only {signals_published} cleared the full qualification filter, which is consistent with SharpPicks' selective approach.",
    "Most slates look efficient on the surface. On {date_formatted}, SharpPicks analyzed {games_analyzed} {sport_upper} games and found only {signals_published} signal{s_plural} worth sending, with {games_passed} games falling short of the threshold.",
    "This slate produced a market efficiency score of {mei_score}, signaling a {regime_lower} environment. That matters because higher efficiency usually means fewer exploitable gaps between the model and the market.",
    "Signal volume stayed restrained on this slate. SharpPicks found {edges_found} edges, but only the strongest setups survived the confidence and qualification filters before publication.",
    "Selectivity is part of the product. Rather than forcing action on every game, SharpPicks filters for true mispricing and leaves the rest alone. On {date_formatted}, that process resulted in {signals_published} published signal{s_plural} and {games_passed} passes.",
]

PASS_EXPLANATION_BLOCKS = [
    "A pass does not mean nothing happened. It means the market price stayed close enough to the model projection that no durable edge was detected.",
    "Most games never become signals. That is usually a sign of market efficiency, not a missed opportunity.",
    "SharpPicks treats discipline as part of the edge. When projected value stays below the qualification line, the game is logged as a pass rather than forced into action.",
    "Efficient markets create fewer mistakes to exploit. On slates like this one, the strongest move is often restraint.",
    "Passing is a decision, not an absence of one. These games remained below the level required for official publication.",
]

LINE_MOVEMENT_BLOCKS = [
    "Line movement matters because it shows whether the market is converging toward the model or drifting away from it.",
    "When prices move toward the model, part of the edge can disappear before game time. When they move away, mispricing can widen.",
    "Today's movement profile included {line_movement_toward_model} games moving toward the model, {line_movement_away} moving away, and {line_movement_none} with little meaningful change.",
    "Market movement does not guarantee value, but it helps explain where price discovery is active and where the board remains stable.",
]

WHY_THIS_MATTERS_BLOCKS = [
    "For most bettors, the hardest part is not finding action. It is recognizing when the market has already priced the game efficiently.",
    "SharpPicks is built around the idea that selective signals compound better than constant volume. This report shows how that discipline plays out on a real slate.",
    "A slate with fewer qualified spots is not a weak day. It is a clearer reminder that edge is scarce and should be treated that way.",
    "Public betting content usually focuses only on what was played. SharpPicks also shows what was rejected, which gives a more honest view of the market.",
]

GAME_MODEL_VIEW_BLOCKS = [
    "SharpPicks identified a measurable gap between the market line and the internal projection for this matchup. The difference was large enough to put the game on the radar, though publication status depended on the full qualification process.",
    "This matchup showed a meaningful disagreement between price and projection. Whether that disagreement became an official signal depended on edge strength, confidence filters, and validation checks.",
    "Not every pricing gap becomes a signal. This page tracks how the model viewed the matchup, how the market moved, and how the setup ultimately graded out.",
]

PASS_OVERVIEW_BLOCKS = [
    "SharpPicks passed on {games_passed} of {games_analyzed} {sport_upper} games on {date_formatted}. None of these matchups produced enough projected value to justify an official signal.",
    "Most of the slate stayed inside efficient pricing ranges. As a result, {games_passed} games were logged as passes rather than forced into action.",
    "Passing is part of the system. On {date_formatted}, {games_passed} of {games_analyzed} {sport_upper} games remained below the qualification threshold and were excluded from the official signal layer.",
]

CTA_BLOCKS = {
    'market_report': {"headline": "Only the signal layer is hidden.", "body": "Full model output. Live alerts. Bet tracking. One pick beats five."},
    'game': {"headline": "This qualified. See all signals live.", "body": "SharpPicks members get real-time alerts and full model transparency."},
    'pass': {"headline": "Most games never qualify.", "body": "Get notified when one actually does. Selectivity is the system."},
    'edges': {"headline": "See what qualified in real time.", "body": "SharpPicks subscribers get the live signal layer, alerts, and tracking tools."},
    'default': {"headline": "SharpPicks is built for selectivity, not volume.", "body": "Get signal alerts in real time."},
}

MARKET_REPORT_FAQ = [
    {
        "question": "What is a market efficiency score?",
        "answer": "The Market Efficiency Index (MEI) measures disagreement between the SharpPicks model and market prices across a full slate. Higher scores indicate more potential opportunity."
    },
    {
        "question": "Why were most games passed?",
        "answer": "A game is passed when the model's projected edge falls below the 3.5% qualification threshold. The market price is close enough to the model's estimate that betting offers no meaningful expected value."
    },
    {
        "question": "What makes a game qualify as a signal?",
        "answer": "A signal requires the model's edge to exceed 3.5% AND pass confidence and validation filters. The four ensemble models must show sufficient agreement on direction."
    },
]

PILLAR_LINKS = [
    {"url": "/blog/why-we-pass", "title": "Why We Pass More Than We Play"},
    {"url": "/blog/beginners-guide", "title": "Beginner's Guide to Sports Betting"},
    {"url": "/blog/between-lines-phone", "title": "Between the Lines: Betting from Your Phone"},
    {"url": "/blog/cost-of-bad-bet", "title": "The Real Cost of a Bad Bet"},
    {"url": "/tools/clv-calculator", "title": "CLV Calculator"},
    {"url": "/tools/edge-calculator", "title": "Edge Calculator"},
]


def choose_blocks(blocks, count=2, seed=None):
    rng = random.Random(seed)
    if len(blocks) <= count:
        return blocks
    return rng.sample(blocks, count)


def get_rotating_pillar(page_key):
    idx = abs(hash(page_key)) % len(PILLAR_LINKS)
    return PILLAR_LINKS[idx]


def get_rotating_cta(page_key, page_type='default'):
    return CTA_BLOCKS.get(page_type, CTA_BLOCKS['default'])


# ---------------------------------------------------------------------------
# SEO metadata helpers
# ---------------------------------------------------------------------------

def build_market_report_meta(data):
    if data.get('signals_published', 0) > 0:
        return (
            f"SharpPicks analyzed {data['games_analyzed']} {data['sport_upper']} games on "
            f"{data['date_formatted']}. {data['signals_published']} signal published, "
            f"{data['games_passed']} passed, market regime {data.get('regime', 'Normal')}."
        )
    return (
        f"SharpPicks analyzed {data['games_analyzed']} {data['sport_upper']} games on "
        f"{data['date_formatted']}. No official signal qualified. "
        f"See the full pass report and market breakdown."
    )


def build_pass_report_meta(data):
    return (
        f"SharpPicks passed on {data['games_passed']} of {data['games_analyzed']} "
        f"{data['sport_upper']} games on {data['date_formatted']}. See pass reasons, "
        f"edge bands, and why selectivity matters."
    )


def build_edges_meta(data):
    return (
        f"Today's {data['sport_upper']} edge rankings from the SharpPicks model. "
        f"{data['games_analyzed']} games analyzed, "
        f"{data.get('edges_found', 0)} above the 3.5% threshold."
    )


def build_game_page_meta(game, data):
    status = "Signal published" if game.get('signal') else "Passed"
    edge_band = get_public_edge_band(game.get('edge', 0))
    matchup = f"{game.get('away_team', '?')} vs {game.get('home_team', '?')}"
    return (
        f"SharpPicks model analysis for {matchup} on "
        f"{data['date_formatted']}. Edge band: {edge_band}. "
        f"Status: {status}."
    )


def build_team_page_meta(team_name, sport_upper):
    return (
        f"SharpPicks model insights for the {team_name}. "
        f"See signals, edges, CLV data, and betting analysis for the current {sport_upper} season."
    )


def build_jsonld_article(title, description, date_str, url):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "datePublished": date_str,
        "dateModified": date_str,
        "author": {"@type": "Organization", "name": "SharpPicks"},
        "publisher": {
            "@type": "Organization",
            "name": "SharpPicks",
            "url": "https://sharppicks.ai"
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
    })


def build_jsonld_faq(faq_items):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": q["answer"]
                }
            }
            for q in faq_items
        ]
    })


def build_jsonld_sports_event(game, data):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": f"{game.get('away_team', '?')} vs {game.get('home_team', '?')}",
        "startDate": data.get('date', ''),
        "location": {"@type": "Place", "name": f"{game.get('home_team', '')} Arena"},
        "homeTeam": {"@type": "SportsTeam", "name": _team_full_name(game.get('home_team', ''), data.get('sport', 'nba'))},
        "awayTeam": {"@type": "SportsTeam", "name": _team_full_name(game.get('away_team', ''), data.get('sport', 'nba'))},
        "description": build_game_page_meta(game, data),
    })


def build_jsonld_collection(title, description, url):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title,
        "description": description,
        "url": url,
        "publisher": {"@type": "Organization", "name": "SharpPicks"},
    })


def build_jsonld_software(name, description, url):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": name,
        "description": description,
        "url": url,
        "applicationCategory": "FinanceApplication",
        "operatingSystem": "Web",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
    })


# ---------------------------------------------------------------------------
# Data layer
# ---------------------------------------------------------------------------

def get_daily_report_data(date_str, sport='nba'):
    """
    Build the content-engine data dict for a given date and sport.
    Wraps the existing build_market_report_dict() and enriches with
    slug generation, pass reasons, formatted dates, and edge bands.
    """
    report = build_market_report_dict(date_str, sport)

    if not report.get('available'):
        return None

    sport_upper = (sport or 'nba').upper()
    date_formatted = _format_date_display(date_str)
    date_short = _format_date_short(date_str)

    board = report.get('board', [])
    signal_game = None
    games = []
    for g in board:
        edge_val = abs(g.get('edge', 0) or 0)
        is_signal = bool(g.get('signal'))
        away = _resolve_team_abbr(g.get('away_team', '?'), sport)
        home = _resolve_team_abbr(g.get('home_team', '?'), sport)

        # Deduplicate reasoning/factors (normalize whitespace for comparison)
        raw_reasoning = g.get('reasoning', [])
        seen_reasons = set()
        unique_reasoning = []
        for r in raw_reasoning:
            normalized = ' '.join(r.strip().split()).lower()
            if normalized and normalized not in seen_reasons:
                seen_reasons.add(normalized)
                unique_reasoning.append(r.strip())

        # Convert raw fail_reasons to user-facing copy
        raw_fail = g.get('fail_reasons', [])
        display_fail = format_fail_reasons(raw_fail)

        # Determine public status: SIGNAL / FILTERED / PASS
        if is_signal:
            public_status = 'Signal'
        elif edge_val >= 3.5 and not is_signal:
            public_status = 'Filtered'
        else:
            public_status = 'Pass'

        game_entry = {
            'away_team': away,
            'home_team': home,
            'away_name': _team_full_name(away, sport),
            'home_name': _team_full_name(home, sport),
            'matchup': f"{away} @ {home}",
            'matchup_display': f"{_team_full_name(away, sport)} vs {_team_full_name(home, sport)}",
            'market_line': g.get('market_line'),
            'model_line': g.get('model_line'),
            'edge': edge_val,
            'edge_band': get_public_edge_band(edge_val),
            'signal': is_signal,
            'status': public_status,
            'pick_side': g.get('pick_side'),
            'pick_label': g.get('pick_label', ''),
            'pick': g.get('pick', ''),
            'reasoning': unique_reasoning,
            'fail_reasons': display_fail,
            'predicted_margin': g.get('predicted_margin'),
            'pass_reason': '' if is_signal else get_pass_reason(edge_val),
            'slug': make_game_slug(away, home, date_str, sport),
        }
        games.append(game_entry)
        if is_signal and signal_game is None:
            signal_game = game_entry

    games_analyzed = report.get('games_analyzed', len(games))
    edges_found = sum(1 for g in games if g['edge'] >= 3.5)
    signals_published = sum(1 for g in games if g['signal'])
    games_passed = sum(1 for g in games if not g['signal'])

    lm = report.get('line_movement', {})
    lm_toward = lm.get('toward_model', 0)
    lm_away = lm.get('away_from_model', 0)
    lm_none = lm.get('no_movement', 0)
    lm_games = lm.get('games', [])

    mei = report.get('mei', {})

    top_edge_game = max(games, key=lambda g: g['edge']) if games else None

    data = {
        'date': date_str,
        'date_formatted': date_formatted,
        'date_short': date_short,
        'sport': sport,
        'sport_upper': sport_upper,
        'games': games,
        'signal': signal_game,
        'games_analyzed': games_analyzed,
        'edges_found': edges_found,
        'signals_published': signals_published,
        's_plural': '' if signals_published == 1 else 's',
        'games_passed': games_passed,
        'mei_score': report.get('market_efficiency_index', 0),
        'regime': report.get('regime', 'Normal'),
        'regime_lower': (report.get('regime') or 'normal').lower(),
        'regime_micro': report.get('regime_micro', ''),
        'signal_density': report.get('signal_density', 0),
        'top_edge': get_public_edge_band(top_edge_game['edge']) if top_edge_game else 'N/A',
        'top_edge_game': top_edge_game['matchup'] if top_edge_game else 'N/A',
        'line_movement_toward_model': lm_toward,
        'line_movement_away': lm_away,
        'line_movement_none': lm_none,
        'line_movement_games': lm_games,
        'mei_sparkline': mei.get('sparkline', []),
        'mei_7d_avg': mei.get('seven_day_avg'),
        'mei_season_avg': mei.get('season_avg'),
        'market_stability': report.get('market_stability'),
        'insight': report.get('insight', ''),
        'briefing': report.get('briefing', []),
        'last_updated': report.get('last_updated'),
    }
    return data


def _format_blocks(blocks, data):
    """Format narrative block templates with data dict, safely."""
    result = []
    for b in blocks:
        try:
            result.append(b.format(**data))
        except (KeyError, IndexError):
            result.append(b)
    return result


# ---------------------------------------------------------------------------
# Post-game helpers
# ---------------------------------------------------------------------------

def build_postgame_summary(game):
    if not game.get('final_score') and not game.get('result'):
        return None
    result = game.get('result_label', game.get('result', 'Final recorded'))
    clv = game.get('clv_display', game.get('clv', 'N/A'))
    return (
        f"After the game closed, this matchup was graded as {result}. "
        f"Closing line value came in at {clv}, which helps show whether "
        f"the number moved toward or away from the model before tip-off."
    )


# ---------------------------------------------------------------------------
# Team page data helpers
# ---------------------------------------------------------------------------

def get_team_season_data(abbr, sport='nba'):
    """Aggregate signal history for a team across the current season."""
    team_info = _team_lookup(abbr, sport)
    full_name = team_info['name']

    # DB stores full team names, so query by full name AND abbreviation
    picks = Pick.query.filter(
        Pick.sport == sport,
        Pick.result != 'revoked',
    ).filter(
        db.or_(
            Pick.home_team == abbr, Pick.away_team == abbr,
            Pick.home_team == full_name, Pick.away_team == full_name,
        )
    ).order_by(Pick.game_date.desc()).all()

    signal_picks = [p for p in picks if p.side and (
        abbr.lower() in (p.side or '').lower() or
        full_name.lower() in (p.side or '').lower()
    )]

    wins = sum(1 for p in signal_picks if p.result == 'win')
    losses = sum(1 for p in signal_picks if p.result == 'loss')
    pending = sum(1 for p in signal_picks if p.result == 'pending' or not p.result)

    avg_edge = 0
    clv_positive = 0
    clv_total = 0
    edges = []
    for p in signal_picks:
        if p.edge_pct:
            edges.append(abs(p.edge_pct))
        if p.clv is not None:
            clv_total += 1
            if p.clv > 0:
                clv_positive += 1

    if edges:
        avg_edge = sum(edges) / len(edges)

    clv_rate = round(clv_positive / clv_total * 100) if clv_total > 0 else 0

    recent_games = []
    all_team_picks = Pick.query.filter(
        Pick.sport == sport,
        Pick.result != 'revoked',
        db.or_(
            Pick.home_team == abbr, Pick.away_team == abbr,
            Pick.home_team == full_name, Pick.away_team == full_name,
        )
    ).order_by(Pick.game_date.desc()).limit(10).all()

    for p in all_team_picks:
        is_signal_for_team = abbr.lower() in (p.side or '').lower() or full_name.lower() in (p.side or '').lower()
        opp = p.away_team if p.home_team in (abbr, full_name) else p.home_team
        at_home = p.home_team in (abbr, full_name)
        recent_games.append({
            'date': p.game_date,
            'date_short': _format_date_short(p.game_date) if p.game_date else '',
            'opponent': opp,
            'opponent_name': _team_full_name(opp, sport),
            'at_home': at_home,
            'spread': p.line,
            'edge': abs(p.edge_pct) if p.edge_pct else 0,
            'edge_band': get_public_edge_band(p.edge_pct) if p.edge_pct else 'N/A',
            'result': p.result or 'pending',
            'is_signal': is_signal_for_team,
            'slug': make_game_slug(p.away_team or '?', p.home_team or '?', p.game_date or '', sport),
        })

    return {
        'abbr': abbr,
        'name': team_info['name'],
        'slug': team_info['slug'],
        'conf': team_info.get('conf', ''),
        'div': team_info.get('div', ''),
        'sport': sport,
        'sport_upper': sport.upper(),
        'signals': len(signal_picks),
        'wins': wins,
        'losses': losses,
        'pending': pending,
        'record': f"{wins}-{losses}",
        'avg_edge': avg_edge,
        'avg_edge_band': get_public_edge_band(avg_edge),
        'clv_rate': clv_rate,
        'recent_games': recent_games,
        'edges': edges,
    }


# ---------------------------------------------------------------------------
# Typefully integration
# ---------------------------------------------------------------------------

def create_social_draft(report_data):
    """Auto-create a Typefully draft from today's report data."""
    import os
    import requests as req

    api_key = os.environ.get('TYPEFULLY_API_KEY')
    if not api_key:
        log.warning("TYPEFULLY_API_KEY not set, skipping social draft")
        return

    sport = report_data.get('sport_upper', 'NBA')
    date_str = report_data.get('date', '')

    if report_data.get('signals_published', 0) > 0:
        text = (
            f"{report_data['games_analyzed']} {sport} games analyzed today.\n\n"
            f"{report_data['edges_found']} edges found. "
            f"{report_data['signals_published']} qualified.\n\n"
            f"Top edge: {report_data['top_edge']} on "
            f"{report_data['top_edge_game']}\n\n"
            f"Full report: sharppicks.ai/market-report/{date_str}"
        )
    else:
        text = (
            f"{report_data['games_analyzed']} {sport} games analyzed today.\n\n"
            f"0 qualified above the 3.5% edge threshold.\n\n"
            f"The model passed on the full slate.\n\n"
            f"Pass report: sharppicks.ai/passes/{date_str}"
        )

    try:
        resp = req.post(
            'https://api.typefully.com/v1/drafts/',
            headers={
                'X-API-KEY': api_key,
                'Content-Type': 'application/json',
            },
            json={
                'content': text,
                'threadify': False,
                'social_set_id': 291495,
            },
            timeout=10,
        )
        if resp.ok:
            log.info("Typefully draft created successfully")
        else:
            log.warning("Typefully draft failed: %s %s", resp.status_code, resp.text[:200])
    except Exception as e:
        log.warning("Typefully draft error: %s", e)


# ---------------------------------------------------------------------------
# Sitemap generation
# ---------------------------------------------------------------------------

def build_sitemap_urls(report_data=None, game_pages=None):
    """Build sitemap URL entries for content engine pages."""
    urls = []
    base = 'https://sharppicks.ai'

    for sport in get_live_sports():
        urls.append({'loc': f"{base}/edges/{sport}-today", 'changefreq': 'daily', 'priority': '0.8'})

    if report_data:
        date_str = report_data['date']
        urls.append({'loc': f"{base}/market-report/{date_str}", 'changefreq': 'daily', 'priority': '0.9'})
        urls.append({'loc': f"{base}/passes/{date_str}", 'changefreq': 'daily', 'priority': '0.7'})

    if game_pages:
        sport = report_data['sport'] if report_data else 'nba'
        for gp in game_pages:
            if gp.get('indexable'):
                urls.append({
                    'loc': f"{base}/{sport}/{gp['slug']}",
                    'changefreq': 'daily',
                    'priority': '0.6',
                })

    for sport_key, teams in SPORT_TEAM_MAP.items():
        if sport_key not in get_live_sports():
            continue
        for abbr, info in teams.items():
            urls.append({
                'loc': f"{base}/{sport_key}/{info['slug']}-betting-insights",
                'changefreq': 'weekly',
                'priority': '0.7',
            })

    urls.append({'loc': f"{base}/tools/clv-calculator", 'changefreq': 'monthly', 'priority': '0.8'})
    urls.append({'loc': f"{base}/tools/edge-calculator", 'changefreq': 'monthly', 'priority': '0.8'})

    return urls


def get_proof_module(sport='nba', limit=7):
    """Build a compact proof/receipts block from the last N resolved picks."""
    try:
        recent = Pick.query.filter(
            Pick.sport == sport,
            Pick.result.in_(['win', 'loss', 'push']),
        ).order_by(Pick.game_date.desc()).limit(limit).all()

        if not recent:
            return None

        wins = sum(1 for p in recent if p.result == 'win')
        losses = sum(1 for p in recent if p.result == 'loss')
        pushes = sum(1 for p in recent if p.result == 'push')
        total = wins + losses
        clv_positive = sum(1 for p in recent if p.clv and float(p.clv) > 0)
        clv_pct = round(clv_positive / len(recent) * 100) if recent else 0
        edges = [abs(float(p.edge_pct)) for p in recent if p.edge_pct]
        avg_edge = round(sum(edges) / len(edges), 1) if edges else 0

        return {
            'record': f"{wins}-{losses}" + (f"-{pushes}" if pushes else ""),
            'win_rate': round(wins / total * 100) if total else 0,
            'clv_pct': clv_pct,
            'avg_edge': avg_edge,
            'count': len(recent),
        }
    except Exception as e:
        log.warning('Proof module failed: %s', e)
        return None


# ---------------------------------------------------------------------------
# Routes -- Market Report
# ---------------------------------------------------------------------------

@content_bp.route('/market-report/<date_str>')
def market_report_page(date_str):
    sport = request.args.get('sport', 'nba')
    if sport not in get_live_sports():
        sport = 'nba'

    data = get_daily_report_data(date_str, sport)
    if not data:
        abort(404)

    seed = f"{sport}-{date_str}-market-report"
    overview_blocks = _format_blocks(
        choose_blocks(MARKET_OVERVIEW_BLOCKS, count=1, seed=seed), data
    )
    selectivity_blocks = _format_blocks(
        choose_blocks(PASS_EXPLANATION_BLOCKS, count=1, seed=seed + '-sel'), data
    )
    lm_blocks = _format_blocks(
        choose_blocks(LINE_MOVEMENT_BLOCKS, count=1, seed=seed + '-lm'), data
    )
    why_blocks = _format_blocks(
        choose_blocks(WHY_THIS_MATTERS_BLOCKS, count=1, seed=seed + '-why'), data
    )

    pillar = get_rotating_pillar(seed)
    cta = get_rotating_cta(seed, page_type='market_report')
    proof = get_proof_module(sport)

    title = f"{data['sport_upper']} Betting Market Report {data['date_formatted']} | SharpPicks"
    meta_desc = build_market_report_meta(data)
    canonical = f"https://sharppicks.ai/market-report/{date_str}?sport={sport}"

    jsonld_article = build_jsonld_article(title, meta_desc, date_str, canonical)
    jsonld_faq = build_jsonld_faq(MARKET_REPORT_FAQ)

    top_game_slugs = sorted(data['games'], key=lambda g: g['edge'], reverse=True)[:2]
    internal_links = [
        {'label': 'Passes', 'text': f"{data['games_passed']} games the model passed on", 'url': f"/passes/{date_str}?sport={sport}"},
        {'label': 'Edges', 'text': f"Today's {data['sport_upper']} edge rankings", 'url': f"/edges/{sport}-today"},
    ]
    for g in top_game_slugs:
        internal_links.append({
            'label': 'Game',
            'text': f"{g['away_team']} @ {g['home_team']}",
            'url': f"/{sport}/{g['slug']}",
        })
    internal_links.append({'label': 'Learn', 'text': pillar['title'], 'url': pillar['url']})

    resp = make_response(render_template(
        'content/market_report.html',
        data=data,
        overview_blocks=overview_blocks,
        selectivity_blocks=selectivity_blocks,
        lm_blocks=lm_blocks,
        why_blocks=why_blocks,
        cta=cta,
        proof=proof,
        faq=MARKET_REPORT_FAQ,
        internal_links=internal_links,
        title=title,
        meta_desc=meta_desc,
        canonical=canonical,
        jsonld_article=jsonld_article,
        jsonld_faq=jsonld_faq,
        meta_robots='index,follow',
        get_public_edge_band=get_public_edge_band,
    ))
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


# ---------------------------------------------------------------------------
# Routes -- Pass Report
# ---------------------------------------------------------------------------

@content_bp.route('/passes/<date_str>')
def pass_report_page(date_str):
    sport = request.args.get('sport', 'nba')
    if sport not in get_live_sports():
        sport = 'nba'

    data = get_daily_report_data(date_str, sport)
    if not data:
        abort(404)

    passed_games = [g for g in data['games'] if not g['signal']]

    seed = f"{sport}-{date_str}-pass-report"
    overview_blocks = _format_blocks(
        choose_blocks(PASS_OVERVIEW_BLOCKS, count=1, seed=seed), data
    )
    explanation_blocks = _format_blocks(
        choose_blocks(PASS_EXPLANATION_BLOCKS, count=1, seed=seed + '-exp'), data
    )

    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        is_early_mlb = sport == 'mlb' and dt.month <= 5 and dt.day <= 15
    except Exception:
        is_early_mlb = False

    pillar = get_rotating_pillar(seed)
    cta = get_rotating_cta(seed, page_type='pass')

    # Only include true passes (not filtered) in avg edge calculation
    true_passes = [g for g in passed_games if g['status'] == 'Pass']
    avg_edge = 0
    if true_passes:
        avg_edge = sum(g['edge'] for g in true_passes) / len(true_passes)
    elif passed_games:
        avg_edge = sum(g['edge'] for g in passed_games) / len(passed_games)

    title = f"Games the Model Passed On {data['date_formatted']} | SharpPicks"
    meta_desc = build_pass_report_meta(data)
    canonical = f"https://sharppicks.ai/passes/{date_str}?sport={sport}"
    jsonld_article = build_jsonld_article(title, meta_desc, date_str, canonical)

    internal_links = [
        {'label': 'Report', 'text': f"Full Market Report {data['date_short']}", 'url': f"/market-report/{date_str}?sport={sport}"},
        {'label': 'Read', 'text': 'Why We Pass More Than We Play', 'url': '/blog/why-we-pass'},
        {'label': 'Edges', 'text': f"Today's {data['sport_upper']} edge rankings", 'url': f"/edges/{sport}-today"},
    ]
    top_passed = sorted(passed_games, key=lambda g: g['edge'], reverse=True)[:2]
    for g in top_passed:
        internal_links.append({
            'label': 'Team',
            'text': f"{_team_full_name(g['away_team'], sport)} Insights",
            'url': f"/{sport}/{_team_slug(g['away_team'], sport)}-betting-insights",
        })

    resp = make_response(render_template(
        'content/pass_report.html',
        data=data,
        passed_games=passed_games,
        overview_blocks=overview_blocks,
        explanation_blocks=explanation_blocks,
        is_early_mlb=is_early_mlb,
        avg_edge=avg_edge,
        avg_edge_band=get_public_edge_band(avg_edge),
        cta=cta,
        internal_links=internal_links,
        title=title,
        meta_desc=meta_desc,
        canonical=canonical,
        jsonld_article=jsonld_article,
        meta_robots='index,follow',
    ))
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


# ---------------------------------------------------------------------------
# Routes -- Edge Summary
# ---------------------------------------------------------------------------

@content_bp.route('/edges/<sport_slug>')
def edges_page(sport_slug):
    match = re.match(r'^(nba|mlb|nfl)-today$', sport_slug)
    if not match:
        abort(404)
    sport = match.group(1)
    if sport not in get_live_sports():
        abort(404)

    today = datetime.now(ET).strftime('%Y-%m-%d')
    data = get_daily_report_data(today, sport)
    if not data:
        abort(404)

    for g in data['games']:
        g['index_score'] = get_index_score(g)
        g['indexable'] = should_index_game_page(g)

    seed = f"{sport}-{today}-edges"
    pillar = get_rotating_pillar(seed)
    cta = get_rotating_cta(seed, page_type='edges')

    title = f"Today's {data['sport_upper']} Betting Edges | SharpPicks"
    meta_desc = build_edges_meta(data)
    canonical = f"https://sharppicks.ai/edges/{sport}-today"

    internal_links = [
        {'label': 'Report', 'text': f"Market Report {data['date_short']}", 'url': f"/market-report/{today}?sport={sport}"},
        {'label': 'Passes', 'text': f"Pass Report {data['date_short']}", 'url': f"/passes/{today}?sport={sport}"},
    ]
    top_edge_games = sorted(data['games'], key=lambda g: g['edge'], reverse=True)[:2]
    for g in top_edge_games:
        internal_links.append({
            'label': 'Game',
            'text': f"{g['away_team']} @ {g['home_team']}",
            'url': f"/{sport}/{g['slug']}",
        })
    internal_links.append({'label': 'Learn', 'text': pillar['title'], 'url': pillar['url']})

    proof = get_proof_module(sport)

    resp = make_response(render_template(
        'content/edges.html',
        data=data,
        cta=cta,
        proof=proof,
        internal_links=internal_links,
        title=title,
        meta_desc=meta_desc,
        canonical=canonical,
        meta_robots='index,follow',
        get_public_edge_band=get_public_edge_band,
    ))
    resp.headers['Cache-Control'] = 'public, max-age=900'
    return resp


# ---------------------------------------------------------------------------
# Routes -- Team Page (registered before game page for route specificity)
# ---------------------------------------------------------------------------

@content_bp.route('/nba/<team_slug>-betting-insights')
@content_bp.route('/mlb/<team_slug>-betting-insights')
@content_bp.route('/nfl/<team_slug>-betting-insights')
@content_bp.route('/wnba/<team_slug>-betting-insights')
def team_page(team_slug):
    sport = request.path.strip('/').split('/')[0]
    if sport not in get_live_sports():
        abort(404)

    teams = SPORT_TEAM_MAP.get(sport, {})
    abbr = None
    for a, info in teams.items():
        if info['slug'] == team_slug:
            abbr = a
            break

    if not abbr:
        abort(404)

    team_data = get_team_season_data(abbr, sport)

    signal_freq = ''
    if team_data['signals'] > 0:
        signal_freq = (
            f"The {team_data['name']} have generated {team_data['signals']} official "
            f"signal{'s' if team_data['signals'] != 1 else ''} this season, "
            f"converting at a {team_data['clv_rate']}% CLV+ rate."
        )
    else:
        signal_freq = (
            f"The {team_data['name']} have not generated any official signals "
            f"this season. The market has priced their games efficiently."
        )

    pricing_tendency = ''
    if team_data['signals'] >= 3:
        home_signals = sum(1 for g in team_data['recent_games'] if g['is_signal'] and g['at_home'])
        away_signals = sum(1 for g in team_data['recent_games'] if g['is_signal'] and not g['at_home'])
        if home_signals > away_signals:
            pricing_tendency = f"The market tends to underprice {team_data['abbr']} at home, where the majority of signals have been generated."
        elif away_signals > home_signals:
            pricing_tendency = f"The market has undervalued {team_data['abbr']} on the road, where most signals have appeared."
        else:
            pricing_tendency = f"Signals have been evenly split between home and road games for {team_data['abbr']}."

    seed = f"{sport}-{abbr}-team"
    pillar = get_rotating_pillar(seed)
    cta = get_rotating_cta(seed)

    title = f"{team_data['name']} Betting Insights and Analysis | SharpPicks"
    meta_desc = build_team_page_meta(team_data['name'], team_data['sport_upper'])
    canonical = f"https://sharppicks.ai/{sport}/{team_slug}-betting-insights"

    jsonld = build_jsonld_collection(title, meta_desc, canonical)

    internal_links = []
    for g in team_data['recent_games'][:3]:
        internal_links.append({
            'label': 'Game',
            'text': f"{team_data['abbr']} {'vs' if g['at_home'] else '@'} {g['opponent']} {g['date_short']}",
            'url': f"/{sport}/{g['slug']}",
        })
    internal_links.append({'label': 'Tool', 'text': 'CLV Calculator', 'url': '/tools/clv-calculator'})
    internal_links.append({'label': 'Learn', 'text': pillar['title'], 'url': pillar['url']})

    resp = make_response(render_template(
        'content/team.html',
        team=team_data,
        signal_freq=signal_freq,
        pricing_tendency=pricing_tendency,
        cta=cta,
        internal_links=internal_links,
        title=title,
        meta_desc=meta_desc,
        canonical=canonical,
        jsonld=jsonld,
        meta_robots='index,follow',
        get_public_edge_band=get_public_edge_band,
    ))
    resp.headers['Cache-Control'] = 'public, max-age=21600'
    return resp


# ---------------------------------------------------------------------------
# Routes -- Game Page (catch-all for /<sport>/<slug>, registered after team)
# ---------------------------------------------------------------------------

@content_bp.route('/nba/<slug>')
@content_bp.route('/mlb/<slug>')
@content_bp.route('/nfl/<slug>')
@content_bp.route('/wnba/<slug>')
def game_page(slug):
    sport = request.path.strip('/').split('/')[0]
    if sport not in get_live_sports():
        abort(404)

    match = re.match(r'^(.+)-vs-(.+)-(\d{4}-\d{2}-\d{2})$', slug)
    if not match:
        abort(404)

    date_str = match.group(3)
    data = get_daily_report_data(date_str, sport)
    if not data:
        abort(404)

    game = None
    for g in data['games']:
        if g['slug'] == slug:
            game = g
            break

    if not game:
        abort(404)

    game['index_score'] = get_index_score(game)
    game['indexable'] = should_index_game_page(game)
    meta_robots = 'index,follow' if game['indexable'] else 'noindex,follow'

    pick_obj = Pick.query.filter_by(
        sport=sport,
        game_date=date_str,
        home_team=game['home_team'],
    ).first()

    postgame_summary = None
    result_data = None
    if pick_obj and pick_obj.result and pick_obj.result not in ('pending', 'revoked'):
        result_data = {
            'result': pick_obj.result,
            'home_score': pick_obj.home_score,
            'away_score': pick_obj.away_score,
            'clv': pick_obj.clv,
            'pnl': pick_obj.pnl,
        }
        postgame_summary = build_postgame_summary({
            'result': pick_obj.result,
            'result_label': 'Covered' if pick_obj.result == 'win' else 'Did not cover',
            'clv_display': f"{pick_obj.clv:+.1f}" if pick_obj.clv else 'N/A',
            'final_score': True,
        })

    seed = f"{sport}-{date_str}-{slug}"
    model_view_blocks = _format_blocks(
        choose_blocks(GAME_MODEL_VIEW_BLOCKS, count=1, seed=seed), data
    )

    pillar = get_rotating_pillar(seed)
    cta = get_rotating_cta(seed, page_type='game')

    title = f"{game['away_name']} vs {game['home_name']} Betting Analysis {data['date_formatted']} | SharpPicks"
    meta_desc = build_game_page_meta(game, data)
    canonical = f"https://sharppicks.ai/{sport}/{slug}"

    jsonld_article = build_jsonld_article(title, meta_desc, date_str, canonical)
    jsonld_event = build_jsonld_sports_event(game, data)

    internal_links = [
        {'label': 'Report', 'text': f"Market Report {data['date_short']}", 'url': f"/market-report/{date_str}?sport={sport}"},
        {'label': 'Team', 'text': f"{game['away_name']} Insights", 'url': f"/{sport}/{_team_slug(game['away_team'], sport)}-betting-insights"},
        {'label': 'Team', 'text': f"{game['home_name']} Insights", 'url': f"/{sport}/{_team_slug(game['home_team'], sport)}-betting-insights"},
        {'label': 'Learn', 'text': pillar['title'], 'url': pillar['url']},
        {'label': 'Tool', 'text': 'CLV Calculator', 'url': '/tools/clv-calculator'},
    ]

    resp = make_response(render_template(
        'content/game.html',
        data=data,
        game=game,
        model_view_blocks=model_view_blocks,
        result_data=result_data,
        postgame_summary=postgame_summary,
        cta=cta,
        internal_links=internal_links,
        title=title,
        meta_desc=meta_desc,
        canonical=canonical,
        jsonld_article=jsonld_article,
        jsonld_event=jsonld_event,
        meta_robots=meta_robots,
        get_public_edge_band=get_public_edge_band,
    ))
    cache_time = 86400 if result_data else 3600
    resp.headers['Cache-Control'] = f'public, max-age={cache_time}'
    return resp


# ---------------------------------------------------------------------------
# Routes -- Tools
# ---------------------------------------------------------------------------

@content_bp.route('/tools/clv-calculator')
def clv_calculator():
    title = "CLV Calculator | SharpPicks"
    meta_desc = "Calculate your Closing Line Value (CLV) to measure bet quality. Enter your bet line and closing line to see if you beat the market."
    canonical = "https://sharppicks.ai/tools/clv-calculator"
    jsonld_sw = build_jsonld_software("CLV Calculator", meta_desc, canonical)
    jsonld_faq = build_jsonld_faq([
        {"question": "What is Closing Line Value?", "answer": "CLV measures whether you got a better price than the closing line. Consistently positive CLV indicates long-term edge."},
        {"question": "How do I calculate CLV?", "answer": "Compare the line you bet at versus the closing line. If you bet -3 and it closed at -4.5, you captured 1.5 points of CLV."},
        {"question": "Why does CLV matter?", "answer": "CLV is the strongest predictor of long-term betting profitability. Bettors who consistently beat the closing line tend to profit over time."},
    ])
    cta = get_rotating_cta('clv-calculator')
    resp = make_response(render_template(
        'content/clv_calculator.html',
        title=title,
        meta_desc=meta_desc,
        canonical=canonical,
        jsonld_sw=jsonld_sw,
        jsonld_faq=jsonld_faq,
        cta=cta,
        meta_robots='index,follow',
    ))
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp


@content_bp.route('/tools/edge-calculator')
def edge_calculator():
    title = "Edge Calculator | SharpPicks"
    meta_desc = "Calculate your betting edge by comparing your estimated probability against market odds. See if your edge exceeds the 3.5% qualification threshold."
    canonical = "https://sharppicks.ai/tools/edge-calculator"
    jsonld_sw = build_jsonld_software("Edge Calculator", meta_desc, canonical)
    jsonld_faq = build_jsonld_faq([
        {"question": "What is a betting edge?", "answer": "A betting edge is the difference between your estimated true probability and the implied probability from market odds. A positive edge means you have an expected profit."},
        {"question": "What is the 3.5% threshold?", "answer": "SharpPicks requires at least a 3.5% edge before publishing a signal. This threshold filters out noise and ensures only meaningful mispricing is acted on."},
        {"question": "How do I estimate true probability?", "answer": "True probability is estimated using statistical models that account for team strength, matchup factors, injuries, and other variables. SharpPicks uses an ensemble of four models."},
    ])
    cta = get_rotating_cta('edge-calculator')
    resp = make_response(render_template(
        'content/edge_calculator.html',
        title=title,
        meta_desc=meta_desc,
        canonical=canonical,
        jsonld_sw=jsonld_sw,
        jsonld_faq=jsonld_faq,
        cta=cta,
        meta_robots='index,follow',
    ))
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp


# ---------------------------------------------------------------------------
# Routes -- Dynamic Sitemap
# ---------------------------------------------------------------------------

@content_bp.route('/sitemap-content.xml')
def sitemap_content():
    today = datetime.now(ET).strftime('%Y-%m-%d')
    urls = []
    base = 'https://sharppicks.ai'

    for sport in get_live_sports():
        urls.append({'loc': f"{base}/edges/{sport}-today", 'changefreq': 'daily', 'priority': '0.8'})

        data = get_daily_report_data(today, sport)
        if data:
            urls.append({'loc': f"{base}/market-report/{today}?sport={sport}", 'changefreq': 'daily', 'priority': '0.9'})
            urls.append({'loc': f"{base}/passes/{today}?sport={sport}", 'changefreq': 'daily', 'priority': '0.7'})
            for g in data['games']:
                if should_index_game_page(g):
                    urls.append({'loc': f"{base}/{sport}/{g['slug']}", 'changefreq': 'daily', 'priority': '0.6'})

    for sport_key, teams in SPORT_TEAM_MAP.items():
        if sport_key not in get_live_sports():
            continue
        for abbr, info in teams.items():
            urls.append({'loc': f"{base}/{sport_key}/{info['slug']}-betting-insights", 'changefreq': 'weekly', 'priority': '0.7'})

    urls.append({'loc': f"{base}/tools/clv-calculator", 'changefreq': 'monthly', 'priority': '0.8'})
    urls.append({'loc': f"{base}/tools/edge-calculator", 'changefreq': 'monthly', 'priority': '0.8'})

    last_30_days = [(datetime.now(ET) - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 31)]
    for d in last_30_days:
        for sport in get_live_sports():
            urls.append({'loc': f"{base}/market-report/{d}?sport={sport}", 'changefreq': 'weekly', 'priority': '0.6'})
            urls.append({'loc': f"{base}/passes/{d}?sport={sport}", 'changefreq': 'weekly', 'priority': '0.5'})

    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for u in urls:
        xml_parts.append(f"  <url><loc>{u['loc']}</loc><changefreq>{u['changefreq']}</changefreq><priority>{u['priority']}</priority></url>")
    xml_parts.append('</urlset>')

    resp = make_response('\n'.join(xml_parts))
    resp.headers['Content-Type'] = 'application/xml'
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


# ---------------------------------------------------------------------------
# Cron endpoints
# ---------------------------------------------------------------------------

@content_bp.route('/api/cron/content-engine', methods=['POST'])
def cron_content_engine():
    """Run after model pipeline to create social drafts."""
    import os
    secret = os.environ.get('CRON_SECRET', '')
    if secret and request.headers.get('X-Cron-Secret') != secret:
        return {'error': 'unauthorized'}, 403

    today = datetime.now(ET).strftime('%Y-%m-%d')
    results = []
    for sport in get_live_sports():
        data = get_daily_report_data(today, sport)
        if data:
            create_social_draft(data)
            results.append(f"{sport}: draft created")
        else:
            results.append(f"{sport}: no data")

    return {'status': 'ok', 'results': results}
