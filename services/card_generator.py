import asyncio
import logging

async def _generate_card_png(html_string: str) -> bytes:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})
        await page.set_content(html_string, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        png_bytes = await page.screenshot(type="png")
        await browser.close()
        return png_bytes


def generate_card_png(html_string: str) -> bytes:
    """Synchronous wrapper for Playwright screenshot generation."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(
                    lambda: asyncio.run(_generate_card_png(html_string))
                ).result(timeout=30)
        else:
            return loop.run_until_complete(_generate_card_png(html_string))
    except RuntimeError:
        return asyncio.run(_generate_card_png(html_string))
    except Exception as e:
        logging.error(f"Card generation failed: {e}")
        raise
