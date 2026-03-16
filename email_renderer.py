"""
React Email renderer — calls the Node.js render script via subprocess.
Returns HTML strings ready for Resend.
"""

import json
import logging
import os
import subprocess
import shutil
from typing import Dict, Optional

_EMAILS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'emails')
_NPX = shutil.which('npx') or 'npx'

_HTML_CACHE: Dict[str, str] = {}


def render_template(template_name: str, props: Optional[dict] = None) -> str:
    """Render a React Email template to an HTML string.

    Args:
        template_name: One of the template names (signal, result, weekly-summary,
                       no-signal, trial-expiring, welcome, verification,
                       password-reset, cancellation, payment-failed,
                       founding-member, trial-started, trial-expired).
        props: Dict of props passed to the React component as JSON via stdin.

    Returns:
        Rendered HTML string.

    Raises:
        RuntimeError: If the render subprocess fails.
    """
    props = props or {}
    cache_key = f"{template_name}:{json.dumps(props, sort_keys=True)}"
    if cache_key in _HTML_CACHE:
        return _HTML_CACHE[cache_key]

    stdin_data = json.dumps(props)

    try:
        result = subprocess.run(
            [_NPX, 'tsx', 'render.ts', template_name],
            input=stdin_data,
            capture_output=True,
            text=True,
            cwd=_EMAILS_DIR,
            timeout=20,
        )
    except FileNotFoundError:
        logging.error("npx not found — cannot render React Email template. "
                      "Ensure Node.js is installed and npx is on PATH.")
        raise RuntimeError("npx not found — Node.js required for email rendering")
    except subprocess.TimeoutExpired:
        logging.error(f"Email render timed out for template '{template_name}'")
        raise RuntimeError(f"Email render timed out for template '{template_name}'")

    if result.returncode != 0:
        logging.error(f"Email render failed for '{template_name}': {result.stderr}")
        raise RuntimeError(f"Email render failed: {result.stderr[:500]}")

    html = result.stdout
    if not html.strip():
        raise RuntimeError(f"Email render returned empty HTML for '{template_name}'")

    if len(_HTML_CACHE) < 200:
        _HTML_CACHE[cache_key] = html

    return html
