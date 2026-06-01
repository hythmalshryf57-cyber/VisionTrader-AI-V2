from typing import Any, Dict, List

class LiquidityFlow:
    def __init__(self):
        self.name = "Liquidity Flow Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        flows = data.get("liquidity_flows") or []
        destinations = []
        rotations = []
        for entry in flows:
            symbol = entry.get("symbol") or "unknown"
            volume = float(entry.get("volume") or 0)
            direction = entry.get("direction") or ""
            if volume > 0 and direction == "in":
                destinations.append(symbol)
            if entry.get("rotation"):
                rotations.append(symbol)

        report = ""
        if destinations:
            report += f"تدفقات الأموال الكبيرة تتجه نحو: {', '.join(destinations)}. "
        if rotations:
            report += f"يوجد تحولات في القطاعات: {', '.join(rotations)}."
        if not report:
            report = "لا توجد إشارات تعدين سيولة واضحة حالياً."

        return {
            "agent": self.name,
            "signal": "neutral",
            "confidence": 55,
            "report": report,
            "destinations": destinations,
            "rotations": rotations,
        }
