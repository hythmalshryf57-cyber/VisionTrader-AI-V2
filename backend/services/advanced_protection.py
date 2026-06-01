from typing import Any, Dict

class AdvancedProtection:
    def __init__(self):
        self.name = "Advanced Protection Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        alerts = data.get("protection_signals") or {}
        fake_breakout = bool(alerts.get("fake_breakout"))
        stop_hunt = bool(alerts.get("stop_hunt"))
        report_parts = []
        if stop_hunt:
            report_parts.append("تم اكتشاف احتمالية Stop Hunt؛ فعّل حماية المخاطر.")
        if fake_breakout:
            report_parts.append("احتمالية Fake Breakout عالية؛ لا تفتح صفقة على الاختراق بسرعة.")
        if not report_parts:
            report_parts.append("لا توجد ظروف خطيرة ملحوظة حالياً.")

        signal = "neutral" if stop_hunt or fake_breakout else "buy"
        confidence = 40 if stop_hunt or fake_breakout else 70

        return {
            "agent": self.name,
            "signal": signal,
            "confidence": confidence,
            "report": " ".join(report_parts),
            "stop_hunt": stop_hunt,
            "fake_breakout": fake_breakout,
        }
