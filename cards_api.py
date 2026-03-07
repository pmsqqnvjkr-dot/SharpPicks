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
BG = (13, 13, 13)
GREEN = (52, 211, 153)
RED = (204, 51, 51)
WHITE = (255, 255, 255)
GRAY = (102, 102, 102)
LIGHT_GRAY = (170, 170, 170)
BORDER = (34, 34, 34)
DIVIDER = (51, 51, 51)


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
    pick = Pick.query.get(signal_id)
    if not pick:
        return jsonify({'error': 'Not found'}), 404

    img, draw = _new_card()
    fonts = _fonts()
    _draw_wordmark(draw, 'SHARPPICKS RESULT')

    y = 80
    side = pick.side or ''
    is_win = pick.result == 'win'
    is_push = pick.result == 'push'
    icon = '\u2714' if is_win else ('\u2014' if is_push else '\u2718')
    icon_color = GREEN if is_win else (GRAY if is_push else RED)

    draw.text((32, y), side, fill=WHITE, font=fonts['hero'])
    side_bbox = fonts['hero'].getbbox(side)
    side_w = (side_bbox[2] - side_bbox[0]) if side_bbox else 300
    draw.text((42 + side_w, y + 6), f'  {icon}', fill=icon_color, font=fonts['large'])

    y += 60
    if pick.closing_spread is not None:
        draw.text((32, y), f'Closing Line: {_fmt_spread(pick.closing_spread)}', fill=WHITE, font=fonts['medium'])
        y += 30
    if pick.clv is not None:
        clv_color = GREEN if pick.clv > 0 else (RED if pick.clv < 0 else GRAY)
        clv_sign = '+' if pick.clv > 0 else ''
        draw.text((32, y), f'CLV: {clv_sign}{pick.clv:.1f}', fill=clv_color, font=fonts['medium'])
        y += 30

    y += 10
    if pick.edge_pct:
        draw.text((32, y), f'Model Edge: +{pick.edge_pct:.1f}%', fill=WHITE, font=fonts['medium'])
        y += 30

    result_text = pick.result.upper() if pick.result else 'PENDING'
    result_color = GREEN if is_win else (RED if pick.result == 'loss' else GRAY)
    draw.text((32, y), f'Result: {result_text}', fill=result_color, font=fonts['medium'])
    if pick.profit_units is not None:
        units_sign = '+' if pick.profit_units > 0 else ''
        units_text = f'{units_sign}{pick.profit_units:.1f}u'
        bbox = fonts['medium'].getbbox(units_text)
        tw = bbox[2] - bbox[0] if bbox else 80
        units_color = GREEN if pick.profit_units > 0 else (RED if pick.profit_units < 0 else GRAY)
        draw.text((W - 32 - tw, y), units_text, fill=units_color, font=fonts['medium'])

    _draw_footer(draw, _date_label(pick))
    return Response(_to_png(img).read(), mimetype='image/png',
                    headers={'Cache-Control': 'public, max-age=86400'})


@cards_bp.route('/user-results')
def user_results_card():
    from public_api import _get_sport_filter
    from sqlalchemy import func

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
    total_passes = pass_q.count()
    total_games = total_decided + total_passes
    selectivity = round(total_decided / total_games * 100, 1) if total_games > 0 else 0

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

    img, draw = _new_card()
    fonts = _fonts()
    _draw_wordmark(draw, 'SHARPPICKS USER RESULTS')

    y = 80
    pnl_color = GREEN if total_pnl >= 0 else RED
    pnl_sign = '+' if total_pnl >= 0 else ''
    draw.text((32, y), f'Profit: {pnl_sign}{total_pnl:.1f}u', fill=pnl_color, font=fonts['hero'])

    roi_text = f'ROI: {roi}%'
    bbox = fonts['large'].getbbox(roi_text)
    tw = bbox[2] - bbox[0] if bbox else 200
    draw.text((W - 32 - tw, y + 4), roi_text, fill=pnl_color, font=fonts['large'])

    y += 55
    draw.text((32, y), f'Record: {wins}\u2013{losses}', fill=WHITE, font=fonts['medium'])

    y += 50
    draw.line([(32, y), (W - 32, y)], fill=DIVIDER, width=1)

    y += 25
    draw.text((32, y), f'Discipline Score: {grade}', fill=WHITE, font=fonts['medium'])
    y += 30
    draw.text((32, y), f'Selectivity: {selectivity}%', fill=WHITE, font=fonts['medium'])

    _draw_footer(draw, None)
    return Response(_to_png(img).read(), mimetype='image/png',
                    headers={'Cache-Control': 'public, max-age=300'})


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
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    et = ZoneInfo('America/New_York')
    now = datetime.now(et)

    end = now - timedelta(days=now.weekday() + 1)
    start = end - timedelta(days=6)
    start_str = start.strftime('%Y-%m-%d')
    end_str = end.strftime('%Y-%m-%d')

    sport = request.args.get('sport')
    pick_q = Pick.query.filter(Pick.game_date >= start_str, Pick.game_date <= end_str)
    pass_q = Pass.query.filter(Pass.date >= start_str, Pass.date <= end_str)
    if sport:
        pick_q = pick_q.filter_by(sport=sport)
        pass_q = pass_q.filter_by(sport=sport)

    picks = pick_q.all()
    decided = [p for p in picks if p.result in ('win', 'loss', 'push')]
    wins = sum(1 for p in decided if p.result == 'win')
    losses = sum(1 for p in decided if p.result == 'loss')
    total_units = sum((p.profit_units or 0) for p in decided)
    total_decided = len(decided)
    roi = round((sum((p.pnl or 0) for p in decided) / (total_decided * 110)) * 100, 1) if total_decided > 0 else 0
    avg_edge = round(sum((p.edge_pct or 0) for p in picks) / len(picks), 1) if picks else 0
    days_passed = pass_q.count()

    all_picks = Pick.query
    all_passes = Pass.query
    if sport:
        all_picks = all_picks.filter_by(sport=sport)
        all_passes = all_passes.filter_by(sport=sport)
    season_decided = all_picks.filter(Pick.result.in_(['win', 'loss', 'push'])).all()
    season_wins = sum(1 for p in season_decided if p.result == 'win')
    season_losses = sum(1 for p in season_decided if p.result == 'loss')
    clv_pos = sum(1 for p in season_decided if (p.clv or 0) > 0)
    clv_pct = round(clv_pos / len(season_decided) * 100, 1) if season_decided else 0

    img, draw = _new_card()
    fonts = _fonts()
    _draw_wordmark(draw, 'SHARPPICKS WEEKLY REPORT')

    y = 56
    range_label = f'{start.strftime("%b %-d")}\u2013{end.strftime("%b %-d, %Y")}'
    draw.text((32, y), range_label, fill=LIGHT_GRAY, font=fonts['small'])

    y = 100
    draw.text((32, y), f'Record: {wins}\u2013{losses}', fill=WHITE, font=fonts['medium'])
    roi_text = f'ROI: {roi:+.1f}%'
    bbox = fonts['medium'].getbbox(roi_text)
    tw = bbox[2] - bbox[0] if bbox else 120
    draw.text((W - 32 - tw, y), roi_text, fill=GREEN if roi >= 0 else RED, font=fonts['medium'])

    y += 32
    units_sign = '+' if total_units >= 0 else ''
    draw.text((32, y), f'Units: {units_sign}{total_units:.1f}u', fill=WHITE, font=fonts['medium'])
    edge_text = f'Avg Edge: +{avg_edge:.1f}%'
    bbox2 = fonts['medium'].getbbox(edge_text)
    tw2 = bbox2[2] - bbox2[0] if bbox2 else 160
    draw.text((W - 32 - tw2, y), edge_text, fill=WHITE, font=fonts['medium'])

    y += 50
    draw.line([(32, y), (W - 32, y)], fill=DIVIDER, width=1)

    y += 25
    draw.text((32, y), f'Season: {season_wins}\u2013{season_losses}', fill=WHITE, font=fonts['medium'])
    clv_text = f'CLV+: {clv_pct}%'
    bbox3 = fonts['medium'].getbbox(clv_text)
    tw3 = bbox3[2] - bbox3[0] if bbox3 else 100
    draw.text((W - 32 - tw3, y), clv_text, fill=WHITE, font=fonts['medium'])

    y += 32
    draw.text((32, y), f'Days passed: {days_passed}', fill=WHITE, font=fonts['medium'])

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
            f'SharpPicks Result: {pick.side or ""} — {result_label}{units}',
            ' | '.join(filter(None, [clv, edge])) or 'Signal outcome',
            f'{BASE_URL}/api/cards/result/{signal_id}',
        ),
        mimetype='text/html',
        headers={'Cache-Control': 'public, max-age=86400'},
    )
