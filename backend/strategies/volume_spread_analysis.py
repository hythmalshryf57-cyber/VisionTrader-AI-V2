"""Lightweight VSA strategy using pandas and numpy.

Logic:
 - compute average volume over last 20 candles
 - if current volume > avg_volume * 1.5 and close is up -> strong buy
 - if current volume > avg_volume * 1.5 and close is down -> strong sell
 - otherwise neutral

This keeps the strategy lightweight but data-driven for live trading.
"""
from typing import Dict

USE_PANDAS = False
try:
    import numpy as np  # type: ignore
    import pandas as pd  # type: ignore
    USE_PANDAS = True
except Exception:
    USE_PANDAS = False


class VolumeSpreadAnalysisStrategy:
    """VSA lightweight implementation. Uses pandas/numpy if available,
    otherwise falls back to a pure-Python implementation for environments
    without those packages.
    """

    def analyze(self, chart_data: Dict) -> Dict:
        closes = chart_data.get('closes') or []
        volumes = chart_data.get('volumes') or []

        if not closes or not volumes or len(closes) < 3 or len(volumes) < 3:
            return {"recommendation": "محايد", "confidence": 20}

        window = min(20, len(volumes))

        if USE_PANDAS:
            vol_s = pd.Series(volumes)
            close_s = pd.Series(closes)
            avg_vol = float(vol_s.iloc[-window:].mean())
            curr_vol = float(vol_s.iloc[-1])
            last = float(close_s.iloc[-1])
            prev = float(close_s.iloc[-2])
        else:
            # pure-python fallback
            recent_vols = volumes[-window:]
            avg_vol = float(sum(recent_vols) / len(recent_vols)) if recent_vols else 0.0
            curr_vol = float(volumes[-1])
            last = float(closes[-1])
            prev = float(closes[-2])

        is_up = last > prev
        is_down = last < prev

        # higher sensitivity: treat 1.2x volume spike as strong VSA signal
        if avg_vol > 0 and curr_vol > avg_vol * 1.2:
            if is_up:
                return {"recommendation": "شراء", "confidence": 65, "reason": "VSA: volume spike + close up"}
            elif is_down:
                return {"recommendation": "بيع", "confidence": 65, "reason": "VSA: volume spike + close down"}

        # moderate elevation (taller spike) gives milder signal
        if avg_vol > 0 and curr_vol > avg_vol * 1.5:
            if is_up:
                return {"recommendation": "شراء", "confidence": 55, "reason": "VSA: moderate volume + close up"}
            elif is_down:
                return {"recommendation": "بيع", "confidence": 55, "reason": "VSA: moderate volume + close down"}

        return {"recommendation": "محايد", "confidence": 30, "reason": "VSA: no significant volume/direction signal"}
