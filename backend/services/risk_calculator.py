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

    def estimate_tp_sl(
        self,
        entry_price: float,
        recommendation: str,
        avg_range: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not entry_price or recommendation not in ("شراء", "بيع"):
            return {
                "stop_loss": None,
                "take_profit": None,
                "volatility_estimate": None,
                "note": "Invalid entry price or recommendation.",
            }

        volatility = max(avg_range or abs(entry_price * 0.006), abs(entry_price * 0.002), 0.0001)
        if recommendation == "شراء":
            stop_loss = round(entry_price - volatility, 6)
            take_profit = round(entry_price + volatility * 1.8, 6)
        else:
            stop_loss = round(entry_price + volatility, 6)
            take_profit = round(entry_price - volatility * 1.8, 6)

        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "volatility_estimate": round(volatility, 6),
            "note": "Smart TP/SL estimated from recent volatility.",
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
