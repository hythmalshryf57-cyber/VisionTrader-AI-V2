from typing import Any, Dict, List

class RadarAgent:
    def __init__(self):
        self.name = "Radar Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        alerts = data.get("radar_alerts") or []
        early = []
        for event in alerts:
            if event.get("type") in ["breakout", "volume_spike"] and float(event.get("intensity") or 0) > 0.7:
                early.append(f"{event.get('symbol','?')} -> {event.get('type')}")

        report = (
            f"تنبيهات مبكرة: {', '.join(early)}." if early else "لا توجد تنبيهات فورية ملحوظة."
        )
        return {
            "agent": self.name,
            "signal": "neutral",
            "confidence": 65 if early else 35,
            "report": report,
            "early_warnings": early,
        }
