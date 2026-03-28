"""
Share card image generation — PIL-based, no browser dependencies.
Produces 1200x675 PNG cards for Twitter/X summary_large_image.
Includes OG meta endpoints for crawler/bot previews.
"""

from flask import Blueprint, Response, jsonify, request
from models import db, Pick, Pass, ModelRun
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from functools import lru_cache
import json, os
from markupsafe import escape

cards_bp = Blueprint('cards', __name__)

W, H = 1200, 675
BG = (10, 22, 40)
GREEN = (90, 158, 114)
RED = (196, 104, 107)
WHITE = (232, 236, 241)
GRAY = (106, 122, 141)
LIGHT_GRAY = (170, 170, 170)
BORDER = (30, 48, 80)
DIVIDER = (30, 48, 80)


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
        'caption': load(mono or sans, 12),
    }


def _new_card():
    img = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W - 1, H - 1], outline=BORDER)
    draw.line([3, 0, 3, H], fill=GREEN, width=3)
    return img, draw


def _draw_wordmark(draw, text='SHARPPICKS SIGNAL'):
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
    _draw_wordmark(draw, 'SHARPPICKS SIGNAL')

    y = 80
    side = pick.side or ''
    draw.text((32, y), side, fill=WHITE, font=fonts['hero'])

    edge_text = f'Edge: +{pick.edge_pct:.1f}%' if pick.edge_pct else ''
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
    draw.text((32, y), '\u2714  Qualified Signal', fill=GREEN, font=fonts['small'])
    y += 28
    draw.text((32, y), 'Selective by design', fill=GRAY, font=fonts['small'])

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
    _draw_wordmark(draw, 'SHARPPICKS MARKET REPORT')

    y = 80
    draw.text((32, y), f'{games_analyzed} games analyzed', fill=WHITE, font=fonts['medium'])
    y += 32
    draw.text((32, y), f'{edges_detected} edges detected', fill=WHITE, font=fonts['medium'])
    y += 32
    draw.text((32, y), f'{qualified_signals} signal{"s" if qualified_signals != 1 else ""}', fill=WHITE, font=fonts['medium'])

    y += 60
    tagline = 'Passing is a position.' if qualified_signals == 0 else 'Selective by design.'
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
    _draw_wordmark(draw, 'SHARPPICKS RESULT')
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
    _draw_wordmark(draw, 'SHARPPICKS RESULTS')
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
    _draw_wordmark(draw, 'SHARPPICKS WEEKLY REPORT')
    draw.text((32, 80), 'Weekly report', fill=WHITE, font=fonts['hero'])
    draw.text((32, 135), 'Card generation unavailable', fill=GRAY, font=fonts['medium'])
    _draw_footer(draw, None)
    return Response(_to_png(img).read(), mimetype='image/png',
                    headers={'Cache-Control': 'public, max-age=300'})


# ── Open Graph meta endpoints for crawler/bot previews ──

BASE_URL = os.environ.get('APP_BASE_URL', 'https://app.sharppicks.ai')

def _og_html(title, description, image_url):
    t = escape(title)
    d = escape(description)
    i = escape(image_url)
    return f'''<!DOCTYPE html>
<html><head>
<meta property="og:title" content="{t}" />
<meta property="og:description" content="{d}" />
<meta property="og:image" content="{i}" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="675" />
<meta property="og:type" content="website" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:site" content="@sharppicksai" />
<meta name="twitter:title" content="{t}" />
<meta name="twitter:description" content="{d}" />
<meta name="twitter:image" content="{i}" />
<meta http-equiv="refresh" content="0;url={BASE_URL}" />
<title>{t}</title>
</head><body></body></html>'''


@cards_bp.route('/og/signal/<signal_id>')
def og_signal(signal_id):
    pick = Pick.query.get(signal_id)
    if not pick:
        return '', 404

    model_prob = pick.cover_prob or pick.model_confidence
    market_prob = pick.implied_prob
    edge = f'+{pick.edge_pct:.1f}%' if pick.edge_pct else ''
    desc_parts = []
    if edge:
        desc_parts.append(f'Edge: {edge}')
    if model_prob and market_prob:
        desc_parts.append(f'Model: {model_prob*100:.1f}% vs Market: {market_prob*100:.1f}%')

    return Response(
        _og_html(
            f'SharpPicks Signal: {pick.side or ""}',
            ' | '.join(desc_parts) if desc_parts else 'Qualified Signal',
            f'{BASE_URL}/api/cards/signal/{signal_id}',
        ),
        mimetype='text/html',
        headers={'Cache-Control': 'public, max-age=3600'},
    )


@cards_bp.route('/og/result/<signal_id>')
def og_result(signal_id):
    pick = Pick.query.get(signal_id)
    if not pick:
        return '', 404

    result_label = (pick.result or 'pending').upper()
    units = ''
    if pick.profit_units is not None:
        s = '+' if pick.profit_units > 0 else ''
        units = f' {s}{pick.profit_units:.1f}u'
    clv = ''
    if pick.clv is not None:
        s = '+' if pick.clv > 0 else ''
        clv = f'CLV: {s}{pick.clv:.1f}'
    edge = f'Edge: +{pick.edge_pct:.1f}%' if pick.edge_pct else ''

    return Response(
        _og_html(
            f'SharpPicks Result: {pick.side or ""} · {result_label}{units}',
            ' | '.join(filter(None, [clv, edge])) or 'Signal outcome',
            f'{BASE_URL}/api/cards/result/{signal_id}',
        ),
        mimetype='text/html',
        headers={'Cache-Control': 'public, max-age=86400'},
    )
