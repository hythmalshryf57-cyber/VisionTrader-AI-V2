from typing import Optional, Dict, Any


class RiskCalculator:
    MAX_RISK_PERCENT = 2.0
    MIN_CONFIDENCE_MULTIPLIER = 0.5
    CONFIDENCE_THRESHOLD = 60

    def adjusted_risk(self, confidence: int, base_risk: float = 2.0) -> float:
        risk_percent = min(self.MAX_RISK_PERCENT, max(0.25, base_risk))
        if confidence < self.CONFIDENCE_THRESHOLD:
            risk_percent *= self.MIN_CONFIDENCE_MULTIPLIER
        if confidence > 90:
            risk_percent = min(self.MAX_RISK_PERCENT, risk_percent * 1.05)
        return round(max(0.25, min(self.MAX_RISK_PERCENT, risk_percent)), 2)

    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        risk_percent: float,
    ) -> Dict[str, Any]:
        result = {
            "position_size": 0.0,
            "risk_amount": 0.0,
            "risk_percent": round(risk_percent, 2),
            "stop_distance": 0.0,
            "valid": False,
            "note": "Unable to calculate position size.",
        }

        if not account_balance or not entry_price or not stop_loss:
            result["note"] = "Account balance, entry price or stop-loss missing."
            return result

        risk_amount = account_balance * (risk_percent / 100.0)
        stop_distance = abs(entry_price - stop_loss)
        if stop_distance <= 0:
            result["note"] = "Invalid stop-loss distance."
            return result

        position_size = risk_amount / stop_distance
        result.update({
            "position_size": round(position_size, 6),
            "risk_amount": round(risk_amount, 2),
            "stop_distance": round(stop_distance, 6),
            "valid": position_size > 0,
            "note": "Position size estimated from fixed risk allocation.",
        })
        return result

    def _normalize_price_history(self, price_history: Optional[list]) -> list:
        normalized = []
        if not price_history:
            return normalized

        for item in price_history[-50:]:
            if isinstance(item, dict):
                open_p = float(item.get('open', item.get('o', 0) or 0))
                high_p = float(item.get('high', item.get('h', 0) or 0))
                low_p = float(item.get('low', item.get('l', 0) or 0))
                close_p = float(item.get('close', item.get('c', 0) or 0))
            elif isinstance(item, (list, tuple)) and len(item) >= 4:
                open_p, high_p, low_p, close_p = map(float, item[:4])
            else:
                continue
            normalized.append({
                'open': open_p,
                'high': high_p,
                'low': low_p,
                'close': close_p,
            })
        return normalized

    def _find_nearest_swing_low(self, candles: list, entry_price: float) -> Optional[float]:
        swing_lows = []
        for i in range(1, len(candles) - 1):
            if candles[i]['low'] < candles[i - 1]['low'] and candles[i]['low'] < candles[i + 1]['low']:
                swing_lows.append(candles[i]['low'])
        below_entry = [low for low in swing_lows if low < entry_price]
        if below_entry:
            return max(below_entry)
        lows = [c['low'] for c in candles if c['low'] < entry_price]
        return max(lows) if lows else None

    def _find_nearest_swing_high(self, candles: list, entry_price: float) -> Optional[float]:
        swing_highs = []
        for i in range(1, len(candles) - 1):
            if candles[i]['high'] > candles[i - 1]['high'] and candles[i]['high'] > candles[i + 1]['high']:
                swing_highs.append(candles[i]['high'])
        above_entry = [high for high in swing_highs if high > entry_price]
        if above_entry:
            return min(above_entry)
        highs = [c['high'] for c in candles if c['high'] > entry_price]
        return min(highs) if highs else None

    def _find_nearest_liquidity_level(self, liquidity_levels: Optional[list], entry_price: float, max_target: float) -> Optional[float]:
        if not liquidity_levels:
            return None
        clean_levels = []
        for lvl in liquidity_levels:
            try:
                clean_levels.append(float(lvl))
            except Exception:
                continue
        candidates = [lvl for lvl in clean_levels if entry_price < lvl < max_target]
        return min(candidates) if candidates else None

    def estimate_tp_sl(
        self,
        entry_price: float,
        recommendation: str,
        avg_range: Optional[float] = None,
        price_history: Optional[list] = None,
        liquidity_levels: Optional[list] = None,
    ) -> Dict[str, Any]:
        if not entry_price or recommendation not in ("شراء", "بيع"):
            return {
                "stop_loss": None,
                "take_profit": None,
                "volatility_estimate": None,
                "note": "Invalid entry price or recommendation.",
            }

        candles = self._normalize_price_history(price_history)
        protective_buffer = 1.5
        if recommendation == "شراء":
            swing_low = self._find_nearest_swing_low(candles, entry_price)
            if swing_low is not None:
                stop_loss = round(swing_low - protective_buffer, 6)
                if stop_loss >= entry_price:
                    stop_loss = round(entry_price - protective_buffer, 6)
            else:
                stop_loss = round(entry_price - max(abs(entry_price * 0.002), protective_buffer), 6)

            target_base = entry_price + abs(entry_price - stop_loss) * 1.8
            liquidity_target = self._find_nearest_liquidity_level(liquidity_levels, entry_price, target_base)
            swing_high = self._find_nearest_swing_high(candles, entry_price)
            soft_target = liquidity_target or swing_high
            if soft_target is not None and soft_target < target_base:
                take_profit = round(max(entry_price + 0.5, soft_target - 0.5), 6)
            else:
                take_profit = round(target_base, 6)

        else:
            swing_high = self._find_nearest_swing_high(candles, entry_price)
            if swing_high is not None:
                stop_loss = round(swing_high + protective_buffer, 6)
                if stop_loss <= entry_price:
                    stop_loss = round(entry_price + protective_buffer, 6)
            else:
                stop_loss = round(entry_price + max(abs(entry_price * 0.002), protective_buffer), 6)

            target_base = entry_price - abs(entry_price - stop_loss) * 1.8
            liquidity_target = self._find_nearest_liquidity_level(liquidity_levels, target_base, entry_price)
            swing_low = self._find_nearest_swing_low(candles, entry_price)
            soft_target = liquidity_target or swing_low
            if soft_target is not None and soft_target > target_base:
                take_profit = round(min(entry_price - 0.5, soft_target + 0.5), 6)
            else:
                take_profit = round(target_base, 6)

        volatility = None
        if avg_range is not None:
            volatility = abs(avg_range)
        elif candles:
            recent_ranges = [abs(c['high'] - c['low']) for c in candles if c['high'] is not None and c['low'] is not None]
            if recent_ranges:
                volatility = round(sum(recent_ranges[-14:]) / max(1, min(14, len(recent_ranges))), 6)

        volatility = volatility or abs(entry_price * 0.002)

        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "volatility_estimate": round(volatility, 6),
            "note": "TP/SL estimated from recent swings and liquidity structure.",
        }

    def risk_of_ruin(
        self,
        win_rate: float,
        risk_per_trade: float,
        reward_ratio: float = 1.5,
    ) -> float:
        if risk_per_trade <= 0 or reward_ratio <= 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0

        probability_of_loss = 1.0 - win_rate
        if win_rate <= 0 or probability_of_loss <= 0:
            return 0.0

        ratio = probability_of_loss / win_rate
        risk_of_ruin = ratio / (ratio + reward_ratio)
        return round(max(0.0, min(100.0, risk_of_ruin * 100.0)), 2)
