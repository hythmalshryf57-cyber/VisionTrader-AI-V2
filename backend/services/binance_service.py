import requests
from datetime import datetime
from typing import Dict, List, Optional
from .websocket_service import BinanceWebSocketService


class BinanceService:
    BASE_URL = "https://fapi.binance.com"

    def __init__(self, ws_service: Optional[BinanceWebSocketService] = None):
        self.ws_service = ws_service

    def _request(self, path: str, params: dict = None) -> dict:
        url = f"{self.BASE_URL}{path}"
        try:
            response = requests.get(url, params=params or {}, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "url": url, "params": params}

    def get_open_interest(self, symbol: str) -> float:
        if self.ws_service:
            live_data = self.ws_service.get_live_data(symbol)
            oi = live_data.get('open_interest')
            if oi is not None:
                return oi
        # Fallback to REST
        result = self._request("/fapi/v1/openInterest", {"symbol": symbol})
        return float(result.get("openInterest", 0.0)) if isinstance(result, dict) else 0.0

    def get_ticker_price(self, symbol: str) -> float:
        if self.ws_service:
            live_data = self.ws_service.get_live_data(symbol)
            price = live_data.get('price')
            if price:
                return price
        # Fallback to REST
        result = self._request("/fapi/v1/ticker/price", {"symbol": symbol})
        return float(result.get("price", 0.0)) if isinstance(result, dict) else 0.0

    def get_correlation(self, symbol_a: str, symbol_b: str, interval: str = "1h", limit: int = 40) -> float:
        if not symbol_a or not symbol_b or symbol_a == symbol_b:
            return 0.0

        klines_a = self.get_klines(symbol_a, interval=interval, limit=limit)
        klines_b = self.get_klines(symbol_b, interval=interval, limit=limit)
        closes_a = [float(item[4]) for item in klines_a if isinstance(item, list) and len(item) >= 5]
        closes_b = [float(item[4]) for item in klines_b if isinstance(item, list) and len(item) >= 5]
        n = min(len(closes_a), len(closes_b))
        if n < 10:
            return 0.0

        closes_a = closes_a[-n:]
        closes_b = closes_b[-n:]
        returns_a = [(closes_a[i] - closes_a[i - 1]) / closes_a[i - 1] for i in range(1, len(closes_a)) if closes_a[i - 1] != 0]
        returns_b = [(closes_b[i] - closes_b[i - 1]) / closes_b[i - 1] for i in range(1, len(closes_b)) if closes_b[i - 1] != 0]
        n = min(len(returns_a), len(returns_b))
        if n < 8:
            return 0.0

        returns_a = returns_a[-n:]
        returns_b = returns_b[-n:]
        mean_a = sum(returns_a) / n
        mean_b = sum(returns_b) / n
        cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(returns_a, returns_b)) / n
        var_a = sum((a - mean_a) ** 2 for a in returns_a) / n
        var_b = sum((b - mean_b) ** 2 for b in returns_b) / n
        if var_a <= 0 or var_b <= 0:
            return 0.0

        corr = cov / ((var_a * var_b) ** 0.5)
        return round(corr, 3)

    def get_klines(self, symbol: str, interval: str = "15m", limit: int = 20) -> List[list]:
        result = self._request("/fapi/v1/klines", {"symbol": symbol, "interval": interval, "limit": limit})
        return result if isinstance(result, list) else []

    def get_force_orders(self, symbol: str, limit: int = 10) -> List[dict]:
        result = self._request("/fapi/v1/allForceOrders", {"symbol": symbol, "limit": limit})
        return result if isinstance(result, list) else []

    def calculate_cumulative_delta(self, klines: List[list]) -> float:
        total_delta = 0.0
        for candle in klines:
            try:
                open_price = float(candle[1])
                close_price = float(candle[4])
                volume = float(candle[5])
                total_delta += volume if close_price >= open_price else -volume
            except Exception:
                continue
        return total_delta

    def format_footprint(self, klines: List[list]) -> List[dict]:
        footprint = []
        for candle in klines[-10:]:
            try:
                footprint.append({
                    "time": datetime.utcfromtimestamp(candle[0] / 1000).isoformat() + "Z",
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5])
                })
            except Exception:
                continue
        return footprint

    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        prices = {}
        for symbol in symbols:
            try:
                prices[symbol] = self.get_ticker_price(symbol)
            except Exception:
                prices[symbol] = 0.0
        return prices

    def scan(self, symbol: str) -> Dict:
        symbol = symbol.upper()
        klines = self.get_klines(symbol)
        open_interest = self.get_open_interest(symbol)
        price = self.get_ticker_price(symbol)
        liquidations = self.get_force_orders(symbol)

        # Use live cumulative delta if available
        cumulative_delta = 0.0
        if self.ws_service:
            live_data = self.ws_service.get_live_data(symbol)
            cumulative_delta = live_data.get('cumulative_delta', 0.0)
        else:
            cumulative_delta = self.calculate_cumulative_delta(klines)

        return {
            "symbol": symbol,
            "price": price,
            "open_interest": open_interest,
            "cumulative_delta": cumulative_delta,
            "footprint": self.format_footprint(klines),
            "last_liquidations": liquidations[:5]
        }


binance_service = BinanceService()