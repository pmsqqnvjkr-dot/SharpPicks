"""Font data URI helpers for share card templates.

Card templates are rendered offline by Playwright via page.set_content().
Playwright's set_content uses about:blank as the base URL, so relative
URLs like /static/fonts/... won't resolve. To sidestep this entirely we
inline the woff2 files as base64 data URIs and inject them into the
template context. The helper is cached so the base64 work happens once
per process.
"""

import base64
import os
from functools import lru_cache

_FONT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'static',
    'fonts',
)

_FONT_FILES = {
    'ibm_plex_serif_400': 'IBMPlexSerif-Regular.woff2',
    'ibm_plex_serif_500': 'IBMPlexSerif-Medium.woff2',
    'ibm_plex_serif_700': 'IBMPlexSerif-Bold.woff2',
    'inter_400': 'Inter-Regular.woff2',
    'inter_500': 'Inter-Medium.woff2',
    'inter_600': 'Inter-SemiBold.woff2',
    'jetbrains_mono_400': 'JetBrainsMono-Regular.woff2',
    'jetbrains_mono_500': 'JetBrainsMono-Medium.woff2',
    'jetbrains_mono_600': 'JetBrainsMono-SemiBold.woff2',
}


@lru_cache(maxsize=16)
def _font_data_uri(filename: str) -> str:
    path = os.path.join(_FONT_DIR, filename)
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('ascii')
    return f"data:font/woff2;base64,{b64}"


@lru_cache(maxsize=1)
def get_card_fonts() -> dict:
    """Return dict of font keys to data: URIs for injection into card templates.

    Missing files degrade to an empty string so templates still render
    (the @font-face declaration becomes a no-op and the browser falls
    back to the local stack). Worst case is fallback fonts in the PNG —
    same outcome we already had before bundling.
    """
    out = {}
    for key, filename in _FONT_FILES.items():
        try:
            out[key] = _font_data_uri(filename)
        except FileNotFoundError:
            out[key] = ''
    return out
