import statistics
from typing import Any, Dict

class RiskManagerAgent:
    def __init__(self):
        self.name = "Risk Manager Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        prefs = data.get("user_preferences", {}) or {}
        capital = float(prefs.get("account_balance") or prefs.get("capital") or 10000.0)
        risk_pct = float(prefs.get("risk_percentage") or 1.0)
        daily_limit = float(prefs.get("daily_loss_limit_amount") or (capital * 0.05))
        current_loss = float(data.get("daily_loss") or 0.0)
        stop_distance = float(data.get("expected_stop_distance") or 50.0)

        max_size = 0.0
        if stop_distance > 0:
            max_size = round((capital * risk_pct / 100.0) / stop_distance, 4)

        status = "healthy"
        if current_loss >= daily_limit:
            status = "locked"
        elif current_loss >= daily_limit * 0.8:
            status = "critical"
        elif current_loss >= daily_limit * 0.5:
            status = "warning"

        if status == "locked":
            signal = "neutral"
            confidence = 10
            report = "الحد اليومي للخسارة تم تجاوزه؛ أوقف جميع الصفقات واغلق المخاطر الآن."
        elif status == "critical":
            signal = "neutral"
            confidence = 30
            report = "وصلت إلى 80% من الحد اليومي للخسارة؛ لا تفتح صفقات جديدة."
        elif status == "warning":
            signal = "neutral"
            confidence = 45
            report = "وصلت إلى 50% من الحد اليومي للخسارة؛ راقب المخاطر عن كثب."
        else:
            reward = float(data.get("expected_reward_distance") or (stop_distance * 2))
            rr = round(reward / stop_distance if stop_distance > 0 else 0.0, 2)
            signal = "buy" if rr >= 1.5 else "neutral"
            confidence = min(100, max(40, int(rr * 30)))
            report = f"حجم العقد الموصى به هو {max_size} بناءً على رأس مال {capital} ونسبة المخاطرة {risk_pct}%. نسبة المخاطرة إلى المكافأة {rr}."

        return {
            "agent": self.name,
            "signal": signal,
            "confidence": confidence,
            "report": report,
            "position_size": max_size,
            "daily_status": status,
            "daily_loss": current_loss,
            "daily_loss_limit": daily_limit,
        }
