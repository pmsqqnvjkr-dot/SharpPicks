"""
Share card image generation — PIL-based, no browser dependencies.
Produces 1200x630 PNG cards for Twitter/X summary_large_image.
Includes OG meta endpoints for crawler/bot previews.
"""

from flask import Blueprint, Response, jsonify, request
from models import db, Pick, Pass, ModelRun
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from functools import lru_cache
import json, os, logging
from markupsafe import escape

cards_bp = Blueprint('cards', __name__)

W, H = 1200, 630
BG = (10, 13, 20)
GREEN = (90, 158, 114)
RED = (196, 104, 107)
WHITE = (232, 236, 241)
GRAY = (106, 122, 141)
MUTED = (74, 85, 104)
LIGHT_GRAY = (170, 170, 170)
BORDER = (30, 48, 80)
DIVIDER = (30, 48, 80)
CARD_BG = (17, 30, 51)

_BASE = os.path.dirname(os.path.abspath(__file__))
_WORDMARK_PATH = os.path.join(_BASE, 'public', 'wordmark-white.png')
_CREST_PATH = os.path.join(_BASE, 'brand', 'images', 'crest.png')

TEAM_ABBR = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
    'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
    'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
    'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM',
    'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN',
    'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC',
    'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
    'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
    'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS',
    'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL',
    'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CWS',
    'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL',
    'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
    'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA',
    'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM',
    'New York Yankees': 'NYY', 'Oakland Athletics': 'OAK', 'Philadelphia Phillies': 'PHI',
    'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD', 'San Francisco Giants': 'SF',
    'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB',
    'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH',
}


def _abbr(team):
    if not team:
        return ''
    if team in TEAM_ABBR:
        return TEAM_ABBR[team]
    return team.split()[-1][:3].upper()


@lru_cache(maxsize=1)
def _fonts():
    paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/System/Library/Fonts/Menlo.ttc',
        '/System/Library/Fonts/SFMono.ttf',
    ]
    mono = mono_bold = sans = sans_bold = None
    for p in paths:
        if not os.path.exists(p):
            continue
        name = os.path.basename(p).lower()
        if 'mono' in name and 'bold' in name:
            mono_bold = p
        elif 'mono' in name or 'menlo' in name or 'sfmono' in name:
            mono = p
        elif 'bold' in name:
            sans_bold = p
        else:
            sans = p

    def load(path, size):
        if path:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
        return ImageFont.load_default()

    return {
        'wordmark': load(mono_bold or mono, 14),
        'hero': load(sans_bold or sans, 36),
        'large': load(sans_bold or sans, 28),
        'medium': load(sans or sans_bold, 18),
        'small': load(sans or sans_bold, 14),
        'small_bold': load(sans_bold or sans, 14),
        'caption': load(mono or sans, 12),
        'caption_bold': load(mono_bold or mono, 12),
        'stat_label': load(mono_bold or mono, 10),
        'stat_val': load(mono or sans, 22),
    }


@lru_cache(maxsize=1)
def _brand_images():
    wordmark = None
    crest = None
    try:
        wordmark = Image.open(_WORDMARK_PATH).convert('RGBA')
    except Exception as e:
        logging.warning(f"Wordmark not found: {e}")
    try:
        crest = Image.open(_CREST_PATH).convert('RGBA')
    except Exception as e:
        logging.warning(f"Crest not found: {e}")
    return wordmark, crest


def _new_card(accent=GREEN):
    img = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 3], fill=accent)
    return img, draw


def _paste_wordmark(img, x=40, y=30, height=22):
    wm, _ = _brand_images()
    if wm:
        ratio = height / wm.height
        new_w = int(wm.width * ratio)
        resized = wm.resize((new_w, height), Image.LANCZOS)
        img.paste(resized, (x, y), resized)
        return new_w
    else:
        draw = ImageDraw.Draw(img)
        fonts = _fonts()
        draw.text((x, y), 'SHARP \u2016 PICKS', fill=WHITE, font=fonts['wordmark'])
        return 150


def _draw_wordmark(draw, text='SHARP \u2016 PICKS'):
    fonts = _fonts()
    draw.text((32, 32), text.upper(), fill=GREEN, font=fonts['wordmark'])


def _draw_footer(draw, date_str=None):
    fonts = _fonts()
    draw.text((32, H - 44), 'sharppicks.ai', fill=GRAY, font=fonts['caption'])
    if date_str:
        bbox = fonts['caption'].getbbox(date_str)
        tw = bbox[2] - bbox[0] if bbox else 100
        draw.text((W - 32 - tw, H - 44), date_str, fill=GRAY, font=fonts['caption'])


def _fmt_spread(val):
    if val is None:
        return '--'
    n = float(val)
    if n == int(n):
        return f'+{int(n)}' if n > 0 else str(int(n))
    return f'+{n:.1f}' if n > 0 else f'{n:.1f}'


def _to_png(img):
    buf = BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    return buf


def _date_label(pick):
    if pick.game_date:
        try:
            from datetime import datetime
            d = datetime.strptime(pick.game_date, '%Y-%m-%d')
            return d.strftime('%b %-d, %Y')
        except Exception:
            return pick.game_date
    return ''


@cards_bp.route('/signal/<signal_id>')
def signal_card(signal_id):
    pick = Pick.query.get(signal_id)
    if not pick:
        return jsonify({'error': 'Not found'}), 404

    img, draw = _new_card()
    fonts = _fonts()
    _draw_wordmark(draw, 'SHARP \u2016 PICKS')

    y = 80
    side = pick.side or ''
    draw.text((32, y), side, fill=WHITE, font=fonts['hero'])

    edge_text = f'+{pick.edge_pct:.1f}% Edge' if pick.edge_pct else ''
    if edge_text:
        bbox = fonts['large'].getbbox(edge_text)
        tw = bbox[2] - bbox[0] if bbox else 200
        draw.text((W - 32 - tw, y + 4), edge_text, fill=GREEN, font=fonts['large'])

    y += 60
    model_prob = pick.cover_prob or pick.model_confidence
    if model_prob:
        draw.text((32, y), f'Model: {model_prob * 100:.1f}%', fill=WHITE, font=fonts['medium'])
    y += 30
    if pick.implied_prob:
        draw.text((32, y), f'Market: {pick.implied_prob * 100:.1f}%', fill=WHITE, font=fonts['medium'])

    y += 50
    draw.text((32, y), 'Qualified Signal', fill=GREEN, font=fonts['small'])
    y += 28
    draw.text((32, y), 'Selective by design.', fill=GRAY, font=fonts['small'])

    _draw_footer(draw, _date_label(pick))
    return Response(_to_png(img).read(), mimetype='image/png',
                    headers={'Cache-Control': 'public, max-age=86400'})


@cards_bp.route('/result/<signal_id>')
def result_card(signal_id):
    from flask import render_template
    from routes.card_routes import _get_logo_base64, _get_wordmark_base64

    pick = Pick.query.get(signal_id)
    if not pick:
        return jsonify({'error': 'Not found'}), 404

    is_win = pick.result == 'win'
    is_loss = pick.result == 'loss'

    units_val = pick.profit_units or 0
    if units_val > 0:
        units_fmt = f'+{units_val:.1f}u'
    elif units_val < 0:
        units_fmt = f'\u2212{abs(units_val):.1f}u'
    else:
        units_fmt = '0.0u'

    clv_val = pick.clv
    if clv_val is not None:
        clv_sign = '+' if clv_val > 0 else ''
        clv_fmt = f'{clv_sign}{clv_val:.1f}'
    else:
        clv_fmt = '--'

    all_decided = Pick.query.filter(Pick.result.in_(['win', 'loss', 'push'])).all()
    s_wins = sum(1 for p in all_decided if p.result == 'win')
    s_losses = sum(1 for p in all_decided if p.result == 'loss')
    s_decided = s_wins + s_losses
    s_win_pct = round(s_wins / s_decided * 100, 1) if s_decided > 0 else 0
    clv_values = [p.clv for p in all_decided if p.clv is not None]
    clv_positive = sum(1 for v in clv_values if v > 0)
    s_clv = round(clv_positive / len(clv_values) * 100, 1) if clv_values else 0

    matchup = f'{pick.away_team} @ {pick.home_team}' if pick.away_team and pick.home_team else ''

    data = {
        'logo_base64': _get_logo_base64(),
        'wordmark_base64': _get_wordmark_base64(),
        'game_date': _date_label(pick),
        'matchup': matchup,
        'side': pick.side or '',
        'result_label': (pick.result or 'pending').upper(),
        'result_color': 'green' if is_win else ('red' if is_loss else 'white'),
        'accent_color': '#5A9E72' if is_win else ('#C4686B' if is_loss else '#5A9E72'),
        'units_fmt': units_fmt,
        'units_color': 'green' if units_val > 0 else ('red' if units_val < 0 else 'white'),
        'edge_pct': f'{pick.edge_pct:.1f}' if pick.edge_pct else '0.0',
        'clv_fmt': clv_fmt,
        'clv_color': 'green' if (clv_val or 0) > 0 else ('red' if (clv_val or 0) < 0 else 'white'),
        'line_fmt': _fmt_spread(pick.line),
        'season_wins': s_wins,
        'season_losses': s_losses,
        'season_win_pct': s_win_pct,
        'season_clv': s_clv,
    }

    html_string = render_template('result_card.html', **data)

    try:
        from services.card_generator import generate_card_png
        png_bytes = generate_card_png(html_string)
        return Response(png_bytes, mimetype='image/png',
                        headers={'Cache-Control': 'public, max-age=86400'})
    except Exception:
        return _result_card_fallback(pick)


@cards_bp.route('/user-results')
def user_results_card():
    from flask import render_template
    from public_api import _get_sport_filter
    from routes.card_routes import _get_logo_base64, _get_wordmark_base64

    sport = _get_sport_filter()
    pick_q = Pick.query
    pass_q = Pass.query
    if sport:
        pick_q = pick_q.filter_by(sport=sport)
        pass_q = pass_q.filter_by(sport=sport)

    decided = pick_q.filter(Pick.result.in_(['win', 'loss', 'push'])).all()
    wins = sum(1 for p in decided if p.result == 'win')
    losses = sum(1 for p in decided if p.result == 'loss')
    total_pnl = sum((p.profit_units or 0) for p in decided)
    total_decided = len(decided)
    roi = round((sum((p.pnl or 0) for p in decided) / (total_decided * 110)) * 100, 1) if total_decided > 0 else 0
    win_pct = round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0
    total_passes = pass_q.count()
    total_picks = pick_q.count()
    total_games = total_decided + total_passes
    selectivity = round(total_decided / total_games * 100, 1) if total_games > 0 else 0

    clv_values = [p.clv for p in decided if p.clv is not None]
    clv_positive = sum(1 for v in clv_values if v > 0)
    clv_beat_rate = round(clv_positive / len(clv_values) * 100, 1) if clv_values else 0

    if selectivity < 20:
        grade = 'A+'
    elif selectivity < 30:
        grade = 'A'
    elif selectivity < 40:
        grade = 'B+'
    elif selectivity < 50:
        grade = 'B'
    elif selectivity < 70:
        grade = 'C'
    else:
        grade = 'D'

    pnl_sign = '+' if total_pnl >= 0 else '\u2212'
    pnl_fmt = f'{pnl_sign}{abs(total_pnl):.1f}'
    roi_sign = '+' if roi >= 0 else '\u2212'
    roi_fmt = f'{roi_sign}{abs(roi)}%'

    data = {
        'logo_base64': _get_logo_base64(),
        'wordmark_base64': _get_wordmark_base64(),
        'wins': wins,
        'losses': losses,
        'pnl_fmt': pnl_fmt,
        'pnl_color': 'green' if total_pnl >= 0 else 'red',
        'roi_fmt': roi_fmt,
        'roi_color': 'green' if roi >= 0 else 'red',
        'win_pct': win_pct,
        'grade': grade,
        'selectivity': selectivity,
        'clv_beat_rate': clv_beat_rate,
        'total_passes': total_passes,
        'total_picks': total_picks,
    }

    html_string = render_template('user_results_card.html', **data)

    try:
        from services.card_generator import generate_card_png
        png_bytes = generate_card_png(html_string)
        return Response(png_bytes, mimetype='image/png',
                        headers={'Cache-Control': 'public, max-age=300'})
    except Exception:
        return _user_results_fallback(wins, losses, total_pnl, roi, grade, selectivity)


@cards_bp.route('/market-report')
def market_report_card():
    from zoneinfo import ZoneInfo
    from datetime import datetime
    et = ZoneInfo('America/New_York')
    today = datetime.now(et).strftime('%Y-%m-%d')
    date_param = request.args.get('date', today)

    sport = request.args.get('sport')
    query = ModelRun.query.filter_by(date=date_param)
    if sport:
        query = query.filter_by(sport=sport)
    run = query.order_by(ModelRun.created_at.desc()).first()

    if not run:
        return jsonify({'error': 'No model run found'}), 404

    games_analyzed = run.games_analyzed or 0
    edges_detected = 0
    qualified_signals = 0
    if run.games_detail:
        try:
            detail = json.loads(run.games_detail)
            for g in detail:
                if abs(g.get('edge', 0) or 0) >= 2.0:
                    edges_detected += 1
                if g.get('passes'):
                    qualified_signals += 1
        except Exception:
            pass

    img, draw = _new_card()
    fonts = _fonts()
    _draw_wordmark(draw, 'SHARP \u2016 PICKS')

    y = 80
    draw.text((32, y), f'{games_analyzed} games scanned', fill=WHITE, font=fonts['medium'])
    y += 32
    draw.text((32, y), f'{edges_detected} edges detected', fill=WHITE, font=fonts['medium'])
    y += 32
    draw.text((32, y), f'{qualified_signals} signal{"s" if qualified_signals != 1 else ""}', fill=WHITE, font=fonts['medium'])

    y += 60
    tagline = 'If it\u2019s not sharp, it\u2019s not sent.' if qualified_signals == 0 else 'Selective by design.'
    draw.text((32, y), tagline, fill=GREEN, font=fonts['large'])

    try:
        from datetime import datetime as dt
        d = dt.strptime(date_param, '%Y-%m-%d')
        date_label = d.strftime('%b %-d, %Y')
    except Exception:
        date_label = date_param
    _draw_footer(draw, date_label)

    return Response(_to_png(img).read(), mimetype='image/png',
                    headers={'Cache-Control': 'public, max-age=300'})


@cards_bp.route('/weekly-report')
def weekly_report_card():
    from flask import render_template
    from routes.card_routes import _get_logo_base64, _get_wordmark_base64, _compute_weekly_data

    try:
        data = _compute_weekly_data()
        html_string = render_template('recap_card.html', **data)
        from services.card_generator import generate_card_png
        png_bytes = generate_card_png(html_string)
        return Response(png_bytes, mimetype='image/png',
                        headers={'Cache-Control': 'public, max-age=300'})
    except Exception:
        return _weekly_report_fallback()


def _result_card_fallback(pick):
    """PIL fallback if Playwright is unavailable."""
    img, draw = _new_card()
    fonts = _fonts()
    _draw_wordmark(draw, 'SHARP \u2016 PICKS')
    is_win = pick.result == 'win'
    y = 80
    draw.text((32, y), pick.side or '', fill=WHITE, font=fonts['hero'])
    y += 60
    result_text = (pick.result or 'pending').upper()
    result_color = GREEN if is_win else (RED if pick.result == 'loss' else GRAY)
    draw.text((32, y), f'Result: {result_text}', fill=result_color, font=fonts['large'])
    _draw_footer(draw, _date_label(pick))
    return Response(_to_png(img).read(), mimetype='image/png',
                    headers={'Cache-Control': 'public, max-age=86400'})


def _user_results_fallback(wins, losses, total_pnl, roi, grade, selectivity):
    """PIL fallback if Playwright is unavailable."""
    img, draw = _new_card()
    fonts = _fonts()
    _draw_wordmark(draw, 'SHARP \u2016 PICKS')
    pnl_color = GREEN if total_pnl >= 0 else RED
    pnl_sign = '+' if total_pnl >= 0 else ''
    draw.text((32, 80), f'Profit: {pnl_sign}{total_pnl:.1f}u', fill=pnl_color, font=fonts['hero'])
    draw.text((32, 135), f'Record: {wins}\u2013{losses}', fill=WHITE, font=fonts['medium'])
    _draw_footer(draw, None)
    return Response(_to_png(img).read(), mimetype='image/png',
                    headers={'Cache-Control': 'public, max-age=300'})


def _weekly_report_fallback():
    """PIL fallback if Playwright is unavailable."""
    img, draw = _new_card()
    fonts = _fonts()
    _draw_wordmark(draw, 'SHARP \u2016 PICKS')
    draw.text((32, 80), 'Weekly report', fill=WHITE, font=fonts['hero'])
    draw.text((32, 135), 'Card generation unavailable', fill=GRAY, font=fonts['medium'])
    _draw_footer(draw, None)
    return Response(_to_png(img).read(), mimetype='image/png',
                    headers={'Cache-Control': 'public, max-age=300'})


# ── Open Graph share system ──

BASE_URL = os.environ.get('APP_BASE_URL', 'https://app.sharppicks.ai')
SHARE_URL = os.environ.get('SHARE_BASE_URL', 'https://sharppicks.ai')


def _season_stats(sport=None):
    q = Pick.query.filter(Pick.result.in_(['win', 'loss', 'push']))
    if sport:
        q = q.filter(Pick.sport == sport)
    decided = q.all()
    wins = sum(1 for p in decided if p.result == 'win')
    losses = sum(1 for p in decided if p.result == 'loss')
    win_pct = round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0
    clv_values = [p.clv for p in decided if p.clv is not None]
    clv_positive = sum(1 for v in clv_values if v > 0)
    beat_close = round(clv_positive / len(clv_values) * 100, 1) if clv_values else 0
    total_pnl = sum((p.profit_units or 0) for p in decided)
    roi = round((sum((p.pnl or 0) for p in decided) / (len(decided) * 110)) * 100, 1) if decided else 0
    return {'wins': wins, 'losses': losses, 'win_pct': win_pct, 'beat_close': beat_close, 'pnl': total_pnl, 'roi': roi}


def _draw_stat_box(draw, x, y, w, h, label, value, color=WHITE):
    fonts = _fonts()
    draw.rounded_rectangle([x, y, x + w, y + h], radius=6, fill=CARD_BG, outline=BORDER)
    draw.text((x + w // 2, y + 12), label, fill=MUTED, font=fonts['stat_label'], anchor='mt')
    draw.text((x + w // 2, y + 30), value, fill=color, font=fonts['stat_val'], anchor='mt')


def _generate_og_signal(pick):
    """Generate the 1200x630 OG landscape card for a resolved signal."""
    is_win = pick.result == 'win'
    is_push = pick.result == 'push'
    is_revoked = pick.result == 'revoked'
    accent = GREEN if is_win else (GRAY if is_push or is_revoked else RED)

    img, draw = _new_card(accent)
    fonts = _fonts()

    _paste_wordmark(img, x=40, y=24, height=20)

    label = 'SIGNAL WITHDRAWN' if is_revoked else 'SIGNAL RESULT'
    label_color = GRAY if is_revoked else GREEN
    draw.text((W - 40, 24), label, fill=label_color, font=fonts['caption_bold'], anchor='rt')
    date_str = _date_label(pick)
    if date_str:
        draw.text((W - 40, 42), date_str, fill=MUTED, font=fonts['caption'], anchor='rt')

    y = 76
    matchup = f'{pick.away_team or ""} @ {pick.home_team or ""}'
    draw.text((40, y), matchup.upper(), fill=MUTED, font=fonts['caption'], anchor='lt')

    y += 28
    side = pick.side or ''
    draw.text((40, y), side, fill=WHITE, font=fonts['hero'])

    if not is_revoked:
        result_label = 'WIN' if is_win else ('PUSH' if is_push else 'LOSS')
        rl_color = GREEN if is_win else (GRAY if is_push else RED)
        units_val = pick.profit_units or 0
        units_str = f'{("+" if units_val >= 0 else "")}{units_val:.1f}u'
        badge_text = f'{result_label}  {units_str}'
        draw.text((W - 40, y + 8), badge_text, fill=rl_color, font=fonts['large'], anchor='rt')
    else:
        draw.text((W - 40, y + 8), 'WITHDRAWN', fill=GRAY, font=fonts['large'], anchor='rt')

    y += 56
    if pick.home_score is not None and pick.away_score is not None:
        score_text = f'{_abbr(pick.away_team)} {pick.away_score} \u00b7 {_abbr(pick.home_team)} {pick.home_score} \u00b7 Final'
        draw.text((40, y), score_text, fill=LIGHT_GRAY, font=fonts['medium'])
    elif is_revoked:
        draw.text((40, y), 'Withdrawn before tip. Capital preserved.', fill=GRAY, font=fonts['medium'])

    y += 48
    box_w, box_h = 180, 62
    gap = 16
    edge_str = f'+{pick.edge_pct:.1f}%' if pick.edge_pct else '--'
    clv_val = pick.clv
    clv_str = f'{("+" if clv_val > 0 else "")}{clv_val:.1f}' if clv_val is not None else '--'
    clv_color = GREEN if (clv_val or 0) > 0 else (RED if (clv_val or 0) < 0 else GRAY)
    line_str = _fmt_spread(pick.line)

    _draw_stat_box(draw, 40, y, box_w, box_h, 'EDGE', edge_str, GREEN)
    _draw_stat_box(draw, 40 + box_w + gap, y, box_w, box_h, 'CLV', clv_str, clv_color)
    _draw_stat_box(draw, 40 + (box_w + gap) * 2, y, box_w, box_h, 'LINE', line_str)

    stats = _season_stats(pick.sport)
    rec_x = W - 40 - 260
    rec_w, rec_h = 260, box_h * 2 + gap
    draw.rounded_rectangle([rec_x, y, rec_x + rec_w, y + rec_h], radius=6, fill=CARD_BG, outline=BORDER)
    draw.text((rec_x + 16, y + 14), 'RECORD', fill=MUTED, font=fonts['stat_label'])
    draw.text((rec_x + rec_w - 16, y + 12), f'{stats["wins"]}-{stats["losses"]}', fill=WHITE, font=fonts['medium'], anchor='rt')
    draw.text((rec_x + 16, y + 40), f'{stats["win_pct"]}% win rate', fill=LIGHT_GRAY, font=fonts['small'])
    draw.line([rec_x + 16, y + 62, rec_x + rec_w - 16, y + 62], fill=BORDER)
    draw.text((rec_x + 16, y + 72), 'BEAT THE CLOSE', fill=MUTED, font=fonts['stat_label'])
    draw.text((rec_x + rec_w - 16, y + 70), f'{stats["beat_close"]}%', fill=GREEN, font=fonts['medium'], anchor='rt')
    draw.text((rec_x + 16, y + 98), f'+{stats["pnl"]:.1f}u \u00b7 {stats["roi"]}% ROI', fill=LIGHT_GRAY, font=fonts['small'])

    draw.text((40, H - 40), 'One pick beats five.', fill=MUTED, font=fonts['small'])
    draw.text((W - 40, H - 40), 'SHARPPICKS.AI', fill=GRAY, font=fonts['caption_bold'], anchor='rt')

    return img


def _generate_og_season(sport=None):
    """Generate the 1200x630 OG card for season results."""
    img, draw = _new_card(GREEN)
    fonts = _fonts()
    _paste_wordmark(img, x=40, y=24, height=20)
    draw.text((W - 40, 24), 'SEASON RESULTS', fill=GREEN, font=fonts['caption_bold'], anchor='rt')

    stats = _season_stats(sport)
    y = 80
    pnl_sign = '+' if stats['pnl'] >= 0 else ''
    pnl_color = GREEN if stats['pnl'] >= 0 else RED
    draw.text((40, y), f'{pnl_sign}{stats["pnl"]:.1f}u', fill=pnl_color, font=fonts['hero'])
    draw.text((300, y + 10), f'{stats["roi"]}% ROI', fill=LIGHT_GRAY, font=fonts['large'])

    y += 70
    draw.text((40, y), f'Record: {stats["wins"]}-{stats["losses"]}', fill=WHITE, font=fonts['medium'])
    draw.text((40, y + 30), f'{stats["win_pct"]}% win rate', fill=LIGHT_GRAY, font=fonts['medium'])
    draw.text((40, y + 60), f'Beat the close: {stats["beat_close"]}%', fill=GREEN, font=fonts['medium'])

    y += 110
    draw.line([40, y, W - 40, y], fill=BORDER)
    y += 20
    draw.text((40, y), 'Selective by design. No edge, no pick.', fill=MUTED, font=fonts['small'])

    draw.text((40, H - 40), 'One pick beats five.', fill=MUTED, font=fonts['small'])
    draw.text((W - 40, H - 40), 'SHARPPICKS.AI', fill=GRAY, font=fonts['caption_bold'], anchor='rt')
    return img


def _og_html(title, description, image_url, canonical_url=None):
    t = escape(title)
    d = escape(description)
    i = escape(image_url)
    c = escape(canonical_url or BASE_URL)
    return f'''<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>{t}</title>
<meta name="description" content="{d}">
<meta property="og:type" content="website">
<meta property="og:url" content="{c}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:image" content="{i}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@SharpPicksApp">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{i}">
<meta http-equiv="refresh" content="0;url={c}">
</head>
<body><p>Redirecting to SharpPicks...</p></body>
</html>'''


@cards_bp.route('/og/signal/<signal_id>')
def og_signal(signal_id):
    pick = Pick.query.get(signal_id)
    if not pick:
        return '', 404

    img_url = f'{BASE_URL}/api/cards/og-image/signal/{signal_id}'
    canonical = f'{SHARE_URL}/signal/{signal_id}'

    result_label = (pick.result or 'pending').upper()
    units = ''
    if pick.profit_units is not None:
        s = '+' if pick.profit_units > 0 else ''
        units = f' {s}{pick.profit_units:.1f}u'

    if pick.result in ('win', 'loss', 'push'):
        title = f'SharpPicks: {pick.side or ""} \u00b7 {result_label}{units}'
    elif pick.result == 'revoked':
        title = f'SharpPicks: {pick.side or ""} \u00b7 Withdrawn'
    else:
        title = f'SharpPicks Signal: {pick.side or ""}'

    desc_parts = []
    if pick.edge_pct:
        desc_parts.append(f'Edge +{pick.edge_pct:.1f}%')
    if pick.clv is not None:
        clv_s = '+' if pick.clv > 0 else ''
        desc_parts.append(f'CLV {clv_s}{pick.clv:.1f}')
    if pick.away_score is not None and pick.home_score is not None:
        desc_parts.append(f'{_abbr(pick.away_team)} {pick.away_score}, {_abbr(pick.home_team)} {pick.home_score}')
    stats = _season_stats(pick.sport)
    desc_parts.append(f'Season: {stats["wins"]}-{stats["losses"]}, {stats["win_pct"]}%')

    return Response(
        _og_html(title, ' \u00b7 '.join(desc_parts), img_url, canonical),
        mimetype='text/html',
        headers={'Cache-Control': 'public, max-age=86400'},
    )


@cards_bp.route('/og/result/<signal_id>')
def og_result(signal_id):
    return og_signal(signal_id)


@cards_bp.route('/og-image/signal/<signal_id>')
def og_image_signal(signal_id):
    """Generate and return the 1200x630 OG PNG for a signal."""
    pick = Pick.query.get(signal_id)
    if not pick:
        return jsonify({'error': 'Not found'}), 404

    cache_dir = os.path.join(_BASE, '.og-cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f'signal-{signal_id}.png')

    is_resolved = pick.result in ('win', 'loss', 'push', 'revoked')
    if is_resolved and os.path.isfile(cache_path):
        with open(cache_path, 'rb') as f:
            return Response(f.read(), mimetype='image/png',
                            headers={'Cache-Control': 'public, max-age=31536000, immutable'})

    img = _generate_og_signal(pick)
    buf = _to_png(img)
    png_bytes = buf.read()

    if is_resolved:
        with open(cache_path, 'wb') as f:
            f.write(png_bytes)

    ttl = 'public, max-age=31536000, immutable' if is_resolved else 'public, max-age=300'
    return Response(png_bytes, mimetype='image/png', headers={'Cache-Control': ttl})


@cards_bp.route('/og/results')
def og_results():
    sport = request.args.get('sport')
    stats = _season_stats(sport)
    pnl_sign = '+' if stats['pnl'] >= 0 else ''
    title = f'SharpPicks: {stats["wins"]}-{stats["losses"]} \u00b7 {pnl_sign}{stats["pnl"]:.1f}u \u00b7 {stats["roi"]}% ROI'
    desc = f'{stats["win_pct"]}% win rate \u00b7 Beat the close {stats["beat_close"]}% \u00b7 Selective by design'
    img_url = f'{BASE_URL}/api/cards/og-image/results'
    canonical = f'{SHARE_URL}/results'
    return Response(
        _og_html(title, desc, img_url, canonical),
        mimetype='text/html',
        headers={'Cache-Control': 'public, max-age=3600'},
    )


@cards_bp.route('/og-image/results')
def og_image_results():
    sport = request.args.get('sport')
    img = _generate_og_season(sport)
    buf = _to_png(img)
    return Response(buf.read(), mimetype='image/png',
                    headers={'Cache-Control': 'public, max-age=3600'})
