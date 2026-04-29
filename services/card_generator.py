"""Playwright-based PNG renderer for share card HTML templates.

Render flow:
1. set_content with wait_until="domcontentloaded"
2. await document.fonts.ready (browser resolves all @font-face faces)
3. Capture which fonts actually loaded for diagnostics
4. 100ms layout settle for any reflow after font swap
5. Screenshot

Fonts are inlined as base64 data URIs in the templates, so there is no
network round-trip and document.fonts.ready resolves as soon as the
embedded faces are decoded. Total render time on a warm worker should
be well under 1s; cold workers add ~0.5s for browser launch.
"""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


async def _render(html_string: str):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})

        start = time.monotonic()
        await page.set_content(html_string, wait_until="domcontentloaded")
        content_loaded_at = time.monotonic() - start

        await page.evaluate("document.fonts.ready")
        fonts_ready_at = time.monotonic() - start

        loaded_fonts = await page.evaluate(
            """
            () => Array.from(document.fonts).map(f => ({
                family: f.family,
                weight: f.weight,
                status: f.status
            }))
            """
        )

        await page.wait_for_timeout(100)
        png_bytes = await page.screenshot(type="png")
        total = time.monotonic() - start

        await browser.close()

        loaded_count = sum(1 for f in loaded_fonts if f.get('status') == 'loaded')
        failed = [f for f in loaded_fonts if f.get('status') != 'loaded']

        logger.info(
            "Card generated: content=%.2fs fonts=%.2fs total=%.2fs loaded_count=%d",
            content_loaded_at, fonts_ready_at, total, loaded_count,
        )
        if failed:
            logger.warning("Card font load incomplete: %s", failed)

        diagnostics = {
            'content_loaded_at': content_loaded_at,
            'fonts_ready_at': fonts_ready_at,
            'total': total,
            'loaded_fonts': loaded_fonts,
            'failed_fonts': failed,
        }
        return png_bytes, diagnostics


async def _generate_card_png(html_string: str) -> bytes:
    png_bytes, _ = await _render(html_string)
    return png_bytes


async def _generate_card_png_with_diagnostics(html_string: str):
    """Async renderer that also returns a diagnostics dict.

    diagnostics keys: content_loaded_at, fonts_ready_at, total,
    loaded_fonts (list of {family, weight, status}), failed_fonts.
    """
    return await _render(html_string)


def _run_async(coro):
    """Run an awaitable from sync code, even if a loop is already running."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(lambda: asyncio.run(coro)).result(timeout=30)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def generate_card_png(html_string: str) -> bytes:
    """Synchronous wrapper for Playwright screenshot generation."""
    try:
        return _run_async(_generate_card_png(html_string))
    except Exception as e:
        logging.error(f"Card generation failed: {e}")
        raise


def generate_card_png_with_diagnostics(html_string: str):
    """Synchronous wrapper returning (png_bytes, diagnostics_dict).

    Used by the admin /api/admin/render-test-card endpoint to verify
    font health after each deploy.
    """
    try:
        return _run_async(_generate_card_png_with_diagnostics(html_string))
    except Exception as e:
        logging.error(f"Card generation (diagnostics) failed: {e}")
        raise
