import base64
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, Response, request, render_template, jsonify

from models import db, Pick, Pass
from admin_api import require_superuser

weekly_card_bp = Blueprint('weekly_card', __name__)
ET = ZoneInfo('America/New_York')

LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'brand', 'images', 'crest.png')

_logo_b64_cache = None

def _get_logo_base64():
    global _logo_b64_cache
    if _logo_b64_cache:
        return _logo_b64_cache
    try:
        with open(LOGO_PATH, 'rb') as f:
            _logo_b64_cache = base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        logging.warning(f"Logo not found at {LOGO_PATH}")
        _logo_b64_cache = ""
    return _logo_b64_cache


def _compute_weekly_data(week_start_str=None, week_end_str=None):
    now_et = datetime.now(ET)

    if week_start_str and week_end_str:
        ws = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        we = datetime.strptime(week_end_str, '%Y-%m-%d').date()
    else:
        today = now_et.date()
        days_since_monday = today.weekday()
        ws = today - timedelta(days=days_since_monday + 7)
        we = ws + timedelta(days=6)

    ws_str = ws.strftime('%Y-%m-%d')
    we_str = we.strftime('%Y-%m-%d')

    weekly_picks = Pick.query.filter(
        Pick.game_date >= ws_str,
        Pick.game_date <= we_str,
        Pick.result.in_(['win', 'loss', 'push']),
    ).all()

    weekly_wins = sum(1 for p in weekly_picks if p.result == 'win')
    weekly_losses = sum(1 for p in weekly_picks if p.result == 'loss')

    weekly_pnl_units = sum(
        (p.profit_units if p.profit_units is not None else (p.pnl / 100 if p.pnl else 0))
        for p in weekly_picks
    )
    weekly_decided = weekly_wins + weekly_losses
    weekly_roi = round(
        (sum(p.pnl or 0 for p in weekly_picks) / (weekly_decided * 110)) * 100, 1
    ) if weekly_decided > 0 else 0.0

    weekly_edges = [p.edge_pct for p in weekly_picks if p.edge_pct is not None]
    weekly_avg_edge = round(sum(weekly_edges) / len(weekly_edges), 1) if weekly_edges else 0.0

    all_picks = Pick.query.filter(Pick.result.in_(['win', 'loss', 'push'])).all()
    season_wins = sum(1 for p in all_picks if p.result == 'win')
    season_losses = sum(1 for p in all_picks if p.result == 'loss')
    season_decided = season_wins + season_losses
    season_win_pct = round(season_wins / season_decided * 100, 1) if season_decided > 0 else 0.0

    clv_values = [p.clv for p in all_picks if p.clv is not None]
    clv_positive = sum(1 for v in clv_values if v > 0)
    season_clv = round(clv_positive / len(clv_values) * 100, 1) if clv_values else 0.0

    total_passes = Pass.query.count()
    total_picks = Pick.query.count()

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    week_start_fmt = f"{months[ws.month - 1]} {ws.day}"
    week_end_fmt = f"{months[we.month - 1]} {we.day}, {we.year}"

    units_val = round(weekly_pnl_units, 1)
    if units_val < 0:
        units_fmt = f"\u2212{abs(units_val)}u"
    elif units_val > 0:
        units_fmt = f"+{units_val}u"
    else:
        units_fmt = "0.0u"

    if weekly_roi < 0:
        roi_fmt = f"\u2212{abs(weekly_roi)}%"
    elif weekly_roi > 0:
        roi_fmt = f"+{weekly_roi}%"
    else:
        roi_fmt = "0.0%"

    return {
        'week_start': week_start_fmt,
        'week_end': week_end_fmt,
        'weekly_wins': weekly_wins,
        'weekly_losses': weekly_losses,
        'weekly_units': units_val,
        'weekly_units_fmt': units_fmt,
        'weekly_roi': weekly_roi,
        'weekly_roi_fmt': roi_fmt,
        'weekly_avg_edge': weekly_avg_edge,
        'season_wins': season_wins,
        'season_losses': season_losses,
        'season_win_pct': season_win_pct,
        'season_clv': season_clv,
        'season_days_passed': total_passes,
        'season_total_picks': total_picks,
        'logo_base64': _get_logo_base64(),
    }


@weekly_card_bp.route('/api/weekly-card')
def weekly_card():
    admin, err_code = require_superuser()
    if not admin:
        return jsonify({'error': 'Login required' if err_code == 401 else 'Unauthorized'}), err_code

    week_start = request.args.get('week_start')
    week_end = request.args.get('week_end')

    try:
        data = _compute_weekly_data(week_start, week_end)
    except Exception as e:
        logging.error(f"Weekly card data error: {e}")
        return jsonify({'error': 'Failed to compute card data'}), 500

    html_string = render_template('recap_card.html', **data)

    try:
        from services.card_generator import generate_card_png
        png_bytes = generate_card_png(html_string)
    except Exception as e:
        logging.error(f"Weekly card screenshot error: {e}")
        return jsonify({'error': f'Screenshot failed: {str(e)}'}), 500

    return Response(
        png_bytes,
        mimetype='image/png',
        headers={
            'Cache-Control': 'public, max-age=300',
            'Content-Disposition': 'inline; filename="sharppicks-weekly-recap.png"',
        },
    )
