from typing import Any, Dict

class PsychologyAgent:
    def __init__(self):
        self.name = "Psychology Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        behavior = data.get("trading_behavior") or {}
        recent_losses = int(behavior.get("recent_loss_count") or 0)
        recent_trades = int(behavior.get("recent_trade_count") or 0)
        recovery_attempts = int(behavior.get("recovery_attempts") or 0)
        consecutive_losses = int(behavior.get("consecutive_losses") or 0)

        warnings = []
        signal = "neutral"
        confidence = 50
        report = "تحليل نفسي للتداول."
        if consecutive_losses >= 2 and recent_trades > 0:
            warnings.append("هناك علامات تداول انتقامي؛ احترس من زيادة المخاطر.")
        if recent_trades > 10 and recent_losses > 8:
            warnings.append("قد تكون في فترة Overtrading؛ خذ استراحة قصيرة.")
        if recovery_attempts >= 2 and recent_losses > 0:
            warnings.append("تجنب تعويض الخسائر بسرعة؛ التزم بخطة إدارة المخاطر.")
        if not warnings:
            warnings.append("السلوك النفسي للتداول يبدو مستقرّاً حالياً.")

        if consecutive_losses >= 3:
            signal = "neutral"
            confidence = 30
        else:
            signal = "neutral"
            confidence = 60

        return {
            "agent": self.name,
            "signal": signal,
            "confidence": confidence,
            "report": " ".join(warnings),
            "flags": warnings,
            "recommendation": "استرح إذا كنت تشعر بالتوتر العالي أو التداول العاطفي.",
        }
