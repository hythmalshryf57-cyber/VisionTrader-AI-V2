"""
tv_screenshot.py — TradingView Automated Screenshot Service
Uses Playwright to open TradingView, wait for chart to load, and capture a screenshot.
"""

import asyncio
import logging
import base64
from typing import Optional

logger = logging.getLogger(__name__)

# TradingView timeframe mapping (user-friendly → TV interval code)
TF_MAP = {
    "M1": "1",
    "M5": "5",
    "M15": "15",
    "M30": "30",
    "H1": "60",
    "H4": "240",
    "D1": "D",
    "W1": "W",
}

# Symbol normalization for TradingView URL
SYMBOL_MAP = {
    "XAUUSD": "OANDA:XAUUSD",
    "EURUSD": "FX:EURUSD",
    "GBPUSD": "FX:GBPUSD",
    "USDJPY": "FX:USDJPY",
    "USDCHF": "FX:USDCHF",
    "AUDUSD": "FX:AUDUSD",
    "USDCAD": "FX:USDCAD",
    "NZDUSD": "FX:NZDUSD",
    "BTCUSDT": "BINANCE:BTCUSDT",
    "ETHUSDT": "BINANCE:ETHUSDT",
    "SOLUSDT": "BINANCE:SOLUSDT",
    "USOIL": "TVC:USOIL",
    "NAS100": "NASDAQ:NDX",
    "US30": "DJ:DJI",
    "US500": "SP:SPX",
    "XAGUSD": "OANDA:XAGUSD",
    "GBPJPY": "FX:GBPJPY",
    "EURJPY": "FX:EURJPY",
}


async def capture_tradingview_chart(
    symbol: str,
    timeframe: str = "H1",
    headless: bool = True,
    timeout_ms: int = 45000,
) -> Optional[bytes]:
    """
    Opens TradingView in a browser, waits for the chart to load, and returns a PNG screenshot as bytes.
    Returns None if capture fails.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return None

    tv_symbol = SYMBOL_MAP.get(symbol.upper(), symbol.upper())
    interval = TF_MAP.get(timeframe.upper(), "60")
    url = f"https://www.tradingview.com/chart/?symbol={tv_symbol}&interval={interval}"

    logger.info(f"Capturing TradingView chart: {symbol} {timeframe} → {url}")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--window-size=1440,900",
                    "--disable-blink-features=AutomationControlled",
                ]
            )
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                # Real browser user-agent to avoid bot detection
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                java_script_enabled=True,
            )
            page = await context.new_page()

            # Only block trackers/analytics — DO NOT block images (chart needs them)
            await page.route("**/ads/**", lambda route: route.abort())
            await page.route("**/analytics/**", lambda route: route.abort())
            await page.route("**/gtm/**", lambda route: route.abort())
            await page.route("**/doubleclick.net/**", lambda route: route.abort())

            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            # Close any popups (cookie banners, login prompts) early
            for selector in [
                "button[id*='cookie']",
                "button[data-role='accept-all']",
                ".js-dialog-close",
                "[aria-label='Close']",
                ".tv-dialog__close",
                "button.close-B02UUUN3",
                "[data-dialog-name='gopro'] button",
            ]:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=800):
                        await btn.click()
                        await asyncio.sleep(0.3)
                except Exception:
                    pass

            # Wait for the chart canvas to appear
            try:
                await page.wait_for_selector("canvas", timeout=18000)
                # Give the chart extra time to render price data and candles
                await asyncio.sleep(5)
            except Exception:
                # Canvas not found — still try to take screenshot
                await asyncio.sleep(6)

            # Dismiss any late-appearing popups
            for selector in [".js-dialog-close", "[aria-label='Close']", ".tv-dialog__close"]:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=500):
                        await btn.click()
                except Exception:
                    pass

            # Take screenshot of the chart area
            screenshot_bytes = await page.screenshot(
                type="png",
                full_page=False,
                clip={"x": 0, "y": 0, "width": 1440, "height": 900},
            )

            await browser.close()
            logger.info(f"Chart screenshot captured successfully: {len(screenshot_bytes)} bytes")
            return screenshot_bytes

    except Exception as exc:
        logger.error(f"TradingView screenshot failed: {exc}")
        return None


def screenshot_to_base64(screenshot_bytes: bytes) -> str:
    """Convert screenshot bytes to base64 string for Gemini Vision API."""
    return base64.b64encode(screenshot_bytes).decode("utf-8")


async def get_chart_as_base64(symbol: str, timeframe: str = "H1") -> Optional[str]:
    """High-level helper: capture chart and return as base64 string."""
    img_bytes = await capture_tradingview_chart(symbol, timeframe)
    if img_bytes:
        return screenshot_to_base64(img_bytes)
    return None
