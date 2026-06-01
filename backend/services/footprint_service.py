"""Footprint analysis service for VisionTrader AI.

Provides analyzers for footprint, bookmap (DOM), volume profile and cumulative delta.
These analyzers are lightweight and consume ingested trades, orderbook snapshots and
klines; they do not assume global service instances and accept data via ingest methods.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

try:
    # prefer relative imports inside the services package
    from .websocket_service import BinanceWebSocketService  # type: ignore
except Exception:
    BinanceWebSocketService = None

try:
    from .binance_service import binance_service  # type: ignore
except Exception:
    binance_service = None


@dataclass
class AnalysisResult:
    signal: str
    confidence: int
    description: str

    def as_dict(self) -> Dict:
        return {"signal": self.signal, "confidence": self.confidence, "description": self.description}


class FootprintChartAnalyzer:
    """Analyze trade stream to compute bid/ask volume per price level and detect absorption/exhaustion.

    Use `ingest_trade(price, qty, side)` to feed data. `analyze()` returns a dict.
    """

    def __init__(self, lookback: int = 200):
        self.lookback = lookback
        self.trades: deque = deque(maxlen=lookback)

    def ingest_trade(self, price: float, qty: float, side: Optional[str]):
        self.trades.append((price, qty, side))

    def analyze(self, top_n_levels: int = 5) -> Dict:
        if not self.trades:
            return AnalysisResult("Neutral", 0, "No trade data").as_dict()

        level_volumes: Dict[float, Dict[str, float]] = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})
        for price, qty, side in self.trades:
            level = round(float(price), 2)
            if side and str(side).lower() in ("buy", "taker_buy", "b"):
                level_volumes[level]["buy"] += float(qty)
            else:
                level_volumes[level]["sell"] += float(qty)

        items = [(lvl, v["buy"], v["sell"], v["buy"] + v["sell"]) for lvl, v in level_volumes.items()]
        if not items:
            return AnalysisResult("Neutral", 0, "Insufficient level volume").as_dict()

        items.sort(key=lambda x: x[3], reverse=True)

        bulls = bears = 0
        descriptions: List[str] = []
        checked = items[:top_n_levels]
        mean_total = statistics.mean([it[3] for it in checked]) if checked else 0

        for lvl, buy_v, sell_v, tot in checked:
            if tot == 0:
                continue
            delta = buy_v - sell_v
            dominance = abs(delta) / tot
            if delta > 0 and dominance > 0.6:
                bulls += 1
                descriptions.append(f"Buy-dominant at {lvl} (buy {buy_v:.2f} vs sell {sell_v:.2f})")
            elif delta < 0 and dominance > 0.6:
                bears += 1
                descriptions.append(f"Sell-dominant at {lvl} (buy {buy_v:.2f} vs sell {sell_v:.2f})")

            if dominance < 0.25 and mean_total and tot > mean_total * 1.5:
                descriptions.append(f"Potential absorption at {lvl} (total {tot:.2f})")

        score = int((bulls - bears) / max(1, (bulls + bears)) * 100) if (bulls + bears) > 0 else 0
        signal = "Neutral"
        if bulls > bears:
            signal = "Bullish"
        elif bears > bulls:
            signal = "Bearish"

        confidence = int(min(90, abs(score) + min(30, (bulls + bears) * 5)))
        desc = "; ".join(descriptions) if descriptions else "No clear footprint signals"
        return AnalysisResult(signal, confidence, desc).as_dict()


class BookmapDOMReader:
    """Analyze orderbook snapshots (depth) to detect hidden liquidity, stop hunts, iceberg orders, walls."""

    def __init__(self):
        self.history: deque = deque(maxlen=20)

    def ingest_snapshot(self, bids: List[Tuple[float, float]], asks: List[Tuple[float, float]]):
        self.history.append({"bids": bids, "asks": asks})

    def analyze(self) -> Dict:
        if not self.history:
            return AnalysisResult("Neutral", 0, "No depth data").as_dict()

        latest = self.history[-1]
        bids = latest.get("bids", [])
        asks = latest.get("asks", [])

        best_bid_qty = bids[0][1] if bids else 0
        best_ask_qty = asks[0][1] if asks else 0

        avg_bid = statistics.mean([q for _, q in bids[:10]]) if len(bids) >= 3 else (best_bid_qty or 0)
        avg_ask = statistics.mean([q for _, q in asks[:10]]) if len(asks) >= 3 else (best_ask_qty or 0)

        descriptions: List[str] = []
        bulls = bears = 0

        if avg_bid and best_bid_qty > avg_bid * 5 and best_bid_qty > 0:
            bulls += 1
            descriptions.append(f"Buy wall at best bid: {best_bid_qty:.2f}")
        if avg_ask and best_ask_qty > avg_ask * 5 and best_ask_qty > 0:
            bears += 1
            descriptions.append(f"Sell wall at best ask: {best_ask_qty:.2f}")

        replenished = 0
        levels_count = defaultdict(int)
        for snap in self.history:
            for p, q in snap.get("bids", [])[:5]:
                if q > 0:
                    levels_count[round(p, 2)] += 1
            for p, q in snap.get("asks", [])[:5]:
                if q > 0:
                    levels_count[round(p, 2)] += 1

        for lvl, cnt in levels_count.items():
            if cnt >= max(3, len(self.history) // 3):
                replenished += 1
        if replenished:
            descriptions.append(f"Potential hidden liquidity at {replenished} levels")

        stop_hunt_detected = False
        if len(self.history) >= 5:
            thin_counts = 0
            for snap in list(self.history)[-5:]:
                small_liq = 0
                if avg_bid:
                    small_liq += sum(1 for _, q in snap.get("bids", [])[:5] if q < avg_bid * 0.3)
                if avg_ask:
                    small_liq += sum(1 for _, q in snap.get("asks", [])[:5] if q < avg_ask * 0.3)
                if small_liq > 6:
                    thin_counts += 1
            if thin_counts >= 3:
                last = self.history[-1]
                if (last.get("asks") and avg_ask and last["asks"][0][1] > avg_ask * 6) or (last.get("bids") and avg_bid and last["bids"][0][1] > avg_bid * 6):
                    stop_hunt_detected = True
                    descriptions.append("Possible stop-hunt activity")

        if stop_hunt_detected:
            signal = "Neutral"
            confidence = 40
        else:
            signal = "Bullish" if bulls > bears else ("Bearish" if bears > bulls else "Neutral")
            confidence = int(min(85, 30 + abs(bulls - bears) * 25 + replenished * 5))

        desc = "; ".join(descriptions) if descriptions else "No significant DOM patterns"
        return AnalysisResult(signal, confidence, desc).as_dict()


class VolumeProfileAnalyzer:
    """Compute volume profile (POC, HVN, LVN) from historical klines."""

    def __init__(self, bins: int = 24):
        self.bins = bins
        self.price_buckets: Dict[int, float] = defaultdict(float)

    def ingest_kline(self, open_p: float, high: float, low: float, close: float, volume: float):
        self._add_volume(float(close), float(volume))

    def _add_volume(self, price: float, volume: float):
        bucket = int(price)
        self.price_buckets[bucket] += volume

    def analyze(self) -> Dict:
        if not self.price_buckets:
            return AnalysisResult("Neutral", 0, "No historical klines").as_dict()
        items = sorted(self.price_buckets.items(), key=lambda x: x[1], reverse=True)
        poc_bucket, poc_vol = items[0]
        hvns = [b for b, v in items[:3]]
        lvns = [b for b, v in list(reversed(items))[:3]]
        description = f"POC: {poc_bucket} (vol {poc_vol:.2f}); HVN: {hvns}; LVN: {lvns}"
        signal = "Neutral"
        confidence = 30
        if len(hvns) and poc_bucket in hvns[:2]:
            signal = "Bullish"
            confidence = 50
        return AnalysisResult(signal, confidence, description).as_dict()


class CumulativeDeltaTracker:
    """Track cumulative delta (buy volume - sell volume) and detect divergence with price."""

    def __init__(self, window: int = 200):
        self.window = window
        self.trades: deque = deque(maxlen=window)
        self.cumulative: deque = deque(maxlen=window)

    def ingest_trade(self, price: float, qty: float, side: Optional[str]):
        delta = float(qty) if side and str(side).lower() in ("buy", "taker_buy", "b") else -float(qty)
        self.trades.append((price, qty, side))
        total = (self.cumulative[-1] if self.cumulative else 0) + delta
        self.cumulative.append(total)

    def analyze(self, current_price: Optional[float] = None) -> Dict:
        if not self.cumulative:
            return AnalysisResult("Neutral", 0, "No delta data").as_dict()
        recent_cd = list(self.cumulative)[-20:]
        cd_slope = (recent_cd[-1] - recent_cd[0]) / max(1, len(recent_cd))
        prices = [t[0] for t in list(self.trades)[-20:]]
        price_slope = (prices[-1] - prices[0]) / max(1, len(prices)) if prices else 0
        desc = f"CD slope {cd_slope:.4f}; price slope {price_slope:.4f}"
        signal = "Neutral"
        confidence = 20
        if cd_slope > 0 and price_slope < 0:
            signal = "Bearish"
            confidence = int(min(95, 50 + min(45, abs(cd_slope) * 1000)))
            desc += "; Bearish divergence (price falling while buyers dominate)"
        elif cd_slope < 0 and price_slope > 0:
            signal = "Bullish"
            confidence = int(min(95, 50 + min(45, abs(cd_slope) * 1000)))
            desc += "; Bullish divergence (price rising while sellers dominate)"
        else:
            if len(recent_cd) >= 3:
                try:
                    mean_abs = statistics.mean([abs(x) for x in recent_cd])
                except Exception:
                    mean_abs = 0
                if abs(cd_slope) < 1e-6 and mean_abs and abs(recent_cd[-1]) > mean_abs * 1.5:
                    signal = "Neutral"
                    confidence = 45
                    desc += "; Possible exhaustion (large cumulative delta but flattening)"
        return AnalysisResult(signal, confidence, desc).as_dict()


__all__ = [
    "FootprintChartAnalyzer",
    "BookmapDOMReader",
    "VolumeProfileAnalyzer",
    "CumulativeDeltaTracker",
    "AnalysisResult",
]
