import requests
import time
from datetime import datetime
from typing import Dict, List, Optional
from .websocket_service import BinanceWebSocketService


class DeepMarketScanner:
    def __init__(self, ws_service: Optional[BinanceWebSocketService] = None):
        self.futures_url = "https://fapi.binance.com/fapi/v1"
        self.session = requests.Session()
        self.ws_service = ws_service

    def _get_klines(self, symbol: str, interval: str = "5m", limit: int = 100) -> List[List]:
        url = f"{self.futures_url}/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching klines: {e}")
            return []

    def _get_recent_trades(self, symbol: str, limit: int = 200) -> List[Dict]:
        url = f"{self.futures_url}/trades"
        params = {"symbol": symbol, "limit": limit}
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching trades: {e}")
            return []

    def _get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        if self.ws_service:
            live_data = self.ws_service.get_live_data(symbol)
            bids = live_data.get('bids', [])
            asks = live_data.get('asks', [])
            if bids and asks:
                return {"bids": bids[:limit], "asks": asks[:limit]}
        # Fallback to REST
        url = f"{self.futures_url}/depth"
        params = {"symbol": symbol, "limit": limit}
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching order book: {e}")
            return {"bids": [], "asks": []}

    def _get_force_orders(self, symbol: str, limit: int = 50) -> List[Dict]:
        url = f"{self.futures_url}/allForceOrders"
        params = {"symbol": symbol, "limit": limit}
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching force orders: {e}")
            return []

    def _get_open_interest(self, symbol: str) -> float:
        if self.ws_service:
            live_data = self.ws_service.get_live_data(symbol)
            oi = live_data.get('open_interest')
            if oi is not None:
                return oi
        # Fallback to REST
        url = f"{self.futures_url}/openInterest"
        params = {"symbol": symbol}
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            return float(data.get("openInterest", 0.0))
        except Exception as e:
            print(f"Error fetching open interest: {e}")
            return 0.0

    def _get_ticker_price(self, symbol: str) -> float:
        if self.ws_service:
            live_data = self.ws_service.get_live_data(symbol)
            price = live_data.get('price')
            if price:
                return price
        # Fallback to REST
        url = f"{self.futures_url}/ticker/price"
        params = {"symbol": symbol}
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            return float(data.get("price", 0.0))
        except Exception as e:
            print(f"Error fetching ticker price: {e}")
            return 0.0

    def _calculate_volume_profile(self, klines: List[List]) -> Dict:
        volume_profile = {}
        for kline in klines:
            close_price = float(kline[4])
            volume = float(kline[5])
            price_level = round(close_price, 2)
            volume_profile[price_level] = volume_profile.get(price_level, 0) + volume

        if not volume_profile:
            return {
                "poc": None,
                "poc_volume": 0,
                "high_volume_nodes": [],
                "low_volume_nodes": [],
                "description": "لا توجد بيانات الحجم الكافية"
            }

        poc_price = max(volume_profile.items(), key=lambda x: x[1])[0]
        poc_volume = volume_profile[poc_price]
        sorted_pairs = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)
        threshold_high = sorted_pairs[max(0, int(len(sorted_pairs) * 0.2))][1]
        threshold_low = sorted_pairs[min(len(sorted_pairs) - 1, int(len(sorted_pairs) * 0.8))][1]

        high_volume_nodes = [price for price, vol in volume_profile.items() if vol >= threshold_high]
        low_volume_nodes = [price for price, vol in volume_profile.items() if vol <= threshold_low]

        return {
            "poc": poc_price,
            "poc_volume": round(poc_volume, 2),
            "high_volume_nodes": sorted(high_volume_nodes)[:5],
            "low_volume_nodes": sorted(low_volume_nodes)[:5],
            "description": f"أكبر تداول عند سعر {round(poc_price, 2)}"
        }

    def _calculate_cumulative_delta(self, klines: List[List]) -> Dict:
        buy_volume = 0.0
        sell_volume = 0.0
        for kline in klines:
            open_price = float(kline[1])
            close_price = float(kline[4])
            volume = float(kline[5])
            if close_price > open_price:
                buy_volume += volume * 0.75
                sell_volume += volume * 0.25
            elif close_price < open_price:
                buy_volume += volume * 0.25
                sell_volume += volume * 0.75
            else:
                buy_volume += volume * 0.5
                sell_volume += volume * 0.5

        cumulative_delta = buy_volume - sell_volume
        if cumulative_delta > 0:
            description = f"المشترون يسيطرون (دلتا موجبة {round(cumulative_delta, 2)})"
        elif cumulative_delta < 0:
            description = f"البائعون يسيطرون (دلتا سالبة {round(abs(cumulative_delta), 2)})"
        else:
            description = "توازن بين المشترين والبائعين"

        return {
            "cumulative_delta": round(cumulative_delta, 2),
            "buy_volume": round(buy_volume, 2),
            "sell_volume": round(sell_volume, 2),
            "description": description
        }

    def _analyze_liquidations(self, symbol: str) -> Dict:
        current_price = self._get_ticker_price(symbol)
        force_orders = self._get_force_orders(symbol)
        levels = []
        for order in force_orders:
            price = float(order.get("liquidationPrice", 0) or 0)
            if price > 0:
                levels.append(price)

        levels = sorted(set(levels))
        closest_level = min(levels, key=lambda p: abs(p - current_price)) if levels else None
        description = "لا توجد تصفيات كبيرة متوقعة"
        if closest_level is not None:
            side = "أسفل" if closest_level < current_price else "أعلى"
            description = f"تصفيات كبيرة متوقعة عند سعر {round(closest_level, 2)} ({side})"

        return {
            "liquidation_levels": levels[:5],
            "closest_level": round(closest_level, 2) if closest_level is not None else None,
            "open_interest": round(self._get_open_interest(symbol), 2),
            "description": description
        }

    def _analyze_order_book_imbalance(self, order_book: Dict) -> Dict:
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        if not bids or not asks:
            return {"imbalance_ratio": 0, "description": "لا توجد بيانات دفتر أوامر كافية", "bid_volume": 0, "ask_volume": 0, "bid_walls": [], "ask_walls": []}

        bid_volume = sum(float(bid[1]) for bid in bids[:10])
        ask_volume = sum(float(ask[1]) for ask in asks[:10])
        imbalance_ratio = float('inf') if ask_volume == 0 else bid_volume / ask_volume

        bid_walls = [{"price": float(bid[0]), "volume": float(bid[1])} for bid in bids[:20] if float(bid[1]) > bid_volume * 0.1]
        ask_walls = [{"price": float(ask[0]), "volume": float(ask[1])} for ask in asks[:20] if float(ask[1]) > ask_volume * 0.1]

        if imbalance_ratio > 1.5:
            description = f"جدار شراء قوي عند {round(bid_walls[0]['price'], 2) if bid_walls else 'مستويات عليا'}"
        elif imbalance_ratio < 0.67:
            description = f"جدار بيع قوي عند {round(ask_walls[0]['price'], 2) if ask_walls else 'مستويات منخفضة'}"
        else:
            description = f"توازن في دفتر الأوامر (نسبة {round(imbalance_ratio, 2)})"

        return {"imbalance_ratio": round(imbalance_ratio, 2) if imbalance_ratio != float('inf') else None, "bid_volume": round(bid_volume, 2), "ask_volume": round(ask_volume, 2), "bid_walls": bid_walls[:3], "ask_walls": ask_walls[:3], "description": description}

    def _detect_whales(self, trades: List[Dict]) -> Dict:
        whale_trades = []
        min_whale_value = 50000
        for trade in trades:
            price = float(trade.get("price", 0))
            qty = float(trade.get("qty", 0))
            trade_value = price * qty
            if trade_value >= min_whale_value:
                whale_trades.append({"price": round(price, 2), "quantity": round(qty, 2), "value": round(trade_value, 2), "is_buyer": not trade.get("isBuyerMaker", False), "timestamp": trade.get("time", 0)})

        if not whale_trades:
            return {"recent_whales": [], "description": "لا توجد صفقات حوت كبيرة مؤخراً"}

        largest_whale = max(whale_trades, key=lambda x: x["value"])
        direction = "اشترى" if largest_whale["is_buyer"] else "باع"
        description = f"حوت {direction} {largest_whale['value']}$ عند سعر {largest_whale['price']}"
        return {"recent_whales": whale_trades[-5:], "largest_whale": largest_whale, "description": description}

    def _calculate_tp_sl(self, price: float, recommendation: str, confluence: int, klines: List[List]) -> Dict:
        if not klines or price == 0:
            return {"tp_levels": [], "sl_level": None, "volatility": "غير معروف", "target_count": 0, "note": "لا توجد بيانات كافية لـ TP/SL"}

        ranges = [float(k[2]) - float(k[3]) for k in klines if len(k) >= 5]
        avg_range = max(0.01, sum(ranges) / len(ranges)) if ranges else 1.0
        volatility = "مرتفع" if avg_range > price * 0.005 else "منخفض"

        if confluence >= 5:
            target_count = 3
        elif confluence == 4:
            target_count = 2
        else:
            target_count = 1

        width_factor = 1.6 if volatility == "مرتفع" else 1.0
        direction = "buy" if recommendation == "شراء" else "sell" if recommendation == "بيع" else "neutral"
        tp_levels = []
        for idx in range(target_count):
            distance = avg_range * width_factor * (1 + idx * 0.8)
            if direction == "buy":
                tp_levels.append(round(price + distance, 2))
            elif direction == "sell":
                tp_levels.append(round(price - distance, 2))

        if direction == "buy":
            sl_level = round(price - avg_range * 0.8, 2)
        elif direction == "sell":
            sl_level = round(price + avg_range * 0.8, 2)
        else:
            sl_level = None

        return {"tp_levels": tp_levels, "sl_level": sl_level, "volatility": volatility, "target_count": target_count, "note": f"{target_count} هدف بناءً على قوة التوافق ({confluence}/5)"}

    def _market_personality(self, symbol: str) -> Dict:
        symbol = symbol.upper()
        if "XAU" in symbol:
            return {"personality": "ذهب متقلب، يحترم المستويات النفسية 00 و 50", "context": "يتأثر بالأخبار العالمية والسيولة"}
        if symbol.startswith("EUR") and "USD" in symbol:
            return {"personality": "EUR/USD الأكثر سيولة، سبريد ضيق، يتحرك في جلسة لندن", "context": "يعمل بشكل قوي خلال الفتح الأوروبي"}
        if symbol.startswith("GBP") and "USD" in symbol:
            return {"personality": "GBP/USD حركات حادة وانعكاسات سريعة", "context": "يتطلب وقف أوسع بسبب التقلب"}
        if symbol.startswith("USD") and "JPY" in symbol:
            return {"personality": "USD/JPY يتبع الترند بقوة", "context": "جيد للاتجاهات الطويلة"}
        if any(ind in symbol for ind in ["US30", "SPX", "NAS", "DAX", "FTM", "DOW"]):
            return {"personality": "المؤشرات تتبع الترند طويلاً", "context": "تنجذب إلى تحركات نيويورك"}
        if any(energy in symbol for energy in ["CL", "WTI", "BRENT"]):
            return {"personality": "النفط متقلب جداً", "context": "يتأثر بالأخبار الجيوسياسية"}
        return {"personality": "سوق عام", "context": "يتطلب تحليل إضافي"}

    def _calculate_confluence(self, volume_profile: Dict, cumulative_delta: Dict, order_imbalance: Dict, liquidations: Dict, whales: Dict) -> int:
        score = 0
        if volume_profile.get("poc") is not None:
            score += 1
        if abs(cumulative_delta.get("cumulative_delta", 0)) > 50:
            score += 1
        if order_imbalance.get("imbalance_ratio") and order_imbalance.get("imbalance_ratio") != 1:
            score += 1
        if liquidations.get("closest_level") is not None:
            score += 1
        if whales.get("recent_whales"):
            score += 1
        return min(5, score)

    def scan_market(self, symbol: str) -> Dict:
        try:
            symbol = symbol.upper()
            klines = self._get_klines(symbol, "5m", 100)
            trades = self._get_recent_trades(symbol, 200)
            order_book = self._get_order_book(symbol, 100)
            price = self._get_ticker_price(symbol)

            volume_profile = self._calculate_volume_profile(klines)
            cumulative_delta = self._calculate_cumulative_delta(klines)
            liquidations = self._analyze_liquidations(symbol)
            order_imbalance = self._analyze_order_book_imbalance(order_book)
            whales = self._detect_whales(trades)

            confluence = self._calculate_confluence(volume_profile, cumulative_delta, order_imbalance, liquidations, whales)
            recommendation = self._generate_recommendation(volume_profile, cumulative_delta, order_imbalance)
            tp_sl = self._calculate_tp_sl(price, recommendation, confluence, klines)

            return {
                "symbol": symbol,
                "timestamp": int(time.time() * 1000),
                "price": round(price, 2),
                "volume_profile": volume_profile,
                "cumulative_delta": cumulative_delta,
                "liquidations": liquidations,
                "order_imbalance": order_imbalance,
                "whales": whales,
                "tp_sl": tp_sl,
                "recommendation": recommendation,
                "confidence": self._calculate_confidence(volume_profile, cumulative_delta, order_imbalance),
                "confluence_score": confluence,
                "market_personality": self._market_personality(symbol)
            }
        except Exception as e:
            return {"symbol": symbol, "error": str(e), "recommendation": "محايد", "confidence": 0}

    def _generate_recommendation(self, volume_profile: Dict, cumulative_delta: Dict, order_imbalance: Dict) -> str:
        score = 0
        if volume_profile.get("poc"):
            score += 10
        delta = cumulative_delta.get("cumulative_delta", 0)
        if delta > 0:
            score += 20
        elif delta < 0:
            score -= 20
        imbalance = order_imbalance.get("imbalance_ratio", 1)
        if imbalance and imbalance > 1.2:
            score += 15
        elif imbalance and imbalance < 0.8:
            score -= 15
        if score > 20:
            return "شراء"
        elif score < -20:
            return "بيع"
        return "محايد"

    def _calculate_confidence(self, volume_profile: Dict, cumulative_delta: Dict, order_imbalance: Dict) -> int:
        confidence = 50
        if volume_profile.get("poc"):
            confidence += 10
        delta = abs(cumulative_delta.get("cumulative_delta", 0))
        if delta > 100:
            confidence += 15
        imbalance = order_imbalance.get("imbalance_ratio", 1)
        if imbalance and (imbalance > 1.5 or imbalance < 0.67):
            confidence += 10
        return min(95, confidence)


deep_market_scanner = DeepMarketScanner()
