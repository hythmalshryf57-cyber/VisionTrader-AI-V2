from typing import Any, Dict, List

class SmartZones:
    def __init__(self):
        self.name = "Smart Zones Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        zones = data.get("market_zones") or []
        strong_zones = []
        repeated = []
        for zone in zones:
            label = zone.get("label") or zone.get("name") or "منطقة"
            tests = int(zone.get("tests") or 0)
            strength = float(zone.get("strength") or 0)
            if tests >= 2 and strength >= 0.7:
                strong_zones.append(label)
            if tests >= 4:
                repeated.append(label)

        report = ""
        if strong_zones:
            report += f"مناطق قوية محددة: {', '.join(strong_zones)}. "
        if repeated:
            report += f"مناطق اختُبرت مرات عديدة: {', '.join(repeated)}."
        if not report:
            report = "لم يتم تحديد مناطق طلب أو عرض بارزة حالياً."

        return {
            "agent": self.name,
            "signal": "neutral",
            "confidence": 60,
            "report": report,
            "strong_zones": strong_zones,
            "repeat_tested_zones": repeated,
        }
