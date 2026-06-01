from typing import Any, Dict

class TradeFollowup:
    def __init__(self):
        self.name = "Trade Follow-up Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        open_trades = data.get("open_trades") or []
        adjustments = []
        for trade in open_trades:
            entry = float(trade.get("entry") or 0)
            current = float(trade.get("current_price") or 0)
            stop = float(trade.get("stop") or 0)
            if entry and current and stop:
                if abs(current - entry) > abs(entry - stop) * 0.6:
                    adjustments.append(f"انقل وقف الصفقة في {trade.get('symbol','?')} لتقليل المخاطرة.")
                elif current > entry and trade.get("side") == "buy":
                    adjustments.append(f"اغلق جزءاً من العقد في {trade.get('symbol','?')} لتحقيق ربح جزئي.")
        if not adjustments:
            report = "لا توجد توصيات تعديل فورية على الصفقات المفتوحة."
        else:
            report = " ".join(adjustments)

        return {
            "agent": self.name,
            "signal": "neutral",
            "confidence": 65,
            "report": report,
            "adjustments": adjustments,
        }
