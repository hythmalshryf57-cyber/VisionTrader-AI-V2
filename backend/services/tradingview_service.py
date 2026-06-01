import requests
import base64
import urllib.parse
from typing import Optional, Dict
from config import settings


class TradingViewService:
    SCREENSHOT_PROVIDER = "https://image.thum.io/get/width/1200/crop/700/"
    GEMINI_ENDPOINT = getattr(settings, 'GEMINI_API_URL', 'https://api.gemini.com/v1/vision/analyze')

    def fetch_chart_snapshot(self, url: str) -> bytes:
        if not url:
            raise ValueError("TradingView URL is required")
        snapshot_url = self.SCREENSHOT_PROVIDER + url
        response = requests.get(snapshot_url, timeout=25)
        response.raise_for_status()
        return response.content

    def analyze_with_gemini(self, image_bytes: bytes) -> Dict:
        if not getattr(settings, 'GEMINI_API_KEY', None):
            return {
                "analysis": {
                    "recommendation": "محايد",
                    "confidence": 40,
                    "note": "Gemini API key غير مضبوطة. تم إرجاع تحليل احتياطي." 
                },
                "source": "fallback"
            }
        payload = {
            "image_base64": base64.b64encode(image_bytes).decode('utf-8'),
            "instructions": "حلل لقطة شاشة TradingView وقدم توصية سوقية، مستويات دعم ومقاومة، واتجاه عام."
        }
        # Use API key as query parameter to match authentication method requested
        url = f"{self.GEMINI_ENDPOINT}?key={settings.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return {"analysis": response.json(), "source": "gemini"}
        except Exception as e:
            return {
                "analysis": {
                    "recommendation": "محايد",
                    "confidence": 40,
                    "note": f"فشل الاتصال بـ Gemini: {e}. تم استخدام تحليل احتياطي."
                },
                "source": "fallback"
            }

    def fetch_and_analyze(self, url: str) -> Dict:
        image_bytes = self.fetch_chart_snapshot(url)
        return self.analyze_with_gemini(image_bytes)

    def detect_chart_details(self, image_bytes: bytes) -> Dict:
        if not getattr(settings, 'GEMINI_API_KEY', None):
            return {
                "pair": "UNKNOWN",
                "timeframe": "UNKNOWN",
                "confidence": 0,
                "note": "Gemini API key غير مضبوطة."
            }

        payload = {
            "image_base64": base64.b64encode(image_bytes).decode('utf-8'),
            "instructions": "حلل هذه الصورة للشارت واستخرج: الزوج التجاري (مثل XAU/USD, EUR/USD), الفريم الزمني (مثل 1H, 4H, Daily). أعد الإجابة بتنسيق JSON فقط."
        }
        url = f"{self.GEMINI_ENDPOINT}?key={settings.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            # Assume result has pair, timeframe, confidence
            return {
                "pair": result.get("pair", "UNKNOWN"),
                "timeframe": result.get("timeframe", "UNKNOWN"),
                "confidence": result.get("confidence", 50)
            }
        except Exception as e:
            return {
                "pair": "UNKNOWN",
                "timeframe": "UNKNOWN",
                "confidence": 0,
                "note": f"فشل التعرف: {e}"
            }

    def get_price_from_twelvedata(self, symbol: str) -> Optional[float]:
        """Fetch the latest price from Twelve Data for FX, gold, indices, and crypto."""
        if not symbol:
            return None
        api_key = getattr(settings, 'TWELVEDATA_API_KEY', None)
        if not api_key:
            return None

        request_symbol = symbol.replace(" ", "").replace("/", "").upper()
        symbol_map = {
            "US30": "DJI",
            "US100": "NDX",
            "SPX500": "SPX",
            "UK100": "FTSE",
            "GER30": "DAX",
            "JP225": "NIKKEI",
            "XAUUSD": "XAUUSD",
            "XAGUSD": "XAGUSD",
        }
        request_symbol = symbol_map.get(request_symbol, request_symbol)

        url = (
            f"https://api.twelvedata.com/price?symbol="
            f"{urllib.parse.quote(request_symbol, safe='')}"
            f"&apikey={urllib.parse.quote(api_key, safe='')}"
        )

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and data.get("status") == "error":
                return None
            price = data.get("price") or data.get("close")
            if price is not None:
                return float(price)
        except Exception:
            pass
        return None

    def get_price_from_binance(self, symbol: str) -> Optional[float]:
        """Fetch live crypto price from Binance when Twelve Data and Yahoo fail."""
        if not symbol:
            return None
        s = symbol.replace(" ", "").replace("/", "").upper()
        if s.endswith("USD") and not s.endswith("USDT"):
            s = s[:-3] + "USDT"

        # Binance only supports crypto trading pairs, so preserve only likely crypto symbols.
        if not any(token in s for token in ("USDT", "BUSD", "BTC", "ETH", "BNB", "SOL", "ADA", "XRP", "DOGE", "MATIC", "LTC", "LINK", "DOT", "ATOM", "AVAX", "TRX", "BCH", "XLM")):
            return None

        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={urllib.parse.quote(s, safe='')}"
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            data = response.json()
            price = data.get("price")
            if price is not None:
                return float(price)
        except Exception:
            pass
        return None

    def get_symbol_price(self, symbol: str) -> Optional[float]:
        """Fetch a near-real-time price for common FX/gold/indices symbols.

        This method first normalizes common symbol forms, then attempts to
        fetch a price using Twelve Data first, then Yahoo Finance, and finally
        Binance for crypto pairs only. Returns None when price cannot be obtained.
        """
        if not symbol:
            return None
        s = symbol.replace(" ", "").replace("/", "").upper()
        # Preferred mapping to common tickers (Yahoo / yfinance)
        mapping = {
            "XAUUSD": "GC=F",       # Gold futures
            "EURUSD": "EURUSD=X",
            "GBPUSD": "GBPUSD=X",
            "USDJPY": "USDJPY=X",
            "USDCHF": "USDCHF=X",
            "AUDUSD": "AUDUSD=X",
            "NZDUSD": "NZDUSD=X",
            "USDCAD": "USDCAD=X",
            "EURGBP": "EURGBP=X",
            "XAGUSD": "SI=F",      # Silver futures
            "US30": "^DJI",
            "US100": "^NDX",
            "SPX500": "^GSPC",
            "BTCUSD": "BTC-USD",
        }

        ticker = mapping.get(s, s)

        # First choice: Twelve Data API as the preferred live price data source.
        try:
            price = self.get_price_from_twelvedata(s)
            if price is not None:
                return price
        except Exception:
            pass

        # Then try yfinance first (if installed) for a robust client.
        try:
            import yfinance as yf
            try:
                t = yf.Ticker(ticker)
                # Try fast info access
                info = None
                try:
                    info = t.fast_info if hasattr(t, 'fast_info') else getattr(t, 'info', None)
                except Exception:
                    info = getattr(t, 'info', None)

                if info:
                    # fast_info may contain 'last_price' or 'lastPrice'
                    for k in ("last_price", "lastPrice", "regularMarketPrice", "previousClose", "previous_close"):
                        if isinstance(info.get(k, None), (int, float)):
                            return float(info.get(k))

                # If info not useful, try recent history
                hist = t.history(period="1d", interval="1m")
                if hist is not None and not hist.empty:
                    last = hist['Close'].dropna().iloc[-1]
                    return float(last)
            except Exception:
                pass
        except Exception:
            pass

        # REST fallback to Yahoo Finance public API
        try:
            q = urllib.parse.quote(ticker, safe='')
            url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={q}"
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("quoteResponse", {}).get("result", [])
            if results:
                price = results[0].get("regularMarketPrice") or results[0].get("bid") or results[0].get("ask") or results[0].get("lastPrice")
                if price is not None:
                    return float(price)
        except Exception:
            pass

        # For crypto symbols only, try Binance as final fallback.
        try:
            price = self.get_price_from_binance(s)
            if price is not None:
                return price
        except Exception:
            pass

        # Final fallback: call TradingView webhook if configured (expects JSON {"symbol":..., "price":...})
        try:
            webhook = getattr(settings, 'TRADINGVIEW_WEBHOOK_URL', None)
            if webhook:
                resp = requests.post(webhook, json={"symbol": s}, timeout=6)
                resp.raise_for_status()
                body = resp.json()
                # Accept body.price or body.get('price') or nested
                if isinstance(body, dict):
                    p = body.get('price') or body.get('last') or body.get('close')
                    if p is not None:
                        return float(p)
        except Exception:
            pass

        return None


# Module-level singleton for convenience
tradingview_service = TradingViewService()
