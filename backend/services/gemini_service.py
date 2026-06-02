from .tradingview_service import TradingViewService

_tv = TradingViewService()

def analyze_image_with_fallback(image_bytes: bytes) -> dict:
    """Analyze an image using Gemini, falling back to DeepSeek/OpenRouter if needed.
    Returns a dict with keys: 'analysis' and 'source' or a fallback note.
    """
    return _tv.analyze_with_gemini(image_bytes)


def detect_chart_details_with_fallback(image_bytes: bytes) -> dict:
    """Detect chart pair/timeframe using the same provider chain."""
    return _tv.detect_chart_details(image_bytes)
