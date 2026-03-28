import base64
import logging
import os

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(SCRIPT_DIR, 'brand', 'images', 'crest.png')
WORDMARK_PATH = os.path.join(SCRIPT_DIR, 'public', 'wordmark-white.png')

_logo_b64_cache = None
_wordmark_b64_cache = None


def get_logo_base64():
    global _logo_b64_cache
    if _logo_b64_cache is not None:
        return _logo_b64_cache
    try:
        with open(LOGO_PATH, 'rb') as f:
            _logo_b64_cache = base64.b64encode(f.read()).decode('utf-8')
    except FileNotFoundError:
        logging.error(f"Logo not found at {LOGO_PATH} — emails will render without logo")
        _logo_b64_cache = ""
    return _logo_b64_cache


def get_wordmark_base64():
    global _wordmark_b64_cache
    if _wordmark_b64_cache is not None:
        return _wordmark_b64_cache
    try:
        with open(WORDMARK_PATH, 'rb') as f:
            _wordmark_b64_cache = base64.b64encode(f.read()).decode('utf-8')
    except FileNotFoundError:
        logging.error(f"Wordmark not found at {WORDMARK_PATH}")
        _wordmark_b64_cache = ""
    return _wordmark_b64_cache


def get_edge_strength(edge_pct):
    if edge_pct >= 7.5:
        return {"bars": 3, "label": "Strong"}
    elif edge_pct >= 5.0:
        return {"bars": 2, "label": "Moderate"}
    else:
        return {"bars": 1, "label": "Standard"}


def result_color(result):
    if result in ('W', 'win', 'WIN'):
        return '#5A9E72'
    elif result in ('L', 'loss', 'LOSS'):
        return '#9E7A7C'
    return '#666666'


def fmt_line(val):
    if val is None:
        return '--'
    n = float(val)
    if n == int(n):
        return f"+{int(n)}" if n > 0 else str(int(n))
    return f"+{n:.1f}" if n > 0 else f"{n:.1f}"


def fmt_signed(val, suffix=''):
    if val is None:
        return '--'
    n = float(val)
    if n > 0:
        return f"+{n:.1f}{suffix}"
    return f"{n:.1f}{suffix}"
